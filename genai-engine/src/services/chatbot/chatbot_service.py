import asyncio
import json
import logging
from typing import AsyncGenerator, List, MutableMapping, Optional, Tuple

from arthur_common.models.common_schemas import VariableTemplateValue
from arthur_common.models.llm_model_providers import (
    MessageRole,
    ModelProvider,
    OpenAIMessage,
    ToolCall,
    ToolCallFunction,
)
from cachetools import TTLCache
from sqlalchemy.orm import Session

from clients.llm.llm_client import LLMClient
from schemas.agentic_prompt_schemas import AgenticPrompt
from schemas.chatbot_schemas import (
    ApiCallSummary,
    CallArthurApiArgs,
    SearchArthurApiArgs,
)
from schemas.enums import SSEEventType
from schemas.request_schemas import PromptCompletionRequest
from schemas.response_schemas import AgenticPromptRunResponse
from services.chatbot.api_call_service import ApiCallService
from services.prompt.chat_completion_service import ChatCompletionService
from services.trace.internal_trace_service import InternalTraceService
from utils import constants
from utils.llm_tool_functions import search_api_index
from utils.sse_events import format_sse, format_sse_error, format_sse_json
from utils.utils import get_env_var

logger = logging.getLogger(__name__)


MAX_ITERATIONS = int(
    get_env_var(constants.GENAI_ENGINE_CHATBOT_MAX_ITERATIONS_ENV_VAR, True) or 30,
)
MAX_HISTORY_SIZE = int(
    get_env_var(constants.GENAI_ENGINE_CHATBOT_MAX_HISTORY_SIZE_ENV_VAR, True) or 15,
)

CONVERSATION_HISTORIES: MutableMapping[Tuple[str, str], List[OpenAIMessage]] = TTLCache(
    maxsize=1000,
    ttl=3600,
)


def get_conversation_history(user_id: str, conversation_id: str) -> List[OpenAIMessage]:
    return CONVERSATION_HISTORIES.get((user_id, conversation_id), [])


def clear_conversation_history(user_id: str, conversation_id: str) -> None:
    CONVERSATION_HISTORIES.pop((user_id, conversation_id), None)


class ChatbotService:
    def __init__(
        self,
        chat_completion_service: ChatCompletionService,
        api_call_service: ApiCallService,
        api_index: List[str],
        db_session: Session,
        summarizer_prompt: AgenticPrompt,
    ):
        self.chat_completion_service = chat_completion_service
        self.api_call_service = api_call_service
        self.api_index = api_index
        self.tracing = InternalTraceService(
            db_session,
            task_id=constants.ARTHUR_SYSTEM_TASK_ID,
            service_name="chatbot",
        )
        self.summarizer_prompt = summarizer_prompt

    def build_prompt(
        self,
        chatbot_prompt: AgenticPrompt,
        model_provider: ModelProvider,
        model_name: str,
        task_id: str,
        history: List[OpenAIMessage],
        user_message: str,
        blacklist: Optional[List[str]] = None,
    ) -> AgenticPrompt:
        chatbot_prompt.model_provider = model_provider
        chatbot_prompt.model_name = model_name

        if history:
            # History already contains the rendered system prompt from the first turn
            messages = list(history)
        else:
            # First turn: render variables into the system prompt and use it
            blacklist_str = "\n".join(blacklist) if blacklist else "None"
            self.chat_completion_service.replace_variables(
                {"task_id": task_id, "endpoint_blacklist": blacklist_str},
                chatbot_prompt.messages,
            )
            messages = chatbot_prompt.messages

        messages.append(OpenAIMessage(role=MessageRole.USER, content=user_message))
        chatbot_prompt.messages = messages
        return chatbot_prompt

    def _summarize_history(
        self,
        messages: List[OpenAIMessage],
        llm_client: LLMClient,
    ) -> List[OpenAIMessage]:
        if len(messages) <= MAX_HISTORY_SIZE:
            return messages

        system_msg = next(m for m in messages if m.role == MessageRole.SYSTEM.value)  # type: ignore[comparison-overlap]
        non_system = [m for m in messages if m.role != MessageRole.SYSTEM.value]  # type: ignore[comparison-overlap]

        keep_count = MAX_HISTORY_SIZE // 2
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

    async def stream(
        self,
        prompt: AgenticPrompt,
        llm_client: LLMClient,
        user_id: str,
        conversation_id: str,
    ) -> AsyncGenerator[str, None]:
        api_calls_made: List[ApiCallSummary] = []
        current_prompt = prompt
        agent_span = self.tracing.start_agent_span(
            name="chatbot",
            agent_name="arthur_chatbot",
            user_id=user_id,
            session_id=conversation_id,
        )

        self.tracing.set_input_json(
            agent_span,
            [
                {"role": m.role, "content": m.content or ""}
                for m in current_prompt.messages
            ],
        )

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

                summarized_history = await asyncio.to_thread(
                    self._summarize_history,
                    current_prompt.messages,
                    llm_client,
                )
                CONVERSATION_HISTORIES[(user_id, conversation_id)] = summarized_history
                return
            assistant_msg = OpenAIMessage(
                role=MessageRole.AI,
                content=final_response.content,
                tool_calls=tool_calls,
            )
            new_messages = list(current_prompt.messages) + [assistant_msg]

            for tool_call in tool_calls:
                tool_call_id = tool_call.id
                args_str = tool_call.function.arguments or "{}"

                if tool_call.function.name == "search_arthur_api":
                    search_args = SearchArthurApiArgs.model_validate_json(args_str)
                    tool_span = self.tracing.start_tool_span(
                        agent_span,
                        "search_arthur_api",
                    )
                    self.tracing.set_tool_input(tool_span, search_args.query)
                    search_result = search_api_index(self.api_index, search_args.query)
                    self.tracing.set_tool_output(tool_span, search_result)
                    self.tracing.end_span(tool_span)
                    new_messages.append(
                        OpenAIMessage(
                            role=MessageRole.TOOL,
                            content=search_result,
                            tool_call_id=tool_call_id,
                        ),
                    )
                    # Signal the frontend to start a new message bubble — search is internal
                    # but the LLM's next response should be in a fresh bubble
                    yield format_sse_json(SSEEventType.SEARCH_COMPLETE, {})
                    continue
                elif tool_call.function.name == "call_arthur_api":
                    call_args = CallArthurApiArgs.model_validate_json(args_str)
                    tool_span = self.tracing.start_tool_span(
                        agent_span,
                        "call_arthur_api",
                    )
                    self.tracing.set_tool_input(
                        tool_span,
                        json.dumps(
                            {
                                "method": call_args.method,
                                "path": call_args.path,
                                "query_params": call_args.query_params,
                                "body": call_args.body,
                            },
                        ),
                    )

                    yield format_sse_json(
                        SSEEventType.TOOL_CALL,
                        {"method": call_args.method, "path": call_args.path},
                    )

                    result = await self.api_call_service.call(
                        call_args.method,
                        call_args.path,
                        call_args.query_params,
                        call_args.body,
                    )
                    api_calls_made.append(
                        ApiCallSummary(
                            method=call_args.method,
                            path=call_args.path,
                            status_code=result.status_code,
                        ),
                    )

                    self.tracing.set_tool_output(
                        tool_span,
                        result.to_tool_result_content(),
                    )
                    self.tracing.end_span(tool_span)

                    yield format_sse_json(
                        SSEEventType.TOOL_RESULT,
                        {
                            "method": call_args.method,
                            "path": call_args.path,
                            "status_code": result.status_code,
                        },
                    )

                    new_messages.append(
                        OpenAIMessage(
                            role=MessageRole.TOOL,
                            content=result.to_tool_result_content(),
                            tool_call_id=tool_call_id,
                        ),
                    )
                else:
                    new_messages.append(
                        OpenAIMessage(
                            role=MessageRole.TOOL,
                            content=f"Unknown tool: {tool_call.function.name}",
                            tool_call_id=tool_call_id,
                        ),
                    )

            current_prompt = AgenticPrompt(
                name=current_prompt.name,
                messages=new_messages,
                model_name=current_prompt.model_name,
                model_provider=current_prompt.model_provider,
                tools=current_prompt.tools,
                config=current_prompt.config,
                created_at=current_prompt.created_at,
            )

        # Hit MAX_ITERATIONS without returning
        logger.warning(
            "Chatbot hit MAX_ITERATIONS (%d) for user=%s conversation=%s",
            MAX_ITERATIONS,
            user_id,
            conversation_id,
        )
        error_msg = "I'm sorry, I wasn't able to complete your request within the allowed number of steps. Please try simplifying your question."
        current_prompt.messages.append(
            OpenAIMessage(role=MessageRole.AI, content=error_msg),
        )
        self.tracing.set_output_json(agent_span, {"text": error_msg})
        self.tracing.end_span(agent_span)
        self.tracing.flush()
        yield format_sse_error(error_msg)

        summarized_history = await asyncio.to_thread(
            self._summarize_history,
            current_prompt.messages,
            llm_client,
        )
        CONVERSATION_HISTORIES[(user_id, conversation_id)] = summarized_history
