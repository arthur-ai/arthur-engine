from enum import Enum
from typing import Annotated, Union

from arthur_common.models.agent_governance_schemas import (
    AgentCreationSource,
    CloudAgentCreationSource,
    EndpointAgentCreationSource,
    SIEMAgentCreationSource,
)
from pydantic import BaseModel, Field, field_validator


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


# Cap on one resolve request. A scan that finds more than this splits into several
# calls; the limit exists so a runaway connector cannot hand the engine an unbounded
# batch, not because any smaller batch is meaningful.
MAX_DISCOVERED_RECORDS_PER_REQUEST = 1000


# The creation sources a scan can report, narrower than the union a task can carry.
# OTEL and MANUAL are not things a scan finds, and a record claiming to be either would
# mint a task whose provenance says nobody discovered it; deprecated GCP is not an input
# anyone should start using. Spelled out rather than validated after the fact against
# DISCOVERY_SOURCE_CLASSES so the OpenAPI schema -- and therefore the generated client
# the scan job calls this with -- states what it accepts. A fourth discovery category
# lands here as one more member.
DiscoverySourceUnion = Annotated[
    Union[
        CloudAgentCreationSource,
        SIEMAgentCreationSource,
        EndpointAgentCreationSource,
    ],
    Field(discriminator="type"),
]


class DiscoveredAgentRecord(BaseModel):
    """One record from a discovery scan, on its way to becoming a task.

    Task-shaped and keyed on ``external_id``: everything the engine needs to mint a
    task, plus the identity the source knows the agent by. The scan job builds one of
    these per row its connector returned, after that row has passed the connector's
    output contract (``DiscoveryOutputRecord``).
    """

    external_id: str = Field(
        min_length=1,
        description="The source's own identifier for this agent, and the identity the "
        "whole feature keys on. Required: a record without one has no stable identity, "
        "and routing it to the unmapped task would silently collapse every such finding "
        "together. The connector's output contract rejects it upstream; this bound is "
        "the engine's own backstop.",
    )
    name: str = Field(
        min_length=1,
        description="Human-readable agent name, used as the task name when a task is "
        "minted. Never rewrites the name of a task that already exists -- renaming on "
        "every scan would churn a field people sort and search on.",
    )
    creation_source: DiscoverySourceUnion = Field(
        description="The sensor that reported this agent, its upstream address and what "
        "it observed.",
    )
    task_id: str | None = Field(
        default=None,
        description="Existing task to route this record to, when the caller already "
        "knows it. Optional HERE AND ONLY HERE -- a SIEM does not know Arthur's task "
        "IDs. Every record still comes back with one.",
    )

    @field_validator("external_id", "name")
    @classmethod
    def _must_not_be_blank(cls, value: str) -> str:
        """Reject a value that is only whitespace.

        `min_length` alone lets a single space through, and a space is not an
        identity: two agents whose sources both report one would key to the same
        mapping and collapse onto one task -- the failure `external_id` exists to
        prevent, arriving through the backstop meant to stop it. A blank `name`
        would mint a task that reads as nameless everywhere it is listed.

        The value is returned unchanged rather than stripped: what the source calls
        the agent is the source's to decide, and silently rewriting a key would
        make the identity depend on this engine's idea of trailing space.
        """
        if not value.strip():
            raise ValueError("must contain a non-whitespace character")
        return value

    @property
    def task_creation_source(self) -> AgentCreationSource:
        """The creation source in the shape a task stores it."""
        return AgentCreationSource(root=self.creation_source)

    @property
    def service_names(self) -> list[str]:
        """Service names this agent emits telemetry under, if the sensor saw any.

        The link between a discovered agent and traces already arriving, and read off
        the creation source rather than duplicated as a field of its own so there is
        one place it can come from.
        """
        return list(self.creation_source.observations.service_names)


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
