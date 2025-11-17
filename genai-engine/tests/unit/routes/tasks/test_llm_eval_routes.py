import random
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from litellm.types.utils import ModelResponse

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
        (
            "GET",
            f"/api/v1/tasks/{agentic_task.id}/llm_evals/test_llm_eval/versions/latest",
        ),
        ("GET", f"/api/v1/tasks/{agentic_task.id}/llm_evals/test_llm_eval/versions"),
        ("GET", f"/api/v1/tasks/{agentic_task.id}/llm_evals"),
        ("POST", f"/api/v1/tasks/{agentic_task.id}/llm_evals/test_llm_eval"),
        ("DELETE", f"/api/v1/tasks/{agentic_task.id}/llm_evals/test_llm_eval"),
        (
            "DELETE",
            f"/api/v1/tasks/{agentic_task.id}/llm_evals/test_llm_eval/versions/latest",
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
    }

    response = client.base_client.post(
        f"/api/v1/tasks/{agentic_task.id}/llm_evals/incomplete_eval",
        json=eval_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 400

    # Test save llm eval with invalid template syntax - should return 400, not 500
    eval_data_invalid_template = {
        "instructions": "{% end %}",
        "model_name": "gpt-4",
        "model_provider": "openai",
    }

    response = client.base_client.post(
        f"/api/v1/tasks/{agentic_task.id}/llm_evals/invalid_template_eval",
        json=eval_data_invalid_template,
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
    assert (
        f"no matching version of '{nonexistent_eval}' found for task '{agentic_task.id}'"
        in response.json()["detail"].lower()
    )

    # --- Case 2: Already soft-deleted version (400) ---
    eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Test instructions",
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


@pytest.mark.unit_tests
@pytest.mark.parametrize("eval_version", ["latest", "1", "datetime"])
def test_soft_delete_llm_eval_by_version_route(
    client: GenaiEngineTestClientBase,
    eval_version,
):
    """Test soft deleting an llm eval with different version formats (latest, version number, datetime)"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Save an llm eval
    eval_name = "test_llm_eval"
    eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Test instructions",
    }

    save_response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}",
        json=eval_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert save_response.status_code == 200

    if eval_version == "datetime":
        eval_version = save_response.json()["created_at"]

    # Soft-delete the eval using different version formats
    response = client.base_client.delete(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}/versions/{eval_version}",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 204

    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}/versions/{eval_version}",
        headers=client.authorized_user_api_key_headers,
    )
    if eval_version == "latest":
        assert response.status_code == 404
        assert (
            response.json()["detail"]
            == f"'{eval_name}' (version 'latest') not found for task '{task.id}'"
        )
    else:
        assert response.status_code == 200

        eval_response = response.json()
        assert eval_response["name"] == eval_name
        assert eval_response["instructions"] == ""
        assert eval_response["model_name"] == ""
        assert eval_response["model_provider"] == "openai"
        assert eval_response["deleted_at"] is not None


@pytest.mark.unit_tests
def test_get_llm_eval_success(client: GenaiEngineTestClientBase):
    """Test successfully getting an llm eval"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200
    assert task.is_agentic == True

    # First save an llm eval
    eval_name = "test_llm_eval"
    eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Test instructions",
    }

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}",
        json=eval_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    # Now get the llm eval
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}/versions/1",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    eval_response = response.json()
    assert eval_response["name"] == eval_name
    assert eval_response["instructions"] == eval_data["instructions"]
    assert eval_response["model_name"] == eval_data["model_name"]
    assert eval_response["model_provider"] == eval_data["model_provider"]
    assert eval_response["version"] == 1


@pytest.mark.unit_tests
def test_get_llm_eval_not_found(client: GenaiEngineTestClientBase):
    """Test getting an llm eval that doesn't exist"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Try to get a non-existent llm eval
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/llm_evals/nonexistent_eval/versions/1",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.unit_tests
def test_get_llm_eval_non_agentic_task(client: GenaiEngineTestClientBase):
    """Test getting an llm eval from a non-agentic task should fail"""
    # Create a non-agentic task
    task_name = f"non_agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=False)
    assert status_code == 200
    assert task.is_agentic == False

    # Try to get an llm eval from non-agentic task
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/llm_evals/test_llm_eval/versions/1",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 400
    assert "not agentic" in response.json()["detail"].lower()


@pytest.mark.unit_tests
def test_get_llm_eval_does_not_raise_err_for_deleted_eval(
    client: GenaiEngineTestClientBase,
):
    """
    Test retrieving a deleted llm eval does not raise an error
    """
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Save an llm eval
    eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Test instructions",
    }
    eval_name = "test_llm_eval"

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}",
        json=eval_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == eval_name
    assert response.json()["version"] == 1
    assert response.json()["instructions"] == eval_data["instructions"]
    assert response.json()["model_name"] == eval_data["model_name"]
    assert response.json()["model_provider"] == eval_data["model_provider"]

    # save 2 versions to have a deleted and non-deleted version
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}",
        json=eval_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == eval_name
    assert response.json()["version"] == 2
    assert response.json()["instructions"] == eval_data["instructions"]
    assert response.json()["model_name"] == eval_data["model_name"]
    assert response.json()["model_provider"] == eval_data["model_provider"]

    # should not spawn an error
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}/versions/2",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == eval_name
    assert response.json()["version"] == 2

    # delete version 2 of the eval
    response = client.base_client.delete(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}/versions/2",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 204

    # should not raise an error
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}/versions/2",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == eval_name
    assert response.json()["version"] == 2
    assert response.json()["instructions"] == ""
    assert response.json()["model_name"] == ""
    assert response.json()["model_provider"] == "openai"


@pytest.mark.unit_tests
@pytest.mark.parametrize("eval_version", ["latest", "1", "datetime"])
def test_get_llm_eval_by_version_route(
    client: GenaiEngineTestClientBase,
    eval_version,
):
    """Test getting an llm eval with different version formats (latest, version number, datetime)"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Save an llm eval
    eval_name = "test_llm_eval"
    eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Test instructions",
    }
    if eval_version == "datetime":
        eval_version = datetime.now().isoformat()

    save_response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}",
        json=eval_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert save_response.status_code == 200

    # Get the llm eval using different version formats
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}/versions/{eval_version}",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    eval_response = response.json()
    assert eval_response["name"] == eval_name
    assert eval_response["instructions"] == eval_data["instructions"]
    assert eval_response["model_name"] == eval_data["model_name"]
    assert eval_response["model_provider"] == eval_data["model_provider"]
    assert eval_response["version"] == 1


@pytest.mark.unit_tests
def test_get_llm_eval_versions(client: GenaiEngineTestClientBase):
    """Test retrieving all versions of an llm eval"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Save an llm eval
    eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Test instructions",
    }
    eval_name = "test_llm_eval"

    # save 2 versions of the same llm eval
    for i in range(2):
        response = client.base_client.post(
            f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}",
            json=eval_data,
            headers=client.authorized_user_api_key_headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == eval_name
        assert response.json()["version"] == i + 1
        assert response.json()["instructions"] == eval_data["instructions"]
        assert response.json()["model_name"] == eval_data["model_name"]
        assert response.json()["model_provider"] == eval_data["model_provider"]

    # save an llm eval with a different name
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/llm_evals/different_eval_name",
        json=eval_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == "different_eval_name"
    assert response.json()["version"] == 1
    assert response.json()["instructions"] == eval_data["instructions"]
    assert response.json()["model_name"] == eval_data["model_name"]
    assert response.json()["model_provider"] == eval_data["model_provider"]

    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}/versions",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["versions"]) == 2
    assert response.json()["count"] == 2

    for version in response.json()["versions"]:
        assert version["created_at"] is not None
        assert "deleted_at" not in version
        assert version["model_provider"] == eval_data["model_provider"]
        assert version["model_name"] == eval_data["model_name"]

    # now check the different eval name
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/llm_evals/different_eval_name/versions",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["versions"]) == 1
    assert response.json()["count"] == 1

    # soft-delete version 2 of the llm eval
    response = client.base_client.delete(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}/versions/2",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 204

    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}/versions",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["versions"]) == 2
    assert response.json()["count"] == 2

    for version in response.json()["versions"]:
        assert version["created_at"] is not None
        assert version["model_provider"] == "openai"

        if "deleted_at" in version:
            assert version["model_name"] == ""
        else:
            assert version["model_name"] == eval_data["model_name"]

    # cleanup
    response = client.base_client.delete(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 204

    response = client.base_client.delete(
        f"/api/v1/tasks/{task.id}/llm_evals/different_eval_name",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 204


@pytest.mark.unit_tests
def test_get_llm_eval_versions_pagination_and_filtering(
    client: GenaiEngineTestClientBase,
):
    """Test pagination, sorting, and filtering for get_llm_eval_versions"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    eval_name = "test_llm_eval"

    # Create llm evals with different versions
    for i in range(4):
        eval_data = {
            "instructions": f"Version {i+1}",
            "model_name": "gpt-4",
            "model_provider": "openai",
        }
        response = client.base_client.post(
            f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}",
            json=eval_data,
            headers=client.authorized_user_api_key_headers,
        )
        assert response.status_code == 200

    # Test version pagination
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}/versions",
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
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}/versions",
        headers=client.authorized_user_api_key_headers,
        params={"min_version": 2, "max_version": 3},
    )
    assert response.status_code == 200
    result = response.json()
    assert len(result["versions"]) == 2
    assert result["count"] == 2

    # Delete a version and test deleted is included in the results
    response = client.base_client.delete(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}/versions/2",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 204

    # Test include deleted (default behavior, exclude_deleted=False)
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}/versions",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    result = response.json()
    assert result["count"] == 4  # Includes deleted version by default
    versions = [v["version"] for v in result["versions"]]
    assert 2 in versions

    # Test exclude deleted
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}/versions",
        headers=client.authorized_user_api_key_headers,
        params={"exclude_deleted": True},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["count"] == 3  # One version excluded
    versions = [v["version"] for v in result["versions"]]
    assert 2 not in versions


@pytest.mark.unit_tests
def test_get_all_llm_evals_success(client: GenaiEngineTestClientBase):
    """Test getting all llm evals for an agentic task"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Save multiple llm evals
    llm_evals_data = [
        {
            "model_name": "gpt-4",
            "model_provider": "openai",
            "instructions": "First eval",
        },
        {
            "model_name": "gpt-4",
            "model_provider": "openai",
            "instructions": "Second eval",
        },
        {
            "model_name": "gpt-4",
            "model_provider": "openai",
            "instructions": "Third eval",
        },
    ]

    eval_names = ["test_llm_eval_1", "test_llm_eval_2", "test_llm_eval_2"]

    for i, eval_data in enumerate(llm_evals_data):
        response = client.base_client.post(
            f"/api/v1/tasks/{task.id}/llm_evals/{eval_names[i]}",
            json=eval_data,
            headers=client.authorized_user_api_key_headers,
        )
        assert response.status_code == 200

    # Get all llm evals
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/llm_evals",
        headers=client.authorized_user_api_key_headers,
        params={"sort": "asc"},
    )
    assert response.status_code == 200

    llm_evals_response = response.json()
    assert "llm_metadata" in llm_evals_response
    assert len(llm_evals_response["llm_metadata"]) == 2

    metadata = llm_evals_response["llm_metadata"]

    for i, llm_metadata in enumerate(metadata):
        assert llm_metadata["name"] == eval_names[i]
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
def test_get_all_llm_evals_empty(client: GenaiEngineTestClientBase):
    """Test getting all llm evals when none exist"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Get all llm evals (should be empty)
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/llm_evals",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    llm_evals_response = response.json()
    assert "llm_metadata" in llm_evals_response
    assert len(llm_evals_response["llm_metadata"]) == 0


@pytest.mark.unit_tests
def test_get_all_llm_evals_includes_deleted_evals(client: GenaiEngineTestClientBase):
    """
    Test retrieving all llm evals includes deleted evals
    """
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Save an llm eval
    eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "First eval",
    }

    eval_name = "test_llm_eval"

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}",
        json=eval_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == eval_name
    assert response.json()["version"] == 1
    assert response.json()["instructions"] == eval_data["instructions"]

    # save 2 versions to have a deleted and non-deleted version
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}",
        json=eval_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == eval_name
    assert response.json()["version"] == 2
    assert response.json()["instructions"] == eval_data["instructions"]

    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/llm_evals",
        headers=client.authorized_user_api_key_headers,
    )

    metadata = response.json()["llm_metadata"]
    created = datetime.fromisoformat(metadata[0]["created_at"])
    latest = datetime.fromisoformat(metadata[0]["latest_version_created_at"])

    assert response.status_code == 200
    assert len(metadata) == 1
    assert metadata[0]["name"] == eval_name
    assert metadata[0]["versions"] == 2
    assert metadata[0]["created_at"] is not None
    assert metadata[0]["latest_version_created_at"] is not None
    assert abs((created - latest).total_seconds()) < 1
    assert metadata[0]["deleted_versions"] == []

    # delete version 2 of the eval
    response = client.base_client.delete(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}/versions/2",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 204

    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/llm_evals",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["llm_metadata"]) == 1

    metadata = response.json()["llm_metadata"]
    created = datetime.fromisoformat(metadata[0]["created_at"])
    latest = datetime.fromisoformat(metadata[0]["latest_version_created_at"])

    assert metadata[0]["name"] == eval_name
    assert metadata[0]["versions"] == 2
    assert metadata[0]["created_at"] is not None
    assert metadata[0]["latest_version_created_at"] is not None
    assert created != latest
    assert metadata[0]["deleted_versions"] == [2]


@pytest.mark.unit_tests
def test_get_all_llm_evals_pagination_and_filtering(client: GenaiEngineTestClientBase):
    """Test pagination, sorting, and filtering for get_all_llm_evals"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Create llm evals with different providers
    for i, eval_name in enumerate(["alpha", "beta", "gamma"]):
        provider = "openai" if i < 2 else "anthropic"
        model = "gpt-4o" if provider == "openai" else "claude-3-5-sonnet"
        eval_data = {
            "model_name": model,
            "model_provider": provider,
            "instructions": f"Eval {eval_name}",
        }
        response = client.base_client.post(
            f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}",
            json=eval_data,
            headers=client.authorized_user_api_key_headers,
        )
        assert response.status_code == 200

    # Test pagination on get_all_llm_evals
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/llm_evals",
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
        f"/api/v1/tasks/{task.id}/llm_evals",
        headers=client.authorized_user_api_key_headers,
        params={"sort": "desc"},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["llm_metadata"][0]["name"] == "gamma"
    assert result["llm_metadata"][2]["name"] == "alpha"

    # Test filtering by provider
    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/llm_evals",
        headers=client.authorized_user_api_key_headers,
        params={"model_provider": "openai"},
    )
    assert response.status_code == 200
    result = response.json()
    assert len(result["llm_metadata"]) == 2
    assert result["count"] == 2


@pytest.mark.unit_tests
def test_get_unique_llm_eval_names(client: GenaiEngineTestClientBase):
    """Test retrieving all unique llm eval names"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Save an llm eval
    eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "First eval",
    }

    eval_name = "test_llm_eval"

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}",
        json=eval_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == eval_name
    assert response.json()["version"] == 1
    assert response.json()["instructions"] == eval_data["instructions"]

    # save 2 versions to have a deleted and non-deleted version
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}",
        json=eval_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == eval_name
    assert response.json()["version"] == 2
    assert response.json()["instructions"] == eval_data["instructions"]

    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}/versions",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["versions"]) == 2

    # delete version 2 of the eval
    response = client.base_client.delete(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}/versions/2",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 204

    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/llm_evals",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1

    response = client.base_client.get(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}/versions",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert len(response.json()["versions"]) == 2


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
def test_run_saved_llm_eval_success(
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    """Test running a saved llm eval"""
    mock_response = MagicMock(spec=ModelResponse)
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": '{"reason": "This answer is true because it is supported by the ground truth.", "score": 1}',
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

    # First save an llm eval
    eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Assess the following answer based on ground truth",
    }

    eval_name = "test_llm_eval"

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}",
        json=eval_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    # Now run the saved eval
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}/versions/latest/completions",
        json={},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    run_response = response.json()
    assert (
        run_response["reason"]
        == "This answer is true because it is supported by the ground truth."
    )
    assert run_response["score"] == 1
    assert run_response["cost"] == "0.002345"


@pytest.mark.unit_tests
def test_run_saved_llm_eval_not_found(client: GenaiEngineTestClientBase):
    """Test running a saved llm eval that doesn't exist"""
    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Try to run a non-existent saved llm eval
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/llm_evals/nonexistent_eval/versions/latest/completions",
        json={},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
def test_run_deleted_llm_eval_spawns_error(
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    """Test running a deleted version of a saved llm eval spawns an error"""
    mock_response = MagicMock(spec=ModelResponse)
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": '{"reason": "This answer is true because it is supported by the ground truth.", "score": 1}',
    }
    mock_completion.return_value = mock_response
    mock_completion_cost.return_value = 0.001234

    # Create an agentic task
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    # Save an llm eval
    eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Assess the following answer based on ground truth",
    }

    eval_name = "test_llm_eval"

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}",
        json=eval_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == eval_name
    assert response.json()["version"] == 1
    assert response.json()["instructions"] == eval_data["instructions"]

    # save 2 versions to have a deleted and non-deleted version
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}",
        json=eval_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert response.json()["name"] == eval_name
    assert response.json()["version"] == 2
    assert response.json()["instructions"] == eval_data["instructions"]

    # soft delete version 2 of the eval
    response = client.base_client.delete(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}/versions/2",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 204

    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}/versions/2/completions",
        json={},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 400
    assert (
        "cannot run this llm eval because it was deleted on"
        in response.json()["detail"].lower()
    )

    # running latest should run the latest non-deleted version of an eval
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}/versions/latest/completions",
        json={},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    assert (
        response.json()["reason"]
        == "This answer is true because it is supported by the ground truth."
    )
    assert response.json()["score"] == 1
    assert response.json()["cost"] == "0.001234"


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
@pytest.mark.parametrize(
    "instructions,variables,expected_error",
    [
        ("Hello, {{name}}!", {"name": "John"}, None),
        ("Hello, {{name}}!", {"name": ""}, None),
        (
            "Hello, {{name}}!",
            None,
            "Missing values for the following variables: name",
        ),
        ("Hello, name!", {"name": "John"}, None),
        ("Hello, name!", {"first_name": "John"}, None),
        (
            "Hello, {{ first_name }} {{ last_name }}!",
            {"first_name": "John", "last_name": "Doe"},
            None,
        ),
        (
            "Hello, {{ first_name }} {{ last_name }}!",
            {"first_name": "John", "name": "Doe"},
            "Missing values for the following variables: last_name",
        ),
        (
            "Hello, {{ first_name }} {{ last_name }}!",
            {"name1": "John", "name2": "Doe"},
            "Missing values for the following variables: first_name, last_name",
        ),
        (
            "Hello, {{ first_name }} {last_name}!",
            {"first_name": "John", "name": "Doe"},
            None,
        ),
        (
            "Hello, {{ first_name }} {{ last_name }}!",
            {"first_name": "", "last_name": ""},
            None,
        ),
    ],
)
def test_run_saved_llm_eval_strict_mode(
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
    instructions,
    variables,
    expected_error,
):
    """Test running a saved llm eval with strict mode"""
    task_name = f"agentic_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    mock_response = MagicMock(spec=ModelResponse)
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": '{"reason": "This answer is true because it is supported by the ground truth.", "score": 1}',
    }
    mock_completion.return_value = mock_response
    mock_completion_cost.return_value = 0.001234

    eval_name = "test_llm_eval"

    eval_data = {
        "instructions": instructions,
        "model_name": "gpt-4o",
        "model_provider": "openai",
    }

    completion_request = {}

    if variables:
        completion_request["variables"] = [
            {"name": name, "value": value} for name, value in variables.items()
        ]

    # Save llm eval
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}",
        json=eval_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200

    # verify running saved llm eval enforces strict=True
    response = client.base_client.post(
        f"/api/v1/tasks/{task.id}/llm_evals/{eval_name}/versions/latest/completions",
        json=completion_request,
        headers=client.authorized_user_api_key_headers,
    )
    if expected_error:
        assert response.status_code == 400
        assert response.json()["detail"] == expected_error
    else:
        assert response.status_code == 200
