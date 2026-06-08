import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple, cast
from uuid import UUID, uuid4

from arthur_common.models.llm_model_providers import (
    MessageRole,
    ModelProvider,
    OpenAIMessage,
)
from arthur_common.models.task_eval_schemas import LLMEval
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from openinference.semconv.trace import SpanAttributes
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from sqlalchemy.orm import Session

from repositories.agentic_prompts_repository import AgenticPromptRepository
from repositories.continuous_evals_repository import ContinuousEvalsRepository
from repositories.datasets_repository import DatasetRepository
from repositories.llm_evals_repository import LLMEvalsRepository
from repositories.model_provider_repository import ModelProviderRepository
from repositories.trace_transform_repository import TraceTransformRepository
from schemas.agentic_prompt_schemas import AgenticPrompt
from schemas.internal_schemas import (
    ContinuousEval,
    Dataset,
    NewTraceTransformRequest,
    TraceTransform,
)
from schemas.request_schemas import (
    ContinuousEvalCreateRequest,
    ContinuousEvalTransformVariableMappingRequest,
    CreateAgenticPromptRequest,
    CreateEvalRequest,
)
from schemas.response_schemas import TraceTransformVersionResponse
from services.chatbot.chatbot_prompts import SUMMARIZE_HISTORY_PROMPT
from services.chatbot.demo_chatbot_service import DemoChatbotService
from services.prompt.chat_completion_service import ChatCompletionService
from services.trace.trace_ingestion_service import TraceIngestionService
from utils import constants
from utils.demo_task_fixtures.demo_task_resources import (
    DEMO_CHATBOT_TRACE_TO_DATASET_TRANSFORM,
    DEMO_TASK_ANSWER_RELEVANCE_EVAL_PROMPT,
    DEMO_TASK_ANSWER_RELEVANCE_EVAL_TRANSFORM,
    DEMO_TASK_DATASET_REQUEST,
    DEMO_TASK_DATASET_VERSION_REQUEST,
    DEMO_TASK_PROMPT_MESSAGES,
    DEMO_TASK_RESPONSE_EXTRACTION_TRANSFORM,
    DEMO_TASK_SOURCE_ATTRIBUTION_EVAL_PROMPT,
    DEMO_TASK_TOOLS,
)


class DemoTaskRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.continuous_evals_repo = ContinuousEvalsRepository(db_session)
        self.agentic_prompt_repo = AgenticPromptRepository(db_session)
        self.llm_evals_repo = LLMEvalsRepository(db_session)
        self.trace_transform_repo = TraceTransformRepository(db_session)
        self.dataset_repo = DatasetRepository(db_session)
        self.model_provider_repo = ModelProviderRepository(db_session)
        self.trace_ingestion_service = TraceIngestionService(db_session)
        self.chat_completion_service = ChatCompletionService()
        self.demo_prompt_name = "demo_task_prompt"
        self.demo_summarizer_prompt_name = "demo_chatbot_summarizer_prompt"

    def _get_model_provider_and_name(self) -> tuple[ModelProvider, str]:
        """
        Returns the demo task's model provider and model name.

        Prefers Anthropic, falls back to OpenAI. get_model_provider_client
        raises an 400 err when a provider is not configured, so we
        catch it to fall through to the next provider.

        Raises a 400 err if neither provider is configured.
        """
        for provider, model_name in (
            (ModelProvider.ANTHROPIC, "claude-haiku-4-5"),
            (ModelProvider.OPENAI, "gpt-5.4-nano"),
        ):
            try:
                self.model_provider_repo.get_model_provider_client(provider)
                return provider, model_name
            except HTTPException:
                continue

        raise HTTPException(
            status_code=400,
            detail="No model provider found",
        )

    def _create_transform_variable_mapping(
        self,
        transform_version: TraceTransformVersionResponse,
    ) -> List[ContinuousEvalTransformVariableMappingRequest]:
        return [
            ContinuousEvalTransformVariableMappingRequest(
                transform_variable=transform_version.definition.variables[
                    i
                ].variable_name,
                eval_variable=transform_version.definition.variables[i].variable_name,
            )
            for i in range(len(transform_version.definition.variables))
        ]

    def _create_continuous_eval(
        self,
        task_id: str,
        eval_name: str,
        eval_instructions: str,
        continuous_eval_name: str,
        continuous_eval_description: str,
        model_provider: ModelProvider,
        model_name: str,
        transform_request: Optional[NewTraceTransformRequest] = None,
        existing_transform_id: Optional[UUID] = None,
        commit: bool = True,
    ) -> Tuple[ContinuousEval, LLMEval, TraceTransform, TraceTransformVersionResponse]:
        if transform_request is None and existing_transform_id is None:
            raise ValueError(
                "Either transform_request or existing_transform_id must be provided",
            )

        llm_eval = self.llm_evals_repo.save_llm_item(
            task_id=task_id,
            item_name=eval_name,
            item=CreateEvalRequest(
                model_name=model_name,
                model_provider=model_provider,
                instructions=eval_instructions,
            ),
            commit=commit,
        )

        transform: Optional[TraceTransform] = None
        if existing_transform_id is not None:
            transform = self.trace_transform_repo.get_transform_by_id(
                existing_transform_id,
            )
            if transform is None and transform_request is None:
                raise ValueError(f"Transform with id {existing_transform_id} not found")
            elif transform_request is not None:
                transform = self.trace_transform_repo.create_transform(
                    task_id=task_id,
                    transform=transform_request,
                    commit=commit,
                )
        elif transform_request is not None:
            transform = self.trace_transform_repo.create_transform(
                task_id=task_id,
                transform=transform_request,
                commit=commit,
            )

        if transform is None:
            raise ValueError("Failed to resolve transform")

        transform_versions = self.trace_transform_repo.list_versions(
            transform_id=transform.id,
        )

        if len(transform_versions.versions) == 0:
            raise ValueError("No versions found for prompt adherence transform")

        transform_version = transform_versions.versions[0]

        continuous_eval = self.continuous_evals_repo.create_continuous_eval(
            task_id=task_id,
            continuous_eval_request=ContinuousEvalCreateRequest(
                name=continuous_eval_name,
                description=continuous_eval_description,
                llm_eval_name=eval_name,
                llm_eval_version=llm_eval.version,
                transform_id=transform.id,
                transform_version_id=transform_version.id,
                transform_variable_mapping=self._create_transform_variable_mapping(
                    transform_version,
                ),
            ),
            commit=commit,
        )

        return continuous_eval, llm_eval, transform, transform_version

    def _create_demo_prompt(
        self,
        task_id: str,
        model_provider: ModelProvider,
        model_name: str,
        commit: bool = True,
    ) -> None:
        """
        Create the demo prompt
        """
        prompt = self.agentic_prompt_repo.save_llm_item(
            task_id=task_id,
            item_name=self.demo_prompt_name,
            item=CreateAgenticPromptRequest(
                model_name=model_name,
                model_provider=model_provider,
                messages=DEMO_TASK_PROMPT_MESSAGES,
                tools=DEMO_TASK_TOOLS,
                config=None,
            ),
            commit=commit,
        )
        self.agentic_prompt_repo.add_tag_to_llm_item_version(
            task_id=task_id,
            item_name=self.demo_prompt_name,
            item_version=str(prompt.version),
            tag="production",
            commit=commit,
        )

    def _create_demo_summarizer_prompt(
        self,
        task_id: str,
        model_provider: ModelProvider,
        model_name: str,
        commit: bool = True,
    ) -> None:
        prompt = self.agentic_prompt_repo.save_llm_item(
            task_id=task_id,
            item_name=self.demo_summarizer_prompt_name,
            item=CreateAgenticPromptRequest(
                messages=[
                    OpenAIMessage(
                        role=MessageRole.SYSTEM,
                        content=SUMMARIZE_HISTORY_PROMPT,
                    ),
                    OpenAIMessage(
                        role=MessageRole.USER,
                        content="PREVIOUS CONVERSATION:\n\n{{prev_conversation}}",
                    ),
                ],
                model_name=model_name,
                model_provider=model_provider,
                tools=None,
                config=None,
            ),
            commit=commit,
        )
        self.agentic_prompt_repo.add_tag_to_llm_item_version(
            task_id=task_id,
            item_name=self.demo_summarizer_prompt_name,
            item_version=str(prompt.version),
            tag="production",
            commit=commit,
        )

    def _create_demo_dataset(self, task_id: str, commit: bool = True) -> Dataset:
        dataset = Dataset._from_request_model(task_id, DEMO_TASK_DATASET_REQUEST)
        self.dataset_repo.create_dataset(dataset, commit=commit)
        self.dataset_repo.create_dataset_version(
            dataset_id=dataset.id,
            dataset_version=DEMO_TASK_DATASET_VERSION_REQUEST,
            commit=commit,
        )
        return dataset

    def _replay_demo_traces(
        self,
        task_id: str,
        user_id: str,
        commit: bool = True,
    ) -> None:
        fixtures_dir = (
            Path(__file__).resolve().parent.parent / "utils" / "demo_task_fixtures"
        )
        fixture_paths = sorted(fixtures_dir.glob("*.binpb"))
        if not fixture_paths:
            return

        all_spans = []
        for fixture_path in fixture_paths:
            request = ExportTraceServiceRequest()
            request.ParseFromString(fixture_path.read_bytes())

            for resource_span in request.resource_spans:
                for attr in resource_span.resource.attributes:
                    if attr.key == constants.TASK_ID_KEY:
                        attr.value.string_value = task_id

                new_trace_id = os.urandom(16)
                new_session_id = f"demo-session-{uuid4()}"
                span_id_map: dict[bytes, bytes] = {}
                max_end_ns = 0
                for scope_span in resource_span.scope_spans:
                    for span in scope_span.spans:
                        span_id_map[span.span_id] = os.urandom(8)
                        if span.end_time_unix_nano > max_end_ns:
                            max_end_ns = span.end_time_unix_nano

                now_ns = int(datetime.now(timezone.utc).timestamp() * 1e9)
                shift_ns = now_ns - max_end_ns if max_end_ns else 0

                for scope_span in resource_span.scope_spans:
                    for span in scope_span.spans:
                        span.trace_id = new_trace_id
                        span.span_id = span_id_map[span.span_id]
                        if span.parent_span_id:
                            span.parent_span_id = span_id_map.get(
                                span.parent_span_id,
                                span.parent_span_id,
                            )
                        span.start_time_unix_nano += shift_ns
                        span.end_time_unix_nano += shift_ns
                        for attr in span.attributes:
                            if attr.key == SpanAttributes.USER_ID:
                                attr.value.string_value = user_id
                            elif attr.key == SpanAttributes.SESSION_ID:
                                attr.value.string_value = new_session_id

            db_spans, _ = self.trace_ingestion_service.process_trace_data(
                request.SerializeToString(),
                commit=commit,
            )
            all_spans.extend(db_spans)

        if all_spans:
            self.continuous_evals_repo.enqueue_continuous_evals_for_root_spans(
                all_spans,
                commit=commit,
            )

    def create_demo_items_for_task(
        self,
        task_id: str,
        user_id: str,
        commit: bool = True,
    ) -> None:
        model_provider, model_name = self._get_model_provider_and_name()

        # Create demo prompt
        self._create_demo_prompt(
            task_id=task_id,
            model_provider=model_provider,
            model_name=model_name,
            commit=commit,
        )

        # Create demo summarizer prompt
        self._create_demo_summarizer_prompt(
            task_id=task_id,
            model_provider=model_provider,
            model_name=model_name,
            commit=commit,
        )

        # Create demo continuous evals
        self._create_continuous_eval(
            task_id=task_id,
            eval_name="Answer Relevance Eval",
            eval_instructions=DEMO_TASK_ANSWER_RELEVANCE_EVAL_PROMPT,
            continuous_eval_name="Answer Relevance Continuous Eval",
            continuous_eval_description="Evaluates if the assistant's response is relevant to the user's input.",
            model_provider=model_provider,
            model_name=model_name,
            transform_request=DEMO_TASK_ANSWER_RELEVANCE_EVAL_TRANSFORM,
            commit=commit,
        )

        self._create_continuous_eval(
            task_id=task_id,
            eval_name="Source Attribution Eval",
            eval_instructions=DEMO_TASK_SOURCE_ATTRIBUTION_EVAL_PROMPT,
            continuous_eval_name="Source Attribution Continuous Eval",
            continuous_eval_description="Evaluates if the AI cites its sources.",
            model_provider=model_provider,
            model_name=model_name,
            transform_request=DEMO_TASK_RESPONSE_EXTRACTION_TRANSFORM,
            commit=commit,
        )

        self.trace_transform_repo.create_transform(
            task_id=task_id,
            transform=DEMO_CHATBOT_TRACE_TO_DATASET_TRANSFORM,
            commit=commit,
        )

        # Create demo dataset
        self._create_demo_dataset(task_id=task_id, commit=commit)

        # Replay demo traces
        self._replay_demo_traces(task_id=task_id, user_id=user_id, commit=commit)

    def stream_response(
        self,
        task_id: str,
        history: List[OpenAIMessage],
        user_id: str,
        session_id: Optional[str] = None,
    ) -> StreamingResponse:
        chatbot_prompt = cast(
            AgenticPrompt,
            self.agentic_prompt_repo.get_llm_item_by_tag(
                task_id=task_id,
                item_name=self.demo_prompt_name,
                tag="production",
            ),
        )

        model_provider = chatbot_prompt.require_configured_provider()
        model_name = chatbot_prompt.model_name
        llm_client = self.model_provider_repo.get_model_provider_client(model_provider)

        summarizer_prompt = cast(
            AgenticPrompt,
            self.agentic_prompt_repo.get_llm_item_by_tag(
                task_id=task_id,
                item_name="demo_chatbot_summarizer_prompt",
                tag="production",
            ),
        )

        chatbot_service = DemoChatbotService(
            chat_completion_service=ChatCompletionService(),
            db_session=self.db_session,
            summarizer_prompt=summarizer_prompt,
            task_id=task_id,
        )

        # Remove the non-system messages from the chatbot prompt to use the real agentic loop
        chatbot_prompt.messages = [
            message
            for message in chatbot_prompt.messages
            if message.role == MessageRole.SYSTEM.value  # type: ignore[comparison-overlap]
        ]

        prompt = chatbot_service.build_prompt(
            chatbot_prompt=chatbot_prompt,
            model_provider=model_provider,
            model_name=model_name,
            history=history,
        )

        return StreamingResponse(
            chatbot_service.safe_stream(prompt, llm_client, user_id, session_id),
            media_type="text/event-stream",
        )
