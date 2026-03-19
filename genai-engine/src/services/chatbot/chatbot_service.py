import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, List

from arthur_common.models.llm_model_providers import (
    MessageRole,
    ModelProvider,
    OpenAIMessage,
    ToolCall,
    ToolCallFunction,
)

from clients.llm.llm_client import LLMClient
from schemas.agentic_prompt_schemas import AgenticPrompt
from schemas.chatbot_schemas import ApiCallSummary
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

CONVERSATION_HISTORIES: Dict[str, List[OpenAIMessage]] = {}


def get_conversation_history(conversation_id: str) -> List[OpenAIMessage]:
    return CONVERSATION_HISTORIES.get(conversation_id, [])


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
                CONVERSATION_HISTORIES[conversation_id] = [
                    m for m in current_prompt.messages if m.role != MessageRole.SYSTEM
                ]
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
                try:
                    args = json.loads(args_str)
                except json.JSONDecodeError:
                    args = {}

                if tool_call.function.name == "search_arthur_api":
                    query = args.get("query", "")
                    new_messages.append(
                        OpenAIMessage(
                            role=MessageRole.TOOL,
                            content=search_api_index(self.api_index, query),
                            tool_call_id=tool_call_id,
                        ),
                    )
                    # Signal the frontend to start a new message bubble — search is internal
                    # but the LLM's next response should be in a fresh bubble
                    yield "event: search_complete\ndata: {}\n\n"
                    continue

                method = args.get("method", "GET")
                path = args.get("path", "/")
                query_params_raw = args.get("query_params")
                body_raw = args.get("body")

                try:
                    query_params = (
                        json.loads(query_params_raw) if query_params_raw else None
                    )
                except (json.JSONDecodeError, TypeError):
                    query_params = None

                try:
                    body = json.loads(body_raw) if body_raw else None
                except (json.JSONDecodeError, TypeError):
                    body = None

                yield f"event: tool_call\ndata: {json.dumps({'method': method, 'path': path})}\n\n"

                result = await self.api_call_service.call(
                    method,
                    path,
                    query_params,
                    body,
                )
                api_calls_made.append(
                    ApiCallSummary(
                        method=method,
                        path=path,
                        status_code=result.status_code,
                    ),
                )

                yield f"event: tool_result\ndata: {json.dumps({'method': method, 'path': path, 'status_code': result.status_code})}\n\n"

                tool_result_msg = OpenAIMessage(
                    role=MessageRole.TOOL,
                    content=result.to_tool_result_content(),
                    tool_call_id=tool_call_id,
                )
                new_messages.append(tool_result_msg)

            current_prompt = AgenticPrompt(
                name=current_prompt.name,
                messages=new_messages,
                model_name=current_prompt.model_name,
                model_provider=current_prompt.model_provider,
                tools=current_prompt.tools,
                config=current_prompt.config,
                created_at=current_prompt.created_at,
            )
