"""
Executor for discovering unregistered agents from GCP data planes.

This executor:
1. Lists all deployed Vertex AI agent engines
2. Fetches traces from Cloud Trace to extract agent metadata (tools, sub-agents)
3. Converts them to Arthur's unregistered agent format
4. Publishes them to the Arthur platform
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Set

import vertexai
from arthur_client.api_bindings import (
    DiscoverAgentsJobSpec,
    Job,
    PutUnregisteredAgents,
    UnregisteredAgent,
    UnregisteredAgentsV1Api,
)
from google.cloud import trace_v1


class DiscoverAgentsExecutor:
    def __init__(
        self,
        unregistered_agents_client: UnregisteredAgentsV1Api,
        logger: logging.Logger,
    ) -> None:
        self.unregistered_agents_client = unregistered_agents_client
        self.logger = logger

    def execute(self, job: Job, job_spec: DiscoverAgentsJobSpec) -> None:
        """Execute agent discovery job."""
        self.logger.info(
            f"Starting agent discovery for workspace {job_spec.workspace_id}, "
            f"data plane {job_spec.data_plane_id}, "
            f"lookback {job_spec.lookback_hours} hours",
            extra={
                "workspace_id": str(job_spec.workspace_id),
                "data_plane_id": str(job_spec.data_plane_id),
                "lookback_hours": job_spec.lookback_hours,
            },
        )

        try:
            # Load GCP configuration from data plane
            gcp_config = self._load_gcp_config(str(job_spec.data_plane_id))

            if not gcp_config:
                self.logger.warning(
                    f"Data plane {job_spec.data_plane_id} is not GCP infrastructure, skipping",
                    extra={"data_plane_id": str(job_spec.data_plane_id)},
                )
                return

            # Discover agents from GCP
            agents = self._discover_gcp_agents(
                gcp_config,
                str(job_spec.data_plane_id),
                job_spec.lookback_hours,
            )

            if not agents:
                self.logger.info(
                    f"No agents found for data plane {job_spec.data_plane_id}",
                    extra={"data_plane_id": str(job_spec.data_plane_id)},
                )
                return

            # Publish to Arthur platform
            results = self._publish_agents(
                str(job_spec.workspace_id),
                agents,
            )

            self.logger.info(
                f"Agent discovery completed for data plane {job_spec.data_plane_id}",
                extra={
                    "data_plane_id": str(job_spec.data_plane_id),
                    "total_agents": len(agents),
                    "num_created": results["created"],
                    "num_updated": results["updated"],
                    "num_skipped": results["skipped"],
                },
            )

        except Exception as e:
            self.logger.error(
                f"Agent discovery failed for data plane {job_spec.data_plane_id}: {str(e)}",
                extra={
                    "data_plane_id": str(job_spec.data_plane_id),
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    def _load_gcp_config(self, data_plane_id: str) -> Dict[str, str] | None:
        """Load GCP configuration from environment variables.

        If GCP environment variables are not set, returns None (non-GCP environment).
        This allows the executor to run in local/non-GCP environments.
        """
        try:
            # Extract GCP configuration from environment variables
            # These are set by the GCP infrastructure when running on GCP
            gcp_config = {
                "project_id": os.getenv("GOOGLE_CLOUD_PROJECT"),
                "project_number": os.getenv("GOOGLE_CLOUD_PROJECT_NUMBER"),
                "location": os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
            }

            # If GCP project_id is not set, this is not a GCP environment
            # Note: project_number is optional and not used by the GCP APIs
            if not gcp_config["project_id"]:
                self.logger.info(
                    f"GOOGLE_CLOUD_PROJECT not set, skipping GCP discovery for data plane {data_plane_id}",
                    extra={"data_plane_id": data_plane_id},
                )
                return None

            self.logger.info(
                f"Loaded GCP config for data plane {data_plane_id}",
                extra={
                    "data_plane_id": data_plane_id,
                    "project_id": gcp_config["project_id"],
                    "location": gcp_config["location"],
                },
            )

            return gcp_config

        except Exception as e:
            self.logger.error(
                f"Failed to load GCP config for data plane {data_plane_id}: {str(e)}",
                extra={"data_plane_id": data_plane_id, "error": str(e)},
            )
            return None

    def _discover_gcp_agents(
        self, gcp_config: Dict[str, str], data_plane_id: str, lookback_hours: int
    ) -> List[Dict[str, Any]]:
        """Discover agents from GCP Vertex AI and Cloud Trace."""
        # List Vertex AI agents
        vertex_agents = self._list_vertex_ai_agents(gcp_config)

        if not vertex_agents:
            self.logger.info(
                "No Vertex AI agents found",
                extra={"project_id": gcp_config["project_id"]},
            )
            return []

        self.logger.info(
            f"Found {len(vertex_agents)} Vertex AI agent(s)",
            extra={"num_agents": len(vertex_agents)},
        )

        # Fetch trace data
        trace_resources = self._fetch_trace_data(
            gcp_config["project_id"],
            lookback_hours,
        )

        self.logger.info(
            f"Extracted trace data for {len(trace_resources)} resource(s)",
            extra={"num_resources": len(trace_resources)},
        )

        # Build lookup of agents by ID
        agents_by_id = {}
        for agent in vertex_agents:
            api_resource = agent.api_resource
            resource_name = getattr(api_resource, "name", "")
            agent_id = resource_name.split("/")[-1] if resource_name else None
            if agent_id:
                agents_by_id[agent_id] = agent

        # Convert agents to unregistered agent format
        agents_payload = []

        # Process agents with trace data
        for resource_id, trace_data in trace_resources.items():
            # Extract ID from resource_id
            agent_id = None
            if "/reasoningEngines/" in resource_id or "/agentEngines/" in resource_id:
                agent_id = resource_id.split("/")[-1]

            # Find matching agent
            if agent_id and agent_id in agents_by_id:
                agent = agents_by_id[agent_id]
                payload = self._convert_to_unregistered_agent(
                    agent, trace_data, data_plane_id
                )
                agents_payload.append(payload)
                self.logger.debug(
                    f"Converted agent {payload['name']} with trace data",
                    extra={
                        "agent_name": payload["name"],
                        "num_tools": len(payload["tools"]),
                        "num_sub_agents": len(payload["sub_agents"]),
                        "num_spans": trace_data.get("num_spans", 0),
                    },
                )

        # Add agents without trace data
        for agent_id, agent in agents_by_id.items():
            # Check if this agent was already processed from trace data
            already_processed = False
            for resource_id in trace_resources.keys():
                if agent_id in resource_id:
                    already_processed = True
                    break

            if not already_processed:
                payload = self._convert_to_unregistered_agent(
                    agent, None, data_plane_id
                )
                agents_payload.append(payload)
                self.logger.debug(
                    f"Converted agent {payload['name']} without trace data",
                    extra={"agent_name": payload["name"]},
                )

        return agents_payload

    def _list_vertex_ai_agents(self, gcp_config: Dict[str, str]) -> List[Any]:
        """List all deployed Vertex AI agent engines."""
        try:
            # Initialize Vertex AI
            vertexai.init(
                project=gcp_config["project_id"],
                location=gcp_config["location"],
            )

            # List agent engines
            client = vertexai.Client(
                project=gcp_config["project_id"],
                location=gcp_config["location"],
            )
            agents = list(client.agent_engines.list())

            return agents

        except Exception as e:
            self.logger.error(
                f"Failed to list Vertex AI agents: {str(e)}",
                extra={"error": str(e)},
            )
            return []

    def _fetch_trace_data(
        self, project_id: str, lookback_hours: int
    ) -> Dict[str, Dict[str, Any]]:
        """Fetch traces from Google Cloud Trace and extract agents/tools grouped by cloud.resource_id."""
        try:
            # Initialize Cloud Trace client
            trace_client = trace_v1.TraceServiceClient()

            # Define time range for trace fetching
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=lookback_hours)

            self.logger.info(
                f"Fetching traces from {start_time.isoformat()} to {end_time.isoformat()}",
                extra={
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                },
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

            self.logger.info(
                f"Found {len(trace_ids)} trace ID(s)",
                extra={"num_traces": len(trace_ids)},
            )

            if not trace_ids:
                return {}

            # Fetch complete traces and extract resource data
            resources = {}

            for i, trace_id in enumerate(trace_ids, 1):
                if i % 10 == 0:
                    self.logger.debug(
                        f"Processing trace {i}/{len(trace_ids)}",
                        extra={"current_trace": i, "total_traces": len(trace_ids)},
                    )

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
                    self.logger.debug(
                        f"Error fetching trace {trace_id}: {str(e)}",
                        extra={"trace_id": trace_id, "error": str(e)},
                    )
                    continue

            return resources

        except Exception as e:
            self.logger.error(
                f"Failed to fetch trace data: {str(e)}",
                extra={"error": str(e)},
            )
            return {}

    def _convert_to_unregistered_agent(
        self,
        agent: Any,
        trace_data: Dict[str, Set[str]] | None,
        data_plane_id: str,
    ) -> Dict[str, Any]:
        """Convert a Vertex AI agent to Arthur unregistered agent format."""
        api_resource = agent.api_resource

        # Extract agent details
        name = getattr(api_resource, "display_name", None) or getattr(
            api_resource, "name", "Unknown Agent"
        )
        resource_name = getattr(api_resource, "name", "")
        agent_id = resource_name.split("/")[-1] if resource_name else "unknown"

        # Get creation time or use current time
        create_time = getattr(api_resource, "create_time", None)
        if create_time:
            # Ensure proper ISO format: either Z or +00:00, not both
            first_detected = create_time.isoformat()
            # Remove timezone info and add Z for UTC
            first_detected = first_detected.replace("+00:00", "").replace("Z", "") + "Z"
        else:
            # Use current time in UTC with Z suffix
            first_detected = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        # Extract tools, sub-agents, and span count from trace data if available
        tools = []
        sub_agents = []
        num_spans = 0
        if trace_data:
            # Convert tool names to Tool objects with name and arguments (list)
            tool_names = sorted(list(trace_data.get("tools", set())))
            tools = [{"name": tool_name, "arguments": []} for tool_name in tool_names]

            # Convert agent names to SubAgent objects with name
            agent_names = sorted(list(trace_data.get("agents", set())))
            sub_agents = [{"name": agent_name} for agent_name in agent_names]

            # Get span count from trace data
            num_spans = trace_data.get("num_spans", 0)

        # Build unregistered agent payload
        unregistered_agent = {
            "name": f"Vertex AI Agent: {name}",
            "creation_source": {
                "top_level_span_name": f"vertex-ai-agent-{agent_id}",
            },
            "first_detected": first_detected,
            "infrastructure": "GCP",
            "num_spans": num_spans,
            "tools": tools,
            "sub_agents": sub_agents,
            "data_plane_id": data_plane_id,
        }

        return unregistered_agent

    def _publish_agents(
        self, workspace_id: str, agents_payload: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Publish unregistered agents to Arthur platform."""
        self.logger.info(
            f"Publishing {len(agents_payload)} agent(s) to workspace {workspace_id}",
            extra={"workspace_id": workspace_id, "num_agents": len(agents_payload)},
        )

        try:
            # Simplified: just create all agents without checking for existing ones
            # The database should handle duplicates via unique constraints
            self.logger.info(
                f"Creating {len(agents_payload)} new agent(s)",
                extra={"num_new": len(agents_payload)},
            )

            agent_objects = [UnregisteredAgent(**agent) for agent in agents_payload]
            put_request = PutUnregisteredAgents(unregistered_agents=agent_objects)

            self.unregistered_agents_client.put_unregistered_agents(
                workspace_id=workspace_id,
                put_unregistered_agents=put_request,
            )

            results = {
                "created": len(agents_payload),
                "updated": 0,
                "skipped": 0,
            }

            self.logger.info(
                f"Publish completed: {results['created']} created, {results['updated']} updated, {results['skipped']} skipped",
                extra={
                    "num_created": results["created"],
                    "num_updated": results["updated"],
                    "num_skipped": results["skipped"],
                },
            )

            return results

        except Exception as e:
            self.logger.error(
                f"Failed to publish agents: {str(e)}",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise
