import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, List, Optional, Tuple

import litellm
from arthur_common.models.common_schemas import VariableTemplateValue
from arthur_common.models.llm_model_providers import (
    MessageRole,
    OpenAIMessage,
    ToolCall,
    ToolCallFunction,
)
from sqlalchemy.orm import Session

from clients.llm.llm_client import LLMClient
from schemas.agentic_prompt_schemas import AgenticPrompt
from schemas.enums import SSEEventType
from schemas.request_schemas import PromptCompletionRequest
from schemas.response_schemas import AgenticPromptRunResponse
from services.prompt.chat_completion_service import ChatCompletionService
from services.trace.internal_trace_service import InternalTraceService, TraceSpanBuilder
from utils import constants
from utils.sse_events import format_sse, format_sse_error, format_sse_json
from utils.utils import get_env_var

logger = logging.getLogger(__name__)


MAX_ITERATIONS = int(
    get_env_var(constants.GENAI_ENGINE_CHATBOT_MAX_ITERATIONS_ENV_VAR, True) or 30,
)


class BaseChatbotService(ABC):
    def __init__(
        self,
        chat_completion_service: ChatCompletionService,
        db_session: Session,
        summarizer_prompt: AgenticPrompt,
        task_id: str,
        enqueue_continuous_evals: bool = False,
    ):
        self.chat_completion_service = chat_completion_service
        self.summarizer_prompt = summarizer_prompt
        self.tracing = InternalTraceService(
            db_session,
            task_id=task_id,
            service_name=self.service_name,
            enqueue_continuous_evals=enqueue_continuous_evals,
        )

    @property
    @abstractmethod
    def service_name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def agent_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def execute_tool(
        self,
        tool_call: ToolCall,
        agent_span: TraceSpanBuilder,
    ) -> AsyncGenerator[Tuple[Optional[str], Optional[OpenAIMessage]], None]:
        raise NotImplementedError

    def build_variable_map(self, prompt: AgenticPrompt) -> Dict[str, str]:
        """Hook for subclasses to supply per-request prompt variables."""
        return {}

    def summarize_history(
        self,
        messages: List[OpenAIMessage],
        llm_client: LLMClient,
    ) -> List[OpenAIMessage]:
        system_msg = next(m for m in messages if m.role == MessageRole.SYSTEM.value)  # type: ignore[comparison-overlap]
        non_system = [m for m in messages if m.role != MessageRole.SYSTEM.value]  # type: ignore[comparison-overlap]

        keep_count = len(non_system) // 2
        to_summarize = non_system[:-keep_count]
        to_keep = non_system[-keep_count:]

        summary_input = json.dumps(
            [m.model_dump(exclude_none=True) for m in to_summarize],
        )

        response = self.chat_completion_service.run_chat_completion(
            self.summarizer_prompt,
            llm_client,
            PromptCompletionRequest(
                variables=[
                    VariableTemplateValue(
                        name="prev_conversation",
                        value=summary_input,
                    ),
                ],
            ),
        )

        return [
            system_msg,
            OpenAIMessage(
                role=MessageRole.AI,
                content=f"Summary of previous conversation:\n{response.content}",
            ),
            *to_keep,
        ]

    async def summarize_and_emit_replace(
        self,
        messages: List[OpenAIMessage],
        llm_client: LLMClient,
        model_name: str,
    ) -> AsyncGenerator[str, None]:
        # Get the context window size for the specified model
        max_tokens = litellm.get_max_tokens(model_name)

        # Count the tokens in the messages using the provider's api
        token_response = await llm_client.acount_tokens(
            model=model_name,
            messages=[m.model_dump(exclude_none=True) for m in messages],
        )

        # If the total tokens are less than the context window size, don't summarize
        if max_tokens is None or token_response.total_tokens <= max_tokens:
            return

        # Summarize the history
        summarized_history = await asyncio.to_thread(
            self.summarize_history,
            messages,
            llm_client,
        )

        # Emit the summarized history
        yield format_sse_json(
            SSEEventType.HISTORY_REPLACE,
            {
                "history": [
                    m.model_dump(exclude_none=True)
                    for m in summarized_history
                    if m.role != MessageRole.SYSTEM.value  # type: ignore[comparison-overlap]
                ],
            },
        )

    async def stream(
        self,
        prompt: AgenticPrompt,
        llm_client: LLMClient,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        current_prompt = prompt
        agent_span = self.tracing.start_agent_span(
            name="chatbot",
            agent_name=self.agent_name,
            user_id=user_id,
            session_id=session_id,
        )

        self.tracing.set_input_json(
            agent_span,
            [
                {"role": m.role, "content": m.content or ""}
                for m in current_prompt.messages
            ],
        )

        variable_map = self.build_variable_map(current_prompt)
        if variable_map:
            template_snapshot = [
                m.model_copy(deep=True) for m in current_prompt.messages
            ]
            prompt_span = self.tracing.start_prompt_span(
                agent_span,
                prompt_name=current_prompt.name,
            )
            self.tracing.set_prompt_template(
                prompt_span,
                template_snapshot,
                variable_map,
                version=current_prompt.version,
            )
            self.chat_completion_service.replace_variables(
                variable_map,
                current_prompt.messages,
            )
            self.tracing.set_prompt_rendered(prompt_span, current_prompt.messages)
            self.tracing.end_span(prompt_span)

        for _ in range(MAX_ITERATIONS):
            final_response: AgenticPromptRunResponse | None = None

            llm_span = self.tracing.start_llm_span(
                agent_span,
                current_prompt.model_name,
                current_prompt.model_provider,
            )
            self.tracing.set_llm_input_messages(llm_span, current_prompt.messages)

            async for event in self.chat_completion_service.stream_chat_completion(
                current_prompt,
                llm_client,
                PromptCompletionRequest(stream=True, strict=False),
            ):
                if event.startswith(f"event: {SSEEventType.FINAL_RESPONSE.value}"):
                    data = event.split("data: ", 1)[1].strip()
                    final_response = AgenticPromptRunResponse.model_validate_json(data)
                elif event.startswith(f"event: {SSEEventType.ERROR.value}"):
                    self.tracing.end_span_with_error(llm_span, event)
                    self.tracing.end_span_with_error(agent_span, event)
                    self.tracing.flush()
                    yield event
                    return
                else:
                    yield event

            if final_response is None:
                self.tracing.end_span(llm_span)
                self.tracing.end_span(agent_span)
                self.tracing.flush()
                return

            tool_calls = (
                [
                    ToolCall(
                        id=tc.id,
                        type="function",
                        function=ToolCallFunction(
                            name=tc.function.name or "",
                            arguments=tc.function.arguments or "{}",
                        ),
                    )
                    for tc in final_response.tool_calls
                ]
                if final_response.tool_calls
                else []
            )

            self.tracing.set_llm_response(
                llm_span,
                content=final_response.content,
                tool_calls=tool_calls or None,
                input_tokens=final_response.input_tokens,
                output_tokens=final_response.output_tokens,
                total_tokens=final_response.total_tokens,
            )
            self.tracing.end_span(llm_span)

            if not tool_calls:
                current_prompt.messages.append(
                    OpenAIMessage(role=MessageRole.AI, content=final_response.content),
                )
                self.tracing.set_output_json(
                    agent_span,
                    {"text": final_response.content or ""},
                )
                self.tracing.end_span(agent_span)
                self.tracing.flush()
                yield format_sse(
                    SSEEventType.FINAL_RESPONSE,
                    final_response.model_dump_json(),
                )

                async for event in self.summarize_and_emit_replace(
                    current_prompt.messages,
                    llm_client,
                    current_prompt.model_name,
                ):
                    yield event
                return

            assistant_msg = OpenAIMessage(
                role=MessageRole.AI,
                content=final_response.content,
                tool_calls=tool_calls,
            )
            new_messages = list(current_prompt.messages) + [assistant_msg]

            for tool_call in tool_calls:
                async for sse_event, tool_message in self.execute_tool(
                    tool_call,
                    agent_span,
                ):
                    if sse_event is not None:
                        yield sse_event
                    if tool_message is not None:
                        new_messages.append(tool_message)

            current_prompt = AgenticPrompt(
                name=current_prompt.name,
                messages=new_messages,
                model_name=current_prompt.model_name,
                model_provider=current_prompt.model_provider,
                tools=current_prompt.tools,
                config=current_prompt.config,
                created_at=current_prompt.created_at,
            )

        logger.warning(
            "Chatbot hit MAX_ITERATIONS (%d) for user=%s",
            MAX_ITERATIONS,
            user_id,
        )
        error_msg = "I'm sorry, I wasn't able to complete your request within the allowed number of steps. Please try simplifying your question."
        current_prompt.messages.append(
            OpenAIMessage(role=MessageRole.AI, content=error_msg),
        )
        self.tracing.set_output_json(agent_span, {"text": error_msg})
        self.tracing.end_span(agent_span)
        self.tracing.flush()
        yield format_sse_error(error_msg)

        async for event in self.summarize_and_emit_replace(
            current_prompt.messages,
            llm_client,
            current_prompt.model_name,
        ):
            yield event

    async def safe_stream(
        self,
        prompt: AgenticPrompt,
        llm_client: LLMClient,
        user_id: str,
        session_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        try:
            async for event in self.stream(prompt, llm_client, user_id, session_id):
                yield event
        except Exception as e:
            logger.exception(
                "Chatbot stream failed for user_id=%s",
                user_id,
            )
            yield format_sse_error(f"Failed to stream chatbot response: {e}")
