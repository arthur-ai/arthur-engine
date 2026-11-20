from unittest.mock import MagicMock, patch

import litellm
import pytest
from arthur_common.models.llm_model_providers import MessageRole, OpenAIMessage

from services.chatbot.base_chatbot_service import summarize_threshold
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
def test_summarize_history():
    """Single test covering the happy path plus item 10 edge cases.

    Sub-cases (one fake LLM, reused service):
      1) Happy path: SYSTEM + 6 non-system -> [SYSTEM, summary, last-half].
      2) No SYSTEM + len(non_system) >= 2 -> [summary, last-half], LLM called.
      3) Has SYSTEM + len(non_system) == 1 -> input returned unchanged, no LLM call
         (item 10b: keep_count=0 previously corrupted the slices).
      4) No SYSTEM + len(non_system) == 1 -> input returned unchanged, no LLM call
         (item 10a: would have raised StopIteration before the fix).
    """
    service = make_service()
    summary_text = "summary"
    service.chat_completion_service.run_chat_completion.return_value = MagicMock(
        content=summary_text,
    )

    # Sub-case 1: happy path — SYSTEM + 6 non-system messages.
    case = "system + 6 non-system"
    messages = [
        OpenAIMessage(role=MessageRole.SYSTEM, content="system prompt"),
        OpenAIMessage(role=MessageRole.USER, content="u1"),
        OpenAIMessage(role=MessageRole.AI, content="a1"),
        OpenAIMessage(role=MessageRole.USER, content="u2"),
        OpenAIMessage(role=MessageRole.AI, content="a2"),
        OpenAIMessage(role=MessageRole.USER, content="u3"),
        OpenAIMessage(role=MessageRole.AI, content="a3"),
    ]
    service.chat_completion_service.run_chat_completion.reset_mock()
    result = service.summarize_history(messages, llm_client=MagicMock())
    assert service.chat_completion_service.run_chat_completion.call_count == 1, case
    assert len(result) == 1 + 1 + 3, case
    assert result[0].role == MessageRole.SYSTEM.value, case
    assert result[0].content == "system prompt", case
    assert result[1].role == MessageRole.AI.value, case
    assert (
        result[1].content == f"Summary of previous conversation:\n{summary_text}"
    ), case
    assert [m.content for m in result[2:]] == ["a2", "u3", "a3"], case

    # Sub-case 2: no SYSTEM, len(non_system) == 4 -> split, summarize, keep half.
    case = "no system + 4 non-system"
    no_system = [
        OpenAIMessage(role=MessageRole.USER, content="u1"),
        OpenAIMessage(role=MessageRole.AI, content="a1"),
        OpenAIMessage(role=MessageRole.USER, content="u2"),
        OpenAIMessage(role=MessageRole.AI, content="a2"),
    ]
    service.chat_completion_service.run_chat_completion.reset_mock()
    result = service.summarize_history(no_system, llm_client=MagicMock())
    assert service.chat_completion_service.run_chat_completion.call_count == 1, case
    assert len(result) == 1 + 2, case
    assert result[0].role == MessageRole.AI.value, case
    assert (
        result[0].content == f"Summary of previous conversation:\n{summary_text}"
    ), case
    assert [m.content for m in result[1:]] == ["u2", "a2"], case
    assert not any(m.role == MessageRole.SYSTEM.value for m in result), case

    # Sub-case 3: has SYSTEM, only one non-system -> bail out, no LLM call.
    case = "has system + 1 non-system"
    one_with_sys = [
        OpenAIMessage(role=MessageRole.SYSTEM, content="sys"),
        OpenAIMessage(role=MessageRole.USER, content="huge"),
    ]
    service.chat_completion_service.run_chat_completion.reset_mock()
    result = service.summarize_history(one_with_sys, llm_client=MagicMock())
    assert service.chat_completion_service.run_chat_completion.call_count == 0, case
    assert result is one_with_sys, case

    # Sub-case 4: no SYSTEM + 1 non-system -> bail out, no crash.
    case = "no system + 1 non-system"
    one_no_sys = [OpenAIMessage(role=MessageRole.USER, content="huge")]
    service.chat_completion_service.run_chat_completion.reset_mock()
    result = service.summarize_history(one_no_sys, llm_client=MagicMock())
    assert service.chat_completion_service.run_chat_completion.call_count == 0, case
    assert result is one_no_sys, case


@pytest.mark.unit_tests
def test_summarize_threshold_uses_the_input_window():
    # A 1M-token window: summarize at 150k, not at the 128k output limit
    with patch(
        "services.chatbot.base_chatbot_service.litellm.get_model_info",
        return_value={"max_input_tokens": 1_000_000, "max_output_tokens": 128_000},
    ):
        assert summarize_threshold("claude-opus-5-5") == 150_000
    with patch(
        "services.chatbot.base_chatbot_service.litellm.get_model_info",
        return_value={"max_input_tokens": 100_000, "max_output_tokens": 16_000},
    ):
        assert summarize_threshold("small-window-model") == 85_000
    with patch(
        "services.chatbot.base_chatbot_service.litellm.get_model_info",
        side_effect=litellm.ModelNotMappedError("This model isn't mapped yet."),
    ):
        assert summarize_threshold("unknown-model") is None
    # Any other failure is logged, and summarizing is skipped rather than failing the chat
    with (
        patch(
            "services.chatbot.base_chatbot_service.litellm.get_model_info",
            side_effect=TypeError("bad call"),
        ),
        patch("services.chatbot.base_chatbot_service.logger") as mock_logger,
    ):
        assert summarize_threshold("claude-opus-5-5") is None
        mock_logger.warning.assert_called_once()
