import copy
import json
import logging
import uuid
from typing import List, Optional, Type, cast

from arthur_common.models.llm_model_providers import (
    LLMConfigSettings,
    LLMResponseFormat,
    LLMResponseFormatEnum,
)
from fastapi import HTTPException
from litellm import supports_response_schema
from openinference.semconv.trace import SpanAttributes
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool
from starlette.responses import StreamingResponse
from starlette.status import HTTP_400_BAD_REQUEST

from clients.llm.llm_client import LLMClient
from db_models.agentic_prompt_models import (
    DatabaseAgenticPrompt,
    DatabaseAgenticPromptVersionTag,
)
from db_models.telemetry_models import DatabaseSpan
from repositories.base_llm_repository import BaseLLMRepository
from repositories.model_provider_repository import ModelProviderRepository
from schemas.agentic_prompt_schemas import AgenticPrompt
from schemas.request_schemas import (
    CompletionRequest,
    CreateAgenticPromptRequest,
    PromptCompletionRequest,
    VariableRenderingRequest,
)
from schemas.response_schemas import (
    AgenticPromptRunResponse,
    AgenticPromptVersionListResponse,
    AgenticPromptVersionResponse,
)
from services.prompt.chat_completion_service import ChatCompletionService
from services.trace.internal_trace_service import (
    InternalTraceService,
    TraceSpanBuilder,
)
from utils.constants import ARTHUR_SYSTEM_TASK_ID, EMPTY_MODEL_PROVIDER
from utils.trace import timestamp_ns_to_datetime

logger = logging.getLogger(__name__)

# Derives one trace id per session id, so a session's runs share a trace.
_SESSION_TRACE_NAMESPACE = uuid.UUID("5f0e5d3a-2b8a-4f63-9a51-6c8d0e7f4b21")


def session_trace_id(session_id: str) -> bytes:
    """The trace that a session's system-task prompt runs are recorded in."""
    return uuid.uuid5(_SESSION_TRACE_NAMESPACE, session_id).bytes


def session_root_span_id(session_id: str) -> bytes:
    """The span a session's system-task prompt runs are recorded under, as the
    chatbot's calls are under its agent span."""
    return uuid.uuid5(_SESSION_TRACE_NAMESPACE, f"root:{session_id}").bytes[:8]


class AgenticPromptRepository(
    BaseLLMRepository[
        DatabaseAgenticPrompt,  # type: ignore[type-var]
        DatabaseAgenticPromptVersionTag,
        CreateAgenticPromptRequest,
    ],
):
    db_model: Type[DatabaseAgenticPrompt] = DatabaseAgenticPrompt
    tag_db_model: Type[DatabaseAgenticPromptVersionTag] = (
        DatabaseAgenticPromptVersionTag
    )
    version_list_response_model: Type[BaseModel] = AgenticPromptVersionListResponse

    def __init__(self, db_session: Session):
        super().__init__(db_session)
        self.model_provider_repo = ModelProviderRepository(db_session)

    def from_db_model(self, db_prompt: DatabaseAgenticPrompt) -> AgenticPrompt:
        # Added the type override to avoid type error when overriding the method from the base class
        tags = self._get_all_tags_for_item_version(db_prompt)

        return AgenticPrompt(
            name=db_prompt.name,
            messages=db_prompt.messages,
            model_name=db_prompt.model_name,
            model_provider=db_prompt.model_provider,
            version=db_prompt.version,
            tools=db_prompt.tools,
            variables=db_prompt.variables,
            tags=tags or [],
            config=db_prompt.config,
            created_at=db_prompt.created_at,
            deleted_at=db_prompt.deleted_at,
        )

    def _extract_variables_from_item(
        self,
        item: CreateAgenticPromptRequest,
    ) -> List[str]:
        return list(
            self.chat_completion_service.find_missing_variables_in_messages(
                variable_map={},
                messages=item.messages,
            ),
        )

    def _to_versions_reponse_item(
        self,
        db_item: DatabaseAgenticPrompt,
    ) -> AgenticPromptVersionResponse:
        num_messages = len(db_item.messages or [])
        num_tools = len(db_item.tools or [])
        tags = self._get_all_tags_for_item_version(db_item)

        return AgenticPromptVersionResponse(
            version=db_item.version,
            created_at=db_item.created_at,
            deleted_at=db_item.deleted_at,
            model_provider=db_item.model_provider,
            model_name=db_item.model_name,
            num_messages=num_messages,
            num_tools=num_tools,
            tags=tags or [],
        )

    def _clear_db_item_data(self, db_item: DatabaseAgenticPrompt) -> None:
        db_item.model_name = ""
        db_item.messages = []
        db_item.tools = None
        db_item.config = None

    def save_llm_item(
        self,
        task_id: str,
        item_name: str,
        item: CreateAgenticPromptRequest,
        commit: bool = True,
    ) -> AgenticPrompt:
        if item.model_name == "":
            raise ValueError("Model name cannot be empty.")
        return cast(
            AgenticPrompt,
            super().save_llm_item(task_id, item_name, item, commit=commit),
        )

    async def run_unsaved_prompt(
        self,
        unsaved_prompt: CompletionRequest,
        org_id: uuid.UUID,
    ) -> AgenticPromptRunResponse | StreamingResponse:
        llm_client = self.model_provider_repo.get_model_provider_client(
            provider=unsaved_prompt.model_provider,
        )
        prompt, completion_request = ChatCompletionService.to_prompt_and_request(
            unsaved_prompt,
        )
        return await self.chat_completion_service.execute_prompt_completion(
            llm_client,
            prompt,
            completion_request,
            org_id=org_id,
        )

    async def run_saved_prompt(
        self,
        task_id: str,
        prompt_name: str,
        prompt_version: str,
        completion_request: PromptCompletionRequest,
        org_id: uuid.UUID,
        session_id: Optional[str] = None,
    ) -> AgenticPromptRunResponse | StreamingResponse:
        """Run a saved prompt. A non-streaming run of a prompt in the Arthur system
        task, which Arthur's own features call, is recorded there as an LLM span, as
        the chatbot's calls are; `session_id` puts a caller's runs in one session and
        one trace."""
        prompt = self._with_resolved_model(
            self.get_llm_item(
                task_id,
                prompt_name,
                prompt_version,
            ),
        )
        llm_client = self.model_provider_repo.get_model_provider_client(
            provider=prompt.require_configured_provider(),
        )
        if task_id == ARTHUR_SYSTEM_TASK_ID and not completion_request.stream:
            # The model call blocks, so it runs in a worker thread: on the event loop it
            # would hold every other request, and a caller's parallel calls would run
            # one after another.
            return await run_in_threadpool(
                self._run_recorded,
                prompt,
                llm_client,
                completion_request,
                org_id,
                session_id,
            )
        return await self.chat_completion_service.execute_prompt_completion(
            llm_client,
            prompt,
            completion_request,
            org_id=org_id,
        )

    def _run_recorded(
        self,
        prompt: AgenticPrompt,
        llm_client: LLMClient,
        completion_request: PromptCompletionRequest,
        org_id: uuid.UUID,
        session_id: Optional[str],
    ) -> AgenticPromptRunResponse:
        """Run the prompt and record the call as an LLM span in the system task.

        The span holds the prompt's name and version, the model, the tokens, the cost,
        the latency (its start and end) and, for a failed call, the error's type. Not the
        messages or the reply: what a feature sends can be another task's traces.
        Recording never fails the run.
        """
        tracer = InternalTraceService(
            self.db_session,
            task_id=ARTHUR_SYSTEM_TASK_ID,
            service_name="system task prompt",
            trace_id=session_trace_id(session_id) if session_id else None,
        )
        root_span_id = (
            self._open_session_root(tracer, session_id) if session_id else None
        )
        span = tracer.start_llm_span(
            None,
            model_name=prompt.model_name,
            model_provider=str(prompt.model_provider),
        )
        if root_span_id is not None:
            span.parent_span_id = root_span_id
        span.name = prompt.name
        span.set_attribute(SpanAttributes.LLM_PROMPT_TEMPLATE_VERSION, prompt.version)
        span.set_attribute(
            SpanAttributes.METADATA,
            json.dumps({"prompt_name": prompt.name, "prompt_version": prompt.version}),
        )
        if session_id:
            span.set_attribute(SpanAttributes.SESSION_ID, session_id)
        try:
            response = self.chat_completion_service.run_chat_completion(
                prompt,
                llm_client,
                completion_request,
                org_id=org_id,
            )
        except Exception as e:
            status = f" {e.status_code}" if isinstance(e, HTTPException) else ""
            tracer.end_span_with_error(span, f"{type(e).__name__}{status}")
            tracer.flush()
            self._extend_session_root(tracer, root_span_id, span)
            raise
        for attribute, tokens in (
            (SpanAttributes.LLM_TOKEN_COUNT_PROMPT, response.input_tokens),
            (SpanAttributes.LLM_TOKEN_COUNT_COMPLETION, response.output_tokens),
            (SpanAttributes.LLM_TOKEN_COUNT_TOTAL, response.total_tokens),
        ):
            if tokens is not None:
                span.set_attribute(attribute, tokens)
        try:
            span.set_attribute(SpanAttributes.LLM_COST_TOTAL, float(response.cost))
        except (TypeError, ValueError):
            pass
        tracer.end_span(span)
        tracer.flush()
        self._extend_session_root(tracer, root_span_id, span)
        return response

    def _session_root(
        self,
        tracer: InternalTraceService,
        root_span_id: bytes,
    ) -> Optional[DatabaseSpan]:
        return (
            self.db_session.query(DatabaseSpan)
            .filter(
                DatabaseSpan.task_id == ARTHUR_SYSTEM_TASK_ID,
                DatabaseSpan.trace_id == tracer.trace_id.hex(),
                DatabaseSpan.span_id == root_span_id.hex(),
            )
            .first()
        )

    def _open_session_root(
        self,
        tracer: InternalTraceService,
        session_id: str,
    ) -> bytes:
        """The session's root span id, adding the AGENT root span to this flush when it
        is the session's first run. It is named for the caller, the part of the session
        id before ":" (`onboarding_analysis:<job id>` gives `onboarding_analysis`).

        Two first runs of one session at the same moment would each add one: callers
        send a session's first run alone (the onboarding job does).
        """
        root_span_id = session_root_span_id(session_id)
        if self._session_root(tracer, root_span_id) is None:
            caller = session_id.split(":", 1)[0] or "system task prompts"
            root = tracer.start_agent_span(
                name=caller,
                agent_name=caller,
                session_id=session_id,
            )
            root.span_id = root_span_id
            tracer.end_span(root)
        return root_span_id

    def _extend_session_root(
        self,
        tracer: InternalTraceService,
        root_span_id: Optional[bytes],
        span: TraceSpanBuilder,
    ) -> None:
        """Stretch the session's root span to end with its latest run. Never fails the run."""
        if root_span_id is None or span.end_time is None:
            return
        try:
            end_ns = int(span.end_time.timestamp() * 1e9)
            end_time = timestamp_ns_to_datetime(end_ns)
            root = self._session_root(tracer, root_span_id)
            if root is None or root.end_time >= end_time:
                return
            root.end_time = end_time
            root.raw_data = {**root.raw_data, "endTimeUnixNano": str(end_ns)}
            self.db_session.commit()
        except Exception:
            logger.exception("Failed to extend the session's root span")
            self.db_session.rollback()

    def _with_resolved_model(self, prompt: AgenticPrompt) -> AgenticPrompt:
        """The prompt with the model it runs on. A prompt saved with the 'empty'
        placeholder runs on the instance's default model provider, with that provider's
        reasoning defaults where the model takes them, as an eval would; one that names
        its model keeps it, and its own settings."""
        if prompt.model_provider != EMPTY_MODEL_PROVIDER:
            return prompt
        provider, model_name = self.model_provider_repo.resolve_model(None, None)
        response_format = prompt.config.response_format if prompt.config else None
        # The prompt's author could not see which model would answer, so a schema
        # it asks for is checked here rather than left to fail inside the provider.
        if (
            isinstance(response_format, LLMResponseFormat)
            and response_format.type == LLMResponseFormatEnum.JSON_SCHEMA
            and not supports_response_schema(
                model=model_name,
                custom_llm_provider=provider.value,
            )
        ):
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=(
                    f"Prompt '{prompt.name}' needs structured output, which the "
                    f"default model {model_name} ({provider.value}) does not support. "
                    "Choose a default model that does on the Model Providers page."
                ),
            )
        # The prompt's author could not pick reasoning settings for an unknown model, so
        # the provider's defaults fill them, only for a model that accepts them.
        config = prompt.config.model_dump(exclude_none=True) if prompt.config else {}
        self.model_provider_repo.apply_eval_defaults(provider, model_name, config)
        return prompt.model_copy(
            update={
                "model_provider": provider.value,
                "model_name": model_name,
                "config": LLMConfigSettings(**config) if config else None,
            },
        )

    def render_saved_prompt(
        self,
        task_id: str,
        prompt_name: str,
        prompt_version: str,
        render_request: VariableRenderingRequest,
    ) -> AgenticPrompt:
        """
        Render a saved prompt by replacing template variables with provided values.

        Args:
            task_id: The task ID
            prompt_name: The name of the prompt
            prompt_version: The version identifier ('latest', version number, or ISO datetime)
            render_request: VariableRenderingRequest containing variables for template substitution

        Returns:
            AgenticPrompt with rendered messages

        Raises:
            ValueError: If prompt not found or required variables are missing
            jinja2.exceptions.TemplateSyntaxError: If template syntax is invalid
            jinja2.exceptions.UndefinedError: If required variables are not provided
        """
        # Get the prompt from the database
        prompt = self.get_llm_item(
            task_id,
            prompt_name,
            prompt_version,
        )

        # Build variable map from the request
        variable_map = render_request._variable_map if render_request.variables else {}

        # Check for missing variables if strict mode is enabled
        if render_request.strict:
            missing_vars = (
                self.chat_completion_service.find_missing_variables_in_messages(
                    variable_map,
                    prompt.messages,
                )
            )
            if missing_vars:
                raise ValueError(
                    f"Missing values for the following variables: {', '.join(sorted(missing_vars))}",
                )

        # Create a copy of messages and render them
        rendered_messages = copy.deepcopy(prompt.messages)
        rendered_messages = self.chat_completion_service.replace_variables(
            variable_map,
            rendered_messages,
        )

        # Return a new AgenticPrompt with rendered messages
        return AgenticPrompt(
            name=prompt.name,
            messages=rendered_messages,
            model_name=prompt.model_name,
            model_provider=prompt.model_provider,
            version=prompt.version,
            tools=prompt.tools,
            variables=prompt.variables,
            tags=prompt.tags,
            config=prompt.config,
            created_at=prompt.created_at,
            deleted_at=prompt.deleted_at,
        )

    def get_llm_item(
        self,
        task_id: str,
        item_name: str,
        item_version: str = "latest",
    ) -> AgenticPrompt:
        return cast(
            AgenticPrompt,
            super().get_llm_item(task_id, item_name, item_version),
        )
