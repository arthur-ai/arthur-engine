from enum import Enum

from arthur_common.models.agent_discovery_schemas import (
    MAX_DISCOVERED_RECORDS_PER_REQUEST,
    DiscoveredAgentRecord,
)
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


class ResolveDiscoveredAgentsRequest(BaseModel):
    """A scan's worth of discovered records to resolve to tasks."""

    records: list[DiscoveredAgentRecord] = Field(
        min_length=1,
        max_length=MAX_DISCOVERED_RECORDS_PER_REQUEST,
        description="Records to resolve. Order is preserved in the response.",
    )


class ResolveDiscoveredAgentsResponse(BaseModel):
    """One entry per submitted record, in the order they were submitted."""

    resolved: list[ResolvedAgentTask] = Field(
        description="Resolution outcome per record, in request order",
    )
