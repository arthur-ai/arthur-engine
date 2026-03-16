"""Unit tests for the trace retention service."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from schemas.internal_schemas import ApplicationConfiguration
from services.trace_retention_service import (
    TraceRetentionJob,
    TraceRetentionService,
    get_trace_retention_service,
    initialize_trace_retention_service,
    shutdown_trace_retention_service,
)
from utils.constants import DEFAULT_TRACE_RETENTION_DAYS


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
    service = TraceRetentionService()
    job = TraceRetentionJob()
    assert service._get_job_key(job) == "trace_retention"


@pytest.mark.unit_tests
@patch("services.trace_retention_service.delete_trace_batch")
@patch("services.trace_retention_service.get_expired_trace_ids")
@patch("services.trace_retention_service.get_db_session")
@patch("services.trace_retention_service.ConfigurationRepository")
def test_execute_job_uses_config_retention_days_and_calls_repository(
    mock_config_repo_cls: MagicMock,
    mock_get_db_session: MagicMock,
    mock_get_expired_trace_ids: MagicMock,
    mock_delete_trace_batch: MagicMock,
) -> None:
    """_execute_job uses trace_retention_days from config and calls repo with correct cutoff."""
    mock_db = MagicMock()
    mock_get_db_session.return_value = iter([mock_db])

    config = ApplicationConfiguration(
        chat_task_id=None,
        default_currency="USD",
        document_storage_configuration=None,
        max_llm_rules_per_task_count=10,
        trace_retention_days=30,
    )
    mock_config_repo = MagicMock()
    mock_config_repo.get_configurations.return_value = config
    mock_config_repo_cls.return_value = mock_config_repo

    mock_get_expired_trace_ids.side_effect = [
        ["trace-1"],
        [],
    ]  # first batch, then empty

    service = TraceRetentionService()
    service._execute_job(TraceRetentionJob())

    mock_config_repo.get_configurations.assert_called_once()
    mock_get_expired_trace_ids.assert_called()
    call_kwargs = mock_get_expired_trace_ids.call_args[1]
    cutoff = call_kwargs["cutoff"]
    now = datetime.now(timezone.utc)
    expected_cutoff = now - timedelta(days=30)
    assert abs((cutoff - expected_cutoff).total_seconds()) < 2
    mock_delete_trace_batch.assert_called_once_with(mock_db, ["trace-1"])
    mock_db.close.assert_called_once()


@pytest.mark.unit_tests
@patch("services.trace_retention_service.delete_trace_batch")
@patch("services.trace_retention_service.get_expired_trace_ids")
@patch("services.trace_retention_service.get_db_session")
@patch("services.trace_retention_service.ConfigurationRepository")
def test_execute_job_uses_default_retention_when_not_in_config(
    mock_config_repo_cls: MagicMock,
    mock_get_db_session: MagicMock,
    mock_get_expired_trace_ids: MagicMock,
    mock_delete_trace_batch: MagicMock,
) -> None:
    """_execute_job uses DEFAULT_TRACE_RETENTION_DAYS when config has no trace_retention_days."""
    mock_db = MagicMock()
    mock_get_db_session.return_value = iter([mock_db])

    class ConfigWithoutRetention:
        pass

    config = ConfigWithoutRetention()
    mock_config_repo = MagicMock()
    mock_config_repo.get_configurations.return_value = config
    mock_config_repo_cls.return_value = mock_config_repo

    mock_get_expired_trace_ids.return_value = []

    service = TraceRetentionService()
    service._execute_job(TraceRetentionJob())

    call_kwargs = mock_get_expired_trace_ids.call_args[1]
    cutoff = call_kwargs["cutoff"]
    now = datetime.now(timezone.utc)
    expected_cutoff = now - timedelta(days=DEFAULT_TRACE_RETENTION_DAYS)
    assert abs((cutoff - expected_cutoff).total_seconds()) < 2
    mock_delete_trace_batch.assert_not_called()


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
