"""Unit tests for the GlobalAgentPollingService."""

import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from db_models import DatabaseTask
from db_models.agent_polling_models import DatabaseTaskPollingState
from arthur_common.models.agent_governance_schemas import (
    GCPCreationSource,
    ManualCreationSource,
    TaskMetadata,
)
from schemas.internal_schemas import Task
from services.task.global_agent_polling_service import (
    AgentPollingJob,
    GlobalAgentPollingService,
    get_global_agent_polling_service,
    initialize_global_agent_polling_service,
    shutdown_global_agent_polling_service,
)


@pytest.mark.unit_tests
def test_agent_polling_job_creation():
    job = AgentPollingJob(task_id="test-task-id")
    assert job.task_id == "test-task-id"
    assert job.delay_seconds == 0


@pytest.mark.unit_tests
def test_agent_polling_job_with_delay():
    job = AgentPollingJob(task_id="test-task-id", delay_seconds=10)
    assert job.task_id == "test-task-id"
    assert job.delay_seconds == 10


@pytest.mark.unit_tests
def test_get_job_key_uses_task_id():
    service = GlobalAgentPollingService()
    job = AgentPollingJob(task_id="task-123")
    assert service._get_job_key(job) == "task-123"


@pytest.mark.unit_tests
def test_get_job_key_deduplicates():
    service = GlobalAgentPollingService()
    job1 = AgentPollingJob(task_id="task-123")
    job2 = AgentPollingJob(task_id="task-123")
    assert service._get_job_key(job1) == service._get_job_key(job2)


@pytest.mark.unit_tests
@patch("services.task.global_agent_polling_service.get_db_session")
@patch("os.getenv")
def test_discover_gcp_agents_skips_when_no_project(mock_getenv, mock_get_db):
    """Discovery is skipped when GOOGLE_CLOUD_PROJECT is not set."""
    mock_getenv.return_value = None

    service = GlobalAgentPollingService()
    service._discover_gcp_agents()

    mock_get_db.assert_not_called()


@pytest.mark.unit_tests
@patch("services.task.global_agent_polling_service.get_db_session")
@patch("os.getenv")
def test_poll_all_gcp_tasks_skips_when_no_project(mock_getenv, mock_get_db):
    """Polling is skipped when GOOGLE_CLOUD_PROJECT is not set."""
    mock_getenv.return_value = None

    service = GlobalAgentPollingService()
    service._poll_all_gcp_tasks()

    mock_get_db.assert_not_called()


@pytest.mark.unit_tests
def test_is_task_eligible_matching_project_and_region():
    """Task is eligible when project and region match."""

    service = GlobalAgentPollingService()
    creation_source = GCPCreationSource(
        gcp_project_id="my-project",
        gcp_region="us-central1",
        gcp_reasoning_engine_id="12345",
    )

    assert service._is_task_eligible_for_polling(
        "task-1", creation_source, "my-project", "us-central1"
    )


@pytest.mark.unit_tests
def test_is_task_eligible_mismatched_project():
    """Task is ineligible when project doesn't match."""

    service = GlobalAgentPollingService()
    creation_source = GCPCreationSource(
        gcp_project_id="old-project",
        gcp_region="us-central1",
        gcp_reasoning_engine_id="12345",
    )

    assert not service._is_task_eligible_for_polling(
        "task-1", creation_source, "new-project", "us-central1"
    )


@pytest.mark.unit_tests
def test_is_task_eligible_mismatched_region():
    """Task is ineligible when region doesn't match."""

    service = GlobalAgentPollingService()
    creation_source = GCPCreationSource(
        gcp_project_id="my-project",
        gcp_region="us-east1",
        gcp_reasoning_engine_id="12345",
    )

    assert not service._is_task_eligible_for_polling(
        "task-1", creation_source, "my-project", "us-central1"
    )


@pytest.mark.unit_tests
@patch("services.task.global_agent_polling_service.get_db_session")
@patch("services.task.global_agent_polling_service.ExternalTraceRetrievalService")
@patch("services.task.global_agent_polling_service.TaskRepository")
@patch("services.task.global_agent_polling_service.TaskPollingStateRepository")
@patch("services.task.global_agent_polling_service.SpanRepository")
@patch("services.task.global_agent_polling_service.RuleRepository")
@patch("services.task.global_agent_polling_service.MetricRepository")
@patch("services.task.global_agent_polling_service.ConfigurationRepository")
@patch("services.task.global_agent_polling_service.TasksMetricsRepository")
def test_execute_job_success(
    mock_tasks_metrics_repo_cls,
    mock_config_repo_cls,
    mock_metric_repo_cls,
    mock_rule_repo_cls,
    mock_span_repo_cls,
    mock_polling_repo_cls,
    mock_task_repo_cls,
    mock_trace_service_cls,
    mock_get_db,
):
    """Test successful trace fetch and ingestion for a GCP task."""
    task_id = str(uuid.uuid4())

    mock_task = MagicMock(spec=Task)
    mock_task.id = task_id
    mock_task.name = "Test GCP Agent"
    mock_task.task_metadata = TaskMetadata(
        creation_source=GCPCreationSource(
            gcp_project_id="test-project",
            gcp_region="us-central1",
            gcp_reasoning_engine_id="12345",
        )
    )

    mock_polling_state = MagicMock(spec=DatabaseTaskPollingState)
    mock_polling_state.last_fetched = None

    mock_trace_service = MagicMock()
    # Return an iterator of pages (each page is a list of traces)
    mock_trace_service.fetch_traces_from_cloud_trace.return_value = iter([
        [{"traceId": "trace-1", "spans": []}]
    ])
    mock_trace_service_cls.return_value = mock_trace_service

    mock_session = MagicMock()
    mock_get_db.return_value = iter([mock_session])

    mock_task_repo = MagicMock()
    mock_task_repo.get_task_by_id.return_value = mock_task
    mock_task_repo_cls.return_value = mock_task_repo

    mock_polling_repo = MagicMock()
    mock_polling_repo.get_or_create.return_value = mock_polling_state
    mock_polling_repo_cls.return_value = mock_polling_repo

    mock_span_repo = MagicMock()
    mock_span_repo_cls.return_value = mock_span_repo

    service = GlobalAgentPollingService()
    job = AgentPollingJob(task_id=task_id)
    service._execute_job(job)

    # Verify traces were fetched
    mock_trace_service.fetch_traces_from_cloud_trace.assert_called_once()
    call_kwargs = mock_trace_service.fetch_traces_from_cloud_trace.call_args
    assert call_kwargs.kwargs["project_id"] == "test-project"
    assert call_kwargs.kwargs["reasoning_engine_id"] == "12345"
    assert call_kwargs.kwargs["task_id"] == task_id

    # Verify traces were ingested (once per page)
    mock_span_repo.convert_and_send_traces_from_external_provider.assert_called_once()

    # Verify last_fetched was updated
    mock_polling_repo.update_last_fetched.assert_called_once()


@pytest.mark.unit_tests
@patch("services.task.global_agent_polling_service.get_db_session")
@patch("services.task.global_agent_polling_service.ExternalTraceRetrievalService")
@patch("services.task.global_agent_polling_service.TaskRepository")
@patch("services.task.global_agent_polling_service.TaskPollingStateRepository")
@patch("services.task.global_agent_polling_service.SpanRepository")
@patch("services.task.global_agent_polling_service.RuleRepository")
@patch("services.task.global_agent_polling_service.MetricRepository")
@patch("services.task.global_agent_polling_service.ConfigurationRepository")
@patch("services.task.global_agent_polling_service.TasksMetricsRepository")
def test_execute_job_failure_does_not_update_polling_state(
    mock_tasks_metrics_repo_cls,
    mock_config_repo_cls,
    mock_metric_repo_cls,
    mock_rule_repo_cls,
    mock_span_repo_cls,
    mock_polling_repo_cls,
    mock_task_repo_cls,
    mock_trace_service_cls,
    mock_get_db,
):
    """Test that a failed poll does NOT update last_fetched (will retry next loop)."""
    task_id = str(uuid.uuid4())

    mock_task = MagicMock(spec=Task)
    mock_task.id = task_id
    mock_task.name = "Test GCP Agent"
    mock_task.task_metadata = TaskMetadata(
        creation_source=GCPCreationSource(
            gcp_project_id="test-project",
            gcp_region="us-central1",
            gcp_reasoning_engine_id="12345",
        )
    )

    mock_polling_state = MagicMock(spec=DatabaseTaskPollingState)
    mock_polling_state.last_fetched = datetime.now() - timedelta(hours=1)

    mock_trace_service = MagicMock()
    mock_trace_service.fetch_traces_from_cloud_trace.side_effect = Exception(
        "GCP API error"
    )
    mock_trace_service_cls.return_value = mock_trace_service

    mock_session = MagicMock()
    mock_get_db.return_value = iter([mock_session])

    mock_task_repo = MagicMock()
    mock_task_repo.get_task_by_id.return_value = mock_task
    mock_task_repo_cls.return_value = mock_task_repo

    mock_polling_repo = MagicMock()
    mock_polling_repo.get_or_create.return_value = mock_polling_state
    mock_polling_repo_cls.return_value = mock_polling_repo

    service = GlobalAgentPollingService()
    job = AgentPollingJob(task_id=task_id)

    # Should not raise — error is caught and logged
    service._execute_job(job)

    # Verify last_fetched was NOT updated
    mock_polling_repo.update_last_fetched.assert_not_called()


@pytest.mark.unit_tests
@patch("services.task.global_agent_polling_service.get_db_session")
@patch("services.task.global_agent_polling_service.ExternalTraceRetrievalService")
@patch("services.task.global_agent_polling_service.TaskRepository")
@patch("services.task.global_agent_polling_service.TaskPollingStateRepository")
@patch("services.task.global_agent_polling_service.SpanRepository")
@patch("services.task.global_agent_polling_service.RuleRepository")
@patch("services.task.global_agent_polling_service.MetricRepository")
@patch("services.task.global_agent_polling_service.ConfigurationRepository")
@patch("services.task.global_agent_polling_service.TasksMetricsRepository")
def test_execute_job_no_traces_still_updates_last_fetched(
    mock_tasks_metrics_repo_cls,
    mock_config_repo_cls,
    mock_metric_repo_cls,
    mock_rule_repo_cls,
    mock_span_repo_cls,
    mock_polling_repo_cls,
    mock_task_repo_cls,
    mock_trace_service_cls,
    mock_get_db,
):
    """Test that when no traces are found, last_fetched is still updated."""
    task_id = str(uuid.uuid4())

    mock_task = MagicMock(spec=Task)
    mock_task.id = task_id
    mock_task.name = "Test GCP Agent"
    mock_task.task_metadata = TaskMetadata(
        creation_source=GCPCreationSource(
            gcp_project_id="test-project",
            gcp_region="us-central1",
            gcp_reasoning_engine_id="12345",
        )
    )

    mock_polling_state = MagicMock(spec=DatabaseTaskPollingState)
    mock_polling_state.last_fetched = datetime.now() - timedelta(hours=1)

    mock_trace_service = MagicMock()
    # Return an empty iterator (no pages yielded)
    mock_trace_service.fetch_traces_from_cloud_trace.return_value = iter([])
    mock_trace_service_cls.return_value = mock_trace_service

    mock_session = MagicMock()
    mock_get_db.return_value = iter([mock_session])

    mock_task_repo = MagicMock()
    mock_task_repo.get_task_by_id.return_value = mock_task
    mock_task_repo_cls.return_value = mock_task_repo

    mock_polling_repo = MagicMock()
    mock_polling_repo.get_or_create.return_value = mock_polling_state
    mock_polling_repo_cls.return_value = mock_polling_repo

    service = GlobalAgentPollingService()
    job = AgentPollingJob(task_id=task_id)
    service._execute_job(job)

    # Verify last_fetched WAS updated (even though no traces found)
    mock_polling_repo.update_last_fetched.assert_called_once()


@pytest.mark.unit_tests
@patch("services.task.global_agent_polling_service.get_db_session")
@patch("services.task.global_agent_polling_service.TaskRepository")
@patch("services.task.global_agent_polling_service.RuleRepository")
@patch("services.task.global_agent_polling_service.MetricRepository")
@patch("services.task.global_agent_polling_service.ConfigurationRepository")
def test_execute_job_skips_non_gcp_task(
    mock_config_repo_cls,
    mock_metric_repo_cls,
    mock_rule_repo_cls,
    mock_task_repo_cls,
    mock_get_db,
):
    """Test that _execute_job skips tasks that are not GCP."""
    task_id = str(uuid.uuid4())

    mock_task = MagicMock(spec=Task)
    mock_task.id = task_id
    mock_task.name = "Manual Agent"
    mock_task.task_metadata = TaskMetadata(
        creation_source=ManualCreationSource()
    )

    mock_session = MagicMock()
    mock_get_db.return_value = iter([mock_session])

    mock_task_repo = MagicMock()
    mock_task_repo.get_task_by_id.return_value = mock_task
    mock_task_repo_cls.return_value = mock_task_repo

    service = GlobalAgentPollingService()
    job = AgentPollingJob(task_id=task_id)

    # Should complete without error and without calling trace service
    service._execute_job(job)


@pytest.mark.unit_tests
def test_find_task_by_gcp_engine_id_found():
    """Test the JSON query for finding tasks by engine ID."""
    mock_task = MagicMock(spec=DatabaseTask)
    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.first.return_value = mock_task

    service = GlobalAgentPollingService()

    # Patch the SQLAlchemy JSON column to avoid real column subscript operations
    with patch.object(
        DatabaseTask, "task_metadata", create=True, new_callable=MagicMock
    ):
        result = service._find_task_by_gcp_engine_id(mock_session, "12345")

    assert result is mock_task
    mock_session.query.assert_called_once_with(DatabaseTask)


@pytest.mark.unit_tests
def test_find_task_by_gcp_engine_id_not_found():
    """Test returns None when no task matches engine ID."""
    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.first.return_value = None

    service = GlobalAgentPollingService()

    with patch.object(
        DatabaseTask, "task_metadata", create=True, new_callable=MagicMock
    ):
        result = service._find_task_by_gcp_engine_id(mock_session, "nonexistent")

    assert result is None


@pytest.mark.unit_tests
def test_initialize_and_shutdown():
    # Ensure clean state
    shutdown_global_agent_polling_service()
    assert get_global_agent_polling_service() is None

    # Initialize
    initialize_global_agent_polling_service(num_workers=1)
    service = get_global_agent_polling_service()
    assert service is not None
    assert isinstance(service, GlobalAgentPollingService)

    # Shutdown
    shutdown_global_agent_polling_service()
    assert get_global_agent_polling_service() is None


@pytest.mark.unit_tests
def test_initialize_is_idempotent():
    shutdown_global_agent_polling_service()

    initialize_global_agent_polling_service(num_workers=1)
    service1 = get_global_agent_polling_service()

    # Second call should not create a new instance
    initialize_global_agent_polling_service(num_workers=2)
    service2 = get_global_agent_polling_service()

    assert service1 is service2

    shutdown_global_agent_polling_service()
