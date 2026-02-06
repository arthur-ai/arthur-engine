"""
Unit tests for service name mapping API routes.
"""
import pytest

from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.mark.unit_tests
def test_create_service_name_mapping_success(client: GenaiEngineTestClientBase):
    """Test successfully creating a service name mapping."""
    # Create a task
    task_name = "test_task_for_mapping"
    status_code, task = client.create_task(task_name)
    assert status_code == 200

    # Create service name mapping
    status_code, data = client.create_service_name_mapping(
        service_name="test-service",
        task_id=task.id,
    )

    assert status_code == 201
    assert data["service_name"] == "test-service"
    assert data["task_id"] == task.id
    assert data["task_name"] == task_name
    assert "created_at" in data
    assert "traces_updated" in data
    assert data["traces_updated"] >= 0


@pytest.mark.unit_tests
def test_create_service_name_mapping_task_not_found(client: GenaiEngineTestClientBase):
    """Test creating mapping with non-existent task fails."""
    status_code, response = client.create_service_name_mapping(
        service_name="test-service",
        task_id="non-existent-task-id",
    )

    assert status_code == 404
    # response will be error text since status != 201
    import json
    error_detail = json.loads(response)
    assert "not found" in error_detail["detail"].lower()


@pytest.mark.unit_tests
def test_create_service_name_mapping_duplicate(client: GenaiEngineTestClientBase):
    """Test creating duplicate mapping fails with 409."""
    # Create a task
    status_code, task = client.create_task("test_task")
    assert status_code == 200

    # Create first mapping
    status_code, _ = client.create_service_name_mapping(
        service_name="duplicate-service",
        task_id=task.id,
    )
    assert status_code == 201

    # Try to create duplicate
    status_code, response = client.create_service_name_mapping(
        service_name="duplicate-service",
        task_id=task.id,
    )

    assert status_code == 409
    import json
    error_detail = json.loads(response)
    assert "already exists" in error_detail["detail"].lower()


@pytest.mark.unit_tests
def test_list_service_name_mappings(client: GenaiEngineTestClientBase):
    """Test listing service name mappings with pagination."""
    # Create tasks and mappings
    status_code, task1 = client.create_task("task1")
    assert status_code == 200
    status_code, task2 = client.create_task("task2")
    assert status_code == 200

    # Create mappings
    client.base_client.post(
        "/api/v1/service_name_mappings",
        json={"service_name": "service1", "task_id": task1.id},
        headers=client.authorized_user_api_key_headers,
    )
    client.base_client.post(
        "/api/v1/service_name_mappings",
        json={"service_name": "service2", "task_id": task2.id},
        headers=client.authorized_user_api_key_headers,
    )

    # List mappings
    response = client.base_client.get(
        "/api/v1/service_name_mappings?page=0&page_size=20",
        headers=client.authorized_user_api_key_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "mappings" in data
    assert "total_count" in data
    assert data["total_count"] >= 2
    assert len(data["mappings"]) >= 2

    # Verify mapping structure
    for mapping in data["mappings"]:
        assert "service_name" in mapping
        assert "task_id" in mapping
        assert "task_name" in mapping
        assert "created_at" in mapping


@pytest.mark.unit_tests
def test_get_service_name_mapping_by_name(client: GenaiEngineTestClientBase):
    """Test getting a specific service name mapping."""
    # Create task and mapping
    status_code, task = client.create_task("test_task")
    assert status_code == 200

    service_name = "get-test-service"
    client.base_client.post(
        "/api/v1/service_name_mappings",
        json={"service_name": service_name, "task_id": task.id},
        headers=client.authorized_user_api_key_headers,
    )

    # Get the mapping
    response = client.base_client.get(
        f"/api/v1/service_name_mappings/{service_name}",
        headers=client.authorized_user_api_key_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["service_name"] == service_name
    assert data["task_id"] == task.id
    assert data["task_name"] == "test_task"


@pytest.mark.unit_tests
def test_get_service_name_mapping_not_found(client: GenaiEngineTestClientBase):
    """Test getting non-existent mapping returns 404."""
    response = client.base_client.get(
        "/api/v1/service_name_mappings/non-existent-service",
        headers=client.authorized_user_api_key_headers,
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.unit_tests
def test_update_service_name_mapping(client: GenaiEngineTestClientBase):
    """Test updating a service name mapping."""
    # Create tasks
    status_code, task1 = client.create_task("original_task")
    assert status_code == 200
    status_code, task2 = client.create_task("new_task")
    assert status_code == 200

    # Create mapping
    service_name = "update-test-service"
    client.base_client.post(
        "/api/v1/service_name_mappings",
        json={"service_name": service_name, "task_id": task1.id},
        headers=client.authorized_user_api_key_headers,
    )

    # Update mapping
    response = client.base_client.put(
        f"/api/v1/service_name_mappings/{service_name}",
        json={"task_id": task2.id},
        headers=client.authorized_user_api_key_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["service_name"] == service_name
    assert data["task_id"] == task2.id
    assert data["task_name"] == "new_task"
    assert "traces_updated" in data


@pytest.mark.unit_tests
def test_update_service_name_mapping_not_found(client: GenaiEngineTestClientBase):
    """Test updating non-existent mapping returns 404."""
    status_code, task = client.create_task("test_task")
    assert status_code == 200

    response = client.base_client.put(
        "/api/v1/service_name_mappings/non-existent-service",
        json={"task_id": task.id},
        headers=client.authorized_user_api_key_headers,
    )

    assert response.status_code == 404


@pytest.mark.unit_tests
def test_update_service_name_mapping_new_task_not_found(
    client: GenaiEngineTestClientBase,
):
    """Test updating mapping with non-existent new task fails."""
    # Create task and mapping
    status_code, task = client.create_task("test_task")
    assert status_code == 200

    service_name = "test-service"
    client.base_client.post(
        "/api/v1/service_name_mappings",
        json={"service_name": service_name, "task_id": task.id},
        headers=client.authorized_user_api_key_headers,
    )

    # Try to update with non-existent task
    response = client.base_client.put(
        f"/api/v1/service_name_mappings/{service_name}",
        json={"task_id": "non-existent-task"},
        headers=client.authorized_user_api_key_headers,
    )

    assert response.status_code == 404


@pytest.mark.unit_tests
def test_delete_service_name_mapping(client: GenaiEngineTestClientBase):
    """Test deleting a service name mapping."""
    # Create task and mapping
    status_code, task = client.create_task("test_task")
    assert status_code == 200

    service_name = "delete-test-service"
    client.base_client.post(
        "/api/v1/service_name_mappings",
        json={"service_name": service_name, "task_id": task.id},
        headers=client.authorized_user_api_key_headers,
    )

    # Delete mapping
    response = client.base_client.delete(
        f"/api/v1/service_name_mappings/{service_name}",
        headers=client.authorized_user_api_key_headers,
    )

    assert response.status_code == 204

    # Verify it's deleted
    response = client.base_client.get(
        f"/api/v1/service_name_mappings/{service_name}",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 404


@pytest.mark.unit_tests
def test_delete_service_name_mapping_not_found(client: GenaiEngineTestClientBase):
    """Test deleting non-existent mapping returns 404."""
    response = client.base_client.delete(
        "/api/v1/service_name_mappings/non-existent-service",
        headers=client.authorized_user_api_key_headers,
    )

    assert response.status_code == 404


@pytest.mark.unit_tests
def test_service_name_mapping_requires_auth(client: GenaiEngineTestClientBase):
    """Test that service name mapping endpoints require authentication."""
    # Try to create without auth
    response = client.base_client.post(
        "/api/v1/service_name_mappings",
        json={"service_name": "test", "task_id": "task-123"},
    )
    assert response.status_code == 401

    # Try to list without auth
    response = client.base_client.get("/api/v1/service_name_mappings")
    assert response.status_code == 401

    # Try to get without auth
    response = client.base_client.get("/api/v1/service_name_mappings/test-service")
    assert response.status_code == 401

    # Try to update without auth
    response = client.base_client.put(
        "/api/v1/service_name_mappings/test-service",
        json={"task_id": "task-123"},
    )
    assert response.status_code == 401

    # Try to delete without auth
    response = client.base_client.delete("/api/v1/service_name_mappings/test-service")
    assert response.status_code == 401


@pytest.mark.unit_tests
def test_create_mapping_validates_request_body(client: GenaiEngineTestClientBase):
    """Test that request validation works correctly."""
    # Missing service_name
    response = client.base_client.post(
        "/api/v1/service_name_mappings",
        json={"task_id": "task-123"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 422

    # Missing task_id
    response = client.base_client.post(
        "/api/v1/service_name_mappings",
        json={"service_name": "test-service"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 422

    # Empty body
    response = client.base_client.post(
        "/api/v1/service_name_mappings",
        json={},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 422


@pytest.mark.unit_tests
def test_update_mapping_validates_request_body(client: GenaiEngineTestClientBase):
    """Test that update request validation works correctly."""
    # Missing task_id
    response = client.base_client.put(
        "/api/v1/service_name_mappings/test-service",
        json={},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 422


@pytest.mark.unit_tests
def test_list_mappings_pagination(client: GenaiEngineTestClientBase):
    """Test pagination works correctly for listing mappings."""
    # Create multiple mappings
    for i in range(5):
        status_code, task = client.create_task(f"task_{i}")
        assert status_code == 200
        client.base_client.post(
            "/api/v1/service_name_mappings",
            json={"service_name": f"service_{i}", "task_id": task.id},
            headers=client.authorized_user_api_key_headers,
        )

    # Get first page
    response = client.base_client.get(
        "/api/v1/service_name_mappings?page=0&page_size=2",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["mappings"]) <= 2
    assert data["total_count"] >= 5

    # Get second page
    response = client.base_client.get(
        "/api/v1/service_name_mappings?page=1&page_size=2",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["mappings"]) <= 2
