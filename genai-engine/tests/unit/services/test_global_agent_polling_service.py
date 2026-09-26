"""Unit tests for the GlobalAgentPollingService."""

import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from db_models import DatabaseTask
from db_models.agent_polling_models import DatabaseTaskPollingState
from db_models.telemetry_models import DatabaseServiceNameTaskMapping
from arthur_common.models.agent_governance_schemas import (
    GCPAgentCreationSource,
    ManualAgentCreationSource,
    TaskMetadata,
)
from repositories.metrics_repository import MetricRepository
from repositories.rules_repository import RuleRepository
from repositories.service_name_mapping_repository import ServiceNameMappingRepository
from repositories.tasks_repository import TaskRepository
from dependencies import get_application_config
from schemas.internal_schemas import Task
from services.task.global_agent_polling_service import (
    AgentPollingJob,
    GlobalAgentPollingService,
    get_global_agent_polling_service,
    initialize_global_agent_polling_service,
    shutdown_global_agent_polling_service,
    POLLING_ADVISORY_LOCK_KEY,
)
from tests.clients.base_test_client import override_get_db_session
from utils.constants import DEFAULT_ORG_ID


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
    creation_source = GCPAgentCreationSource(
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
    creation_source = GCPAgentCreationSource(
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
    creation_source = GCPAgentCreationSource(
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
        creation_source=GCPAgentCreationSource(
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
        creation_source=GCPAgentCreationSource(
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
        creation_source=GCPAgentCreationSource(
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
        creation_source=ManualAgentCreationSource()
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
@patch("services.task.global_agent_polling_service.get_db_session")
def test_background_loop_leader_acquires_lock_and_polls(mock_get_db):
    """Leader replica acquires the advisory lock and runs the polling loop."""
    mock_session = MagicMock()
    mock_session.execute.return_value.scalar.return_value = True  # lock acquired
    mock_get_db.return_value = iter([mock_session])

    service = GlobalAgentPollingService()

    def run_once_then_shutdown():
        service.shutdown_event.set()

    with patch.object(
        service, "_discover_and_poll_agents", side_effect=run_once_then_shutdown
    ) as mock_dap:
        with patch.object(service.shutdown_event, "wait", return_value=False):
            service._background_loop()

    mock_dap.assert_called_once()
    mock_session.close.assert_called_once()
    # Verify advisory lock was requested with the correct key
    call_args = mock_session.execute.call_args
    assert call_args.args[1] == {"key": POLLING_ADVISORY_LOCK_KEY}


@pytest.mark.unit_tests
@patch("services.task.global_agent_polling_service.get_db_session")
def test_background_loop_standby_does_not_poll(mock_get_db):
    """Non-leader replica skips the polling loop when lock is held by another replica."""
    mock_session = MagicMock()
    mock_session.execute.return_value.scalar.return_value = False  # lock not acquired
    mock_get_db.return_value = iter([mock_session])

    service = GlobalAgentPollingService()

    def wait_then_shutdown(timeout=None):
        service.shutdown_event.set()

    with patch.object(
        service, "_discover_and_poll_agents"
    ) as mock_dap:
        with patch.object(service.shutdown_event, "wait", side_effect=wait_then_shutdown):
            service._background_loop()

    mock_dap.assert_not_called()
    mock_session.close.assert_called_once()


@pytest.mark.unit_tests
@patch("services.task.global_agent_polling_service.get_db_session")
def test_background_loop_leader_closes_session_on_shutdown(mock_get_db):
    """Leader session is closed (releasing the lock) when shutdown is signalled mid-loop."""
    mock_session = MagicMock()
    mock_session.execute.return_value.scalar.return_value = True  # lock acquired
    mock_get_db.return_value = iter([mock_session])

    service = GlobalAgentPollingService()

    # Inner wait() sets the shutdown event and returns True, causing the inner loop to
    # break after a single poll. is_set() then returns True so the outer loop also exits.
    def wait_then_shutdown(timeout=None):
        service.shutdown_event.set()
        return True

    with patch.object(service, "_discover_and_poll_agents") as mock_dap:
        with patch.object(service.shutdown_event, "wait", side_effect=wait_then_shutdown):
            service._background_loop()

    # The leader polls once immediately before the wait signals shutdown.
    mock_dap.assert_called_once()
    mock_session.close.assert_called_once()


@pytest.mark.unit_tests
@patch("services.task.global_agent_polling_service.get_db_session")
def test_background_loop_closes_session_on_db_error(mock_get_db):
    """Session is closed even if the advisory lock query itself raises."""
    mock_session = MagicMock()

    # execute() raises and also sets the shutdown event so the outer loop exits cleanly
    def execute_with_error(*args, **kwargs):
        service.shutdown_event.set()
        raise Exception("DB connection error")

    mock_session.execute.side_effect = execute_with_error
    mock_get_db.return_value = iter([mock_session])

    service = GlobalAgentPollingService()

    with patch.object(service, "_discover_and_poll_agents") as mock_dap:
        service._background_loop()

    mock_dap.assert_not_called()
    mock_session.close.assert_called_once()


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


# --- D-14 (UP-4986): migrating discovery onto a gcp_vertex Discovery Source ----------

VERTEX_RESOURCE_NAME = (
    "projects/123456789012/locations/us-central1/reasoningEngines/1111111111111111111"
)


def _run_legacy_discovery(monkeypatch, mapped_task_id):
    """Run `_discover_gcp_agents` over one listed engine, with every collaborator mocked.

    `mapped_task_id` is what the service-name mapping holds for the engine's resource
    name: a task ID when a gcp_vertex Discovery Source has already resolved it, None when
    nothing has. Returns (created count, the mocked task repository).
    """
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "example-project-123456")
    monkeypatch.delenv("GENAI_ENGINE_LEGACY_GCP_DISCOVERY_ENABLED", raising=False)
    agent = MagicMock()
    agent.api_resource.name = VERTEX_RESOURCE_NAME
    agent.api_resource.display_name = "personal-assistant"
    module = "services.task.global_agent_polling_service"
    with (
        patch(f"{module}.get_db_session") as mock_get_db,
        patch(f"{module}.vertexai") as mock_vertexai,
        patch(f"{module}.TaskRepository") as mock_task_repo_cls,
        patch(f"{module}.ServiceNameMappingRepository") as mock_mapping_repo_cls,
        patch(f"{module}.TaskPollingStateRepository"),
        patch(f"{module}.RuleRepository"),
        patch(f"{module}.MetricRepository"),
        patch(f"{module}.ConfigurationRepository"),
    ):
        mock_get_db.return_value = iter([MagicMock()])
        mock_vertexai.Client.return_value.agent_engines.list.return_value = [agent]
        task_repo = mock_task_repo_cls.return_value
        task_repo.find_by_gcp_engine_id.return_value = None
        task_repo.create_task.return_value = MagicMock(id="new-task", name="n")
        mock_mapping_repo_cls.return_value.create_mapping.side_effect = (
            lambda name, task_id, *args, **kwargs: MagicMock(task_id=task_id)
        )
        mock_mapping_repo_cls.return_value.get_task_id_by_service_name.side_effect = (
            lambda name, key_kind=None: (
                mapped_task_id if name == VERTEX_RESOURCE_NAME else None
            )
        )
        created = GlobalAgentPollingService()._discover_gcp_agents()
    return created, task_repo


@pytest.mark.unit_tests
def test_legacy_discovery_skips_an_engine_a_discovery_source_already_resolved(
    monkeypatch,
):
    """A task minted by a gcp_vertex source carries a CLOUD creation source, which
    `find_by_gcp_engine_id` cannot see. The resource-name mapping it wrote can, and
    without checking it every newly deployed agent would get a second task while both
    discovery paths run."""
    created, task_repo = _run_legacy_discovery(monkeypatch, mapped_task_id="task-x")
    assert created == 0
    task_repo.create_task.assert_not_called()


@pytest.mark.unit_tests
def test_legacy_discovery_still_creates_a_task_for_an_unmapped_engine(monkeypatch):
    created, task_repo = _run_legacy_discovery(monkeypatch, mapped_task_id=None)
    assert created == 1
    task_repo.create_task.assert_called_once()


@pytest.mark.unit_tests
@pytest.mark.parametrize("value", ["false", "False", "0", "no"])
@patch("services.task.global_agent_polling_service.get_db_session")
def test_legacy_discovery_can_be_switched_off(mock_get_db, value, monkeypatch):
    """Once a gcp_vertex source scans the project, the startup-variable discovery is
    switched off without touching the trace-fetch phase."""
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "example-project-123456")
    monkeypatch.setenv("GENAI_ENGINE_LEGACY_GCP_DISCOVERY_ENABLED", value)
    assert GlobalAgentPollingService()._discover_gcp_agents() == 0
    mock_get_db.assert_not_called()


@pytest.mark.unit_tests
def test_legacy_discovery_yields_a_resource_claimed_after_its_check(monkeypatch):
    """A gcp_vertex source can map the resource name between the legacy path's
    "already mapped?" check and its own claim. The legacy task is only flushed until
    its mapping commits, so losing the claim rolls it back: no unreferenced duplicate,
    no polling state for it, and the source's task keeps the mapping."""
    resource_name = (
        "projects/123456789012/locations/us-central1/reasoningEngines/"
        f"{uuid.uuid4().int % 10**19:019d}"
    )
    display_name = f"race-agent-{uuid.uuid4().hex[:8]}"
    db_session = override_get_db_session()
    task_repo = TaskRepository(
        db_session,
        RuleRepository(db_session),
        MetricRepository(db_session),
        get_application_config(session=db_session),
    )
    owner = task_repo.create_task(
        Task(
            id=str(uuid.uuid4()),
            name="Discovery Source task",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            is_agentic=True,
            is_autocreated=True,
            org_id=DEFAULT_ORG_ID,
        ),
        with_default_rules=False,
    )
    ServiceNameMappingRepository(db_session).create_mapping(resource_name, owner.id)
    polling_states_before = db_session.query(DatabaseTaskPollingState).count()

    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "example-project-123456")
    monkeypatch.delenv("GENAI_ENGINE_LEGACY_GCP_DISCOVERY_ENABLED", raising=False)
    agent = MagicMock()
    agent.api_resource.name = resource_name
    agent.api_resource.display_name = display_name
    module = "services.task.global_agent_polling_service"
    try:
        with (
            patch(
                f"{module}.get_db_session",
                side_effect=lambda: iter([override_get_db_session()]),
            ),
            patch(f"{module}.vertexai") as mock_vertexai,
            # The engine-id lookup is Postgres JSON SQL, and the source's task has
            # no GCP creation source for it to find anyway.
            patch.object(TaskRepository, "find_by_gcp_engine_id", return_value=None),
            # The race: the check ran before the source's mapping was written.
            patch.object(
                GlobalAgentPollingService,
                "_resource_already_mapped",
                return_value=False,
            ),
        ):
            mock_vertexai.Client.return_value.agent_engines.list.return_value = [agent]
            created = GlobalAgentPollingService()._discover_gcp_agents()

        db_session.expire_all()
        assert created == 0
        assert (
            db_session.query(DatabaseTask)
            .filter(DatabaseTask.name == f"Vertex AI Agent: {display_name}")
            .count()
            == 0
        )
        assert db_session.query(DatabaseTaskPollingState).count() == (
            polling_states_before
        )
        assert (
            ServiceNameMappingRepository(db_session).get_task_id_by_service_name(
                resource_name,
            )
            == owner.id
        )
    finally:
        db_session.query(DatabaseServiceNameTaskMapping).filter(
            DatabaseServiceNameTaskMapping.task_id == owner.id,
        ).delete(synchronize_session=False)
        db_session.query(DatabaseTask).filter(DatabaseTask.id == owner.id).delete(
            synchronize_session=False,
        )
        db_session.commit()
        db_session.close()
