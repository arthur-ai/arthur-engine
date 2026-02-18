import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from arthur_common.models.enums import AgentPollingStatus, RegisteredAgentProvider
from google.api_core.exceptions import GoogleAPIError
from sqlalchemy.orm import Session

from db_models.agent_polling_models import DatabaseAgentPollingData
from db_models.task_models import DatabaseTask
from db_models.telemetry_models import DatabaseSpan, DatabaseTraceMetadata
from services.task.registered_agent_polling_service import (
    AgentPollingJob,
    RegisteredAgentPollingService,
)
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)


def mock_get_db_session_generator():
    """Generator function that yields the test database session."""
    yield override_get_db_session()


def mock_fetch_traces_from_cloud_trace(*args, **kwargs):
    """Mock function that returns sample traces."""
    return [
        {
            "trace_id": "0123456789abcdef0123456789abcdef",
            "spans": [
                {
                    "span_id": "0123456789abcdef",
                    "name": "test_operation",
                    "start_time": "2024-01-01T00:00:00.000000Z",
                    "end_time": "2024-01-01T00:00:01.000000Z",
                    "attributes": {"test_key": "test_value"},
                },
            ],
        },
    ]


def create_task(db_session: Session) -> DatabaseTask:
    task_response = DatabaseTask(
        id=str(uuid.uuid4()),
        name="test_registered_agent_polling_execution_success_task",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        is_agentic=True,
        task_metadata={
            "provider": RegisteredAgentProvider.GCP.value,
            "gcp_metadata": {
                "project_id": "test-project",
                "region": "test-region",
                "resource_id": "test-resource",
            },
        },
    )
    db_session.add(task_response)
    db_session.commit()
    db_session.expire_all()
    return task_response


@pytest.mark.unit_tests
@patch(
    "services.task.registered_agent_polling_service.get_db_session",
    side_effect=mock_get_db_session_generator,
)
@patch(
    "services.trace.external_trace_retrieval_service.ExternalTraceRetrievalService.fetch_traces_from_cloud_trace",
    side_effect=mock_fetch_traces_from_cloud_trace,
)
def test_registered_agent_polling_execution_success(
    mock_fetch_traces,
    mock_get_db_session,
    client: GenaiEngineTestClientBase,
):
    """Test the registered agent polling execution"""

    db_session = override_get_db_session()

    task_response = create_task(db_session)

    agent_polling_data = None
    try:
        # Create agent polling data
        agent_polling_data_id = uuid.uuid4()
        agent_polling_data = DatabaseAgentPollingData(
            id=agent_polling_data_id,
            task_id=task_response.id,
            status=AgentPollingStatus.PENDING.value,
            failed_runs=0,
            error_message=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_fetched=None,
        )

        db_session.add(agent_polling_data)
        db_session.commit()

        # Create the job
        job = AgentPollingJob(
            agent_polling_data_id=agent_polling_data.id,
            delay_seconds=0,
        )

        registered_agent_polling_service = RegisteredAgentPollingService()
        registered_agent_polling_service._execute_job(job)

        # Refresh the session to get updated data
        db_session.expire_all()

        # Check the agent polling data
        db_agent_polling_data = (
            db_session.query(DatabaseAgentPollingData)
            .filter(DatabaseAgentPollingData.id == agent_polling_data.id)
            .first()
        )
        assert db_agent_polling_data is not None
        assert db_agent_polling_data.status == AgentPollingStatus.IDLE.value
        assert db_agent_polling_data.last_fetched is not None
        assert db_agent_polling_data.error_message is None
        assert db_agent_polling_data.failed_runs == 0
    finally:
        if agent_polling_data is not None:
            db_session.delete(agent_polling_data)

        db_session.delete(task_response)
        db_session.commit()


@pytest.mark.unit_tests
@patch(
    "services.task.registered_agent_polling_service.get_db_session",
    side_effect=mock_get_db_session_generator,
)
@patch(
    "services.trace.external_trace_retrieval_service.ExternalTraceRetrievalService.fetch_traces_from_cloud_trace",
    side_effect=mock_fetch_traces_from_cloud_trace,
)
def test_registered_agent_polling_execution_nonexistent_agent_polling_data(
    mock_fetch_traces,
    mock_get_db_session,
    client: GenaiEngineTestClientBase,
):
    """Test the registered agent polling execution when agent polling data does not exist"""

    db_session = override_get_db_session()
    task_response = create_task(db_session)

    try:
        # Create agent polling data
        agent_polling_data_id = uuid.uuid4()

        # Create the job
        job = AgentPollingJob(
            agent_polling_data_id=agent_polling_data_id,
            delay_seconds=0,
        )

        registered_agent_polling_service = RegisteredAgentPollingService()

        with pytest.raises(
            ValueError,
            match=f"Agent polling data {agent_polling_data_id} not found",
        ):
            registered_agent_polling_service._execute_job(job)
    finally:
        db_session.delete(task_response)
        db_session.commit()


@pytest.mark.unit_tests
@patch(
    "services.task.registered_agent_polling_service.get_db_session",
    side_effect=mock_get_db_session_generator,
)
@patch(
    "services.trace.external_trace_retrieval_service.ExternalTraceRetrievalService.fetch_traces_from_cloud_trace",
    return_value=[],
)
def test_registered_agent_polling_execution_no_traces_still_updates_last_fetched(
    mock_fetch_traces,
    mock_get_db_session,
    client: GenaiEngineTestClientBase,
):
    """Test the registered agent polling execution when no traces are found"""

    db_session = override_get_db_session()
    task_response = create_task(db_session)

    agent_polling_data = None
    try:
        # Create agent polling data
        agent_polling_data_id = uuid.uuid4()
        agent_polling_data = DatabaseAgentPollingData(
            id=agent_polling_data_id,
            task_id=task_response.id,
            status=AgentPollingStatus.PENDING.value,
            failed_runs=0,
            error_message=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_fetched=None,
        )

        db_session.add(agent_polling_data)
        db_session.commit()

        # Create the job
        job = AgentPollingJob(
            agent_polling_data_id=agent_polling_data_id,
            delay_seconds=0,
        )

        registered_agent_polling_service = RegisteredAgentPollingService()
        registered_agent_polling_service._execute_job(job)

        # Refresh the session to get updated data
        db_session.expire_all()

        # Check the agent polling data
        db_agent_polling_data = (
            db_session.query(DatabaseAgentPollingData)
            .filter(DatabaseAgentPollingData.id == agent_polling_data.id)
            .first()
        )
        assert db_agent_polling_data is not None
        assert db_agent_polling_data.status == AgentPollingStatus.IDLE.value
        assert db_agent_polling_data.last_fetched is not None
    finally:
        if agent_polling_data is not None:
            db_session.delete(agent_polling_data)

        db_session.delete(task_response)
        db_session.commit()


@pytest.mark.unit_tests
@patch(
    "services.task.registered_agent_polling_service.get_db_session",
    side_effect=mock_get_db_session_generator,
)
@patch(
    "services.trace.external_trace_retrieval_service.ExternalTraceRetrievalService.fetch_traces_from_cloud_trace",
    side_effect=GoogleAPIError(),
)
def test_registered_agent_polling_execution_allows_five_failures_before_marking_as_error(
    mock_fetch_traces,
    mock_get_db_session,
    client: GenaiEngineTestClientBase,
):
    """Test the registered agent polling execution when no traces are found"""

    db_session = override_get_db_session()
    task_response = create_task(db_session)

    agent_polling_data = None
    try:
        # Create agent polling data
        agent_polling_data_id = uuid.uuid4()
        agent_polling_data = DatabaseAgentPollingData(
            id=agent_polling_data_id,
            task_id=task_response.id,
            status=AgentPollingStatus.PENDING.value,
            failed_runs=0,
            error_message=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_fetched=None,
        )

        db_session.add(agent_polling_data)
        db_session.commit()

        # Create the job
        job = AgentPollingJob(
            agent_polling_data_id=agent_polling_data_id,
            delay_seconds=0,
        )
        registered_agent_polling_service = RegisteredAgentPollingService()

        for i in range(4):
            registered_agent_polling_service._execute_job(job)

            # Refresh the session to get updated data
            db_session.expire_all()

            # Check the agent polling data
            db_agent_polling_data = (
                db_session.query(DatabaseAgentPollingData)
                .filter(DatabaseAgentPollingData.id == agent_polling_data.id)
                .first()
            )
            assert db_agent_polling_data is not None
            assert db_agent_polling_data.status == AgentPollingStatus.IDLE.value
            assert db_agent_polling_data.last_fetched is None
            assert db_agent_polling_data.failed_runs == i + 1
            assert db_agent_polling_data.error_message is not None
            assert f"attempt {i + 1}/5" in db_agent_polling_data.error_message

        # The 5th failure should raise an exception and mark as ERROR
        with pytest.raises(GoogleAPIError):
            registered_agent_polling_service._execute_job(job)

        # Refresh the session to get updated data
        db_session.expire_all()

        # Check the agent polling data
        db_agent_polling_data = (
            db_session.query(DatabaseAgentPollingData)
            .filter(DatabaseAgentPollingData.id == agent_polling_data.id)
            .first()
        )
        assert db_agent_polling_data is not None
        assert db_agent_polling_data.status == AgentPollingStatus.ERROR.value
        assert db_agent_polling_data.last_fetched is None
        assert db_agent_polling_data.error_message is not None
        assert "Exceeded maximum failed runs (5)" in db_agent_polling_data.error_message
        assert db_agent_polling_data.failed_runs == 5
    finally:
        if agent_polling_data is not None:
            db_session.delete(agent_polling_data)

        db_session.delete(task_response)
        db_session.commit()


@pytest.mark.unit_tests
@patch(
    "services.task.registered_agent_polling_service.get_db_session",
    side_effect=mock_get_db_session_generator,
)
@patch(
    "services.trace.external_trace_retrieval_service.ExternalTraceRetrievalService.fetch_traces_from_cloud_trace",
    side_effect=ValueError("Test error"),
)
def test_registered_agent_polling_execution_errors_immediately_on_non_api_errors(
    mock_fetch_traces,
    mock_get_db_session,
    client: GenaiEngineTestClientBase,
):
    """Test the registered agent polling execution when an error is raised that is not an external service api error"""

    db_session = override_get_db_session()
    task_response = create_task(db_session)

    agent_polling_data = None
    try:
        # Create agent polling data
        agent_polling_data_id = uuid.uuid4()
        agent_polling_data = DatabaseAgentPollingData(
            id=agent_polling_data_id,
            task_id=task_response.id,
            status=AgentPollingStatus.PENDING.value,
            failed_runs=0,
            error_message=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_fetched=None,
        )

        db_session.add(agent_polling_data)
        db_session.commit()

        # Create the job
        job = AgentPollingJob(
            agent_polling_data_id=agent_polling_data_id,
            delay_seconds=0,
        )
        registered_agent_polling_service = RegisteredAgentPollingService()

        with pytest.raises(ValueError, match="Test error"):
            registered_agent_polling_service._execute_job(job)

        # Refresh the session to get updated data
        db_session.expire_all()

        # Check the agent polling data
        db_agent_polling_data = (
            db_session.query(DatabaseAgentPollingData)
            .filter(DatabaseAgentPollingData.id == agent_polling_data.id)
            .first()
        )
        assert db_agent_polling_data is not None
        assert db_agent_polling_data.status == AgentPollingStatus.ERROR.value
        assert db_agent_polling_data.last_fetched is None
        assert db_agent_polling_data.error_message is not None
        assert "Test error" in db_agent_polling_data.error_message
        assert db_agent_polling_data.failed_runs == 0
    finally:
        if agent_polling_data is not None:
            db_session.delete(agent_polling_data)

        db_session.delete(task_response)
        db_session.commit()


@pytest.mark.unit_tests
@patch(
    "services.task.registered_agent_polling_service.get_db_session",
    side_effect=mock_get_db_session_generator,
)
@patch(
    "services.trace.external_trace_retrieval_service.ExternalTraceRetrievalService.fetch_traces_from_cloud_trace",
    side_effect=GoogleAPIError(),
)
def test_registered_agent_polling_execution_already_running(
    mock_fetch_traces,
    mock_get_db_session,
    client: GenaiEngineTestClientBase,
    caplog: pytest.LogCaptureFixture,
):
    """Test the registered agent polling execution when the agent polling data is already running"""

    db_session = override_get_db_session()
    task_response = create_task(db_session)

    agent_polling_data = None
    try:
        # Create agent polling data
        agent_polling_data_id = uuid.uuid4()
        agent_polling_data = DatabaseAgentPollingData(
            id=agent_polling_data_id,
            task_id=task_response.id,
            status=AgentPollingStatus.RUNNING.value,
            failed_runs=0,
            error_message=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_fetched=None,
        )

        db_session.add(agent_polling_data)
        db_session.commit()

        # Create the job
        job = AgentPollingJob(
            agent_polling_data_id=agent_polling_data_id,
            delay_seconds=0,
        )
        registered_agent_polling_service = RegisteredAgentPollingService()

        registered_agent_polling_service._execute_job(job)

        # Check that the log message was sent
        assert (
            f"Agent polling data {agent_polling_data_id} is already running, skipping"
            in caplog.text
        )

        # Refresh the session to get updated data
        db_session.expire_all()

        # Check the agent polling data - should remain unchanged
        db_agent_polling_data = (
            db_session.query(DatabaseAgentPollingData)
            .filter(DatabaseAgentPollingData.id == agent_polling_data.id)
            .first()
        )
        assert db_agent_polling_data is not None
        assert db_agent_polling_data.status == AgentPollingStatus.RUNNING.value
    finally:
        if agent_polling_data is not None:
            db_session.delete(agent_polling_data)

        db_session.delete(task_response)
        db_session.commit()


@pytest.mark.unit_tests
@patch(
    "services.task.registered_agent_polling_service.get_db_session",
    side_effect=mock_get_db_session_generator,
)
@patch(
    "services.trace.external_trace_retrieval_service.ExternalTraceRetrievalService.fetch_traces_from_cloud_trace",
    side_effect=GoogleAPIError(),
)
def test_registered_agent_polling_execution_already_failed(
    mock_fetch_traces,
    mock_get_db_session,
    client: GenaiEngineTestClientBase,
    caplog: pytest.LogCaptureFixture,
):
    """Test the registered agent polling execution when the agent polling data is already failed"""

    db_session = override_get_db_session()
    task_response = create_task(db_session)

    agent_polling_data = None
    try:
        # Create agent polling data
        agent_polling_data_id = uuid.uuid4()
        agent_polling_data = DatabaseAgentPollingData(
            id=agent_polling_data_id,
            task_id=task_response.id,
            status=AgentPollingStatus.ERROR.value,
            failed_runs=0,
            error_message=None,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_fetched=None,
        )

        db_session.add(agent_polling_data)
        db_session.commit()

        # Create the job
        job = AgentPollingJob(
            agent_polling_data_id=agent_polling_data_id,
            delay_seconds=0,
        )
        registered_agent_polling_service = RegisteredAgentPollingService()

        registered_agent_polling_service._execute_job(job)

        # Check that the log message was sent
        assert (
            f"Agent polling data {agent_polling_data_id} has failed, skipping"
            in caplog.text
        )

        # Refresh the session to get updated data
        db_session.expire_all()

        # Check the agent polling data - should remain unchanged
        db_agent_polling_data = (
            db_session.query(DatabaseAgentPollingData)
            .filter(DatabaseAgentPollingData.id == agent_polling_data.id)
            .first()
        )
        assert db_agent_polling_data is not None
        assert db_agent_polling_data.status == AgentPollingStatus.ERROR.value
    finally:
        if agent_polling_data is not None:
            db_session.delete(agent_polling_data)

        db_session.delete(task_response)
        db_session.commit()


@pytest.mark.unit_tests
@patch(
    "services.task.registered_agent_polling_service.get_db_session",
    side_effect=mock_get_db_session_generator,
)
def test_registered_agent_polling_execution_stores_traces_in_database(
    mock_get_db_session,
    client: GenaiEngineTestClientBase,
):
    """Test that the registered agent polling execution stores traces in the database span and trace metadata tables"""

    # Create mock trace objects
    mock_trace_list_item = MagicMock()
    mock_trace_list_item.trace_id = "0123456789abcdef0123456789abcdef"

    mock_span = MagicMock()
    mock_span.span_id = "0123456789abcdef"
    mock_span.name = "test_operation"
    mock_span.start_time = datetime(2024, 1, 1, 0, 0, 0)
    mock_span.end_time = datetime(2024, 1, 1, 0, 0, 1)
    mock_span.labels = {"test_key": "test_value"}
    mock_span.parent_span_id = None

    mock_full_trace = MagicMock()
    mock_full_trace.trace_id = "0123456789abcdef0123456789abcdef"
    mock_full_trace.project_id = "test-project"
    mock_full_trace.spans = [mock_span]

    with patch(
        "services.trace.external_trace_retrieval_service.trace_v1.TraceServiceClient",
    ) as mock_client_class:
        mock_trace_client = MagicMock()
        mock_trace_client.list_traces.return_value = [mock_trace_list_item]
        mock_trace_client.get_trace.return_value = mock_full_trace
        mock_client_class.return_value = mock_trace_client

        db_session = override_get_db_session()
        task_response = create_task(db_session)

        agent_polling_data = None
        try:
            # Create agent polling data
            agent_polling_data_id = uuid.uuid4()
            agent_polling_data = DatabaseAgentPollingData(
                id=agent_polling_data_id,
                task_id=task_response.id,
                status=AgentPollingStatus.PENDING.value,
                failed_runs=0,
                error_message=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                last_fetched=None,
            )

            db_session.add(agent_polling_data)
            db_session.commit()

            # Create the job
            job = AgentPollingJob(
                agent_polling_data_id=agent_polling_data.id,
                delay_seconds=0,
            )

            registered_agent_polling_service = RegisteredAgentPollingService()
            registered_agent_polling_service._execute_job(job)

            # Verify that list_traces and get_trace were called
            assert mock_trace_client.list_traces.called
            assert mock_trace_client.get_trace.called

            # Refresh the session to get updated data
            db_session.expire_all()

            # Check that traces were stored in the database
            trace_metadata = (
                db_session.query(DatabaseTraceMetadata)
                .filter(DatabaseTraceMetadata.task_id == task_response.id)
                .all()
            )
            assert (
                len(trace_metadata) == 1
            ), f"Expected 1 trace metadata, found {len(trace_metadata)}"

            # Verify trace metadata fields
            trace = trace_metadata[0]
            assert trace.trace_id is not None
            assert trace.task_id == task_response.id
            assert trace.start_time is not None
            assert trace.end_time is not None
            assert trace.span_count == 1

            # Check that spans were stored in the database
            spans = (
                db_session.query(DatabaseSpan)
                .filter(DatabaseSpan.task_id == task_response.id)
                .all()
            )
            assert len(spans) == 1, f"Expected 1 span, found {len(spans)}"

            # Verify span fields
            span = spans[0]
            assert span.id is not None
            assert span.trace_id is not None
            assert span.span_id is not None
            assert span.task_id == task_response.id
            assert span.start_time is not None
            assert span.end_time is not None
            assert span.raw_data is not None

            # Verify the trace_id matches between span and trace metadata
            assert span.trace_id == trace.trace_id

        finally:
            # Clean up spans and trace metadata
            spans = (
                db_session.query(DatabaseSpan)
                .filter(DatabaseSpan.task_id == task_response.id)
                .all()
            )
            for span in spans:
                db_session.delete(span)

            trace_metadata = (
                db_session.query(DatabaseTraceMetadata)
                .filter(DatabaseTraceMetadata.task_id == task_response.id)
                .all()
            )
            for trace in trace_metadata:
                db_session.delete(trace)

            if agent_polling_data is not None:
                db_session.delete(agent_polling_data)

            db_session.delete(task_response)
            db_session.commit()


@pytest.mark.unit_tests
@patch(
    "services.task.registered_agent_polling_service.get_db_session",
    side_effect=mock_get_db_session_generator,
)
@patch(
    "services.trace.external_trace_retrieval_service.ExternalTraceRetrievalService.fetch_traces_from_cloud_trace",
    side_effect=mock_fetch_traces_from_cloud_trace,
)
def test_registered_agent_polling_execution_success_resets_failed_runs(
    mock_fetch_traces,
    mock_get_db_session,
    client: GenaiEngineTestClientBase,
):
    """Test a successful registered agent polling execution resets the failed runs count"""

    db_session = override_get_db_session()

    task_response = create_task(db_session)

    agent_polling_data = None
    try:
        # Create agent polling data
        agent_polling_data_id = uuid.uuid4()
        agent_polling_data = DatabaseAgentPollingData(
            id=agent_polling_data_id,
            task_id=task_response.id,
            status=AgentPollingStatus.PENDING.value,
            failed_runs=4,
            error_message="Test error",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_fetched=None,
        )

        db_session.add(agent_polling_data)
        db_session.commit()

        # Create the job
        job = AgentPollingJob(
            agent_polling_data_id=agent_polling_data.id,
            delay_seconds=0,
        )

        registered_agent_polling_service = RegisteredAgentPollingService()
        registered_agent_polling_service._execute_job(job)

        # Refresh the session to get updated data
        db_session.expire_all()

        # Check the agent polling data
        db_agent_polling_data = (
            db_session.query(DatabaseAgentPollingData)
            .filter(DatabaseAgentPollingData.id == agent_polling_data.id)
            .first()
        )
        assert db_agent_polling_data is not None
        assert db_agent_polling_data.status == AgentPollingStatus.IDLE.value
        assert db_agent_polling_data.last_fetched is not None
        assert db_agent_polling_data.error_message is None
        assert db_agent_polling_data.failed_runs == 0
    finally:
        if agent_polling_data is not None:
            db_session.delete(agent_polling_data)

        db_session.delete(task_response)
        db_session.commit()


@pytest.mark.unit_tests
@patch(
    "services.task.registered_agent_polling_service.get_db_session",
    side_effect=mock_get_db_session_generator,
)
@patch(
    "services.trace.external_trace_retrieval_service.ExternalTraceRetrievalService.fetch_traces_from_cloud_trace",
    return_value=[],
)
def test_registered_agent_polling_execution_no_trace_found_resets_failed_runs(
    mock_fetch_traces,
    mock_get_db_session,
    client: GenaiEngineTestClientBase,
):
    """
    Test that when no traces are found in a polling execution, the failed runs count still resets.
    This is because no traces found is still a successful execution, just no new data was found.
    """

    db_session = override_get_db_session()

    task_response = create_task(db_session)

    agent_polling_data = None
    try:
        # Create agent polling data
        agent_polling_data_id = uuid.uuid4()
        agent_polling_data = DatabaseAgentPollingData(
            id=agent_polling_data_id,
            task_id=task_response.id,
            status=AgentPollingStatus.PENDING.value,
            failed_runs=4,
            error_message="Test error",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_fetched=None,
        )

        db_session.add(agent_polling_data)
        db_session.commit()

        # Create the job
        job = AgentPollingJob(
            agent_polling_data_id=agent_polling_data.id,
            delay_seconds=0,
        )

        registered_agent_polling_service = RegisteredAgentPollingService()
        registered_agent_polling_service._execute_job(job)

        # Refresh the session to get updated data
        db_session.expire_all()

        # Check the agent polling data
        db_agent_polling_data = (
            db_session.query(DatabaseAgentPollingData)
            .filter(DatabaseAgentPollingData.id == agent_polling_data.id)
            .first()
        )
        assert db_agent_polling_data is not None
        assert db_agent_polling_data.status == AgentPollingStatus.IDLE.value
        assert db_agent_polling_data.last_fetched is not None
        assert db_agent_polling_data.error_message is None
        assert db_agent_polling_data.failed_runs == 0
    finally:
        if agent_polling_data is not None:
            db_session.delete(agent_polling_data)

        db_session.delete(task_response)
        db_session.commit()