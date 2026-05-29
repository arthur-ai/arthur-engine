import json
import logging
from typing import AsyncGenerator, List, Optional, Tuple

from arthur_common.models.llm_model_providers import (
    MessageRole,
    ModelProvider,
    OpenAIMessage,
    ToolCall,
)
from sqlalchemy.orm import Session

from schemas.agentic_prompt_schemas import AgenticPrompt
from schemas.chatbot_schemas import (
    CallArthurApiArgs,
    SearchArthurApiArgs,
)
from schemas.enums import SSEEventType
from services.chatbot.api_call_service import ApiCallService
from services.chatbot.base_chatbot_service import BaseChatbotService
from services.prompt.chat_completion_service import ChatCompletionService
from services.trace.internal_trace_service import TraceSpanBuilder
from utils import constants
from utils.llm_tool_functions import search_api_index
from utils.sse_events import format_sse_json

logger = logging.getLogger(__name__)


class ChatbotService(BaseChatbotService):
    def __init__(
        self,
        chat_completion_service: ChatCompletionService,
        api_call_service: ApiCallService,
        api_index: List[str],
        db_session: Session,
        summarizer_prompt: AgenticPrompt,
    ):
        super().__init__(
            chat_completion_service=chat_completion_service,
            db_session=db_session,
            summarizer_prompt=summarizer_prompt,
            task_id=constants.ARTHUR_SYSTEM_TASK_ID,
        )
        self.api_call_service = api_call_service
        self.api_index = api_index

    @property
    def service_name(self) -> str:
        return "chatbot"

    @property
    def agent_name(self) -> str:
        return "arthur_chatbot"

    def build_prompt(
        self,
        chatbot_prompt: AgenticPrompt,
        model_provider: ModelProvider,
        model_name: str,
        task_id: str,
        history: List[OpenAIMessage],
        blacklist: Optional[List[str]] = None,
    ) -> AgenticPrompt:
        chatbot_prompt.model_provider = model_provider
        chatbot_prompt.model_name = model_name

        blacklist_str = "\n".join(blacklist) if blacklist else "None"
        self.chat_completion_service.replace_variables(
            {"task_id": task_id, "endpoint_blacklist": blacklist_str},
            chatbot_prompt.messages,
        )

        chatbot_prompt.messages = list(chatbot_prompt.messages) + list(history)
        return chatbot_prompt

    async def execute_tool(
        self,
        tool_call: ToolCall,
        agent_span: TraceSpanBuilder,
    ) -> AsyncGenerator[Tuple[Optional[str], Optional[OpenAIMessage]], None]:
        tool_call_id = tool_call.id
        args_str = tool_call.function.arguments or "{}"

        if tool_call.function.name == "search_arthur_api":
            search_args = SearchArthurApiArgs.model_validate_json(args_str)
            tool_span = self.tracing.start_tool_span(agent_span, "search_arthur_api")
            self.tracing.set_tool_input(tool_span, search_args.query)
            search_result = search_api_index(self.api_index, search_args.query)
            self.tracing.set_tool_output(tool_span, search_result)
            self.tracing.end_span(tool_span)
            yield (
                None,
                OpenAIMessage(
                    role=MessageRole.TOOL,
                    content=search_result,
                    tool_call_id=tool_call_id,
                ),
            )
            # Signal the frontend to start a new message bubble — search is internal
            # but the LLM's next response should be in a fresh bubble
            yield format_sse_json(SSEEventType.SEARCH_COMPLETE, {}), None
            return

        if tool_call.function.name == "call_arthur_api":
            call_args = CallArthurApiArgs.model_validate_json(args_str)
            tool_span = self.tracing.start_tool_span(agent_span, "call_arthur_api")
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

            yield (
                format_sse_json(
                    SSEEventType.TOOL_CALL,
                    {
                        "tool_call_id": tool_call_id,
                        "name": tool_call.function.name,
                        "arguments": args_str,
                        "method": call_args.method,
                        "path": call_args.path,
                    },
                ),
                None,
            )

            result = await self.api_call_service.call(
                call_args.method,
                call_args.path,
                call_args.query_params,
                call_args.body,
            )

            self.tracing.set_tool_output(tool_span, result.to_tool_result_content())
            self.tracing.end_span(tool_span)

            yield (
                format_sse_json(
                    SSEEventType.TOOL_RESULT,
                    {
                        "tool_call_id": tool_call_id,
                        "content": result.to_tool_result_content(),
                        "method": call_args.method,
                        "path": call_args.path,
                        "status_code": result.status_code,
                    },
                ),
                None,
            )

            yield (
                None,
                OpenAIMessage(
                    role=MessageRole.TOOL,
                    content=result.to_tool_result_content(),
                    tool_call_id=tool_call_id,
                ),
            )
            return

        yield (
            None,
            OpenAIMessage(
                role=MessageRole.TOOL,
                content=f"Unknown tool: {tool_call.function.name}",
                tool_call_id=tool_call_id,
            ),
        )
