import logging
import uuid
from typing import AsyncGenerator, Dict, List, Optional, Tuple

from arthur_common.models.llm_model_providers import (
    MessageRole,
    ModelProvider,
    OpenAIMessage,
    OpenAIMessageType,
    ToolCall,
)
from sqlalchemy.orm import Session

from schemas.agentic_prompt_schemas import AgenticPrompt
from schemas.chatbot_schemas import WikipediaFetchArgs, WikipediaSearchArgs
from schemas.enums import SSEEventType
from services.chatbot.base_chatbot_service import BaseChatbotService
from services.prompt.chat_completion_service import ChatCompletionService
from services.trace.internal_trace_service import TraceSpanBuilder
from utils.sse_events import format_sse_json
from utils.wikipedia_tools import wikipedia_fetch, wikipedia_search

logger = logging.getLogger(__name__)


def _extract_latest_user_text(messages: List[OpenAIMessage]) -> str:
    for msg in reversed(messages):
        if msg.role != MessageRole.USER.value:  # type: ignore[comparison-overlap]
            continue
        content = msg.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = [
                item.text
                for item in content
                if item.type == OpenAIMessageType.TEXT.value and item.text
            ]
            if parts:
                return " ".join(parts)
        return ""
    return ""


class DemoChatbotService(BaseChatbotService):
    def __init__(
        self,
        chat_completion_service: ChatCompletionService,
        db_session: Session,
        summarizer_prompt: AgenticPrompt,
        task_id: str,
        org_id: uuid.UUID,
    ):
        super().__init__(
            chat_completion_service=chat_completion_service,
            db_session=db_session,
            summarizer_prompt=summarizer_prompt,
            task_id=task_id,
            org_id=org_id,
            enqueue_continuous_evals=True,
        )
        self.task_id = task_id

    def build_variable_map(self, prompt: AgenticPrompt) -> Dict[str, str]:
        return {"query": _extract_latest_user_text(prompt.messages)}

    @property
    def service_name(self) -> str:
        return "demo_chatbot"

    @property
    def agent_name(self) -> str:
        return "arthur_demo_chatbot"

    def build_prompt(
        self,
        chatbot_prompt: AgenticPrompt,
        model_provider: ModelProvider,
        model_name: str,
        history: List[OpenAIMessage],
    ) -> AgenticPrompt:
        chatbot_prompt.model_provider = model_provider
        chatbot_prompt.model_name = model_name
        chatbot_prompt.messages = list(chatbot_prompt.messages) + list(history)
        return chatbot_prompt

    async def execute_tool(
        self,
        tool_call: ToolCall,
        agent_span: TraceSpanBuilder,
    ) -> AsyncGenerator[Tuple[Optional[str], Optional[OpenAIMessage]], None]:
        tool_call_id = tool_call.id
        tool_name = tool_call.function.name
        args_str = tool_call.function.arguments or "{}"

        if tool_name == "wikipedia_search":
            search_args = WikipediaSearchArgs.model_validate_json(args_str)
            tool_span = self.tracing.start_tool_span(agent_span, "wikipedia_search")
            self.tracing.set_tool_input(tool_span, search_args.query)

            yield (
                format_sse_json(
                    SSEEventType.TOOL_CALL,
                    {
                        "tool_call_id": tool_call_id,
                        "name": tool_name,
                        "arguments": args_str,
                        "query": search_args.query,
                    },
                ),
                None,
            )

            try:
                result = await wikipedia_search(search_args.query)
                content = "\n".join(result.titles) or "No matching articles found."
            except Exception as e:
                logger.warning("wikipedia_search failed: %s", e)
                content = f"wikipedia_search failed: {e}"

            self.tracing.set_tool_output(tool_span, content)
            self.tracing.end_span(tool_span)

            yield (
                format_sse_json(
                    SSEEventType.TOOL_RESULT,
                    {
                        "tool_call_id": tool_call_id,
                        "content": content,
                        "name": tool_name,
                    },
                ),
                None,
            )
            yield (
                None,
                OpenAIMessage(
                    role=MessageRole.TOOL,
                    content=content,
                    tool_call_id=tool_call_id,
                ),
            )
            return

        if tool_name == "wikipedia_fetch":
            fetch_args = WikipediaFetchArgs.model_validate_json(args_str)
            tool_span = self.tracing.start_tool_span(agent_span, "wikipedia_fetch")
            self.tracing.set_tool_input(tool_span, fetch_args.title)

            yield (
                format_sse_json(
                    SSEEventType.TOOL_CALL,
                    {
                        "tool_call_id": tool_call_id,
                        "name": tool_name,
                        "arguments": args_str,
                        "title": fetch_args.title,
                    },
                ),
                None,
            )

            try:
                article = await wikipedia_fetch(fetch_args.title)
                content = (
                    f"{article.title}\n\n{article.extract}"
                    if article.extract
                    else f"No article content available for '{fetch_args.title}'."
                )
            except Exception as e:
                logger.warning("wikipedia_fetch failed: %s", e)
                content = f"wikipedia_fetch failed: {e}"

            self.tracing.set_tool_output(tool_span, content)
            self.tracing.end_span(tool_span)

            yield (
                format_sse_json(
                    SSEEventType.TOOL_RESULT,
                    {
                        "tool_call_id": tool_call_id,
                        "content": content,
                        "name": tool_name,
                    },
                ),
                None,
            )
            yield (
                None,
                OpenAIMessage(
                    role=MessageRole.TOOL,
                    content=content,
                    tool_call_id=tool_call_id,
                ),
            )
            return

        yield (
            None,
            OpenAIMessage(
                role=MessageRole.TOOL,
                content=f"Unknown tool: {tool_name}",
                tool_call_id=tool_call_id,
            ),
        )
