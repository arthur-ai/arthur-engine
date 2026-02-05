import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from arthur_common.models.enums import AgentPollingStatus, RegisteredAgentProvider

from db_models.agent_polling_models import DatabaseAgentPollingData
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)


@pytest.mark.unit_tests
def test_retry_agent_polling_task_success(
    client: GenaiEngineTestClientBase,
):
    """Test the registered agent polling execution"""

    db_session = override_get_db_session()

    # Mock the polling service
    mock_polling_service = MagicMock()
    mock_polling_service.enqueue.return_value = True

    status_code, task_response = client.create_task(
        name="test_registered_agent_polling_execution_success_task",
        is_agentic=True,
    )
    assert status_code == 200

    agent_polling_data = None
    try:
        # Create agent polling data
        agent_polling_data_id = uuid.uuid4()
        agent_polling_data = DatabaseAgentPollingData(
            id=agent_polling_data_id,
            task_id=task_response.id,
            provider=RegisteredAgentProvider.GCP.value,
            gcp_credentials={
                "project_id": "test-project",
                "region": "test-region",
                "resource_id": "test-resource",
            },
            status=AgentPollingStatus.ERROR.value,
            failed_runs=0,
            error_message=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_fetched=None,
        )

        db_session.add(agent_polling_data)
        db_session.commit()

        with patch(
            "repositories.agent_discovery_repository.get_registered_agent_polling_service",
            return_value=mock_polling_service,
        ):
            status_code, response = client.retry_agent_polling_task(
                str(agent_polling_data.id),
            )
            assert status_code == 200
            assert (
                response["message"]
                == f"Successfully enqueued retry job for agent {agent_polling_data.id}"
            )
    finally:
        if agent_polling_data is not None:
            db_session.delete(agent_polling_data)
            db_session.commit()

        client.delete_task(task_response.id)


@pytest.mark.unit_tests
def test_retry_agent_polling_task_not_in_error_state(
    client: GenaiEngineTestClientBase,
):
    """Test that a retry agent polling task is not allowed if the agent polling data is not in an error state"""

    db_session = override_get_db_session()

    # Mock the polling service
    mock_polling_service = MagicMock()
    mock_polling_service.enqueue.return_value = True

    status_code, task_response = client.create_task(
        name="test_registered_agent_polling_execution_success_task",
        is_agentic=True,
    )
    assert status_code == 200

    agent_polling_data = None
    try:
        # Create agent polling data
        agent_polling_data_id = uuid.uuid4()
        agent_polling_data = DatabaseAgentPollingData(
            id=agent_polling_data_id,
            task_id=task_response.id,
            provider=RegisteredAgentProvider.GCP.value,
            gcp_credentials={
                "project_id": "test-project",
                "region": "test-region",
                "resource_id": "test-resource",
            },
            status=AgentPollingStatus.RUNNING.value,
            failed_runs=0,
            error_message=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_fetched=None,
        )

        db_session.add(agent_polling_data)
        db_session.commit()

        with patch(
            "repositories.agent_discovery_repository.get_registered_agent_polling_service",
            return_value=mock_polling_service,
        ):
            status_code, response = client.retry_agent_polling_task(
                str(agent_polling_data.id),
            )
            assert status_code == 400
            assert (
                response["detail"]
                == f"Cannot retry a polling job that is not in an error state"
            )
    finally:
        if agent_polling_data is not None:
            db_session.delete(agent_polling_data)
            db_session.commit()

        client.delete_task(task_response.id)


@pytest.mark.unit_tests
def test_retry_agent_polling_task_not_found(
    client: GenaiEngineTestClientBase,
):
    """Test that a retry agent polling task is not allowed if the agent polling data does not exist"""

    db_session = override_get_db_session()

    # Mock the polling service
    mock_polling_service = MagicMock()
    mock_polling_service.enqueue.return_value = True

    status_code, task_response = client.create_task(
        name="test_registered_agent_polling_execution_success_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Create agent polling data
        agent_polling_data_id = uuid.uuid4()

        with patch(
            "repositories.agent_discovery_repository.get_registered_agent_polling_service",
            return_value=mock_polling_service,
        ):
            status_code, response = client.retry_agent_polling_task(
                str(agent_polling_data_id),
            )
            assert status_code == 404
            assert (
                response["detail"]
                == f"Agent polling data {agent_polling_data_id} not found"
            )
    finally:
        client.delete_task(task_response.id)


@pytest.mark.unit_tests
def test_retry_agent_polling_task_failed_to_enqueue(
    client: GenaiEngineTestClientBase,
):
    """Test that a retry agent polling task is not allowed if the polling service fails to enqueue the job"""

    db_session = override_get_db_session()

    # Mock the polling service
    mock_polling_service = MagicMock()
    mock_polling_service.enqueue.return_value = False

    status_code, task_response = client.create_task(
        name="test_registered_agent_polling_execution_success_task",
        is_agentic=True,
    )
    assert status_code == 200

    agent_polling_data = None
    try:
        # Create agent polling data
        agent_polling_data_id = uuid.uuid4()
        agent_polling_data = DatabaseAgentPollingData(
            id=agent_polling_data_id,
            task_id=task_response.id,
            provider=RegisteredAgentProvider.GCP.value,
            gcp_credentials={
                "project_id": "test-project",
                "region": "test-region",
                "resource_id": "test-resource",
            },
            status=AgentPollingStatus.ERROR.value,
            failed_runs=0,
            error_message=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_fetched=None,
        )

        db_session.add(agent_polling_data)
        db_session.commit()

        with patch(
            "repositories.agent_discovery_repository.get_registered_agent_polling_service",
            return_value=mock_polling_service,
        ):
            status_code, response = client.retry_agent_polling_task(
                str(agent_polling_data.id),
            )
            assert status_code == 503
            assert (
                response["detail"]
                == f"Registered agent polling service is not initialized. Skipping adding this agent to the polling queue."
            )

            db_session.expire_all()
            db_agent_polling_data = (
                db_session.query(DatabaseAgentPollingData)
                .filter(DatabaseAgentPollingData.id == agent_polling_data.id)
                .first()
            )
            assert db_agent_polling_data is not None
            assert db_agent_polling_data.status == AgentPollingStatus.ERROR.value
            assert (
                db_agent_polling_data.error_message
                == "Failed to enqueue retry polling job"
            )
    finally:
        if agent_polling_data is not None:
            db_session.delete(agent_polling_data)
            db_session.commit()

        client.delete_task(task_response.id)
