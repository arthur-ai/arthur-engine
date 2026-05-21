from unittest.mock import MagicMock

import pytest
from arthur_common.models.llm_model_providers import MessageRole, OpenAIMessage

from services.chatbot.chatbot_service import ChatbotService


def make_service() -> ChatbotService:
    return ChatbotService(
        chat_completion_service=MagicMock(),
        api_call_service=MagicMock(),
        api_index=[],
        db_session=MagicMock(),
        summarizer_prompt=MagicMock(),
    )


@pytest.mark.unit_tests
def test_summarize_history_keeps_system_plus_summary_plus_last_half():
    service = make_service()

    messages = [
        OpenAIMessage(role=MessageRole.SYSTEM, content="system prompt"),
        OpenAIMessage(role=MessageRole.USER, content="u1"),
        OpenAIMessage(role=MessageRole.AI, content="a1"),
        OpenAIMessage(role=MessageRole.USER, content="u2"),
        OpenAIMessage(role=MessageRole.AI, content="a2"),
        OpenAIMessage(role=MessageRole.USER, content="u3"),
        OpenAIMessage(role=MessageRole.AI, content="a3"),
    ]

    summary_text = "compressed summary of old turns"
    service.chat_completion_service.run_chat_completion.return_value = MagicMock(
        content=summary_text,
    )

    result = service.summarize_history(messages, llm_client=MagicMock())

    # 6 non-system messages, keep last 3, summarize first 3 into one AI message.
    assert len(result) == 1 + 1 + 3
    assert result[0].role == MessageRole.SYSTEM.value
    assert result[0].content == "system prompt"
    assert result[1].role == MessageRole.AI.value
    assert result[1].content == f"Summary of previous conversation:\n{summary_text}"
    assert [m.content for m in result[2:]] == ["a2", "u3", "a3"]
