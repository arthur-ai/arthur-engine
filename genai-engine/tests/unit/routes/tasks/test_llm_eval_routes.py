import random

import pytest

from schemas.internal_schemas import Task
from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.fixture
def agentic_task(client: GenaiEngineTestClientBase):
    """Create an agentic task"""
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200
    return task


@pytest.mark.unit_tests
def test_llm_eval_routes_require_authentication(
    client: GenaiEngineTestClientBase,
    agentic_task: Task,
):
    """Test that all llm eval routes require authentication"""
    # Test all routes without authentication headers
    routes_and_methods = [
        ("POST", f"/api/v1/tasks/{agentic_task.id}/llm_evals/test_eval"),
        ("DELETE", f"/api/v1/tasks/{agentic_task.id}/llm_evals/test_eval"),
        (
            "DELETE",
            f"/api/v1/tasks/{agentic_task.id}/llm_evals/test_eval/versions/latest",
        ),
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
def test_save_llm_eval_success(client: GenaiEngineTestClientBase, agentic_task: Task):
    """Test saving an llm eval"""
    # Save an llm eval
    eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Test instructions",
        "score_range": {
            "min_score": 0,
            "max_score": 1,
        },
    }

    eval_name = "new_eval"

    response = client.base_client.post(
        f"/api/v1/tasks/{agentic_task.id}/llm_evals/{eval_name}",
        json=eval_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == eval_name
    assert response.json()["version"] == 1
    assert response.json()["instructions"] == eval_data["instructions"]
    assert response.json()["score_range"] == eval_data["score_range"]
    assert response.json()["model_name"] == eval_data["model_name"]
    assert response.json()["model_provider"] == eval_data["model_provider"]


@pytest.mark.unit_tests
def test_save_llm_eval_duplicate(client: GenaiEngineTestClientBase, agentic_task: Task):
    """Test saving a llm eval with duplicate name should be a new version of the llm eval"""
    # Save an llm eval
    eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Test instructions",
        "score_range": {
            "min_score": 0,
            "max_score": 1,
        },
    }

    eval_name = "duplicate_eval"

    response = client.base_client.post(
        f"/api/v1/tasks/{agentic_task.id}/llm_evals/{eval_name}",
        json=eval_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    # test saving an llm eval with a duplicate name should be a new version of the llm eval
    response = client.base_client.post(
        f"/api/v1/tasks/{agentic_task.id}/llm_evals/{eval_name}",
        json=eval_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    assert response.json()["name"] == eval_name
    assert response.json()["version"] == 2
    assert response.json()["instructions"] == eval_data["instructions"]
    assert response.json()["score_range"] == eval_data["score_range"]
    assert response.json()["model_name"] == eval_data["model_name"]
    assert response.json()["model_provider"] == eval_data["model_provider"]


@pytest.mark.unit_tests
def test_save_llm_eval_with_malformed_data(
    client: GenaiEngineTestClientBase,
    agentic_task: Task,
):
    """Test saving an llm eval with malformed request data"""
    # Test save llm eval with missing required fields
    # Missing model_name, model_provider
    eval_data = {
        "instructions": "Test instructions",
        "score_range": {
            "min_score": 0,
            "max_score": 1,
        },
    }

    response = client.base_client.post(
        f"/api/v1/tasks/{agentic_task.id}/llm_evals/incomplete_eval",
        json=eval_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 400


@pytest.mark.unit_tests
def test_delete_llm_eval_success(client: GenaiEngineTestClientBase, agentic_task: Task):
    """Test deleting an llm eval succeeds"""
    # First save an llm eval
    eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Test instructions",
        "score_range": {
            "min_score": 0,
            "max_score": 1,
        },
    }

    eval_name = "delete_eval"

    # Save the llm eval
    response = client.base_client.post(
        f"/api/v1/tasks/{agentic_task.id}/llm_evals/{eval_name}",
        json=eval_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    # Delete the llm eval
    response = client.base_client.delete(
        f"/api/v1/tasks/{agentic_task.id}/llm_evals/{eval_name}",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 204


@pytest.mark.unit_tests
def test_delete_llm_eval_errors(client: GenaiEngineTestClientBase, agentic_task: Task):
    """Test all error cases for deleting an llm eval"""

    # --- Case 1: Eval not found (404) ---
    nonexistent_eval = "nonexistent_eval"
    response = client.base_client.delete(
        f"/api/v1/tasks/{agentic_task.id}/llm_evals/{nonexistent_eval}",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

    # --- Case 2: Delete already deleted eval (404) ---
    eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Test instructions",
        "score_range": {
            "min_score": 0,
            "max_score": 1,
        },
    }

    eval_name = "delete_eval"

    # Create the eval
    response = client.base_client.post(
        f"/api/v1/tasks/{agentic_task.id}/llm_evals/{eval_name}",
        json=eval_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    # Delete it once (should succeed)
    response = client.base_client.delete(
        f"/api/v1/tasks/{agentic_task.id}/llm_evals/{eval_name}",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 204

    # Try to delete again (should fail with 404)
    response = client.base_client.delete(
        f"/api/v1/tasks/{agentic_task.id}/llm_evals/{eval_name}",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.unit_tests
def test_soft_delete_llm_eval_success(
    client: GenaiEngineTestClientBase,
    agentic_task: Task,
):
    """Test deleting an llm eval succeeds"""
    # First save an llm eval
    eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Test instructions",
        "score_range": {
            "min_score": 0,
            "max_score": 1,
        },
    }

    eval_name = "delete_eval"

    # Save the llm eval
    response = client.base_client.post(
        f"/api/v1/tasks/{agentic_task.id}/llm_evals/{eval_name}",
        json=eval_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    # Delete the llm eval
    response = client.base_client.delete(
        f"/api/v1/tasks/{agentic_task.id}/llm_evals/{eval_name}/versions/latest",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 204


@pytest.mark.unit_tests
def test_soft_delete_llm_eval_version_errors(
    client: GenaiEngineTestClientBase,
    agentic_task: Task,
):
    """Test all error cases for soft-deleting an llm eval version"""

    # --- Case 1: Eval not found (404) ---
    nonexistent_eval = "nonexistent_eval"
    response = client.base_client.delete(
        f"/api/v1/tasks/{agentic_task.id}/llm_evals/{nonexistent_eval}/versions/latest",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

    # --- Case 2: Already soft-deleted version (400) ---
    eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Test instructions",
        "score_range": {
            "min_score": 0,
            "max_score": 1,
        },
    }

    eval_name = "soft_delete_eval"

    # Create the eval
    response = client.base_client.post(
        f"/api/v1/tasks/{agentic_task.id}/llm_evals/{eval_name}",
        json=eval_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    # Soft-delete it once (should succeed)
    response = client.base_client.delete(
        f"/api/v1/tasks/{agentic_task.id}/llm_evals/{eval_name}/versions/1",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 204

    # Try to soft-delete the same version again (should fail with 400)
    response = client.base_client.delete(
        f"/api/v1/tasks/{agentic_task.id}/llm_evals/{eval_name}/versions/1",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 400
    assert "has already been deleted" in response.json()["detail"]

    # --- Case 3: Invalid version format (400) ---
    response = client.base_client.delete(
        f"/api/v1/tasks/{agentic_task.id}/llm_evals/{eval_name}/versions/invalid_version",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 400
