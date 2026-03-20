import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator, List, MutableMapping, Tuple

from arthur_common.models.llm_model_providers import (
    MessageRole,
    ModelProvider,
    OpenAIMessage,
    ToolCall,
    ToolCallFunction,
)
from cachetools import TTLCache

from clients.llm.llm_client import LLMClient
from schemas.agentic_prompt_schemas import AgenticPrompt
from schemas.chatbot_schemas import (
    ApiCallSummary,
    CallArthurApiArgs,
    SearchArthurApiArgs,
)
from schemas.request_schemas import PromptCompletionRequest
from schemas.response_schemas import AgenticPromptRunResponse
from services.chatbot.api_call_service import ApiCallService
from services.chatbot.chatbot_prompts import (
    CALL_ARTHUR_API_TOOL,
    SEARCH_ARTHUR_API_TOOL,
    search_api_index,
)
from services.prompt.chat_completion_service import ChatCompletionService
from utils import constants
from utils.utils import get_env_var

logger = logging.getLogger(__name__)


MAX_ITERATIONS = int(
    get_env_var(constants.GENAI_ENGINE_CHATBOT_MAX_ITERATIONS_ENV_VAR, True) or 30,
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
    ):
        self.chat_completion_service = chat_completion_service
        self.api_call_service = api_call_service
        self.api_index = api_index

    def build_prompt(
        self,
        system_prompt: str,
        task_id: str,
        history: List[OpenAIMessage],
        user_message: str,
        model_provider: ModelProvider,
        model_name: str,
    ) -> AgenticPrompt:
        system_content = f"{system_prompt}\n\nYou are currently operating within task ID: {task_id}. Use this task_id when making API calls that require it."
        messages: List[OpenAIMessage] = [
            OpenAIMessage(role=MessageRole.SYSTEM, content=system_content),
        ]
        messages.extend(history)
        messages.append(OpenAIMessage(role=MessageRole.USER, content=user_message))

        return AgenticPrompt(
            name="chatbot",
            messages=messages,
            model_name=model_name,
            model_provider=model_provider,
            tools=[SEARCH_ARTHUR_API_TOOL, CALL_ARTHUR_API_TOOL],
            created_at=datetime.now(timezone.utc),
        )

    async def stream(
        self,
        prompt: AgenticPrompt,
        llm_client: LLMClient,
        user_id: str,
        conversation_id: str,
    ) -> AsyncGenerator[str, None]:
        api_calls_made: List[ApiCallSummary] = []
        current_prompt = prompt

        for _ in range(MAX_ITERATIONS):
            final_response: AgenticPromptRunResponse | None = None

            async for event in self.chat_completion_service.stream_chat_completion(
                current_prompt,
                llm_client,
                PromptCompletionRequest(stream=True, strict=False),
            ):
                if event.startswith("event: final_response"):
                    data = event.split("data: ", 1)[1].strip()
                    final_response = AgenticPromptRunResponse.model_validate_json(data)
                elif event.startswith("event: error"):
                    yield event
                    return
                else:
                    yield event

            if final_response is None:
                return

            if not final_response.tool_calls:
                history = [
                    m for m in current_prompt.messages if m.role != MessageRole.SYSTEM
                ]
                history.append(
                    OpenAIMessage(role=MessageRole.AI, content=final_response.content),
                )
                CONVERSATION_HISTORIES[(user_id, conversation_id)] = history[-15:]
                yield f"event: final_response\ndata: {final_response.model_dump_json()}\n\n"
                return

            tool_calls = [
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
                    new_messages.append(
                        OpenAIMessage(
                            role=MessageRole.TOOL,
                            content=search_api_index(self.api_index, search_args.query),
                            tool_call_id=tool_call_id,
                        ),
                    )
                    # Signal the frontend to start a new message bubble — search is internal
                    # but the LLM's next response should be in a fresh bubble
                    yield "event: search_complete\ndata: {}\n\n"
                    continue
                elif tool_call.function.name == "call_arthur_api":
                    call_args = CallArthurApiArgs.model_validate_json(args_str)

                    yield f"event: tool_call\ndata: {json.dumps({'method': call_args.method, 'path': call_args.path})}\n\n"

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

                    yield f"event: tool_result\ndata: {json.dumps({'method': call_args.method, 'path': call_args.path, 'status_code': result.status_code})}\n\n"

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
