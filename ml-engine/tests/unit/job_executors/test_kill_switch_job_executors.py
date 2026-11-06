"""KillAgentJobExecutor and ReenableAgentJobExecutor, against fakes only.

The order is the point of these executors -- the task's block goes up first and comes
down last -- so the fakes write every call to one shared timeline the tests read back.
"""

import io
import logging
from typing import Any, Iterator, Mapping, Optional
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from arthur_client_support import KILL_SWITCH_SUPPORTED

if not KILL_SWITCH_SUPPORTED:
    pytest.skip(
        "the installed arthur-client/arthur-common predate the kill switch",
        allow_module_level=True,
    )

from arthur_client.api_bindings.models import (  # noqa: E402
    TaskResponse as ScopeClientTaskResponse,
)
from arthur_common.models.agent_governance_schemas import SourceAddress  # noqa: E402
from arthur_common.models.response_schemas import TaskResponse  # noqa: E402
from arthur_common.models.task_job_specs import (  # noqa: E402
    KillAgentJobSpec,
    KillSwitchCloudTarget,
    ReenableAgentJobSpec,
)

from discovery.cloud.azure_ai_foundry.control import AgentStateChange  # noqa: E402
from job_executors import kill_switch_job_executors  # noqa: E402
from job_executors.kill_switch_job_executors import (  # noqa: E402
    CloudVendorControl,
    KillAgentJobExecutor,
    KillSwitchError,
    ReenableAgentJobExecutor,
    foundry_source_fields,
)
from log_redaction import SecretRedactingFilter  # noqa: E402
from tools.api_client_type_converters import ScopeClientTypeConverter  # noqa: E402

TASK_ID = "task-1"
MODEL_ID = "model-1"
SECRET = "s3cr3t-client-value"
ENDPOINT = "https://res.services.ai.azure.com/api/projects/proj"


class FakeShieldConnector:
    """A task whose disabled state the calls change, idempotently."""

    def __init__(self, timeline: list[str]) -> None:
        self.timeline = timeline
        self.disabled = False
        self.reason: Optional[str] = None

    def _task(self) -> TaskResponse:
        return TaskResponse(
            id=TASK_ID,
            name="agent",
            created_at=0,
            updated_at=0,
            is_disabled=self.disabled,
            disabled_reason=self.reason,
            disabled_at=1 if self.disabled else None,
            rules=[],
        )

    def disable_task(self, task_id: str, reason: str) -> TaskResponse:
        assert task_id == TASK_ID
        self.timeline.append("task:disable")
        self.disabled, self.reason = True, reason
        return self._task()

    def enable_task(self, task_id: str) -> TaskResponse:
        assert task_id == TASK_ID
        self.timeline.append("task:enable")
        self.disabled, self.reason = False, None
        return self._task()

    def read_task(self, task_id: str) -> TaskResponse:
        self.timeline.append("task:read")
        return self._task()


class FakeVendor:
    """A cloud vendor holding each resource's state; failing for the names in `failing`."""

    def __init__(self, timeline: list[str], failing: frozenset[str] = frozenset()):
        self.timeline = timeline
        self.failing = failing
        self.states: dict[str, str] = {}
        self.credentials_seen: list[Mapping[str, Optional[str]]] = []

    def _set(
        self,
        target: KillSwitchCloudTarget,
        credentials: Mapping[str, Optional[str]],
        logger: logging.Logger,
        state: str,
    ) -> AgentStateChange:
        name = target.address.resource_id
        self.timeline.append(f"cloud:{state}:{name}")
        self.credentials_seen.append(credentials)
        if name in self.failing:
            raise RuntimeError(f"vendor refused {name} with key {SECRET}")
        previous = self.states.get(name, "enabled")
        self.states[name] = state
        return AgentStateChange(name, previous, state, changed=previous != state)

    def control(self) -> CloudVendorControl:
        return CloudVendorControl(
            disable=lambda t, c, log: self._set(t, c, log, "disabled"),
            enable=lambda t, c, log: self._set(t, c, log, "enabled"),
        )


def _target(
    name: str,
    vendor: str = "azure_ai_foundry",
    config_id: Optional[UUID] = None,
    source_fields: Optional[dict[str, str]] = None,
) -> KillSwitchCloudTarget:
    return KillSwitchCloudTarget(
        vendor=vendor,
        discovery_source_config_id=config_id or uuid4(),
        external_id=f"{ENDPOINT}/agents/{name}",
        address=SourceAddress(instance="res/proj", scope="eastus", resource_id=name),
        source_fields=(
            {"project_endpoint": ENDPOINT} if source_fields is None else source_fields
        ),
    )


class Harness:
    def __init__(self, failing: frozenset[str] = frozenset()) -> None:
        self.timeline: list[str] = []
        self.connector = FakeShieldConnector(self.timeline)
        self.vendor = FakeVendor(self.timeline, failing)
        self.discovery_sources_client = MagicMock()
        self.discovery_sources_client.retrieve_discovery_source_credentials.return_value = {
            "client_secret": SECRET,
        }
        self.uploaded: list[TaskResponse] = []
        self.logger = logging.getLogger(f"kill-switch-test-{uuid4()}")
        self.logger.setLevel(logging.INFO)

    def _wire(self, executor: Any) -> Any:
        executor.retrieve_task_management_resources_from_model_id = MagicMock(
            return_value=(MagicMock(id=MODEL_ID), [], self.connector, TASK_ID),
        )

        def upload(model_id: str, task: TaskResponse, connector: Any) -> None:
            assert model_id == MODEL_ID
            self.timeline.append("upload")
            self.uploaded.append(task)

        executor.upload_final_task_state = upload
        return executor

    def _args(self) -> tuple[Any, ...]:
        return (
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            self.logger,
            self.discovery_sources_client,
            {"azure_ai_foundry": self.vendor.control()},
        )

    def kill(self, targets: list[KillSwitchCloudTarget]) -> None:
        self._wire(KillAgentJobExecutor(*self._args())).execute(
            KillAgentJobSpec(
                scope_model_id=uuid4(),
                kill_switch_event_id=uuid4(),
                reason="prompt injection policy fired",
                cloud_targets=targets,
            ),
        )

    def reenable(self, targets: list[KillSwitchCloudTarget]) -> None:
        self._wire(ReenableAgentJobExecutor(*self._args())).execute(
            ReenableAgentJobSpec(
                scope_model_id=uuid4(),
                kill_switch_event_id=uuid4(),
                cloud_targets=targets,
            ),
        )


def test_kill_disables_the_task_before_any_cloud_target() -> None:
    h = Harness()

    h.kill([_target("a"), _target("b")])

    assert h.timeline == [
        "task:disable",
        "cloud:disabled:a",
        "cloud:disabled:b",
        "upload",
    ]
    assert h.uploaded[-1].is_disabled is True
    assert h.uploaded[-1].disabled_reason == "prompt injection policy fired"
    assert h.vendor.states == {"a": "disabled", "b": "disabled"}


def test_kill_with_no_cloud_targets_still_disables_the_task() -> None:
    h = Harness()

    h.kill([])

    assert h.timeline == ["task:disable", "upload"]
    h.discovery_sources_client.retrieve_discovery_source_credentials.assert_not_called()


def test_kill_is_idempotent() -> None:
    h = Harness()
    targets = [_target("a")]

    h.kill(targets)
    h.kill(targets)

    assert h.connector.disabled is True
    assert h.vendor.states == {"a": "disabled"}
    assert h.uploaded[-1].is_disabled is True


def test_a_failed_target_does_not_stop_the_others_and_fails_the_job() -> None:
    h = Harness(failing=frozenset({"a"}))

    with pytest.raises(KillSwitchError) as raised:
        h.kill([_target("a"), _target("b")])

    assert h.timeline == [
        "task:disable",
        "cloud:disabled:a",
        "cloud:disabled:b",
        "upload",
    ]
    assert h.vendor.states == {"b": "disabled"}
    assert h.connector.disabled is True
    assert "1 step(s) failed" in str(raised.value)
    assert f"{ENDPOINT}/agents/a" in str(raised.value)


def test_an_unknown_vendor_is_a_failure_but_others_still_run() -> None:
    h = Harness()

    with pytest.raises(KillSwitchError) as raised:
        h.kill([_target("x", vendor="aws_bedrock"), _target("b")])

    assert "does not support vendor 'aws_bedrock'" in str(raised.value)
    assert h.vendor.states == {"b": "disabled"}
    assert h.connector.disabled is True
    assert h.timeline[-1] == "upload"


def test_an_upload_failure_fails_the_job_without_hiding_target_failures() -> None:
    h = Harness(failing=frozenset({"a"}))
    executor = h._wire(KillAgentJobExecutor(*h._args()))
    executor.upload_final_task_state = MagicMock(side_effect=RuntimeError("scope down"))

    with pytest.raises(KillSwitchError) as raised:
        executor.execute(
            KillAgentJobSpec(
                scope_model_id=uuid4(),
                kill_switch_event_id=uuid4(),
                reason="r",
                cloud_targets=[_target("a")],
            ),
        )

    assert "2 step(s) failed" in str(raised.value)
    assert "scope down" in str(raised.value)


def test_credentials_are_read_once_per_source_and_scrubbed_from_logs() -> None:
    h = Harness(failing=frozenset({"a"}))
    config_id = uuid4()
    stream = io.StringIO()
    # As ExportContextedLogger installs it on a job's logger.
    h.logger.addFilter(SecretRedactingFilter())
    h.logger.addHandler(logging.StreamHandler(stream))

    with pytest.raises(KillSwitchError):
        h.kill([_target("a", config_id=config_id), _target("b", config_id=config_id)])

    h.discovery_sources_client.retrieve_discovery_source_credentials.assert_called_once_with(
        str(config_id),
    )
    assert h.vendor.credentials_seen == [{"client_secret": SECRET}] * 2
    output = stream.getvalue()
    assert "Failed to disable" in output
    assert SECRET not in output


def test_a_credentials_failure_counts_against_that_target_only() -> None:
    h = Harness()
    bad, good = uuid4(), uuid4()

    def credentials(config_id: str) -> dict[str, str]:
        if config_id == str(bad):
            raise RuntimeError("no such config")
        return {"client_secret": SECRET}

    h.discovery_sources_client.retrieve_discovery_source_credentials.side_effect = (
        credentials
    )

    with pytest.raises(KillSwitchError, match="no such config"):
        h.kill([_target("a", config_id=bad), _target("b", config_id=good)])

    assert h.vendor.states == {"b": "disabled"}


def test_reenable_turns_cloud_targets_on_before_the_task() -> None:
    h = Harness()
    h.kill([_target("a")])
    h.timeline.clear()

    h.reenable([_target("a")])

    assert h.timeline == ["cloud:enabled:a", "task:enable", "upload"]
    assert h.connector.disabled is False
    assert h.uploaded[-1].is_disabled is False
    assert h.vendor.states == {"a": "enabled"}


def test_reenable_is_idempotent() -> None:
    h = Harness()

    h.reenable([_target("a")])
    h.reenable([_target("a")])

    assert h.connector.disabled is False
    assert h.vendor.states == {"a": "enabled"}


def test_a_failed_reenable_tries_every_target_and_leaves_the_task_disabled() -> None:
    h = Harness(failing=frozenset({"a"}))
    h.connector.disabled = True
    h.timeline.clear()

    with pytest.raises(KillSwitchError, match="still disabled"):
        h.reenable([_target("a"), _target("b")])

    assert h.timeline == [
        "cloud:enabled:a",
        "cloud:enabled:b",
        "task:read",
        "upload",
    ]
    assert h.connector.disabled is True
    assert h.uploaded[-1].is_disabled is True


def test_foundry_source_fields_are_used_as_given() -> None:
    fields = foundry_source_fields(
        _target("a", source_fields={"project_endpoint": "https://other/api/projects/p"}),
    )

    assert fields == {"project_endpoint": "https://other/api/projects/p"}


def test_foundry_endpoint_falls_back_to_the_external_id() -> None:
    fields = foundry_source_fields(_target("a", source_fields={"tenant_id": "t"}))

    assert fields == {"tenant_id": "t", "project_endpoint": ENDPOINT}


def test_foundry_endpoint_is_left_missing_when_the_external_id_has_none() -> None:
    target = _target("a", source_fields={}).model_copy(
        update={"external_id": "not-a-foundry-id"},
    )

    assert foundry_source_fields(target) == {}


@pytest.fixture
def foundry_calls(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[tuple[Any, ...]]]:
    calls: list[tuple[Any, ...]] = []

    def record(state: str) -> Any:
        def call(
            source_fields: Mapping[str, str],
            credentials: Mapping[str, Optional[str]],
            agent_name: str,
            logger: logging.Logger,
        ) -> AgentStateChange:
            calls.append((state, dict(source_fields), dict(credentials), agent_name))
            return AgentStateChange(agent_name, None, state, changed=True)

        return call

    control = kill_switch_job_executors.foundry_control
    monkeypatch.setattr(control, "disable_agent", record("disabled"))
    monkeypatch.setattr(control, "enable_agent", record("enabled"))
    yield calls


def test_the_registry_routes_foundry_targets_to_its_control(
    foundry_calls: list[tuple[Any, ...]],
) -> None:
    control = kill_switch_job_executors.CLOUD_VENDOR_CONTROLS["azure_ai_foundry"]
    target = _target("agent-7", source_fields={})
    logger = logging.getLogger("foundry-routing")

    control.disable(target, {"client_secret": SECRET}, logger)
    control.enable(target, {"client_secret": SECRET}, logger)

    assert foundry_calls == [
        ("disabled", {"project_endpoint": ENDPOINT}, {"client_secret": SECRET}, "agent-7"),
        ("enabled", {"project_endpoint": ENDPOINT}, {"client_secret": SECRET}, "agent-7"),
    ]


def test_the_uploaded_task_state_carries_the_disabled_fields() -> None:
    if "is_disabled" not in ScopeClientTaskResponse.model_fields:
        pytest.skip("the installed arthur-client's TaskResponse predates the kill switch")
    connector = FakeShieldConnector([])
    connector.disable_task(TASK_ID, "policy fired")

    scope_task = ScopeClientTypeConverter.task_response_api_to_scope_client(
        connector.read_task(TASK_ID),
    )

    assert scope_task.is_disabled is True
    assert scope_task.disabled_reason == "policy fired"
    assert scope_task.disabled_at == 1
