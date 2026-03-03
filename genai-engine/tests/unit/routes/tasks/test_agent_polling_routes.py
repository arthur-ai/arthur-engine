import random
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from arthur_common.models.enums import RegisteredAgentProvider
from arthur_common.models.request_schemas import AgentMetadata, GCPAgentMetadata

from schemas.agent_discovery_schemas import DiscoverAndPollResponse
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)


@pytest.mark.unit_tests
def test_execute_agent_polling_success(
    client: GenaiEngineTestClientBase,
):
    """Test that executing a polling job for a GCP task succeeds."""
    mock_polling_service = MagicMock()
    mock_polling_service.enqueue.return_value = (True, MagicMock())

    with patch(
        "repositories.agent_polling_repository.get_global_agent_polling_service",
        return_value=mock_polling_service,
    ):
        status_code, task_response = client.create_task(
            name=f"test_execute_polling_{random.random()}",
            is_agentic=True,
            agent_metadata=AgentMetadata(
                provider=RegisteredAgentProvider.GCP,
                gcp_metadata=GCPAgentMetadata(
                    project_id="test-project",
                    region="test-region",
                    resource_id="test-resource",
                ),
            ),
        )
        assert status_code == 200

        try:
            status_code, response = client.execute_agent_polling(
                task_id=task_response.id,
            )
            assert status_code == 200
            assert response["status"] == "enqueued"
            assert response["task_id"] == task_response.id
        finally:
            client.delete_task(task_response.id)


@pytest.mark.unit_tests
def test_execute_agent_polling_task_not_found(
    client: GenaiEngineTestClientBase,
):
    """Test that executing a polling job for a non-existent task returns 404."""
    mock_polling_service = MagicMock()

    with patch(
        "repositories.agent_polling_repository.get_global_agent_polling_service",
        return_value=mock_polling_service,
    ):
        status_code, response = client.execute_agent_polling(
            task_id=str(uuid4()),
        )
        assert status_code == 404


@pytest.mark.unit_tests
def test_execute_agent_polling_non_agentic_task(
    client: GenaiEngineTestClientBase,
):
    """Test that executing a polling job for a non-agentic task returns 400."""
    mock_polling_service = MagicMock()

    with patch(
        "repositories.agent_polling_repository.get_global_agent_polling_service",
        return_value=mock_polling_service,
    ):
        status_code, task_response = client.create_task(
            name=f"test_non_agentic_{random.random()}",
            is_agentic=False,
        )
        assert status_code == 200

        try:
            status_code, response = client.execute_agent_polling(
                task_id=task_response.id,
            )
            assert status_code == 400
            assert "not available for agent polling" in response["detail"]
        finally:
            client.delete_task(task_response.id)


@pytest.mark.unit_tests
def test_execute_agent_polling_non_gcp_task(
    client: GenaiEngineTestClientBase,
):
    """Test that executing a polling job for a non-GCP agentic task returns 400."""
    mock_polling_service = MagicMock()

    with patch(
        "repositories.agent_polling_repository.get_global_agent_polling_service",
        return_value=mock_polling_service,
    ):
        # Create agentic task without GCP metadata (manual creation source)
        status_code, task_response = client.create_task(
            name=f"test_non_gcp_{random.random()}",
            is_agentic=True,
        )
        assert status_code == 200

        try:
            status_code, response = client.execute_agent_polling(
                task_id=task_response.id,
            )
            assert status_code == 400
            assert "not a GCP agent" in response["detail"]
        finally:
            client.delete_task(task_response.id)


@pytest.mark.unit_tests
def test_execute_agent_polling_service_not_initialized(
    client: GenaiEngineTestClientBase,
):
    """Test that executing when service is not initialized returns 503."""
    with patch(
        "repositories.agent_polling_repository.get_global_agent_polling_service",
        return_value=None,
    ):
        mock_polling_service_for_create = MagicMock()
        mock_polling_service_for_create.enqueue.return_value = True

        # Create task first (with a working service mock for the create path)
        status_code, task_response = client.create_task(
            name=f"test_service_down_{random.random()}",
            is_agentic=True,
            agent_metadata=AgentMetadata(
                provider=RegisteredAgentProvider.GCP,
                gcp_metadata=GCPAgentMetadata(
                    project_id="test-project",
                    region="test-region",
                    resource_id="test-resource",
                ),
            ),
        )
        assert status_code == 200

        try:
            status_code, response = client.execute_agent_polling(
                task_id=task_response.id,
            )
            assert status_code == 503
            assert "not initialized" in response["detail"]
        finally:
            client.delete_task(task_response.id)


@pytest.mark.unit_tests
def test_execute_agent_polling_already_active(
    client: GenaiEngineTestClientBase,
):
    """Test that executing when job is already active returns 200 (idempotent)."""
    mock_polling_service = MagicMock()
    # First call returns (True, future), subsequent would return (False, None) (already active)
    mock_polling_service.enqueue.return_value = (False, None)

    with patch(
        "repositories.agent_polling_repository.get_global_agent_polling_service",
        return_value=mock_polling_service,
    ):
        status_code, task_response = client.create_task(
            name=f"test_already_active_{random.random()}",
            is_agentic=True,
            agent_metadata=AgentMetadata(
                provider=RegisteredAgentProvider.GCP,
                gcp_metadata=GCPAgentMetadata(
                    project_id="test-project",
                    region="test-region",
                    resource_id="test-resource",
                ),
            ),
        )
        assert status_code == 200

        try:
            # Execute returns 200 even when job is already active
            status_code, response = client.execute_agent_polling(
                task_id=task_response.id,
            )
            assert status_code == 200
            assert response["status"] == "enqueued"
        finally:
            client.delete_task(task_response.id)


@pytest.mark.unit_tests
def test_execute_all_agent_polling_success(
    client: GenaiEngineTestClientBase,
):
    """Test that execute-all triggers discovery + polling and returns counts."""
    mock_polling_service = MagicMock()
    mock_polling_service._discover_and_poll_agents.return_value = DiscoverAndPollResponse(
        status="completed",
        discovered=2,
        traces_fetched=0,
    )

    with patch(
        "routers.v1.agent_polling_routes.get_global_agent_polling_service",
        return_value=mock_polling_service,
    ):
        status_code, response = client.execute_all_agent_polling()
        assert status_code == 200
        assert response["status"] == "completed"
        assert response["discovered"] == 2
        assert response["traces_fetched"] == 0
        mock_polling_service._discover_and_poll_agents.assert_called_once()


@pytest.mark.unit_tests
def test_execute_all_agent_polling_sync_with_traces_fetched(
    client: GenaiEngineTestClientBase,
):
    """Test that execute-all in synchronous mode returns actual traces_fetched count."""
    mock_polling_service = MagicMock()
    mock_polling_service._discover_and_poll_agents.return_value = DiscoverAndPollResponse(
        status="completed",
        discovered=1,
        traces_fetched=42,
    )

    with patch(
        "routers.v1.agent_polling_routes.get_global_agent_polling_service",
        return_value=mock_polling_service,
    ):
        status_code, response = client.execute_all_agent_polling(
            wait_for_completion=True,
            timeout=30,
        )
        assert status_code == 200
        assert response["status"] == "completed"
        assert response["discovered"] == 1
        assert response["traces_fetched"] == 42
        mock_polling_service._discover_and_poll_agents.assert_called_once_with(
            wait_for_completion=True,
            timeout=30,
        )


@pytest.mark.unit_tests
def test_execute_all_agent_polling_service_not_initialized(
    client: GenaiEngineTestClientBase,
):
    """Test that execute-all returns 503 when service is not initialized."""
    with patch(
        "routers.v1.agent_polling_routes.get_global_agent_polling_service",
        return_value=None,
    ):
        status_code, response = client.execute_all_agent_polling()
        assert status_code == 503
        assert "not initialized" in response["detail"]
