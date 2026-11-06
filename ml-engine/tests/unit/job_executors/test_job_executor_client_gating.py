"""JobExecutor with an arthur-client that predates TEST_DISCOVERY_SOURCE or the kill switch.

The test-connection executor needs models only a newer client has. With an older one,
every other job kind must dispatch exactly as before, and a test-connection job must
fail with a message that says what to upgrade -- not take the module down at import.
"""

import contextlib
import enum
import json
import logging
import types
from typing import Any, Iterator
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from arthur_client.api_bindings import JobKind, JobState

import arthur_client_support
import job_executor
from arthur_client_support import (
    KILL_AGENT_JOB_KIND,
    KILL_SWITCH_SUPPORTED,
    KILL_SWITCH_UNSUPPORTED_MESSAGE,
    REENABLE_AGENT_JOB_KIND,
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


@pytest.mark.parametrize("kind", [KILL_AGENT_JOB_KIND, REENABLE_AGENT_JOB_KIND])
def test_a_kill_switch_job_names_what_to_upgrade(
    unsupported_executor: tuple[job_executor.JobExecutor, MagicMock, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
) -> None:
    monkeypatch.setattr(job_executor, "KILL_SWITCH_SUPPORTED", False)
    executor, list_datasets, errors = unsupported_executor

    state = _run_job_of_kind(executor, kind)

    assert state == JobState.FAILED
    raised = errors.call_args.kwargs["exc_info"]
    assert isinstance(raised, NotImplementedError)
    assert str(raised) == KILL_SWITCH_UNSUPPORTED_MESSAGE


def test_other_job_kinds_dispatch_without_kill_switch_support(
    unsupported_executor: tuple[job_executor.JobExecutor, MagicMock, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(job_executor, "KILL_SWITCH_SUPPORTED", False)
    executor, list_datasets, errors = unsupported_executor

    assert _run_job_of_kind(executor, JobKind.LIST_DATASETS) == JobState.COMPLETED
    errors.assert_not_called()


@pytest.mark.parametrize(
    ("kind", "executor_name", "spec_type"),
    [
        (KILL_AGENT_JOB_KIND, "KillAgentJobExecutor", "KillAgentJobSpec"),
        (REENABLE_AGENT_JOB_KIND, "ReenableAgentJobExecutor", "ReenableAgentJobSpec"),
    ],
)
def test_a_kill_switch_job_dispatches_its_raw_spec_when_supported(
    unsupported_executor: tuple[job_executor.JobExecutor, MagicMock, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
    kind: str,
    executor_name: str,
    spec_type: str,
) -> None:
    if not KILL_SWITCH_SUPPORTED:
        pytest.skip("the installed arthur-client/arthur-common predate the kill switch")
    executor, _, errors = unsupported_executor
    executor.models_client = MagicMock()
    executor.tasks_client = MagicMock()
    kill_executor = MagicMock()
    monkeypatch.setattr(job_executor, executor_name, kill_executor)
    model_id, event_id = uuid4(), uuid4()
    job_spec: dict[str, Any] = {
        "job_type": kind,
        "scope_model_id": str(model_id),
        "kill_switch_event_id": str(event_id),
        "cloud_targets": [],
    }
    if kind == KILL_AGENT_JOB_KIND:
        job_spec["reason"] = "policy fired"
    executor.jobs_client.get_job_with_http_info.return_value.raw_data = json.dumps(  # type: ignore[attr-defined]
        {"job_spec": job_spec},
    ).encode()

    assert _run_job_of_kind(executor, kind) == JobState.COMPLETED

    errors.assert_not_called()
    assert kill_executor.call_args.args[-1] is executor.discovery_sources_client
    spec = kill_executor.return_value.execute.call_args.kwargs["job_spec"]
    assert type(spec).__name__ == spec_type
    assert spec.scope_model_id == model_id
    assert spec.kill_switch_event_id == event_id


def test_kill_switch_support_needs_both_job_kinds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class OldJobKind(enum.Enum):
        LIST_DATASETS = "list_datasets"
        KILL_AGENT = "kill_agent"

    monkeypatch.setattr(arthur_client_support, "JobKind", OldJobKind)

    assert arthur_client_support.client_supports_kill_switch() is False


def test_kill_switch_support_needs_the_arthur_common_specs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class AllKinds(enum.Enum):
        KILL_AGENT = "kill_agent"
        REENABLE_AGENT = "reenable_agent"

    monkeypatch.setattr(arthur_client_support, "JobKind", AllKinds)
    monkeypatch.setattr(
        arthur_client_support,
        "task_job_specs",
        types.SimpleNamespace(KillAgentJobSpec=object),
    )

    assert arthur_client_support.client_supports_kill_switch() is False
