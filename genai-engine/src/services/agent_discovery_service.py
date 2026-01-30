"""Agent Discovery Service for GenAI Engine.

This service handles discovering agents from infrastructure providers (currently GCP).
Uses Google Application Default Credentials (ADC) for authentication.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import vertexai
from google.cloud import trace_v1
from sqlalchemy.orm import Session

from schemas.agent_discovery_schemas import (
    CreationSource,
    DiscoverAgentsResponse,
    DiscoveredAgent,
    SubAgent,
    Tool,
)

logger = logging.getLogger(__name__)


class AgentDiscoveryService:
    """Service for discovering agents from infrastructure using GCP ADC."""

    def __init__(self, db_session: Session):
        """Initialize the agent discovery service.

        Args:
            db_session: Database session (for future use if needed)
        """
        self.db_session = db_session

    def discover_agents(
        self,
        data_plane_id: UUID,
        lookback_hours: int,
    ) -> DiscoverAgentsResponse:
        """Discover agents from GCP infrastructure.

        Uses Google Application Default Credentials (ADC) to access:
        - Vertex AI (to list agent engines)
        - Cloud Trace (to fetch agent metadata like tools and sub-agents)

        Args:
            data_plane_id: UUID of the data plane (used in agent creation_source)
            lookback_hours: Number of hours to look back for traces

        Returns:
            DiscoverAgentsResponse containing discovered agents and metadata

        Raises:
            ValueError: If GOOGLE_CLOUD_PROJECT not configured
            Exception: If GCP discovery fails
        """
        logger.info(
            f"Starting agent discovery for data_plane {data_plane_id}, "
            f"lookback {lookback_hours} hours"
        )

        # Get GCP project info from environment (set via ADC or model provider)
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

        if not project_id:
            raise ValueError(
                "GOOGLE_CLOUD_PROJECT environment variable not set. "
                "Cannot discover agents without GCP project configuration."
            )

        logger.info(f"Using GCP project: {project_id}, location: {location}")

        # Discover agents from GCP
        agents, metadata = self._discover_gcp_agents(
            project_id,
            location,
            data_plane_id,
            lookback_hours,
        )

        logger.info(
            f"Agent discovery completed for data_plane {data_plane_id}: "
            f"{len(agents)} agents found"
        )

        return DiscoverAgentsResponse(
            agents=agents,
            metadata=metadata,
        )

    def _discover_gcp_agents(
        self,
        project_id: str,
        location: str,
        data_plane_id: UUID,
        lookback_hours: int,
    ) -> tuple[list[DiscoveredAgent], dict[str, Any]]:
        """Discover agents from GCP Vertex AI and Cloud Trace.

        Args:
            project_id: GCP project ID
            location: GCP location (e.g., us-central1)
            data_plane_id: Data plane UUID
            lookback_hours: Hours to look back for traces

        Returns:
            Tuple of (list of discovered agents, metadata dictionary)
        """
        # List Vertex AI agents
        vertex_agents = self._list_vertex_ai_agents(project_id, location)

        if not vertex_agents:
            logger.info("No Vertex AI agents found")
            return (
                [],
                {
                    "total_vertex_agents": 0,
                    "total_traces_processed": 0,
                    "errors": [],
                },
            )

        logger.info(f"Found {len(vertex_agents)} Vertex AI agent(s)")

        # Fetch trace data
        trace_resources = self._fetch_trace_data(project_id, lookback_hours)

        logger.info(f"Extracted trace data for {len(trace_resources)} resource(s)")

        # Build lookup of agents by ID
        agents_by_id = {}
        for agent in vertex_agents:
            api_resource = agent.api_resource
            resource_name = getattr(api_resource, "name", "")
            agent_id = resource_name.split("/")[-1] if resource_name else None
            if agent_id:
                agents_by_id[agent_id] = agent

        # Convert agents to discovered agent format
        discovered_agents = []

        # Process agents with trace data
        for resource_id, trace_data in trace_resources.items():
            # Extract ID from resource_id
            agent_id = None
            if "/reasoningEngines/" in resource_id or "/agentEngines/" in resource_id:
                agent_id = resource_id.split("/")[-1]

            # Find matching agent
            if agent_id and agent_id in agents_by_id:
                agent = agents_by_id[agent_id]
                discovered_agent = self._convert_to_discovered_agent(
                    agent, trace_data, resource_id, data_plane_id
                )
                discovered_agents.append(discovered_agent)
                logger.debug(
                    f"Converted agent {discovered_agent.name} with trace data "
                    f"(resource_id={resource_id})"
                )

        # Add agents without trace data
        for agent_id, agent in agents_by_id.items():
            # Check if this agent was already processed from trace data
            already_processed = any(
                agent_id in resource_id for resource_id in trace_resources.keys()
            )

            if not already_processed:
                # Construct resource_id from agent info
                api_resource = agent.api_resource
                resource_name = getattr(api_resource, "name", "")
                resource_id = (
                    resource_name if resource_name else f"vertex-ai-agent-{agent_id}"
                )

                discovered_agent = self._convert_to_discovered_agent(
                    agent, None, resource_id, data_plane_id
                )
                discovered_agents.append(discovered_agent)
                logger.debug(
                    f"Converted agent {discovered_agent.name} without trace data"
                )

        metadata = {
            "total_vertex_agents": len(vertex_agents),
            "total_traces_processed": sum(
                trace_data.get("num_spans", 0)
                for trace_data in trace_resources.values()
            ),
            "errors": [],
        }

        return discovered_agents, metadata

    def _list_vertex_ai_agents(self, project_id: str, location: str) -> list[Any]:
        """List all deployed Vertex AI agent engines.

        Uses Google Application Default Credentials (ADC) for authentication.

        Args:
            project_id: GCP project ID
            location: GCP location

        Returns:
            List of Vertex AI agent engine objects

        Raises:
            Exception: If listing agents fails
        """
        # Initialize Vertex AI with ADC
        vertexai.init(project=project_id, location=location)

        # List agent engines
        client = vertexai.Client(project=project_id, location=location)
        agents = list(client.agent_engines.list())

        return agents

    def _fetch_trace_data(
        self, project_id: str, lookback_hours: int
    ) -> dict[str, dict[str, Any]]:
        """Fetch traces from Google Cloud Trace and extract agents/tools grouped by cloud.resource_id.

        Uses Google Application Default Credentials (ADC) for authentication.

        Args:
            project_id: GCP project ID
            lookback_hours: Hours to look back for traces

        Returns:
            Dictionary mapping resource_id to trace data (tools, agents, num_spans)

        Raises:
            Exception: If fetching traces fails
        """
        # Initialize Cloud Trace client with ADC
        trace_client = trace_v1.TraceServiceClient()

        # Define time range
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=lookback_hours)

        logger.info(
            f"Fetching traces from {start_time.isoformat()} to {end_time.isoformat()}"
        )

        # Fetch trace IDs
        request = trace_v1.ListTracesRequest(
            project_id=project_id,
            start_time=start_time,
            end_time=end_time,
        )

        trace_ids = []
        page_result = trace_client.list_traces(request=request)
        for trace in page_result:
            trace_ids.append(trace.trace_id)

        logger.info(f"Found {len(trace_ids)} trace ID(s)")

        if not trace_ids:
            return {}

        # Fetch complete traces and extract resource data
        resources = {}

        for i, trace_id in enumerate(trace_ids, 1):
            if i % 10 == 0:
                logger.debug(f"Processing trace {i}/{len(trace_ids)}")

            try:
                get_request = trace_v1.GetTraceRequest(
                    project_id=project_id,
                    trace_id=trace_id,
                )
                trace = trace_client.get_trace(request=get_request)

                # Process each span in the trace
                for span in trace.spans:
                    labels = getattr(span, "labels", {})

                    # Extract cloud.resource_id
                    resource_id = labels.get("cloud.resource_id")
                    if not resource_id:
                        continue

                    # Initialize resource entry if not exists
                    if resource_id not in resources:
                        resources[resource_id] = {
                            "agents": set(),
                            "tools": set(),
                            "num_spans": 0,
                        }

                    # Count spans for this resource
                    resources[resource_id]["num_spans"] += 1

                    # Extract gen_ai.agent.name
                    agent_name = labels.get("gen_ai.agent.name")
                    if agent_name:
                        resources[resource_id]["agents"].add(agent_name)

                    # Extract gen_ai.tool.name
                    tool_name = labels.get("gen_ai.tool.name")
                    if tool_name:
                        resources[resource_id]["tools"].add(tool_name)

            except Exception as e:
                # Log individual trace errors but continue processing
                logger.debug(f"Error fetching trace {trace_id}: {str(e)}")
                continue

        return resources

    def _convert_to_discovered_agent(
        self,
        agent: Any,
        trace_data: dict[str, Any] | None,
        resource_id: str,
        data_plane_id: UUID,
    ) -> DiscoveredAgent:
        """Convert a Vertex AI agent to DiscoveredAgent format.

        Args:
            agent: Vertex AI agent object
            trace_data: Optional trace data dictionary
            resource_id: Infrastructure resource ID (full GCP resource path)
            data_plane_id: Data plane UUID (used only in agent object, not for discovery)

        Returns:
            DiscoveredAgent object
        """
        api_resource = agent.api_resource

        # Extract agent details
        name = getattr(api_resource, "display_name", None) or getattr(
            api_resource, "name", "Unknown Agent"
        )

        # Get creation time or use current time
        create_time = getattr(api_resource, "create_time", None)
        if create_time:
            # Ensure proper ISO format with Z for UTC
            first_detected = create_time.isoformat()
            first_detected = first_detected.replace("+00:00", "").replace("Z", "") + "Z"
        else:
            # Use current time in UTC with Z suffix
            first_detected = (
                datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            )

        # Extract tools, sub-agents, and span count from trace data if available
        tools = []
        sub_agents = []
        num_spans = 0

        if trace_data:
            # Convert tool names to Tool objects
            tool_names = sorted(list(trace_data.get("tools", set())))
            tools = [Tool(name=tool_name, arguments=[]) for tool_name in tool_names]

            # Convert agent names to SubAgent objects
            agent_names = sorted(list(trace_data.get("agents", set())))
            sub_agents = [SubAgent(name=agent_name) for agent_name in agent_names]

            # Get span count
            num_spans = trace_data.get("num_spans", 0)

        # Build discovered agent with resource_id as the unique identifier
        return DiscoveredAgent(
            name=f"Vertex AI Agent: {name}",
            creation_source=CreationSource(
                task_id=None,
                resource_id=resource_id,  # Use full GCP resource path (e.g., projects/.../reasoningEngines/...)
            ),
            first_detected=first_detected,
            infrastructure="GCP",
            num_spans=num_spans,
            tools=tools,
            sub_agents=sub_agents,
            data_plane_id=data_plane_id,  # Only used when creating the agent object
        )
