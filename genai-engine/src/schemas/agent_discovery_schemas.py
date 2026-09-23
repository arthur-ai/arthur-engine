from enum import Enum
from typing import Optional
from uuid import UUID

from arthur_common.models.agent_discovery_schemas import (
    MAX_DISCOVERED_RECORDS_PER_REQUEST,
    DiscoveredAgentRecord,
)
from arthur_common.models.agent_governance_schemas import (
    EnrichedTaskResponse as CommonEnrichedTaskResponse,
)
from arthur_common.models.agent_governance_schemas import Provenance
from pydantic import BaseModel, Field


class ExecutePollingResponse(BaseModel):
    """Response model for the single-task agent polling endpoint."""

    status: str = Field(description="Status of the operation")
    task_id: str = Field(description="Task ID that was enqueued")


class DiscoverAndPollResponse(BaseModel):
    """Response model for the execute-all agent polling endpoint."""

    status: str = Field(description="Status of the operation")
    discovered: int = Field(description="Number of new agent tasks created")
    traces_fetched: int = Field(
        description="Total number of traces fetched across all tasks (0 in async mode)"
    )


class TaskResolutionMethod(str, Enum):
    """Which rung of the resolution ladder answered for a record.

    Returned per record because the caller cannot otherwise tell a stable re-scan from
    a run that minted 500 duplicates, and that difference is the whole identity
    guarantee. Not stored: it describes one resolution, not the task.
    """

    EXPLICIT_TASK_ID = "explicit_task_id"
    """The record named its task."""

    EXTERNAL_ID = "external_id"
    """A previous scan already minted a task for this external_id."""

    SERVICE_NAME = "service_name"
    """The agent is already known under a service name the sensor reported -- either
    from its own traces or from another discovery source that saw the same name."""

    CREATED = "created"
    """Nothing matched; a task was minted."""


class ResolvedAgentTask(BaseModel):
    """What one discovered record resolved to. Always carries a task ID."""

    external_id: str = Field(description="Identity the record arrived with")
    task_id: str = Field(description="Task this record's findings belong to")
    name: str = Field(
        description="Name of the resolved task, which for an existing task is its "
        "current name rather than the name the record carried",
    )
    resolved_by: TaskResolutionMethod = Field(
        description="Which rung of the resolution ladder answered",
    )


class DiscoveredRecordFailureReason(str, Enum):
    """Why a record came back in `failed` rather than `resolved`."""

    TASK_NOT_FOUND = "task_not_found"
    """The record named a task, or resolved to one, that does not exist."""


class FailedDiscoveredRecord(BaseModel):
    """A record that could not be resolved, reported so the rest of its batch can be."""

    external_id: str = Field(description="Identity the record arrived with")
    task_id: str = Field(
        description="Task the record named or resolved to, which does not exist",
    )
    reason: DiscoveredRecordFailureReason = Field(
        description="Why the record could not be resolved",
    )
    detail: str = Field(description="Human-readable explanation of the failure")


class ResolveDiscoveredAgentsRequest(BaseModel):
    """A scan's worth of discovered records to resolve to tasks."""

    source_id: UUID = Field(
        description="The Discovery Source whose scan produced these records, recorded "
        "in each resolved task's provenance. Per request rather than per record because "
        "a scan job runs exactly one source config, and so one source. Required: a "
        "record resolved without it could never be fetched back for its source.",
    )
    records: list[DiscoveredAgentRecord] = Field(
        min_length=1,
        max_length=MAX_DISCOVERED_RECORDS_PER_REQUEST,
        description="Records to resolve. Order is preserved in the response.",
    )


class ResolveDiscoveredAgentsResponse(BaseModel):
    """Every submitted record, in exactly one of `resolved` or `failed`.

    A record that cannot be resolved does not fail its batch: the rest resolve, and
    the scan job can tell which records landed without re-submitting them.
    """

    resolved: list[ResolvedAgentTask] = Field(
        description="Records that resolved to a task, in request order",
    )
    failed: list[FailedDiscoveredRecord] = Field(
        default_factory=list,
        description="Records that could not be resolved, in request order. "
        "Re-submitting one unchanged fails the same way.",
    )


class EnrichedTaskResponse(CommonEnrichedTaskResponse):
    """The agent-tasks response, with the task's provenance.

    Extends the shared model rather than living in it only until `arthur_common` carries
    `provenance` on `EnrichedTaskResponse` itself, at which point this subclass goes.
    Named the same so the OpenAPI component, and the generated clients built from it,
    keep their name either way.
    """

    provenance: Optional[Provenance] = Field(
        default=None,
        description="Every sensor that has reported this agent, and where upstream each "
        "reported it. Absent only for a task with no creation source recorded.",
    )
