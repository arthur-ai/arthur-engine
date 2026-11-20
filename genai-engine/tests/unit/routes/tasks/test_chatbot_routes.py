import json
from unittest.mock import patch

import pytest
from arthur_common.models.llm_model_providers import MessageRole, OpenAIMessage
from fastapi import HTTPException

from repositories.agentic_prompts_repository import AgenticPromptRepository
from schemas.response_schemas import AgenticPromptRunResponse
from services.chatbot.api_call_service import ApiCallResult
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)
from tests.unit.routes.tasks.helpers import (
    final_response_events,
    make_stream,
    make_token_count_response,
    make_tool_call,
    parse_sse_event,
)
from utils.constants import ARTHUR_SYSTEM_TASK_ID, CHATBOT_PROMPT_NAME

# The chatbot runs on the default model provider, which is instance-wide state
pytestmark = pytest.mark.xdist_group("default_model_provider")

# Differs from the model the chatbot prompts are seeded with, so a test can tell
# the default apart from the stored model.
DEFAULT_MODEL = "claude-opus-5-5"


@pytest.fixture
def anthropic_default(client: GenaiEngineTestClientBase):
    """Make Anthropic the default model provider for the test, then remove both."""
    headers = client.authorized_user_api_key_headers
    response = client.base_client.put(
        "/api/v1/model_providers/anthropic",
        json={"api_key": "test-key"},
        headers=headers,
    )
    assert response.status_code == 201
    response = client.base_client.put(
        "/api/v1/default_model_provider",
        json={"provider": "anthropic", "model_name": DEFAULT_MODEL},
        headers=headers,
    )
    assert response.status_code == 204
    yield
    # the default first: the API refuses to delete the default provider's credentials
    client.base_client.delete("/api/v1/default_model_provider", headers=headers)
    client.base_client.delete("/api/v1/model_providers/anthropic", headers=headers)


def _get_chatbot_config(client: GenaiEngineTestClientBase):
    return client.base_client.get(
        "/api/v1/chatbot/config",
        headers=client.authorized_org_admin_api_key_headers,
    )


def _put_chatbot_config(client: GenaiEngineTestClientBase, body: dict):
    return client.base_client.put(
        "/api/v1/chatbot/config",
        json=body,
        headers=client.authorized_org_admin_api_key_headers,
    )


@pytest.mark.unit_tests
def test_chatbot_without_default_model_provider(client: GenaiEngineTestClientBase):
    headers = client.authorized_user_api_key_headers
    client.base_client.delete("/api/v1/default_model_provider", headers=headers)
    _, task = client.create_task("chatbot_task_no_default", is_agentic=True)

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/chatbot/stream",
        json={"history": [{"role": "user", "content": "hello"}]},
        headers=headers,
    )
    assert response.status_code == 400
    assert "No default model provider is set" in response.json()["detail"]

    # the config has no model to show
    response = _get_chatbot_config(client)
    assert response.status_code == 200
    config = response.json()
    assert config["model_provider"] is None
    assert config["model_name"] is None


@pytest.mark.unit_tests
def test_chatbot_config_shows_default_model(
    client: GenaiEngineTestClientBase,
    anthropic_default: None,
):
    response = _get_chatbot_config(client)
    assert response.status_code == 200
    config = response.json()
    assert config["model_provider"] == "anthropic"
    assert config["model_name"] == DEFAULT_MODEL
    assert "uses_default_model" not in config


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "body",
    [
        {"model_provider": "openai", "model_name": "gpt-4o"},
        {"model_name": "gpt-4o"},
        {"model_provider": "openai", "blacklist_endpoints": []},
    ],
)
def test_chatbot_config_rejects_a_model(
    client: GenaiEngineTestClientBase,
    anthropic_default: None,
    body: dict,
):
    blacklist_before = _get_chatbot_config(client).json()["blacklist_endpoints"]

    response = _put_chatbot_config(client, body)
    assert response.status_code == 400
    assert "Model Providers page" in response.json()["detail"]
    # nothing in the request was applied
    assert _get_chatbot_config(client).json()["blacklist_endpoints"] == blacklist_before


@pytest.mark.unit_tests
def test_chatbot_config_updates_blacklist_only(
    client: GenaiEngineTestClientBase,
    anthropic_default: None,
):
    try:
        response = _put_chatbot_config(
            client,
            {"blacklist_endpoints": ["/api/v2/tasks"]},
        )
        assert response.status_code == 200
        config = response.json()
        assert config["blacklist_endpoints"] == ["/api/v2/tasks"]
        assert config["model_name"] == DEFAULT_MODEL
    finally:
        _put_chatbot_config(client, {"blacklist_endpoints": []})


@pytest.mark.unit_tests
@patch(
    "services.prompt.chat_completion_service.ChatCompletionService.stream_chat_completion",
)
def test_chatbot_calls_default_not_stored_model(
    mock_stream,
    client: GenaiEngineTestClientBase,
    anthropic_default: None,
):
    db = override_get_db_session()
    try:
        stored = AgenticPromptRepository(db).get_llm_item_by_tag(
            task_id=ARTHUR_SYSTEM_TASK_ID,
            item_name=CHATBOT_PROMPT_NAME,
            tag="production",
        )
    finally:
        db.close()
    assert stored.model_name != DEFAULT_MODEL

    _, task = client.create_task("chatbot_task_default_model", is_agentic=True)
    mock_stream.return_value = make_stream(final_response_events("hi"))

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/chatbot/stream",
        json={"history": [{"role": "user", "content": "hello"}]},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    prompt = mock_stream.call_args.args[0]
    assert (prompt.model_provider, prompt.model_name) == ("anthropic", DEFAULT_MODEL)


@pytest.mark.unit_tests
@patch(
    "repositories.model_provider_repository.ModelProviderRepository.get_model_provider_client",
    side_effect=HTTPException(
        status_code=400,
        detail="model provider anthropic is not configured",
    ),
)
def test_chatbot_no_provider_configured(
    mock_get_client,
    client: GenaiEngineTestClientBase,
    anthropic_default,
):
    """With a default set, a provider client that can't be built returns its error."""
    task_name = "chatbot_task_no_provider"
    _, task = client.create_task(task_name, is_agentic=True)

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/chatbot/stream",
        json={"history": [{"role": "user", "content": "hello"}]},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "model provider anthropic is not configured"
    mock_get_client.assert_called_once()


@pytest.mark.unit_tests
@patch(
    "services.prompt.chat_completion_service.ChatCompletionService.stream_chat_completion",
)
def test_chatbot_simple_response(
    mock_stream, client: GenaiEngineTestClientBase, anthropic_default
):
    task_name = "chatbot_task_simple_response"
    _, task = client.create_task(task_name, is_agentic=True)

    mock_stream.return_value = make_stream(
        final_response_events("Here are your results."),
    )

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/chatbot/stream",
        json={"history": [{"role": "user", "content": "list my tasks"}]},
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
    anthropic_default: None,
):
    task_name = "chatbot_task_search_tool"
    _, task = client.create_task(task_name, is_agentic=True)

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
        json={"history": [{"role": "user", "content": "find my evals"}]},
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
    anthropic_default: None,
):
    task_name = "chatbot_task_api_tool"
    _, task = client.create_task(task_name, is_agentic=True)

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
        json={"history": [{"role": "user", "content": "list my tasks"}]},
        headers=client.authorized_user_api_key_headers,
    )

    assert response.status_code == 200
    assert "tool_call" in response.text
    assert "tool_result" in response.text
    assert "You have no tasks." in response.text
    mock_api_call.assert_called_once()

    # Verify the enriched fields are present in the SSE events so the FE can rebuild
    # OpenAI-shaped history without re-fetching.
    tool_call_event = parse_sse_event(response.text, "tool_call")
    assert tool_call_event["tool_call_id"] == "tc2"
    assert tool_call_event["name"] == "call_arthur_api"
    assert json.loads(tool_call_event["arguments"]) == {
        "method": "GET",
        "path": "/api/v2/tasks",
    }

    tool_result_event = parse_sse_event(response.text, "tool_result")
    assert tool_result_event["tool_call_id"] == "tc2"
    assert tool_result_event["content"] == 'HTTP 200\n{"items": []}'


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.LLMClient.acount_tokens")
@patch("services.chatbot.base_chatbot_service.litellm.get_max_tokens")
@patch("services.chatbot.base_chatbot_service.BaseChatbotService.summarize_history")
@patch(
    "services.prompt.chat_completion_service.ChatCompletionService.stream_chat_completion",
)
def test_chatbot_emits_history_replace_when_over_token_limit(
    mock_stream,
    mock_summarize_history,
    mock_get_max_tokens,
    mock_acount_tokens,
    client: GenaiEngineTestClientBase,
    anthropic_default: None,
):
    task_name = "chatbot_task_history_replace_over"
    _, task = client.create_task(task_name, is_agentic=True)

    mock_stream.return_value = make_stream(final_response_events("Done."))
    mock_get_max_tokens.return_value = 10
    mock_acount_tokens.return_value = make_token_count_response(1000)
    mock_summarize_history.return_value = [
        OpenAIMessage(role=MessageRole.SYSTEM, content="sys"),
        OpenAIMessage(
            role=MessageRole.AI,
            content="Summary of previous conversation:\nabc",
        ),
        OpenAIMessage(role=MessageRole.USER, content="kept user"),
        OpenAIMessage(role=MessageRole.AI, content="kept assistant"),
    ]

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/chatbot/stream",
        json={"history": [{"role": "user", "content": "hi"}]},
        headers=client.authorized_user_api_key_headers,
    )

    assert response.status_code == 200
    assert "event: history_replace" in response.text

    replace_event = parse_sse_event(response.text, "history_replace")
    # System message must be stripped from the FE-bound history.
    assert all(m["role"] != "system" for m in replace_event["history"])
    assert replace_event["history"][0]["content"].startswith(
        "Summary of previous conversation:",
    )
    assert replace_event["history"][-1]["content"] == "kept assistant"
    mock_summarize_history.assert_called_once()
