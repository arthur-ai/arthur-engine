"""Schemas for agent discovery functionality."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# Request Schemas
class DiscoverAgentsRequest(BaseModel):
    """Request to discover agents from infrastructure."""

    data_plane_id: UUID = Field(
        description="UUID of the data plane to discover agents from"
    )
    lookback_hours: int = Field(
        default=720,
        description="Number of hours to look back for traces (default 30 days)",
    )


# Component Schemas
class CreationSource(BaseModel):
    """Source information for how an unregistered agent was created."""

    task_id: UUID | None = Field(
        default=None,
        description="Optional UUID of the task that created this agent.",
    )
    top_level_span_name: str | None = Field(
        default=None,
        description="Optional top-level span name (will be migrated to resource_id in future).",
    )


class ToolArgument(BaseModel):
    """Argument definition for a tool."""

    name: str = Field(description="Name of the tool argument.")
    type_: str = Field(
        alias="type",
        description="Type of the tool argument.",
    )

    class Config:
        populate_by_name = True


class Tool(BaseModel):
    """Tool definition with arguments."""

    name: str = Field(description="Name of the tool.")
    arguments: list[ToolArgument] = Field(
        default_factory=list,
        description="List of arguments for this tool.",
    )


class SubAgent(BaseModel):
    """Sub-agent definition."""

    name: str = Field(description="Name of the sub-agent.")


# Response Schemas
class DiscoveredAgent(BaseModel):
    """A discovered agent from infrastructure."""

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
    """Response containing discovered agents."""

    agents: list[DiscoveredAgent] = Field(description="List of discovered agents")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Discovery metadata (e.g., traces processed, errors)",
    )
