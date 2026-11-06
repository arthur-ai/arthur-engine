"""The kill switch: turning a registered agent off, and back on again.

An agent is turned off in two places. Its task is disabled first, because that is the
fast block: from the moment the GenAI Engine accepts the call, every guarded prompt and
response for the task is refused, whatever the cloud does next. Then each cloud resource
discovery found behind the agent is turned off at its vendor, so traffic that never
passes the guardrails stops too. Re-enabling runs the other way round: cloud resources
first, the task last, so the block is the last thing lifted.

FAILURE. Every cloud target is attempted even after one fails, so one unreachable
resource does not leave the others running. If any failed, the job raises once they are
all tried, and Scope settles the event as kill_failed (or reenable_failed) with that
error. A kill that fails on a cloud target leaves the task disabled; a re-enable that
fails on one leaves the task disabled as well, so a failed event never means the block
was lifted. Both are idempotent end to end -- the task calls and the vendor calls each
treat "already in that state" as success -- so a failed job can simply be run again.

The task's final state is uploaded either way, so Scope's task cache shows what the
task now is.
"""

import logging
from dataclasses import dataclass
from typing import Callable, Mapping, Optional
from uuid import UUID

from arthur_client.api_bindings import (
    DatasetsV1Api,
    DiscoverySourcesV1Api,
    ModelsV1Api,
    TasksV1Api,
)
from arthur_common.models.response_schemas import TaskResponse

# Only in an arthur-common newer than the pin; job_executor imports this module only
# when it is installed, and the ignore keeps mypy passing on the pinned one meanwhile.
from arthur_common.models.task_job_specs import (  # type: ignore[attr-defined,unused-ignore]
    KillAgentJobSpec,
    KillSwitchCloudTarget,
    ReenableAgentJobSpec,
)

from connectors.shield_connector import ShieldBaseConnector
from discovery.cloud.azure_ai_foundry import control as foundry_control
from discovery.cloud.azure_ai_foundry.client import PROJECT_ENDPOINT_FIELD
from discovery.cloud.azure_ai_foundry.connector import VENDOR as FOUNDRY_VENDOR
from job_executors.task_management_job_executors import TaskManagementJobExecutor
from log_redaction import register_secrets, secret_values
from tools.connector_constructor import ConnectorConstructor

Credentials = Mapping[str, Optional[str]]
# Turns one cloud target off or on: (target, its source's credentials, logger).
CloudTargetAction = Callable[
    [KillSwitchCloudTarget, Credentials, logging.Logger],
    foundry_control.AgentStateChange,
]


@dataclass(frozen=True)
class CloudVendorControl:
    """How the kill switch turns one vendor's resources off and on."""

    disable: CloudTargetAction
    enable: CloudTargetAction


class KillSwitchError(Exception):
    """One or more cloud targets could not be turned off or on."""


_FOUNDRY_AGENTS_SEGMENT = "/agents/"


def foundry_source_fields(target: KillSwitchCloudTarget) -> dict[str, str]:
    """The target's source fields, with the project endpoint recovered if missing.

    The Platform snapshots the source's fields onto the target, but one built before it
    did has none. The Foundry connector builds the external id as
    `<project_endpoint>/agents/<agent_name>`, so the endpoint is read back from it.
    """
    fields = dict(target.source_fields)
    if fields.get(PROJECT_ENDPOINT_FIELD, "").strip():
        return fields
    endpoint, separator, _ = target.external_id.rpartition(_FOUNDRY_AGENTS_SEGMENT)
    if separator and endpoint:
        fields[PROJECT_ENDPOINT_FIELD] = endpoint
    return fields


def _foundry_disable(
    target: KillSwitchCloudTarget,
    credentials: Credentials,
    logger: logging.Logger,
) -> foundry_control.AgentStateChange:
    return foundry_control.disable_agent(
        foundry_source_fields(target),
        credentials,
        target.address.resource_id,
        logger,
    )


def _foundry_enable(
    target: KillSwitchCloudTarget,
    credentials: Credentials,
    logger: logging.Logger,
) -> foundry_control.AgentStateChange:
    return foundry_control.enable_agent(
        foundry_source_fields(target),
        credentials,
        target.address.resource_id,
        logger,
    )


# The vendors whose resources the kill switch can turn off, keyed on the discovery
# vendor that reported them. A target of any other vendor fails the job.
CLOUD_VENDOR_CONTROLS: dict[str, CloudVendorControl] = {
    FOUNDRY_VENDOR: CloudVendorControl(
        disable=_foundry_disable, enable=_foundry_enable
    ),
}


class _KillSwitchJobExecutor(TaskManagementJobExecutor):
    def __init__(
        self,
        models_client: ModelsV1Api,
        datasets_client: DatasetsV1Api,
        tasks_client: TasksV1Api,
        connector_constructor: ConnectorConstructor,
        logger: logging.Logger,
        discovery_sources_client: DiscoverySourcesV1Api,
        vendor_controls: Mapping[str, CloudVendorControl] = CLOUD_VENDOR_CONTROLS,
    ) -> None:
        super().__init__(
            models_client,
            datasets_client,
            tasks_client,
            connector_constructor,
            logger,
        )
        self.discovery_sources_client = discovery_sources_client
        self.vendor_controls = vendor_controls
        self._credentials: dict[UUID, Credentials] = {}

    def _source_credentials(self, config_id: UUID) -> Credentials:
        """The config's sensitive fields, read once per job and registered for scrubbing."""
        if config_id not in self._credentials:
            credentials: dict[str, Optional[str]] = (
                self.discovery_sources_client.retrieve_discovery_source_credentials(
                    str(config_id),
                )
            )
            register_secrets(self.logger, secret_values(credentials))
            self._credentials[config_id] = credentials
        return self._credentials[config_id]

    def _apply_to_cloud_targets(
        self,
        targets: list[KillSwitchCloudTarget],
        turn_off: bool,
    ) -> list[str]:
        """Turn every target off (or on), returning one line per target that failed."""
        verb = "disable" if turn_off else "enable"
        failures: list[str] = []
        for target in targets:
            label = f"{target.vendor} resource {target.external_id}"
            control = self.vendor_controls.get(target.vendor)
            if control is None:
                message = (
                    f"Cannot {verb} {label}: the kill switch does not support vendor "
                    f"'{target.vendor}'."
                )
                self.logger.error(message)
                failures.append(message)
                continue
            try:
                credentials = self._source_credentials(
                    target.discovery_source_config_id,
                )
                action = control.disable if turn_off else control.enable
                change = action(target, credentials, self.logger)
            except Exception as e:
                message = f"Failed to {verb} {label}: {e}"
                self.logger.error(message, exc_info=True)
                failures.append(message)
                continue
            if change.changed:
                self.logger.info(
                    f"{label} is now {change.state} (was "
                    f"{change.previous_state or 'unreported'})",
                )
            else:
                self.logger.info(f"{label} was already {change.state}")
        return failures

    def _upload_task_state(
        self,
        model_id: str,
        task: TaskResponse,
        connector: ShieldBaseConnector,
        failures: list[str],
    ) -> None:
        """Upload the task's state, counting a failure with the targets' rather than
        letting it hide theirs."""
        try:
            self.upload_final_task_state(
                model_id=model_id,
                task=task,
                connector=connector,
            )
        except Exception as e:
            message = f"Failed to upload the task's final state: {e}"
            self.logger.error(message, exc_info=True)
            failures.append(message)

    @staticmethod
    def _raise_if_failed(failures: list[str], outcome: str) -> None:
        if failures:
            raise KillSwitchError(
                f"{outcome}; {len(failures)} step(s) failed: " + " | ".join(failures),
            )


class KillAgentJobExecutor(_KillSwitchJobExecutor):
    def execute(self, job_spec: KillAgentJobSpec) -> None:
        model, _, connector, task_id = (
            self.retrieve_task_management_resources_from_model_id(
                model_id=str(job_spec.scope_model_id),
            )
        )
        self.logger.info(
            f"Kill switch event {job_spec.kill_switch_event_id}: disabling task "
            f"{task_id}",
        )
        task = connector.disable_task(task_id=task_id, reason=job_spec.reason)
        self.logger.info(
            f"Task {task_id} is disabled; guarded requests for it are now refused",
        )

        failures = self._apply_to_cloud_targets(job_spec.cloud_targets, turn_off=True)
        self._upload_task_state(model.id, task, connector, failures)
        self._raise_if_failed(failures, f"Task {task_id} is disabled")
        self.logger.info(
            f"Kill switch event {job_spec.kill_switch_event_id}: agent is off "
            f"(task and {len(job_spec.cloud_targets)} cloud target(s))",
        )


class ReenableAgentJobExecutor(_KillSwitchJobExecutor):
    def execute(self, job_spec: ReenableAgentJobSpec) -> None:
        model, _, connector, task_id = (
            self.retrieve_task_management_resources_from_model_id(
                model_id=str(job_spec.scope_model_id),
            )
        )
        self.logger.info(
            f"Kill switch event {job_spec.kill_switch_event_id}: re-enabling "
            f"{len(job_spec.cloud_targets)} cloud target(s), then task {task_id}",
        )
        failures = self._apply_to_cloud_targets(
            job_spec.cloud_targets,
            turn_off=False,
        )
        if failures:
            # The block stays until every resource behind it is back, so a failed
            # re-enable never leaves the task open; running the job again finishes it.
            self.logger.error(
                f"Leaving task {task_id} disabled: not every cloud target came back",
            )
            task = connector.read_task(task_id=task_id)
        else:
            task = connector.enable_task(task_id=task_id)
            self.logger.info(f"Task {task_id} is enabled")

        self._upload_task_state(model.id, task, connector, failures)
        self._raise_if_failed(failures, f"Task {task_id} is still disabled")
        self.logger.info(
            f"Kill switch event {job_spec.kill_switch_event_id}: agent is back on",
        )
