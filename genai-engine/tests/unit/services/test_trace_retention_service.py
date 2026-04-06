"""Unit tests for the trace retention service."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from schemas.internal_schemas import ApplicationConfiguration
from services.trace_retention_service import (
    CIRCUIT_BREAKER_THRESHOLD,
    MAX_TRACES_PER_RUN,
    TraceRetentionJob,
    TraceRetentionService,
    get_trace_retention_service,
    initialize_trace_retention_service,
    shutdown_trace_retention_service,
)


def _make_service() -> TraceRetentionService:
    """Create a service instance with a fresh shutdown_event (not shared across tests)."""
    return TraceRetentionService(num_workers=1)


def _mock_db_session_ctx(mock: MagicMock) -> MagicMock:
    """Configure a db_session_context mock and return the mock session."""
    mock_db = MagicMock()
    mock.return_value.__enter__ = MagicMock(return_value=mock_db)
    mock.return_value.__exit__ = MagicMock(return_value=False)
    return mock_db


def _mock_config_repo(mock_cls: MagicMock, retention_days: int = 30) -> MagicMock:
    """Configure a ConfigurationRepository mock that returns the given retention_days."""
    config = ApplicationConfiguration(
        chat_task_id=None,
        default_currency="USD",
        document_storage_configuration=None,
        max_llm_rules_per_task_count=10,
        trace_retention_days=retention_days,
    )
    mock_repo = MagicMock()
    mock_repo.get_configurations.return_value = config
    mock_cls.return_value = mock_repo
    return mock_repo


@pytest.mark.unit_tests
def test_trace_retention_job_creation() -> None:
    job = TraceRetentionJob()
    assert job.delay_seconds == 0


@pytest.mark.unit_tests
def test_trace_retention_job_with_delay() -> None:
    job = TraceRetentionJob(delay_seconds=30)
    assert job.delay_seconds == 30


@pytest.mark.unit_tests
def test_get_job_key() -> None:
    service = _make_service()
    job = TraceRetentionJob()
    assert service._get_job_key(job) == "trace_retention"


@pytest.mark.unit_tests
@patch("services.trace_retention_service.delete_trace_batch")
@patch("services.trace_retention_service.get_expired_trace_ids")
@patch("services.trace_retention_service.db_session_context")
@patch("services.trace_retention_service.ConfigurationRepository")
def test_execute_job_uses_config_retention_days_and_calls_repository(
    mock_config_repo_cls: MagicMock,
    mock_db_session_ctx: MagicMock,
    mock_get_expired_trace_ids: MagicMock,
    mock_delete_trace_batch: MagicMock,
) -> None:
    """_execute_job uses trace_retention_days from config and calls repo with correct cutoff."""
    mock_db = _mock_db_session_ctx(mock_db_session_ctx)
    _mock_config_repo(mock_config_repo_cls, retention_days=30)

    mock_get_expired_trace_ids.side_effect = [["trace-1"], []]

    service = _make_service()
    service.shutdown_event = MagicMock()
    service.shutdown_event.wait = MagicMock(return_value=False)
    service.shutdown_event.is_set = MagicMock(return_value=False)

    service._execute_job(TraceRetentionJob())

    mock_get_expired_trace_ids.assert_called()
    cutoff = mock_get_expired_trace_ids.call_args[0][1]
    now = datetime.now(timezone.utc)
    expected_cutoff = now - timedelta(days=30)
    assert abs((cutoff - expected_cutoff).total_seconds()) < 2
    mock_delete_trace_batch.assert_called_once_with(mock_db, ["trace-1"])
    mock_db.commit.assert_called_once()
    assert service._consecutive_failures == 0


@pytest.mark.unit_tests
@patch("services.trace_retention_service.db_session_context")
def test_circuit_breaker_trips_after_threshold_consecutive_failures(
    mock_db_session_ctx: MagicMock,
) -> None:
    """Latch trips after CIRCUIT_BREAKER_THRESHOLD consecutive failures, not before."""
    mock_db_session_ctx.return_value.__enter__ = MagicMock(
        side_effect=RuntimeError("db down")
    )
    mock_db_session_ctx.return_value.__exit__ = MagicMock(return_value=False)

    service = _make_service()

    for i in range(CIRCUIT_BREAKER_THRESHOLD - 1):
        service._execute_job(TraceRetentionJob())
        assert not service._tripped.is_set(), f"Tripped too early at failure {i + 1}"
        assert service._consecutive_failures == i + 1

    service._execute_job(TraceRetentionJob())
    assert service._tripped.is_set()
    assert service._consecutive_failures == CIRCUIT_BREAKER_THRESHOLD


@pytest.mark.unit_tests
@patch("services.trace_retention_service.delete_trace_batch")
@patch("services.trace_retention_service.get_expired_trace_ids")
@patch("services.trace_retention_service.db_session_context")
@patch("services.trace_retention_service.ConfigurationRepository")
def test_success_resets_consecutive_failures(
    mock_config_repo_cls: MagicMock,
    mock_db_session_ctx: MagicMock,
    mock_get_expired_trace_ids: MagicMock,
    mock_delete_trace_batch: MagicMock,
) -> None:
    """A successful run resets _consecutive_failures so the breaker doesn't trip."""
    service = _make_service()
    service.shutdown_event = MagicMock()
    service.shutdown_event.wait = MagicMock(return_value=False)
    service.shutdown_event.is_set = MagicMock(return_value=False)
    service.shutdown_event.set = MagicMock()

    # Fail twice (just under threshold)
    mock_db_session_ctx.return_value.__enter__ = MagicMock(
        side_effect=RuntimeError("db down")
    )
    mock_db_session_ctx.return_value.__exit__ = MagicMock(return_value=False)
    for _ in range(CIRCUIT_BREAKER_THRESHOLD - 1):
        service._execute_job(TraceRetentionJob())
    assert service._consecutive_failures == CIRCUIT_BREAKER_THRESHOLD - 1
    assert not service._tripped.is_set()

    # Succeed once
    _mock_db_session_ctx(mock_db_session_ctx)
    _mock_config_repo(mock_config_repo_cls)
    mock_get_expired_trace_ids.return_value = []
    service._execute_job(TraceRetentionJob())
    assert service._consecutive_failures == 0

    # Fail once more — should NOT trip (counter was reset)
    mock_db_session_ctx.return_value.__enter__ = MagicMock(
        side_effect=RuntimeError("db down")
    )
    mock_db_session_ctx.return_value.__exit__ = MagicMock(return_value=False)
    service._execute_job(TraceRetentionJob())
    assert service._consecutive_failures == 1
    assert not service._tripped.is_set()


@pytest.mark.unit_tests
@patch("services.trace_retention_service.delete_trace_batch")
@patch("services.trace_retention_service.get_expired_trace_ids")
@patch("services.trace_retention_service.db_session_context")
@patch("services.trace_retention_service.ConfigurationRepository")
def test_runaway_cap_trips_latch(
    mock_config_repo_cls: MagicMock,
    mock_db_session_ctx: MagicMock,
    mock_get_expired_trace_ids: MagicMock,
    mock_delete_trace_batch: MagicMock,
) -> None:
    """Latch trips when total_deleted reaches MAX_TRACES_PER_RUN."""
    _mock_db_session_ctx(mock_db_session_ctx)
    _mock_config_repo(mock_config_repo_cls)

    batch = [f"trace-{i}" for i in range(500)]
    mock_get_expired_trace_ids.return_value = batch

    service = _make_service()
    service.shutdown_event = MagicMock()
    service.shutdown_event.wait = MagicMock(return_value=False)
    service.shutdown_event.is_set = MagicMock(return_value=False)
    service.shutdown_event.set = MagicMock()

    service._execute_job(TraceRetentionJob())

    expected_batches = MAX_TRACES_PER_RUN // 500
    assert mock_delete_trace_batch.call_count == expected_batches
    assert service._tripped.is_set()
    service.shutdown_event.set.assert_called()


@pytest.mark.unit_tests
@patch("services.trace_retention_service.delete_trace_batch")
@patch("services.trace_retention_service.get_expired_trace_ids")
@patch("services.trace_retention_service.db_session_context")
@patch("services.trace_retention_service.ConfigurationRepository")
def test_inter_batch_delay_respects_shutdown(
    mock_config_repo_cls: MagicMock,
    mock_db_session_ctx: MagicMock,
    mock_get_expired_trace_ids: MagicMock,
    mock_delete_trace_batch: MagicMock,
) -> None:
    """Batch loop exits early when shutdown_event is signaled during inter-batch delay."""
    _mock_db_session_ctx(mock_db_session_ctx)
    _mock_config_repo(mock_config_repo_cls)

    mock_get_expired_trace_ids.return_value = ["trace-1"]

    service = _make_service()
    service.shutdown_event = MagicMock()
    service.shutdown_event.wait = MagicMock(return_value=True)
    service.shutdown_event.is_set = MagicMock(return_value=False)

    service._execute_job(TraceRetentionJob())

    mock_delete_trace_batch.assert_called_once()
    assert not service._tripped.is_set()


@pytest.mark.unit_tests
@patch("services.trace_retention_service.TRACE_RETENTION_SERVICE", None)
def test_get_trace_retention_service_returns_none_before_init() -> None:
    assert get_trace_retention_service() is None


@pytest.mark.unit_tests
def test_initialize_and_shutdown_trace_retention_service() -> None:
    """Initialize starts service; shutdown stops it and sets global to None."""
    shutdown_trace_retention_service()
    assert get_trace_retention_service() is None
    initialize_trace_retention_service()
    svc = get_trace_retention_service()
    assert svc is not None
    shutdown_trace_retention_service()
    assert get_trace_retention_service() is None
