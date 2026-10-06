"""JobExecutor with an arthur-client that predates TEST_DISCOVERY_SOURCE.

The test-connection executor needs models only a newer client has. With an older one,
every other job kind must dispatch exactly as before, and a test-connection job must
fail with a message that says what to upgrade -- not take the module down at import.
"""

import contextlib
import logging
from typing import Any, Iterator
from unittest.mock import MagicMock

import pytest
from arthur_client.api_bindings import JobKind, JobState

import job_executor
from arthur_client_support import (
    TEST_DISCOVERY_SOURCE_JOB_KIND,
    TEST_DISCOVERY_SOURCE_UNSUPPORTED_MESSAGE,
)


@pytest.fixture
def unsupported_executor(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[job_executor.JobExecutor, MagicMock, MagicMock]]:
    monkeypatch.setattr(job_executor, "TEST_DISCOVERY_SOURCE_SUPPORTED", False)
    monkeypatch.setattr(
        job_executor,
        "ExportContextedLogger",
        lambda *args, **kwargs: contextlib.nullcontext(),
    )
    monkeypatch.setattr(job_executor, "ScopeJobLogExporter", MagicMock())
    monkeypatch.setattr(job_executor, "ConnectorConstructor", MagicMock())
    list_datasets = MagicMock()
    monkeypatch.setattr(job_executor, "ListDatasetsExecutor", list_datasets)

    executor = job_executor.JobExecutor.__new__(job_executor.JobExecutor)
    executor.jobs_client = MagicMock()
    executor.connectors_client = MagicMock()
    executor.datasets_client = MagicMock()
    executor.discovery_sources_client = MagicMock()
    executor.logger = logging.getLogger("test-job-executor-client-gating")
    errors = MagicMock()
    monkeypatch.setattr(executor.logger, "error", errors)
    yield executor, list_datasets, errors


def _run_job_of_kind(executor: job_executor.JobExecutor, kind: Any) -> JobState:
    job = MagicMock()
    job.id = "job"
    job.kind = kind
    executor.jobs_client.get_job_with_http_info.return_value.data = job  # type: ignore[attr-defined]
    job_run = MagicMock()
    job_run.id = "run"
    job_run.job_id = "job"
    return executor.execute(job_run)


def test_other_job_kinds_dispatch_without_test_connection_support(
    unsupported_executor: tuple[job_executor.JobExecutor, MagicMock, MagicMock],
) -> None:
    executor, list_datasets, errors = unsupported_executor

    assert _run_job_of_kind(executor, JobKind.LIST_DATASETS) == JobState.COMPLETED
    list_datasets.return_value.execute.assert_called_once()
    errors.assert_not_called()


def test_a_test_connection_job_names_the_client_to_upgrade(
    unsupported_executor: tuple[job_executor.JobExecutor, MagicMock, MagicMock],
) -> None:
    executor, list_datasets, errors = unsupported_executor

    state = _run_job_of_kind(executor, TEST_DISCOVERY_SOURCE_JOB_KIND)

    assert state == JobState.FAILED
    list_datasets.assert_not_called()
    raised = errors.call_args.kwargs["exc_info"]
    assert isinstance(raised, NotImplementedError)
    assert str(raised) == TEST_DISCOVERY_SOURCE_UNSUPPORTED_MESSAGE
    assert "upgrade arthur-client" in str(raised)
