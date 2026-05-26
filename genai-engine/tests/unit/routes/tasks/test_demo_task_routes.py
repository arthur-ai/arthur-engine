import json
import os
from unittest.mock import patch

import pytest

from schemas.chatbot_schemas import WikipediaSearchResult
from schemas.response_schemas import AgenticPromptRunResponse
from tests.clients.base_test_client import GenaiEngineTestClientBase
from tests.unit.routes.tasks.helpers import (
    final_response_events,
    make_stream,
    make_tool_call,
    parse_sse_event,
)


async def stream_patch(*args, **kwargs):
    yield 'event: final_response\ndata: {"content": "hello from the demo chatbot"}\n\n'


@pytest.mark.unit_tests
def test_stream_demo_chatbot_streams_response(client: GenaiEngineTestClientBase):
    """Streaming the demo chatbot returns the SSE events yielded by stream."""
    response = client.base_client.put(
        "/api/v1/model_providers/anthropic",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201

    try:
        with (
            patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "enabled"}),
            patch(
                "repositories.continuous_evals_repository.ContinuousEvalsRepository.enqueue_continuous_evals_for_root_spans",
                return_value=None,
            ),
            patch(
                "services.chatbot.base_chatbot_service.BaseChatbotService.stream",
                new=stream_patch,
            ),
        ):
            status_code, signup = client.signup_tenant()
            assert status_code == 200
            assert signup is not None

            status_code, body = client.stream_demo_chatbot(
                signup.task_id,
                [{"role": "user", "content": "hi"}],
                api_key=signup.api_key,
            )

            assert status_code == 200
            assert "final_response" in body
            assert "hello from the demo chatbot" in body
    finally:
        response = client.base_client.delete(
            "/api/v1/model_providers/anthropic",
            headers=client.authorized_user_api_key_headers,
        )
        assert response.status_code == 204


@pytest.mark.unit_tests
def test_stream_demo_chatbot_yields_error_when_stream_raises(
    client: GenaiEngineTestClientBase,
):
    """If stream raises, safe_stream catches it and yields an SSE error event."""
    response = client.base_client.put(
        "/api/v1/model_providers/anthropic",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201

    try:
        with (
            patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "enabled"}),
            patch(
                "repositories.continuous_evals_repository.ContinuousEvalsRepository.enqueue_continuous_evals_for_root_spans",
                return_value=None,
            ),
            patch(
                "services.chatbot.base_chatbot_service.BaseChatbotService.stream",
                side_effect=RuntimeError("stream failed"),
            ),
        ):
            status_code, signup = client.signup_tenant()
            assert status_code == 200
            assert signup is not None

            status_code, body = client.stream_demo_chatbot(
                signup.task_id,
                [{"role": "user", "content": "hi"}],
                api_key=signup.api_key,
            )

            assert status_code == 200
            assert "event: error" in body
            assert "Failed to stream chatbot response" in body
            assert "stream failed" in body
    finally:
        response = client.base_client.delete(
            "/api/v1/model_providers/anthropic",
            headers=client.authorized_user_api_key_headers,
        )
        assert response.status_code == 204


@pytest.mark.unit_tests
@patch("services.chatbot.demo_chatbot_service.wikipedia_search")
@patch(
    "services.prompt.chat_completion_service.ChatCompletionService.stream_chat_completion",
)
def test_demo_chatbot_emits_enriched_tool_events(
    mock_stream,
    mock_wikipedia_search,
    client: GenaiEngineTestClientBase,
):
    """tool_call/tool_result SSE events from the demo chatbot include the raw fields
    needed by the FE to reconstruct OpenAI-shaped history."""
    response = client.base_client.put(
        "/api/v1/model_providers/anthropic",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201

    try:
        with (
            patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "enabled"}),
            patch(
                "repositories.continuous_evals_repository.ContinuousEvalsRepository.enqueue_continuous_evals_for_root_spans",
                return_value=None,
            ),
        ):
            status_code, signup = client.signup_tenant()
            assert status_code == 200
            assert signup is not None

            mock_wikipedia_search.return_value = WikipediaSearchResult(
                titles=["Rosalind Franklin"],
            )

            search_args = '{"query": "Rosalind Franklin"}'
            tool_call_chunk = make_tool_call("wc1", "wikipedia_search", search_args)
            first = AgenticPromptRunResponse(
                content=None,
                tool_calls=[tool_call_chunk],
                cost="0.0",
            ).model_dump_json()
            first_events = [f"event: final_response\ndata: {first}\n\n"]
            second_events = final_response_events("She was a chemist.")

            responses = [make_stream(first_events), make_stream(second_events)]
            mock_stream.side_effect = lambda *args, **kwargs: responses.pop(0)

            status_code, body = client.stream_demo_chatbot(
                signup.task_id,
                [{"role": "user", "content": "who is rosalind franklin?"}],
                api_key=signup.api_key,
            )

            assert status_code == 200

            tool_call_event = parse_sse_event(body, "tool_call")
            assert tool_call_event["tool_call_id"] == "wc1"
            assert tool_call_event["name"] == "wikipedia_search"
            assert json.loads(tool_call_event["arguments"]) == {
                "query": "Rosalind Franklin",
            }

            tool_result_event = parse_sse_event(body, "tool_result")
            assert tool_result_event["tool_call_id"] == "wc1"
            assert tool_result_event["content"] == "Rosalind Franklin"
    finally:
        response = client.base_client.delete(
            "/api/v1/model_providers/anthropic",
            headers=client.authorized_user_api_key_headers,
        )
        assert response.status_code == 204
