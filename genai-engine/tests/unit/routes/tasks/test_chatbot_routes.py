from unittest.mock import patch

import pytest
from fastapi import HTTPException
from litellm.types.utils import ChatCompletionMessageToolCall, Function

from schemas.response_schemas import AgenticPromptRunResponse
from services.chatbot.api_call_service import ApiCallResult
from services.chatbot.chatbot_service import get_conversation_history
from tests.clients.base_test_client import (
    MASTER_KEY_AUTHORIZED_HEADERS,
    GenaiEngineTestClientBase,
)


async def make_stream(events: list[str]):
    for event in events:
        yield event


def make_tool_call(id: str, name: str, arguments: str) -> ChatCompletionMessageToolCall:
    return ChatCompletionMessageToolCall(
        id=id,
        type="function",
        function=Function(name=name, arguments=arguments),
    )


def final_response_events(content: str) -> list[str]:
    payload = AgenticPromptRunResponse(
        content=content,
        tool_calls=None,
        cost="0.0",
    ).model_dump_json()
    return [f"event: final_response\ndata: {payload}\n\n"]


@pytest.mark.unit_tests
@patch(
    "repositories.chatbot_repository.ChatbotRepository.get_provider_and_client",
    side_effect=HTTPException(status_code=503, detail="No provider configured"),
)
def test_chatbot_no_provider_configured(_, client: GenaiEngineTestClientBase):
    task_name = "chatbot_task_no_provider"
    _, task = client.create_task(task_name, is_agentic=True)

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/chatbot/stream",
        json={"message": "hello", "conversation_id": "test-conv-1"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 503


@pytest.mark.unit_tests
@patch(
    "services.prompt.chat_completion_service.ChatCompletionService.stream_chat_completion",
)
def test_chatbot_simple_response(mock_stream, client: GenaiEngineTestClientBase):
    task_name = "chatbot_task_simple_response"
    _, task = client.create_task(task_name, is_agentic=True)

    client.base_client.put(
        "/api/v1/model_providers/openai",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )

    mock_stream.return_value = make_stream(
        final_response_events("Here are your results."),
    )

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/chatbot/stream",
        json={"message": "list my tasks", "conversation_id": "test-conv-2"},
        headers=client.authorized_user_api_key_headers,
    )

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "final_response" in response.text
    assert "Here are your results." in response.text


@pytest.mark.unit_tests
@patch(
    "services.prompt.chat_completion_service.ChatCompletionService.stream_chat_completion",
)
def test_chatbot_search_tool_emits_search_complete(
    mock_stream,
    client: GenaiEngineTestClientBase,
):
    task_name = "chatbot_task_search_tool"
    _, task = client.create_task(task_name, is_agentic=True)

    client.base_client.put(
        "/api/v1/model_providers/openai",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )

    search_tool_call = make_tool_call("tc1", "search_arthur_api", '{"query": "evals"}')
    search_response = AgenticPromptRunResponse(
        content=None,
        tool_calls=[search_tool_call],
        cost="0.0",
    ).model_dump_json()
    first_call_events = [f"event: final_response\ndata: {search_response}\n\n"]
    second_call_events = final_response_events("Found your evals.")

    responses = [make_stream(first_call_events), make_stream(second_call_events)]
    mock_stream.side_effect = lambda *args, **kwargs: responses.pop(0)

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/chatbot/stream",
        json={"message": "find my evals", "conversation_id": "test-conv-3"},
        headers=client.authorized_user_api_key_headers,
    )

    assert response.status_code == 200
    assert "search_complete" in response.text
    assert "Found your evals." in response.text


@pytest.mark.unit_tests
@patch("services.chatbot.api_call_service.ApiCallService.call")
@patch(
    "services.prompt.chat_completion_service.ChatCompletionService.stream_chat_completion",
)
def test_chatbot_api_tool_emits_tool_call_and_result(
    mock_stream,
    mock_api_call,
    client: GenaiEngineTestClientBase,
):
    task_name = "chatbot_task_api_tool"
    _, task = client.create_task(task_name, is_agentic=True)

    client.base_client.put(
        "/api/v1/model_providers/openai",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )

    mock_api_call.return_value = ApiCallResult(
        method="GET",
        path="/api/v2/tasks",
        status_code=200,
        body='{"items": []}',
    )

    api_tool_call = make_tool_call(
        "tc2",
        "call_arthur_api",
        '{"method": "GET", "path": "/api/v2/tasks"}',
    )
    api_response = AgenticPromptRunResponse(
        content=None,
        tool_calls=[api_tool_call],
        cost="0.0",
    ).model_dump_json()
    first_call_events = [f"event: final_response\ndata: {api_response}\n\n"]
    second_call_events = final_response_events("You have no tasks.")

    responses = [make_stream(first_call_events), make_stream(second_call_events)]
    mock_stream.side_effect = lambda *args, **kwargs: responses.pop(0)

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/chatbot/stream",
        json={"message": "list my tasks", "conversation_id": "test-conv-api-tool"},
        headers=client.authorized_user_api_key_headers,
    )

    assert response.status_code == 200
    assert "tool_call" in response.text
    assert "tool_result" in response.text
    assert "You have no tasks." in response.text
    mock_api_call.assert_called_once()


@pytest.mark.unit_tests
@patch(
    "services.prompt.chat_completion_service.ChatCompletionService.stream_chat_completion",
)
def test_chatbot_conversation_history_persisted(
    mock_stream,
    client: GenaiEngineTestClientBase,
):
    task_name = "chatbot_task_history_persisted"
    _, task = client.create_task(task_name, is_agentic=True)

    client.base_client.put(
        "/api/v1/model_providers/openai",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )

    conversation_id = "test-conv-history-persisted"
    mock_stream.return_value = make_stream(final_response_events("First response."))

    client.base_client.post(
        f"/api/v1/tasks/{task.id}/chatbot/stream",
        json={"message": "first message", "conversation_id": conversation_id},
        headers=MASTER_KEY_AUTHORIZED_HEADERS,
    )

    history = get_conversation_history("master-key", conversation_id)
    assert len(history) > 0


@pytest.mark.unit_tests
@patch(
    "services.prompt.chat_completion_service.ChatCompletionService.stream_chat_completion",
)
def test_clear_chatbot_history(mock_stream, client: GenaiEngineTestClientBase):
    task_name = "chatbot_task_clear_history"
    _, task = client.create_task(task_name, is_agentic=True)

    client.base_client.put(
        "/api/v1/model_providers/openai",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )

    conversation_id = "test-conv-clear-history"
    mock_stream.return_value = make_stream(final_response_events("Hello."))

    client.base_client.post(
        f"/api/v1/tasks/{task.id}/chatbot/stream",
        json={"message": "hello", "conversation_id": conversation_id},
        headers=MASTER_KEY_AUTHORIZED_HEADERS,
    )

    assert len(get_conversation_history("master-key", conversation_id)) > 0

    response = client.base_client.delete(
        f"/api/v1/chatbot/history/{conversation_id}",
        headers=MASTER_KEY_AUTHORIZED_HEADERS,
    )

    assert response.status_code == 200
    assert len(get_conversation_history("master-key", conversation_id)) == 0
