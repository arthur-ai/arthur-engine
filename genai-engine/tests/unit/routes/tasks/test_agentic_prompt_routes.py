import random
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from arthur_common.models.response_schemas import TaskResponse
from litellm.exceptions import BadRequestError
from litellm.types.utils import ModelResponse

from src.schemas.agentic_prompt_schemas import AgenticPrompt
from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.mark.unit_tests
def test_get_agentic_prompt_success(client: GenaiEngineTestClientBase):
    """Test successfully getting an agentic prompt"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200
    assert task.is_agentic == True

    # First save a prompt
    prompt_name = "test_prompt"
    prompt_data = {
        "messages": [{"role": "user", "content": "Hello, world!"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
        "config": {
            "temperature": 0.7,
            "max_tokens": 100,
        },
    }

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    # Now get the prompt
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/1",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    prompt_response = response.json()
    assert prompt_response["name"] == prompt_name
    assert prompt_response["messages"] == [{"role": "user", "content": "Hello, world!"}]
    assert prompt_response["model_name"] == "gpt-4"
    assert prompt_response["model_provider"] == "openai"
    assert prompt_response["config"]["temperature"] == 0.7
    assert prompt_response["config"]["max_tokens"] == 100


@pytest.mark.unit_tests
def test_get_agentic_prompt_not_found(client: GenaiEngineTestClientBase):
    """Test getting a prompt that doesn't exist"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Try to get a non-existent prompt
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts/nonexistent_prompt/versions/1",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.unit_tests
def test_get_agentic_prompt_non_agentic_task(client: GenaiEngineTestClientBase):
    """Test getting a prompt from a non-agentic task should fail"""
    # Create a non-agentic task
    task_name = f"non_agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=False)
    assert status_code == 200
    assert task.is_agentic == False

    # Try to get a prompt from non-agentic task
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts/test_prompt/versions/1",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 400
    assert "not agentic" in response.json()["detail"].lower()


@pytest.mark.unit_tests
def test_get_all_agentic_prompts_success(client: GenaiEngineTestClientBase):
    """Test getting all prompts for an agentic task"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Save multiple prompts
    prompts_data = [
        {
            "messages": [{"role": "user", "content": "First prompt"}],
            "model_name": "gpt-4",
            "model_provider": "openai",
        },
        {
            "messages": [{"role": "user", "content": "First prompt"}],
            "model_name": "gpt-4",
            "model_provider": "openai",
        },
        {
            "messages": [{"role": "user", "content": "Second prompt"}],
            "model_name": "gpt-3.5-turbo",
            "model_provider": "openai",
        },
    ]

    prompt_names = ["prompt1", "prompt2", "prompt2"]

    for i, prompt_data in enumerate(prompts_data):
        response = client.base_client.post(
            f"/api/v1/tasks/{task.id}/prompts/{prompt_names[i]}",
            json=prompt_data,
            headers=client.authorized_user_api_key_headers,
        )
        assert response.status_code == 200

    # Get all prompts
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts",
        headers=client.authorized_user_api_key_headers,
        params={"sort": "asc"},
    )
    assert response.status_code == 200

    prompts_response = response.json()
    assert "llm_metadata" in prompts_response
    assert len(prompts_response["llm_metadata"]) == 2

    metadata = prompts_response["llm_metadata"]

    for i, llm_metadata in enumerate(metadata):
        assert llm_metadata["name"] == prompt_names[i]
        assert llm_metadata["versions"] == i + 1
        assert llm_metadata["created_at"] is not None
        assert llm_metadata["latest_version_created_at"] is not None
        assert llm_metadata["deleted_versions"] == []

        created = datetime.fromisoformat(llm_metadata["created_at"])
        latest = datetime.fromisoformat(llm_metadata["latest_version_created_at"])

        if i == 0:
            assert abs((created - latest).total_seconds()) < 1
        else:
            assert created != latest


@pytest.mark.unit_tests
def test_get_all_agentic_prompts_empty(client: GenaiEngineTestClientBase):
    """Test getting all prompts when none exist"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Get all prompts (should be empty)
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    prompts_response = response.json()
    assert "llm_metadata" in prompts_response
    assert len(prompts_response["llm_metadata"]) == 0


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
def test_run_agentic_prompt_success(
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    """Test running an agentic prompt"""
    mock_response = MagicMock(spec=ModelResponse)
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": "Test LLM response",
        "tool_calls": None,
    }
    mock_completion.return_value = mock_response
    mock_completion_cost.return_value = 0.001234

    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # configure a provider
    response = client.base_client.put(
        f"/api/v1/model_providers/openai",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201

    # Run a prompt
    prompt_data = {
        "messages": [{"role": "user", "content": "Hello, world!"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
        "config": {
            "temperature": 0.7,
        },
    }

    response = client.base_client.post(
        f"/api/v1/completions",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    run_response = response.json()
    assert run_response["content"] == "Test LLM response"
    assert run_response["cost"] == "0.001234"


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
def test_run_saved_agentic_prompt_success(
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    """Test running a saved agentic prompt"""
    mock_response = MagicMock(spec=ModelResponse)
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": "Saved prompt response",
        "tool_calls": [{"id": "call_123", "function": {"name": "test_tool"}}],
    }
    mock_completion.return_value = mock_response
    mock_completion_cost.return_value = 0.002345

    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # configure a provider
    response = client.base_client.put(
        f"/api/v1/model_providers/openai",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201

    # First save a prompt
    prompt_data = {
        "messages": [{"role": "user", "content": "Saved prompt content"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
        "config": {
            "temperature": 0.8,
        },
    }

    prompt_name = "saved_prompt"

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    # Now run the saved prompt
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/1/completions",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    run_response = response.json()
    assert run_response["content"] == "Saved prompt response"
    assert run_response["cost"] == "0.002345"
    assert run_response["tool_calls"] == [
        {
            "function": {"arguments": "", "name": "test_tool"},
            "id": "call_123",
            "type": "function",
        },
    ]


@pytest.mark.unit_tests
def test_run_saved_agentic_prompt_not_found(client: GenaiEngineTestClientBase):
    """Test running a saved prompt that doesn't exist"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Try to run a non-existent saved prompt
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/nonexistent_prompt/versions/1/completions",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.unit_tests
def test_save_agentic_prompt_success(client: GenaiEngineTestClientBase):
    """Test saving an agentic prompt"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Save a prompt
    prompt_data = {
        "messages": [{"role": "user", "content": "New prompt content"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
        "tools": [{"type": "function", "function": {"name": "calculator"}}],
        "config": {
            "temperature": 0.5,
            "max_tokens": 200,
            "tool_choice": "auto",
        },
    }

    prompt_name = "new_prompt"

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == prompt_name
    assert response.json()["version"] == 1
    assert response.json()["messages"] == prompt_data["messages"]

    # Verify the prompt was saved by retrieving it
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/1",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    saved_prompt = response.json()
    assert saved_prompt["name"] == "new_prompt"
    assert saved_prompt["config"]["temperature"] == 0.5
    assert saved_prompt["config"]["max_tokens"] == 200
    assert saved_prompt["tools"] == [
        {"type": "function", "function": {"name": "calculator"}},
    ]


@pytest.mark.unit_tests
def test_save_agentic_prompt_duplicate(client: GenaiEngineTestClientBase):
    """Test saving a prompt with duplicate name should be a new version of the prompt"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Save a prompt
    prompt_data = {
        "messages": [{"role": "user", "content": "First prompt"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
    }

    prompt_name = "duplicate_prompt"

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    # Try to save another prompt with the same name
    duplicate_prompt_data = {
        "messages": [{"role": "user", "content": "Second prompt"}],
        "model_name": "gpt-3.5-turbo",
        "model_provider": "openai",
    }

    # test saving a prompt with a duplicate name should be a new version of the prompt
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}",
        json=duplicate_prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == prompt_name
    assert response.json()["version"] == 2
    assert response.json()["messages"] == duplicate_prompt_data["messages"]

    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/2",
        headers=client.authorized_user_api_key_headers,
    )

    assert response.status_code == 200
    assert response.json()["name"] == prompt_name
    assert response.json()["version"] == 2


@pytest.mark.unit_tests
def test_delete_agentic_prompt_success(client: GenaiEngineTestClientBase):
    """Test deleting an agentic prompt"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # First save a prompt
    prompt_data = {
        "messages": [{"role": "user", "content": "To be deleted"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
    }

    prompt_name = "delete_prompt"

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    # Verify the prompt exists
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/1",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200


@pytest.mark.unit_tests
def test_agentic_prompt_routes_require_authentication(
    client: GenaiEngineTestClientBase,
):
    """Test that all agentic prompt routes require authentication"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Test all routes without authentication headers
    routes_and_methods = [
        ("GET", f"/api/v1/tasks/{task.id}/prompts/test_prompt/versions/1"),
        ("GET", f"/api/v1/tasks/{task.id}/prompts"),
        ("POST", f"/api/v1/tasks/{task.id}/prompts/test_prompt/versions/1/completions"),
        ("POST", f"/api/v1/tasks/{task.id}/prompts/test_prompt"),
        ("DELETE", f"/api/v1/tasks/{task.id}/prompts/test_prompt/versions/1"),
    ]

    for method, url in routes_and_methods:
        if method == "GET":
            response = client.base_client.get(url)
        elif method == "POST":
            response = client.base_client.post(url, json={})
        elif method == "DELETE":
            response = client.base_client.delete(url)

        # Should return 401 for unauthorized access
        assert (
            response.status_code == 401
        ), f"Route {method} {url} should require authentication"


@pytest.mark.unit_tests
def test_agentic_prompt_invalid_task_id(client: GenaiEngineTestClientBase):
    """Test agentic prompt routes with invalid task ID"""
    invalid_task_id = "00000000-0000-0000-0000-000000000000"

    response = client.base_client.get(
        f"/api/v1/tasks/{invalid_task_id}/prompts/test_prompt/versions/1",
        headers=client.authorized_user_api_key_headers,
    )
    # Should return 404 for non-existent task
    assert response.status_code == 404


@pytest.mark.unit_tests
def test_agentic_prompt_routes_with_malformed_data(client: GenaiEngineTestClientBase):
    """Test agentic prompt routes with malformed request data"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Test save prompt with missing required fields
    # Missing messages, model_name, model_provider
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/incomplete_prompt",
        json={"model_name": "incomplete_prompt"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 400

    # Test run prompt with invalid data
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/incomplete_prompt/versions/1/completions",
        json={"invalid": "data"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 400

    # Test save prompt with invalid template syntax - should return 400, not 500
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/invalid_template_prompt",
        json={
            "messages": [{"role": "user", "content": "{% end %}"}],
            "model_name": "gpt-4",
            "model_provider": "openai",
        },
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 400


@pytest.mark.unit_tests
@patch("services.prompt.chat_completion_service.completion_cost")
@patch(
    "services.prompt.chat_completion_service.ChatCompletionService.stream_chat_completion",
)
def test_streaming_agentic_prompt(
    mock_stream_chat_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    """Test streaming works for both unsaved and saved agentic prompts"""

    async def mock_stream(*args, **kwargs):
        for chunk in ["chunk1", "chunk2", "chunk3"]:
            yield f"event: chunk\ndata: {chunk}\n\n"

    mock_stream_chat_completion.side_effect = mock_stream
    mock_completion_cost.return_value = 0.001

    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # configure a provider
    response = client.base_client.put(
        f"/api/v1/model_providers/openai",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201

    # Run a streaming prompt (with stream=True in completion_request)
    prompt_data = {
        "messages": [{"role": "user", "content": "Stream this"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
        "config": {
            "temperature": 0.7,
        },
    }

    prompt_name = "streaming_prompt"

    completion_request = {"stream": True}
    unsaved_run_data = prompt_data.copy()
    unsaved_run_data["completion_request"] = completion_request

    # Test streaming an unsaved prompt
    with client.base_client.stream(
        "POST",
        "/api/v1/completions",
        json=unsaved_run_data,
        headers=client.authorized_user_api_key_headers,
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        content = b"".join(response.iter_bytes())
        for chunk in ["chunk1", "chunk2", "chunk3"]:
            assert chunk.encode() in content

    # Save the prompt
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    # Test saved prompt streaming
    with client.base_client.stream(
        "POST",
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/1/completions",
        json=completion_request,
        headers=client.authorized_user_api_key_headers,
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        content = b"".join(response.iter_bytes())
        for chunk in ["chunk1", "chunk2", "chunk3"]:
            assert chunk.encode() in content


@pytest.mark.unit_tests
@pytest.mark.asyncio
@patch("clients.llm.llm_client.litellm.acompletion")
async def test_run_agentic_prompt_stream_badrequest_returns_error_event(
    mock_acompletion,
    client: GenaiEngineTestClientBase,
):
    """Test that /api/v1/completions yields an error event when LiteLLM raises BadRequestError"""

    model_name = "gpt-4o"
    model_provider = "openai"

    # Simulate LiteLLM failure during streaming
    mock_acompletion.side_effect = BadRequestError(
        "OpenAIException - Invalid schema for response_format 'joke_struct': "
        "In context=(), 'additionalProperties' is required to be supplied and to be false.",
        model=model_name,
        llm_provider=model_provider,
    )

    # configure a provider
    response = client.base_client.put(
        f"/api/v1/model_providers/openai",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201

    prompt_data = {
        "messages": [{"role": "user", "content": "tell me a joke"}],
        "model_name": model_name,
        "model_provider": model_provider,
        "completion_request": {"stream": True},
    }

    # Call the route with streaming enabled
    with client.base_client.stream(
        "POST",
        "/api/v1/completions",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

        content = b"".join(response.iter_bytes()).decode()
        assert "event: error" in content
        assert "Invalid schema for response_format" in content


@pytest.mark.unit_tests
def test_get_prompt_does_not_raise_err_for_deleted_prompt(
    client: GenaiEngineTestClientBase,
):
    """
    Test retrieving a deleted prompt does not raise an error
    """
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Save a prompt
    prompt_data = {
        "messages": [{"role": "user", "content": "First prompt"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
    }

    prompt_name = "test_prompt"

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == prompt_name
    assert response.json()["version"] == 1
    assert response.json()["messages"] == prompt_data["messages"]

    # save 2 versions to have a deleted and non-deleted version
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == prompt_name
    assert response.json()["version"] == 2
    assert response.json()["messages"] == prompt_data["messages"]

    # should not spawn an error
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/2",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == prompt_name
    assert response.json()["version"] == 2

    # delete version 2 of the prompt
    response = client.base_client.delete(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/2",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 204

    # should spawn an error
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/2",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == prompt_name
    assert response.json()["version"] == 2
    assert response.json()["messages"] == []
    assert response.json()["model_name"] == ""
    assert response.json()["model_provider"] == "openai"


@pytest.mark.unit_tests
def test_get_all_prompts_includes_deleted_prompts(client: GenaiEngineTestClientBase):
    """
    Test retrieving all prompts includes deleted prompts
    """
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Save a prompt
    prompt_data = {
        "messages": [{"role": "user", "content": "First prompt"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
    }

    prompt_name = "test_prompt"

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == prompt_name
    assert response.json()["version"] == 1
    assert response.json()["messages"] == prompt_data["messages"]

    # save 2 versions to have a deleted and non-deleted version
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == prompt_name
    assert response.json()["version"] == 2
    assert response.json()["messages"] == prompt_data["messages"]

    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts",
        headers=client.authorized_user_api_key_headers,
    )

    metadata = response.json()["llm_metadata"]
    created = datetime.fromisoformat(metadata[0]["created_at"])
    latest = datetime.fromisoformat(metadata[0]["latest_version_created_at"])

    assert response.status_code == 200
    assert len(metadata) == 1
    assert metadata[0]["name"] == prompt_name
    assert metadata[0]["versions"] == 2
    assert metadata[0]["created_at"] is not None
    assert metadata[0]["latest_version_created_at"] is not None
    assert abs((created - latest).total_seconds()) < 1
    assert metadata[0]["deleted_versions"] == []

    # delete version 2 of the prompt
    response = client.base_client.delete(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/2",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 204

    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["llm_metadata"]) == 1

    metadata = response.json()["llm_metadata"]
    created = datetime.fromisoformat(metadata[0]["created_at"])
    latest = datetime.fromisoformat(metadata[0]["latest_version_created_at"])

    assert metadata[0]["name"] == prompt_name
    assert metadata[0]["versions"] == 2
    assert metadata[0]["created_at"] is not None
    assert metadata[0]["latest_version_created_at"] is not None
    assert created != latest
    assert metadata[0]["deleted_versions"] == [2]


@pytest.mark.unit_tests
def test_get_prompt_versions(client: GenaiEngineTestClientBase):
    """Test retrieving all versions of a prompt"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Save a prompt
    prompt_data = {
        "messages": [{"role": "user", "content": "First prompt"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
    }

    prompt_name = "test_prompt"

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == prompt_name
    assert response.json()["version"] == 1
    assert response.json()["messages"] == prompt_data["messages"]

    # save a prompt with a different name
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == prompt_name
    assert response.json()["version"] == 2
    assert response.json()["messages"] == prompt_data["messages"]

    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["versions"]) == 2

    for version in response.json()["versions"]:
        assert version["created_at"] is not None
        assert "deleted_at" not in version
        assert version["model_provider"] == "openai"
        assert version["model_name"] == "gpt-4"
        assert version["num_messages"] == 1
        assert version["num_tools"] == 0

    # soft-delete version 2 of the prompt
    response = client.base_client.delete(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/2",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 204

    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["versions"]) == 2

    for version in response.json()["versions"]:
        assert version["created_at"] is not None
        assert version["model_provider"] == "openai"
        assert version["num_tools"] == 0

        if "deleted_at" in version:
            assert version["num_messages"] == 0
            assert version["model_name"] == ""
        else:
            assert version["num_messages"] == 1
            assert version["model_name"] == "gpt-4"


@pytest.mark.unit_tests
def test_get_unique_prompt_names(client: GenaiEngineTestClientBase):
    """Test retrieving all unique prompt names"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Save a prompt
    prompt_data = {
        "messages": [{"role": "user", "content": "First prompt"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
    }

    prompt_name = "test_prompt"

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == prompt_name
    assert response.json()["version"] == 1
    assert response.json()["messages"] == prompt_data["messages"]

    # save 2 versions to have a deleted and non-deleted version
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == prompt_name
    assert response.json()["version"] == 2
    assert response.json()["messages"] == prompt_data["messages"]

    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["versions"]) == 2

    # delete version 2 of the prompt
    response = client.base_client.delete(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/2",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 204

    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1

    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["versions"]) == 2


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
def test_run_deleted_prompt_spawns_error(
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    """Test running a deleted version of a saved prompt spawns an error"""
    mock_response = MagicMock(spec=ModelResponse)
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": "Test LLM response",
        "tool_calls": None,
    }
    mock_completion.return_value = mock_response
    mock_completion_cost.return_value = 0.001234

    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Save a prompt
    prompt_data = {
        "messages": [{"role": "user", "content": "First prompt"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
    }

    prompt_name = "test_prompt"

    completion_request = {
        "stream": False,
    }

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == prompt_name
    assert response.json()["version"] == 1
    assert response.json()["messages"] == prompt_data["messages"]

    # save 2 versions to have a deleted and non-deleted version
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == prompt_name
    assert response.json()["version"] == 2
    assert response.json()["messages"] == prompt_data["messages"]

    # soft delete version 2 of the prompt
    response = client.base_client.delete(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/2",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 204

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/2/completions",
        json=completion_request,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 400
    assert (
        "cannot run chat completion for this prompt because it was deleted on"
        in response.json()["detail"].lower()
    )

    # running latest should run the latest non-deleted version of a prompt
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/latest/completions",
        json=completion_request,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["content"] == "Test LLM response"
    assert response.json()["cost"] == "0.001234"


@pytest.mark.unit_tests
def test_get_all_prompts_pagination_and_filtering(client: GenaiEngineTestClientBase):
    """Test pagination, sorting, and filtering for get_all_agentic_prompts"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Create prompts with different providers
    for i, name in enumerate(["alpha", "beta", "gamma"]):
        provider = "openai" if i < 2 else "anthropic"
        model = "gpt-4" if provider == "openai" else "claude-3-5-sonnet"
        prompt_data = {
            "messages": [{"role": "user", "content": f"Prompt {name}"}],
            "model_name": model,
            "model_provider": provider,
        }
        response = client.base_client.post(
            f"/api/v1/tasks/{task.id}/prompts/{name}",
            json=prompt_data,
            headers=client.authorized_user_api_key_headers,
        )
        assert response.status_code == 200

    # Test pagination on get_all_prompts
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts",
        headers=client.authorized_user_api_key_headers,
        params={"page": 0, "page_size": 2, "sort": "asc"},
    )
    assert response.status_code == 200
    result = response.json()
    assert len(result["llm_metadata"]) == 2
    assert result["count"] == 3
    assert result["llm_metadata"][0]["name"] == "alpha"

    # Test sorting descending
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts",
        headers=client.authorized_user_api_key_headers,
        params={"sort": "desc"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["llm_metadata"][0]["name"] == "gamma"
    assert result["llm_metadata"][2]["name"] == "alpha"

    # Test filtering by provider
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts",
        headers=client.authorized_user_api_key_headers,
        params={"model_provider": "openai"},
    )
    assert response.status_code == 200
    result = response.json()
    assert len(result["llm_metadata"]) == 2
    assert result["count"] == 2


@pytest.mark.unit_tests
def test_get_prompt_versions_pagination_and_filtering(
    client: GenaiEngineTestClientBase,
):
    """Test pagination, sorting, and filtering for get_prompt_versions"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Create prompts with different versions
    for i in range(4):
        prompt_data = {
            "messages": [{"role": "user", "content": f"Version {i+1}"}],
            "model_name": "gpt-4",
            "model_provider": "openai",
        }
        response = client.base_client.post(
            f"/api/v1/tasks/{task.id}/prompts/alpha",
            json=prompt_data,
            headers=client.authorized_user_api_key_headers,
        )
        assert response.status_code == 200

    # Test version pagination
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts/alpha/versions",
        headers=client.authorized_user_api_key_headers,
        params={"page": 0, "page_size": 2, "sort": "desc"},
    )
    assert response.status_code == 200
    result = response.json()
    assert len(result["versions"]) == 2
    assert result["count"] == 4
    assert result["versions"][0]["version"] == 4

    # Test version range filter
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts/alpha/versions",
        headers=client.authorized_user_api_key_headers,
        params={"min_version": 2, "max_version": 3},
    )
    assert response.status_code == 200
    result = response.json()
    assert len(result["versions"]) == 2
    assert result["count"] == 2

    # Delete a version and test include_deleted filter
    response = client.base_client.delete(
        f"/api/v1/tasks/{task.id}/prompts/alpha/versions/2",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 204

    # Test include deleted (default behavior, exclude_deleted=False)
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts/alpha/versions",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    result = response.json()
    assert result["count"] == 4  # Includes deleted version by default
    versions = [v["version"] for v in result["versions"]]
    assert 2 in versions

    # Test exclude deleted
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts/alpha/versions",
        headers=client.authorized_user_api_key_headers,
        params={"exclude_deleted": True},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["count"] == 3  # One version excluded
    versions = [v["version"] for v in result["versions"]]
    assert 2 not in versions


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
@pytest.mark.parametrize(
    "messages,variables,expected_error",
    [
        ([{"role": "user", "content": "Hello, {{name}}!"}], {"name": "John"}, None),
        ([{"role": "user", "content": "Hello, {{name}}!"}], {"name": ""}, None),
        (
            [{"role": "user", "content": "Hello, {{name}}!"}],
            None,
            "Missing values for the following variables: name",
        ),
        ([{"role": "user", "content": "Hello, name!"}], {"name": "John"}, None),
        ([{"role": "user", "content": "Hello, name!"}], {"first_name": "John"}, None),
        (
            [{"role": "user", "content": "Hello, {{ first_name }} {{ last_name }}!"}],
            {"first_name": "John", "last_name": "Doe"},
            None,
        ),
        (
            [{"role": "user", "content": "Hello, {{ first_name }} {{ last_name }}!"}],
            {"first_name": "John", "name": "Doe"},
            "Missing values for the following variables: last_name",
        ),
        (
            [{"role": "user", "content": "Hello, {{ first_name }} {{ last_name }}!"}],
            {"name1": "John", "name2": "Doe"},
            "Missing values for the following variables: first_name, last_name",
        ),
        (
            [{"role": "user", "content": "Hello, {{ first_name }} {last_name}!"}],
            {"first_name": "John", "name": "Doe"},
            None,
        ),
        (
            [{"role": "user", "content": "Hello, {{ first_name }} {{ last_name }}!"}],
            {"first_name": "", "last_name": ""},
            None,
        ),
    ],
)
def test_run_agentic_prompt_strict_mode(
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
    messages,
    variables,
    expected_error,
):
    """Test running an agentic prompt with strict mode"""
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    mock_response = MagicMock(spec=ModelResponse)
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": "Test LLM response",
        "tool_calls": None,
    }
    mock_completion.return_value = mock_response
    mock_completion_cost.return_value = 0.001234

    prompt_name = "test_prompt"

    prompt_data = {
        "messages": messages,
        "model_name": "gpt-4",
        "model_provider": "openai",
    }

    completion_request = {
        "strict": True,
    }

    if variables:
        completion_request["variables"] = [
            {"name": name, "value": value} for name, value in variables.items()
        ]

    # Save prompt
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    prompt_data["completion_request"] = completion_request

    # run unsaved prompt with strict=True
    response = client.base_client.post(
        f"/api/v1/completions",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    if expected_error:
        assert response.status_code == 400
        assert response.json()["detail"] == expected_error
    else:
        assert response.status_code == 200

    # run saved prompt with strict=True
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/latest/completions",
        json=completion_request,
        headers=client.authorized_user_api_key_headers,
    )
    if expected_error:
        assert response.status_code == 400
        assert response.json()["detail"] == expected_error
    else:
        assert response.status_code == 200

    # Test the renders endpoint with strict=True
    render_request = {
        "completion_request": {
            "strict": True,
        },
    }
    if variables:
        render_request["completion_request"]["variables"] = [
            {"name": name, "value": value} for name, value in variables.items()
        ]

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/latest/renders",
        json=render_request,
        headers=client.authorized_user_api_key_headers,
    )
    if expected_error:
        assert response.status_code == 400
        assert response.json()["detail"] == expected_error
    else:
        assert response.status_code == 200
        rendered_prompt = response.json()
        assert rendered_prompt["messages"] is not None
        # Verify the template was actually rendered if we have variables
        if variables:
            for message in rendered_prompt["messages"]:
                # Make sure no template syntax remains in the content
                assert "{{" not in message.get("content", "")
                assert "}}" not in message.get("content", "")

    # set strict=False
    completion_request["strict"] = False
    prompt_data["completion_request"] = completion_request

    # run unsaved prompt with strict=False (should never raise an err for missing variables)
    response = client.base_client.post(
        f"/api/v1/completions",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    # run saved prompt with strict=False
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/latest/completions",
        json=completion_request,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    # Test the renders endpoint with strict=False (should never raise an error)
    render_request["completion_request"]["strict"] = False
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/latest/renders",
        json=render_request,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    rendered_prompt = response.json()
    assert rendered_prompt["messages"] is not None


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "endpoint_type,messages,variables,strict,expected_status,expected_error,expected_content",
    [
        # Unsaved endpoint: successful render with all variables
        (
            "unsaved",
            [
                {
                    "role": "system",
                    "content": "You are a helpful assistant named {{assistant_name}}.",
                },
                {"role": "user", "content": "Hello {{user_name}}, how can I help you?"},
            ],
            [
                {"name": "assistant_name", "value": "Claude"},
                {"name": "user_name", "value": "John"},
            ],
            False,
            200,
            None,
            ["Claude", "John"],
        ),
        # Unsaved endpoint: strict mode with missing variables
        (
            "unsaved",
            [{"role": "user", "content": "Hello {{name}}, your age is {{age}}."}],
            [{"name": "name", "value": "John"}],
            True,
            400,
            "Missing values for the following variables: age",
            None,
        ),
        # Unsaved endpoint: strict mode with all variables provided
        (
            "unsaved",
            [{"role": "user", "content": "Hello {{name}}, your age is {{age}}."}],
            [{"name": "name", "value": "John"}, {"name": "age", "value": "30"}],
            True,
            200,
            None,
            ["John", "30"],
        ),
        # Saved endpoint: successful render with all variables
        (
            "saved",
            [
                {"role": "system", "content": "You are {{bot_name}}."},
                {"role": "user", "content": "Hello, I'm {{user_name}}."},
            ],
            [
                {"name": "bot_name", "value": "Assistant"},
                {"name": "user_name", "value": "Alice"},
            ],
            False,
            200,
            None,
            ["Assistant", "Alice"],
        ),
    ],
)
def test_render_endpoints(
    client: GenaiEngineTestClientBase,
    endpoint_type: str,
    messages: list,
    variables: list,
    strict: bool,
    expected_status: int,
    expected_error: str | None,
    expected_content: list | None,
):
    """Test rendering both saved and unsaved agentic prompts with variables and strict mode"""

    if endpoint_type == "unsaved":
        # Test unsaved render endpoint
        render_request = {
            "messages": messages,
            "completion_request": {
                "variables": variables,
                "strict": strict,
            },
        }

        response = client.base_client.post(
            "/api/v1/prompt_renders",
            json=render_request,
            headers=client.authorized_user_api_key_headers,
        )
    else:
        # Test saved render endpoint - create a task and prompt first
        task_name = f"agentic_task_{random.random()}"
        status_code, task = client.create_task(task_name, is_agentic=True)
        assert status_code == 200

        prompt_name = "test_prompt"
        prompt_data = {
            "messages": messages,
            "model_name": "gpt-4",
            "model_provider": "openai",
        }

        response = client.base_client.post(
            f"/api/v1/tasks/{task.id}/prompts/{prompt_name}",
            json=prompt_data,
            headers=client.authorized_user_api_key_headers,
        )
        assert response.status_code == 200

        render_request = {
            "completion_request": {
                "variables": variables,
                "strict": strict,
            },
        }

        response = client.base_client.post(
            f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/latest/renders",
            json=render_request,
            headers=client.authorized_user_api_key_headers,
        )

    # Verify response
    assert response.status_code == expected_status

    if expected_error:
        assert response.json()["detail"] == expected_error
    else:
        rendered_prompt = response.json()
        assert rendered_prompt["messages"] is not None

        # Check that expected content is in the rendered messages
        if expected_content:
            for content_str in expected_content:
                assert any(
                    content_str in msg.get("content", "")
                    for msg in rendered_prompt["messages"]
                )

            # Verify no template syntax remains
            for msg in rendered_prompt["messages"]:
                assert "{{" not in msg.get("content", "")
                assert "}}" not in msg.get("content", "")


@pytest.mark.unit_tests
@pytest.mark.parametrize("prompt_version", ["latest", "1", "datetime", "tag"])
def test_get_agentic_prompt_by_version_route(
    client: GenaiEngineTestClientBase,
    create_agentic_task: TaskResponse,
    create_agentic_prompt: AgenticPrompt,
    prompt_version,
):
    """Test getting an agentic prompt with different version formats (latest, version number, datetime, tag)"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    task = create_agentic_task

    prompt = create_agentic_prompt

    if prompt_version == "datetime":
        prompt_version = prompt.created_at.strftime("%Y-%m-%dT%H:%M:%S")
    elif prompt_version == "tag":
        # Add a tag to the prompt version using the API
        test_tag = "test_tag"
        tag_response = client.base_client.put(
            f"/api/v1/tasks/{task.id}/prompts/{prompt.name}/versions/1/tags",
            json={"tag": test_tag},
            headers=client.authorized_user_api_key_headers,
        )
        assert tag_response.status_code == 200
        prompt_version = test_tag

    # Get the prompt using different version formats
    status_code, prompt_response = client.get_agentic_prompt(
        task_id=task.id,
        prompt_name=prompt.name,
        version=prompt_version,
    )
    assert status_code == 200
    assert prompt_response.name == prompt.name
    assert [
        message.model_dump(exclude_none=True) for message in prompt_response.messages
    ] == [{"role": "user", "content": "Hello, world!"}]
    assert prompt_response.model_name == "gpt-4"
    assert prompt_response.model_provider == "openai"
    assert prompt_response.version == 1
    assert prompt_response.config.temperature == 0.7
    assert prompt_response.config.max_tokens == 100


@pytest.mark.unit_tests
@pytest.mark.parametrize("prompt_version", ["latest", "1", "datetime", "tag"])
def test_soft_delete_agentic_prompt_by_version_route(
    client: GenaiEngineTestClientBase,
    prompt_version,
):
    """Test soft deleting an agentic prompt with different version formats (latest, version number, datetime, tag)"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Save a prompt
    prompt_name = "test_prompt"
    prompt_data = {
        "messages": [{"role": "user", "content": "Hello, world!"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
        "config": {
            "temperature": 0.7,
            "max_tokens": 100,
        },
    }

    save_response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert save_response.status_code == 200

    if prompt_version == "datetime":
        prompt_version = save_response.json()["created_at"]
    # Add a tag if testing tag-based version
    elif prompt_version == "tag":
        test_tag = "test_tag"
        tag_response = client.base_client.put(
            f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/1/tags",
            json={"tag": test_tag},
            headers=client.authorized_user_api_key_headers,
        )
        assert tag_response.status_code == 200
        prompt_version = test_tag

    # Get the prompt using different version formats
    response = client.base_client.delete(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/{prompt_version}",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 204

    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/{prompt_version}",
        headers=client.authorized_user_api_key_headers,
    )
    if prompt_version == "latest" or prompt_version == "test_tag":
        assert response.status_code == 404
        assert (
            response.json()["detail"]
            == f"'{prompt_name}' (version '{prompt_version}') not found for task '{task.id}'"
        )
    else:
        assert response.status_code == 200

        prompt_response = response.json()
        assert prompt_response["name"] == prompt_name
        assert prompt_response["messages"] == []
        assert prompt_response["model_name"] == ""
        assert prompt_response["model_provider"] == "openai"
        assert prompt_response["deleted_at"] is not None


@pytest.mark.unit_tests
def test_get_agentic_prompt_by_tag_route_success(
    client: GenaiEngineTestClientBase,
):
    """Test getting an agentic prompt by tag route successfully"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Save a prompt
    prompt_name = "test_prompt"
    prompt_data = {
        "messages": [{"role": "user", "content": "Hello, world!"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
        "config": {
            "temperature": 0.7,
            "max_tokens": 100,
        },
    }

    save_response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert save_response.status_code == 200

    add_tag_response = client.base_client.put(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/latest/tags",
        json={"tag": "test_tag"},
        headers=client.authorized_user_api_key_headers,
    )
    assert add_tag_response.status_code == 200

    # Get the prompt using different version formats
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/tags/test_tag",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    prompt_response = response.json()
    assert prompt_response["name"] == prompt_name
    assert prompt_response["messages"] == prompt_data["messages"]
    assert prompt_response["model_name"] == "gpt-4"
    assert prompt_response["model_provider"] == "openai"
    assert prompt_response["tags"] == ["test_tag"]


@pytest.mark.unit_tests
def test_get_agentic_prompt_by_tag_route_errors(
    client: GenaiEngineTestClientBase,
):
    """Test getting an agentic prompt by tag route successfully"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    prompt_name = "test_prompt"

    # Test getting the prompt by tag that doesn't exist
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/tags/test_tag",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 404


@pytest.mark.unit_tests
def test_add_agentic_prompt_by_tag_route_success(
    client: GenaiEngineTestClientBase,
):
    """Test adding a tag to an agentic prompt successfully"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Save a prompt
    prompt_name = "test_prompt"
    prompt_data = {
        "messages": [{"role": "user", "content": "Hello, world!"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
        "config": {
            "temperature": 0.7,
            "max_tokens": 100,
        },
    }

    save_response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert save_response.status_code == 200

    add_tag_response = client.base_client.put(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/latest/tags",
        json={"tag": "test_tag"},
        headers=client.authorized_user_api_key_headers,
    )
    assert add_tag_response.status_code == 200

    prompt_response = add_tag_response.json()
    assert prompt_response["name"] == prompt_name
    assert prompt_response["messages"] == prompt_data["messages"]
    assert prompt_response["model_name"] == "gpt-4"
    assert prompt_response["model_provider"] == "openai"
    assert prompt_response["tags"] == ["test_tag"]


@pytest.mark.unit_tests
def test_add_agentic_prompt_by_tag_route_errors(
    client: GenaiEngineTestClientBase,
):
    """Test getting an agentic prompt by tag route successfully"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # test adding a tag to a prompt that doesn't exist
    response = client.base_client.put(
        f"/api/v1/tasks/{task.id}/prompts/test_prompt/versions/latest/tags",
        json={"tag": "test_tag"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == f"'test_prompt' (version 'latest') not found for task '{task.id}'"
    )

    # Save a prompt
    prompt_name = "test_prompt"
    prompt_data = {
        "messages": [{"role": "user", "content": "Hello, world!"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
        "config": {
            "temperature": 0.7,
            "max_tokens": 100,
        },
    }

    save_response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert save_response.status_code == 200

    # test adding an empty tag to a prompt
    response = client.base_client.put(
        f"/api/v1/tasks/{task.id}/prompts/test_prompt/versions/latest/tags",
        json={"tag": ""},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Tag cannot be empty"

    # test adding latest tag to a prompt
    response = client.base_client.put(
        f"/api/v1/tasks/{task.id}/prompts/test_prompt/versions/latest/tags",
        json={"tag": "latest"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "'latest' is a reserved tag"

    # soft delete the prompt version
    response = client.base_client.delete(
        f"/api/v1/tasks/{task.id}/prompts/test_prompt/versions/latest",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 204

    # test adding tag to a deleted prompt version
    response = client.base_client.put(
        f"/api/v1/tasks/{task.id}/prompts/test_prompt/versions/1/tags",
        json={"tag": "test_tag"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "Cannot add tag to a deleted version of 'test_prompt'"
    )


@pytest.mark.unit_tests
def test_delete_agentic_prompt_by_tag_route_success(
    client: GenaiEngineTestClientBase,
):
    """Test deleting a tag from an agentic prompt successfully"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Save a prompt
    prompt_name = "test_prompt"
    prompt_data = {
        "messages": [{"role": "user", "content": "Hello, world!"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
        "config": {
            "temperature": 0.7,
            "max_tokens": 100,
        },
    }

    save_response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert save_response.status_code == 200

    add_tag_response = client.base_client.put(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/latest/tags",
        json={"tag": "test_tag"},
        headers=client.authorized_user_api_key_headers,
    )
    assert add_tag_response.status_code == 200

    prompt_response = add_tag_response.json()
    assert prompt_response["name"] == prompt_name
    assert prompt_response["messages"] == prompt_data["messages"]
    assert prompt_response["model_name"] == "gpt-4"
    assert prompt_response["model_provider"] == "openai"
    assert prompt_response["version"] == 1
    assert prompt_response["tags"] == ["test_tag"]

    delete_tag_response = client.base_client.delete(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/latest/tags/test_tag",
        headers=client.authorized_user_api_key_headers,
    )
    assert delete_tag_response.status_code == 204

    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/tags/test_tag",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == f"Tag 'test_tag' not found for task '{task.id}' and item '{prompt_name}'."
    )


@pytest.mark.unit_tests
def test_delete_agentic_prompt_by_tag_route_errors(
    client: GenaiEngineTestClientBase,
):
    """Test deleting a tag from an agentic prompt route errors"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    prompt_name = "test_prompt"

    # test deleting a tag from a prompt that doesn't exist
    response = client.base_client.delete(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/latest/tags/test_tag",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == f"No matching version of '{prompt_name}' found for task '{task.id}'"
    )

    # Save a prompt
    prompt_data = {
        "messages": [{"role": "user", "content": "Hello, world!"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
        "config": {
            "temperature": 0.7,
            "max_tokens": 100,
        },
    }

    # save a prompt
    save_response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert save_response.status_code == 200

    # test deleting a tag that doesn't exist from an existing prompt
    response = client.base_client.delete(
        f"/api/v1/tasks/{task.id}/prompts/test_prompt/versions/latest/tags/test_tag",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == f"Tag 'test_tag' not found for task '{task.id}', item '{prompt_name}' and version 'latest'."
    )


@pytest.mark.unit_tests
def test_soft_delete_agentic_prompt_deletes_tags_successfully(
    client: GenaiEngineTestClientBase,
):
    """Test soft deleting an agentic prompt deletes all tags associated with that version"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Save a prompt
    prompt_name = "test_prompt"
    prompt_data = {
        "messages": [{"role": "user", "content": "Hello, world!"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
        "config": {
            "temperature": 0.7,
            "max_tokens": 100,
        },
    }

    # save a prompt
    save_response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert save_response.status_code == 200

    # add a tag to the prompt
    add_tag_response = client.base_client.put(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/latest/tags",
        json={"tag": "test_tag"},
        headers=client.authorized_user_api_key_headers,
    )
    assert add_tag_response.status_code == 200

    # soft delete the prompt version
    response = client.base_client.delete(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/latest",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 204

    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}/versions/tags/test_tag",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 404
    assert (
        response.json()["detail"]
        == f"Tag 'test_tag' not found for task '{task.id}' and item '{prompt_name}'."
    )


@pytest.mark.unit_tests
def test_malformed_response_format_errors_on_creation(
    client: GenaiEngineTestClientBase,
):
    """Test saving a prompt with a malformed response format errors"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    prompt_name = "test_prompt"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    prompt_data = {
        "messages": [{"role": "user", "content": "Test"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
        "config": {},
    }

    json_schema = {
        "name": "test_schema",
        "description": "test schema description",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "test_prop": {"type": "string", "description": "test prop description"},
            },
            "required": ["test_prop"],
            "additionalProperties": False,
        },
    }

    # test saving a prompt with a json_schema response format without a json_schema object raises an error
    prompt_data["config"]["response_format"] = {"type": "json_schema"}
    save_response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert save_response.status_code == 400
    assert (
        "json_schema object is required when using type='json_schema'"
        in save_response.json()["detail"]
    )

    # test saving a prompt with a JSON mode response format errors if json_schema is provided
    prompt_data["config"]["response_format"] = {
        "type": "json_object",
        "json_schema": json_schema,
    }
    save_response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert save_response.status_code == 400
    assert (
        f'response format must only be {{"type": "json_object"}} when using type="json_object"'
        in save_response.json()["detail"]
    )

    # test saving a prompt with a text mode response format errors if json_schema is provided
    prompt_data["config"]["response_format"] = {
        "type": "text",
        "json_schema": json_schema,
    }
    save_response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert save_response.status_code == 400
    assert (
        f'response format must only be {{"type": "text"}} when using type="text"'
        in save_response.json()["detail"]
    )


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "messages, expected_variables",
    [
        ([{"role": "user", "content": "Hello, world!"}], []),
        ([{"role": "user", "content": "Hello, {{name}}!"}], ["name"]),
        (
            [
                {
                    "role": "user",
                    "content": "Hello, {{name}}! What is the capital of {{country}}?",
                },
            ],
            ["name", "country"],
        ),
        (
            [
                {"role": "system", "content": "Hello, {{name}}!"},
                {"role": "user", "content": "What is the capital of {{country}}?"},
            ],
            ["name", "country"],
        ),
        (
            [
                {"role": "system", "content": "Hello, {name}!"},
                {"role": "user", "content": "What is the capital of {{country}}?"},
            ],
            ["country"],
        ),
        (
            [
                {
                    "role": "user",
                    "content": "{% if product %}Interested in {{product}}{% endif %}",
                },
            ],
            ["product"],
        ),
        (
            [
                {
                    "role": "system",
                    "content": [{"type": "text", "text": "Hello, {{name}}!"}],
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What is the capital of {{country}}?"},
                    ],
                },
            ],
            ["name", "country"],
        ),
        (
            [
                {
                    "role": "system",
                    "content": [
                        {"type": "image_url", "image_url": {"url": "{{image_url}}"}},
                    ],
                },
            ],
            [],
        ),
        (
            [
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": "{{audio_data}}",
                                "format": "{{audio_format}}",
                            },
                        },
                    ],
                },
            ],
            [],
        ),
    ],
)
def test_get_unsaved_prompt_variables_list_route_success(
    client: GenaiEngineTestClientBase,
    messages: list,
    expected_variables: list,
):
    """Test getting the list of variables needed from an unsaved prompt's messages route successfully"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    message_request = {
        "messages": messages,
    }

    response = client.base_client.post(
        "/api/v1/prompt_variables",
        json=message_request,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    response_variables = response.json()["variables"].sort()
    expected_variables = expected_variables.sort()

    assert response_variables == expected_variables


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "messages",
    [
        ([{"role": "user", "content": "Hello {{ user"}]),
        ([{"role": "user", "content": "{% if user %}Hi {{ user }}"}]),
        ([{"role": "user", "content": "Hello {% user }}"}]),
        ([{"role": "user", "content": "{{ for item in list }}"}]),
        ([{"role": "user", "content": "{{ name | }}"}]),
        ([{"role": "user", "content": "{{ 1 + }}"}]),
    ],
)
def test_get_unsaved_prompt_variables_list_jinja_syntax_errors(
    client: GenaiEngineTestClientBase,
    messages: list,
):
    """
    Test getting the list of variables needed from an unsaved prompt's messages
    raises jinja2 template syntax errors for malformed messages
    """
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    message_request = {
        "messages": messages,
    }

    response = client.base_client.post(
        "/api/v1/prompt_variables",
        json=message_request,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 400
    assert (
        "Invalid Jinja2 template syntax in prompt messages" in response.json()["detail"]
    )
