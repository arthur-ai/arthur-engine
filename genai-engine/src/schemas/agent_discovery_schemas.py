"""Schemas for agent discovery functionality.

.. deprecated::
    The /api/v1/discover-agents endpoint is deprecated.
    Use GET /api/v2/agent-tasks instead.
    Shared schemas (Tool, SubAgent, ToolArgument) have moved to
    arthur_common.models.agent_governance_schemas.
"""

import warnings
from typing import Any
from uuid import UUID

from arthur_common.models.agent_governance_schemas import (  # noqa: F401
    SubAgent,
    Tool,
    ToolArgument,
)
from pydantic import BaseModel, Field


# Request Schemas
class DiscoverAgentsRequest(BaseModel):
    """Request to discover agents from infrastructure.

    .. deprecated::
        Use GET /api/v2/agent-tasks instead.
    """

    data_plane_id: UUID = Field(
        description="UUID of the data plane to discover agents from"
    )
    lookback_hours: int = Field(
        default=720,
        description="Number of hours to look back for traces (default 30 days)",
    )

    def __init_subclass__(cls, **kwargs: Any) -> None:
        warnings.warn(
            "DiscoverAgentsRequest is deprecated. Use GET /api/v2/agent-tasks instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init_subclass__(**kwargs)


# Component Schemas
class CreationSource(BaseModel):
    """Source information for how an unregistered agent was created.

    .. deprecated::
        This flat CreationSource model is deprecated.
        Use the discriminated union CreationSource from
        arthur_common.models.agent_governance_schemas instead.
    """

    task_id: UUID | None = Field(
        default=None,
        description="Optional UUID of the task that created this agent.",
    )
    top_level_span_name: str | None = Field(
        default=None,
        description="Optional top-level span name (legacy field, prefer GCP fields for GCP agents).",
    )
    gcp_project_id: str | None = Field(
        default=None,
        description="Optional GCP project ID where the agent is running.",
    )
    gcp_region: str | None = Field(
        default=None,
        description="Optional GCP region where the agent is running.",
    )
    gcp_reasoning_engine_id: str | None = Field(
        default=None,
        description="Optional GCP Vertex AI Reasoning Engine ID.",
    )


# Response Schemas
class DiscoveredAgent(BaseModel):
    """A discovered agent from infrastructure.

    .. deprecated::
        Use GET /api/v2/agent-tasks with EnrichedTaskResponse instead.
    """

    name: str = Field(description="Name of the agent.")
    creation_source: CreationSource = Field(
        description="Information about how this agent was created."
    )
    first_detected: str = Field(
        description="ISO 8601 timestamp when agent was first detected."
    )
    num_spans: int | None = Field(
        default=None,
        description="Number of spans associated with this agent.",
    )
    infrastructure: str = Field(
        description="Infrastructure where this agent is running (e.g., 'GCP')."
    )
    data_plane_id: UUID = Field(
        description="UUID of the data plane where this agent was detected."
    )
    tools: list[Tool] = Field(
        default_factory=list,
        description="List of tools used by this agent.",
    )
    sub_agents: list[SubAgent] = Field(
        default_factory=list,
        description="List of sub-agents used by this agent.",
    )


class DiscoverAgentsResponse(BaseModel):
    """Response containing discovered agents.

    .. deprecated::
        Use GET /api/v2/agent-tasks instead.
    """

    agents: list[DiscoveredAgent] = Field(description="List of discovered agents")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Discovery metadata (e.g., traces processed, errors)",
    )


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
