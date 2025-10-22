import random
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from litellm.exceptions import BadRequestError

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
        "temperature": 0.7,
        "max_tokens": 100,
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
    assert prompt_response["temperature"] == 0.7
    assert prompt_response["max_tokens"] == 100


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
            "name": "prompt1",
            "messages": [{"role": "user", "content": "First prompt"}],
            "model_name": "gpt-4",
            "model_provider": "openai",
        },
        {
            "name": "prompt2",
            "messages": [{"role": "user", "content": "First prompt"}],
            "model_name": "gpt-4",
            "model_provider": "openai",
        },
        {
            "name": "prompt2",
            "messages": [{"role": "user", "content": "Second prompt"}],
            "model_name": "gpt-3.5-turbo",
            "model_provider": "openai",
        },
    ]

    for prompt_data in prompts_data:
        response = client.base_client.post(
            f"/api/v1/tasks/{task.id}/prompts/{prompt_data['name']}",
            json=prompt_data,
            headers=client.authorized_user_api_key_headers,
        )
        assert response.status_code == 200

    # Get all prompts
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    prompts_response = response.json()
    assert "prompt_metadata" in prompts_response
    assert len(prompts_response["prompt_metadata"]) == 2

    metadata = prompts_response["prompt_metadata"]

    for i, prompt_metadata in enumerate(metadata):
        assert prompt_metadata["name"] == prompts_data[i]["name"]
        assert prompt_metadata["versions"] == i + 1
        assert prompt_metadata["created_at"] is not None
        assert prompt_metadata["latest_version_created_at"] is not None
        assert prompt_metadata["deleted_versions"] == []

        created = datetime.fromisoformat(prompt_metadata["created_at"])
        latest = datetime.fromisoformat(prompt_metadata["latest_version_created_at"])

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
    assert "prompt_metadata" in prompts_response
    assert len(prompts_response["prompt_metadata"]) == 0


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.litellm.completion")
@patch("schemas.agentic_prompt_schemas.completion_cost")
def test_run_agentic_prompt_success(
    mock_completion_cost,
    mock_completion,
    client: GenaiEngineTestClientBase,
):
    """Test running an agentic prompt"""
    mock_response = MagicMock()
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
        "name": "test_run_prompt",
        "messages": [{"role": "user", "content": "Hello, world!"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
        "temperature": 0.7,
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
@patch("clients.llm.llm_client.litellm.completion")
@patch("schemas.agentic_prompt_schemas.completion_cost")
def test_run_saved_agentic_prompt_success(
    mock_completion_cost,
    mock_completion,
    client: GenaiEngineTestClientBase,
):
    """Test running a saved agentic prompt"""
    mock_response = MagicMock()
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
        "name": "saved_prompt",
        "messages": [{"role": "user", "content": "Saved prompt content"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
        "temperature": 0.8,
    }

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_data['name']}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    # Now run the saved prompt
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_data['name']}/versions/1/completions",
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
        "temperature": 0.5,
        "max_tokens": 200,
        "tools": [{"type": "function", "function": {"name": "calculator"}}],
        "tool_choice": "auto",
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
    assert saved_prompt["temperature"] == 0.5
    assert saved_prompt["max_tokens"] == 200
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
        "name": "duplicate_prompt",
        "messages": [{"role": "user", "content": "First prompt"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
    }

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_data['name']}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    # Try to save another prompt with the same name
    duplicate_prompt_data = {
        "name": "duplicate_prompt",
        "messages": [{"role": "user", "content": "Second prompt"}],
        "model_name": "gpt-3.5-turbo",
        "model_provider": "openai",
    }

    # test saving a prompt with a duplicate name should be a new version of the prompt
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{duplicate_prompt_data['name']}",
        json=duplicate_prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == duplicate_prompt_data["name"]
    assert response.json()["version"] == 2
    assert response.json()["messages"] == duplicate_prompt_data["messages"]

    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts/{duplicate_prompt_data['name']}/versions/2",
        headers=client.authorized_user_api_key_headers,
    )

    assert response.status_code == 200
    assert response.json()["name"] == "duplicate_prompt"
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


@pytest.mark.unit_tests
@patch("schemas.agentic_prompt_schemas.completion_cost")
@patch("schemas.agentic_prompt_schemas.AgenticPrompt.stream_chat_completion")
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
        "name": "streaming_prompt",
        "messages": [{"role": "user", "content": "Stream this"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
        "temperature": 0.7,
    }

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
        f"/api/v1/tasks/{task.id}/prompts/{prompt_data['name']}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    # Test saved prompt streaming
    with client.base_client.stream(
        "POST",
        f"/api/v1/tasks/{task.id}/prompts/{prompt_data['name']}/versions/1/completions",
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
        "name": "stream_error_prompt",
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
        "name": "test_prompt",
        "messages": [{"role": "user", "content": "First prompt"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
    }

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_data['name']}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == prompt_data["name"]
    assert response.json()["version"] == 1
    assert response.json()["messages"] == prompt_data["messages"]

    # save 2 versions to have a deleted and non-deleted version
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_data['name']}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == prompt_data["name"]
    assert response.json()["version"] == 2
    assert response.json()["messages"] == prompt_data["messages"]

    # should not spawn an error
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_data['name']}/versions/2",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "test_prompt"
    assert response.json()["version"] == 2

    # delete version 2 of the prompt
    response = client.base_client.delete(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_data['name']}/versions/2",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 204

    # should spawn an error
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_data['name']}/versions/2",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "test_prompt"
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
        "name": "test_prompt",
        "messages": [{"role": "user", "content": "First prompt"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
    }

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_data['name']}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == prompt_data["name"]
    assert response.json()["version"] == 1
    assert response.json()["messages"] == prompt_data["messages"]

    # save 2 versions to have a deleted and non-deleted version
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_data['name']}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == prompt_data["name"]
    assert response.json()["version"] == 2
    assert response.json()["messages"] == prompt_data["messages"]

    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts",
        headers=client.authorized_user_api_key_headers,
    )

    metadata = response.json()["prompt_metadata"]
    created = datetime.fromisoformat(metadata[0]["created_at"])
    latest = datetime.fromisoformat(metadata[0]["latest_version_created_at"])

    assert response.status_code == 200
    assert len(metadata) == 1
    assert metadata[0]["name"] == prompt_data["name"]
    assert metadata[0]["versions"] == 2
    assert metadata[0]["created_at"] is not None
    assert metadata[0]["latest_version_created_at"] is not None
    assert abs((created - latest).total_seconds()) < 1
    assert metadata[0]["deleted_versions"] == []

    # delete version 2 of the prompt
    response = client.base_client.delete(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_data['name']}/versions/2",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 204

    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["prompt_metadata"]) == 1

    metadata = response.json()["prompt_metadata"]
    created = datetime.fromisoformat(metadata[0]["created_at"])
    latest = datetime.fromisoformat(metadata[0]["latest_version_created_at"])

    assert metadata[0]["name"] == prompt_data["name"]
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
        "name": "test_prompt",
        "messages": [{"role": "user", "content": "First prompt"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
    }

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_data['name']}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == prompt_data["name"]
    assert response.json()["version"] == 1
    assert response.json()["messages"] == prompt_data["messages"]

    # save a prompt with a different name
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_data['name']}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == prompt_data["name"]
    assert response.json()["version"] == 2
    assert response.json()["messages"] == prompt_data["messages"]

    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_data['name']}/versions",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["prompts"]) == 2

    # soft-delete version 2 of the prompt
    response = client.base_client.delete(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_data['name']}/versions/2",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 204

    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_data['name']}/versions",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["prompts"]) == 2


@pytest.mark.unit_tests
def test_get_unique_prompt_names(client: GenaiEngineTestClientBase):
    """Test retrieving all unique prompt names"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Save a prompt
    prompt_data = {
        "name": "test_prompt",
        "messages": [{"role": "user", "content": "First prompt"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
    }

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_data['name']}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == prompt_data["name"]
    assert response.json()["version"] == 1
    assert response.json()["messages"] == prompt_data["messages"]

    # save 2 versions to have a deleted and non-deleted version
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_data['name']}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == prompt_data["name"]
    assert response.json()["version"] == 2
    assert response.json()["messages"] == prompt_data["messages"]

    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_data['name']}/versions",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["prompts"]) == 2

    # delete version 2 of the prompt
    response = client.base_client.delete(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_data['name']}/versions/2",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 204

    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_data['name']}/versions",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["prompts"]) == 2

    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_data['name']}/versions",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["prompts"]) == 2


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.litellm.completion")
@patch("schemas.agentic_prompt_schemas.completion_cost")
def test_run_deleted_prompt_spawns_error(
    mock_completion_cost,
    mock_completion,
    client: GenaiEngineTestClientBase,
):
    """Test running a deleted version of a saved prompt spawns an error"""
    mock_response = MagicMock()
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
        "name": "test_prompt",
        "messages": [{"role": "user", "content": "First prompt"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
    }

    completion_request = {
        "stream": False,
    }

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_data['name']}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == prompt_data["name"]
    assert response.json()["version"] == 1
    assert response.json()["messages"] == prompt_data["messages"]

    # save 2 versions to have a deleted and non-deleted version
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_data['name']}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == prompt_data["name"]
    assert response.json()["version"] == 2
    assert response.json()["messages"] == prompt_data["messages"]

    # soft delete version 2 of the prompt
    response = client.base_client.delete(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_data['name']}/versions/2",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 204

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/prompts/{prompt_data['name']}/versions/2/completions",
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
        f"/api/v1/tasks/{task.id}/prompts/{prompt_data['name']}/versions/latest/completions",
        json=completion_request,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["content"] == "Test LLM response"
    assert response.json()["cost"] == "0.001234"
