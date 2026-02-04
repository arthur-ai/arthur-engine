"""Agent discovery job executor - POC implementation."""

import logging

import requests
from arthur_client.api_bindings import DiscoverAgentsJobSpec, WorkspacesV1Api


class AgentDiscoveryJobExecutor:
    """Discovers unregistered agents from Vertex AI and stores them in app-plane."""

    AGENT_DISCOVERY_HOST = "http://agent-discovery:8000"
    AGENT_DISCOVERY_TIMEOUT = 120

    def __init__(
        self,
        workspaces_client: WorkspacesV1Api,
        logger: logging.Logger,
    ) -> None:
        self.workspaces_client: WorkspacesV1Api = workspaces_client
        self.logger: logging.Logger = logger

    def execute(self, job_spec: DiscoverAgentsJobSpec) -> None:
        """Execute agent discovery job."""
        workspace_id = str(job_spec.workspace_id)
        data_plane_id = str(job_spec.data_plane_id)

        self.logger.info(
            f"Executing agent discovery job for workspace {workspace_id}",
        )

        try:
            # Step 1: Call agent discovery service (hardcoded request for POC)
            self.logger.info("Calling agent discovery service...")
            response = requests.post(
                f"{self.AGENT_DISCOVERY_HOST}/api/v1/vertex/agents",
                json={
                    "include_traces": True,
                    "trace_lookback_hours": None,  # Auto-calculate from 2026-01-01
                },
                timeout=self.AGENT_DISCOVERY_TIMEOUT,
            )
            response.raise_for_status()
            discovery_data = response.json()

            self.logger.info(f"Discovered {discovery_data.get('count', 0)} agents")

            # Step 2: Transform to app-plane format
            agents_to_store = []
            for agent in discovery_data.get("agents", []):
                # Map discovery response to PutUnregisteredAgents format
                agent_data = {
                    "name": agent.get("name", agent.get("agent_id")),
                    "data_plane_id": data_plane_id,
                    "infrastructure": agent.get("infrastructure", "GCP"),
                    "first_detected": agent.get("create_time"),
                    "num_spans": agent.get("num_spans", 0),
                    "tools": [{"name": tool} for tool in agent.get("tools", [])],
                    "sub_agents": [
                        {"name": subagent} for subagent in agent.get("subagents", [])
                    ],
                    # Use agent_id as creation source for deduplication
                    "creation_source": {"top_level_span_name": agent.get("agent_id")},
                }
                agents_to_store.append(agent_data)

            # Step 3: Store in app-plane using existing API
            if agents_to_store:
                self.logger.info(
                    f"Storing {len(agents_to_store)} agents in app-plane..."
                )
                self.workspaces_client.put_unregistered_agents(
                    workspace_id=workspace_id,
                    put_unregistered_agents={"agents": agents_to_store},
                )
                self.logger.info("Successfully stored agents")
            else:
                self.logger.info("No agents to store")

        except requests.RequestException as e:
            self.logger.error(f"Failed to call agent discovery service: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error during agent discovery: {e}", exc_info=True)
            raise

        self.logger.info(f"Agent discovery job completed for workspace {workspace_id}")
