import random
from unittest.mock import MagicMock, patch

import pytest

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

    response = client.base_client.put(
        f"/api/v1/{task.id}/agentic_prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    # Now get the prompt
    response = client.base_client.get(
        f"/api/v1/{task.id}/agentic_prompts/{prompt_name}/versions/1",
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
        f"/api/v1/{task.id}/agentic_prompts/nonexistent_prompt/versions/1",
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
        f"/api/v1/{task.id}/agentic_prompts/test_prompt/versions/1",
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
            "messages": [{"role": "user", "content": "Second prompt"}],
            "model_name": "gpt-3.5-turbo",
            "model_provider": "openai",
        },
    ]

    for prompt_data in prompts_data:
        response = client.base_client.put(
            f"/api/v1/{task.id}/agentic_prompts/{prompt_data['name']}",
            json=prompt_data,
            headers=client.authorized_user_api_key_headers,
        )
        assert response.status_code == 200

    # Get all prompts
    response = client.base_client.get(
        f"/api/v1/{task.id}/agentic_prompts",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    prompts_response = response.json()
    assert "prompts" in prompts_response
    assert len(prompts_response["prompts"]) == 2

    prompt_names = [p["name"] for p in prompts_response["prompts"]]
    assert "prompt1" in prompt_names
    assert "prompt2" in prompt_names


@pytest.mark.unit_tests
def test_get_all_agentic_prompts_empty(client: GenaiEngineTestClientBase):
    """Test getting all prompts when none exist"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Get all prompts (should be empty)
    response = client.base_client.get(
        f"/api/v1/{task.id}/agentic_prompts",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    prompts_response = response.json()
    assert "prompts" in prompts_response
    assert len(prompts_response["prompts"]) == 0


@pytest.mark.unit_tests
@patch("schemas.agentic_prompt_schemas.completion")
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
@patch("schemas.agentic_prompt_schemas.completion")
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

    # First save a prompt
    prompt_data = {
        "name": "saved_prompt",
        "messages": [{"role": "user", "content": "Saved prompt content"}],
        "model_name": "gpt-4",
        "model_provider": "openai",
        "temperature": 0.8,
    }

    response = client.base_client.put(
        f"/api/v1/{task.id}/agentic_prompts/{prompt_data['name']}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    # Now run the saved prompt
    response = client.base_client.post(
        f"/api/v1/task/{task.id}/prompt/{prompt_data['name']}/versions/1/completions",
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
        f"/api/v1/task/{task.id}/prompt/nonexistent_prompt/versions/1/completions",
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

    response = client.base_client.put(
        f"/api/v1/{task.id}/agentic_prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Prompt saved successfully"

    # Verify the prompt was saved by retrieving it
    response = client.base_client.get(
        f"/api/v1/{task.id}/agentic_prompts/{prompt_name}/versions/1",
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
    """Test saving a prompt with duplicate name should fail"""
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

    response = client.base_client.put(
        f"/api/v1/{task.id}/agentic_prompts/{prompt_data['name']}",
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

    response = client.base_client.put(
        f"/api/v1/{task.id}/agentic_prompts/{duplicate_prompt_data['name']}",
        json=duplicate_prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


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

    response = client.base_client.put(
        f"/api/v1/{task.id}/agentic_prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    # Verify the prompt exists
    response = client.base_client.get(
        f"/api/v1/{task.id}/agentic_prompts/{prompt_name}/versions/1",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    # Delete the prompt
    response = client.base_client.delete(
        f"/api/v1/{task.id}/agentic_prompts/{prompt_name}/versions/1",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Prompt deleted successfully"

    # Verify the prompt no longer exists
    response = client.base_client.get(
        f"/api/v1/{task.id}/agentic_prompts/{prompt_name}/versions/1",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


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
        ("GET", f"/api/v1/{task.id}/agentic_prompts/test_prompt/versions/1"),
        ("GET", f"/api/v1/{task.id}/agentic_prompts"),
        ("POST", f"/api/v1/task/{task.id}/prompt/test_prompt/versions/1/completions"),
        ("PUT", f"/api/v1/{task.id}/agentic_prompts/test_prompt"),
        ("DELETE", f"/api/v1/{task.id}/agentic_prompts/test_prompt/versions/1"),
    ]

    for method, url in routes_and_methods:
        if method == "GET":
            response = client.base_client.get(url)
        elif method == "POST":
            response = client.base_client.post(url, json={})
        elif method == "PUT":
            response = client.base_client.put(url, json={})
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
        f"/api/v1/{invalid_task_id}/agentic_prompts/test_prompt/versions/1",
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
    response = client.base_client.put(
        f"/api/v1/{task.id}/agentic_prompts/incomplete_prompt",
        json={"model_name": "incomplete_prompt"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 400

    # Test run prompt with invalid data
    response = client.base_client.post(
        f"/api/v1/task/{task.id}/prompt/incomplete_prompt/versions/1/completions",
        json={"invalid": "data"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 400
