"""
Executor for discovering unregistered agents from GCP data planes.

This executor:
1. Calls GenAI Engine API to discover agents from infrastructure
2. Filters discovered agents against existing Models
3. Publishes filtered agents to the Arthur platform as UnregisteredAgents
"""

import json
import logging
from typing import Any, Dict, List

from arthur_client.api_bindings import (
    DiscoverAgentsJobSpec,
    Job,
    ModelsV1Api,
    PutUnregisteredAgents,
    UnregisteredAgent,
    UnregisteredAgentsV1Api,
)
from genai_client import (
    AgentDiscoveryApi,
    ApiClient,
    Configuration,
    DiscoverAgentsRequest,
)
import urllib3


class DiscoverAgentsExecutor:
    def __init__(
        self,
        unregistered_agents_client: UnregisteredAgentsV1Api,
        models_client: ModelsV1Api,
        logger: logging.Logger,
        genai_engine_url: str,
        genai_engine_api_key: str,
    ) -> None:
        self.unregistered_agents_client = unregistered_agents_client
        self.models_client = models_client
        self.logger = logger
        self.genai_engine_url = genai_engine_url
        self.genai_engine_api_key = genai_engine_api_key

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
            # Call GenAI Engine to discover agents
            discovered_agents = self._discover_agents_from_genai_engine(
                str(job_spec.data_plane_id),
                job_spec.lookback_hours,
            )

            if not discovered_agents:
                self.logger.info(
                    f"No agents discovered for data plane {job_spec.data_plane_id}",
                    extra={"data_plane_id": str(job_spec.data_plane_id)},
                )
                return

            self.logger.info(
                f"Discovered {len(discovered_agents)} agent(s) from GenAI Engine",
                extra={"num_discovered": len(discovered_agents)},
            )

            # Filter against existing Models (if project_id provided)
            project_id = str(job_spec.project_id) if job_spec.project_id else None
            filtered_agents = self._filter_against_existing_models(
                discovered_agents,
                str(job_spec.workspace_id),
                str(job_spec.data_plane_id),
                project_id,
            )

            if not filtered_agents:
                self.logger.info(
                    f"All discovered agents match existing Models, nothing to publish",
                    extra={
                        "data_plane_id": str(job_spec.data_plane_id),
                        "num_discovered": len(discovered_agents),
                        "num_filtered": 0,
                    },
                )
                return

            self.logger.info(
                f"Filtered to {len(filtered_agents)} new agent(s) after matching",
                extra={
                    "num_discovered": len(discovered_agents),
                    "num_filtered": len(filtered_agents),
                },
            )

            # Publish to Arthur platform
            results = self._publish_agents(
                str(job_spec.workspace_id),
                filtered_agents,
            )

            self.logger.info(
                f"Agent discovery completed for data plane {job_spec.data_plane_id}",
                extra={
                    "data_plane_id": str(job_spec.data_plane_id),
                    "total_discovered": len(discovered_agents),
                    "total_filtered": len(filtered_agents),
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

    def _discover_agents_from_genai_engine(
        self, data_plane_id: str, lookback_hours: int
    ) -> List[Dict[str, Any]]:
        """Call GenAI Engine API to discover agents."""
        try:
            self.logger.info(
                f"Calling GenAI Engine for agent discovery",
                extra={
                    "genai_engine_url": self.genai_engine_url,
                    "data_plane_id": data_plane_id,
                    "lookback_hours": lookback_hours,
                },
            )

            # Configure OpenAPI client
            config = Configuration(
                host=self.genai_engine_url,
                access_token=self.genai_engine_api_key,
            )

            # Call GenAI Engine discover agents endpoint
            with ApiClient(config) as api_client:
                api = AgentDiscoveryApi(api_client)
                request = DiscoverAgentsRequest(
                    data_plane_id=data_plane_id,
                    lookback_hours=lookback_hours,
                )

                response = api.discover_agents_api_v1_discover_agents_post(request)

                # Convert response agents to dict format
                agents = []
                for agent in response.agents:
                    self.logger.info(f"Agent: {agent.name}, creation_source: {agent.creation_source}")
                    agent_dict = agent.model_dump(exclude_none=False)
                    agents.append(agent_dict)

                self.logger.info(f"Received {len(agents)} agent(s) from GenAI Engine")

                return agents

        except Exception as e:
            self.logger.error(
                f"Failed to discover agents from GenAI Engine: {str(e)}",
                extra={"error": str(e)},
                exc_info=True,
            )
            raise

    def _filter_against_existing_models(
        self,
        agents: List[Dict[str, Any]],
        workspace_id: str,
        data_plane_id: str,
        project_id: str | None,
    ) -> List[Dict[str, Any]]:
        """Filter discovered agents against existing Models.

        Args:
            agents: List of discovered agents to filter
            workspace_id: Workspace ID (for logging)
            data_plane_id: Data plane ID to filter models by
            project_id: Optional project ID for "Registered Applications" project.
                       If None, no filtering is performed (all agents returned).

        Returns:
            List of agents that don't match existing Models.
        """
        # If no project_id provided, skip filtering
        if not project_id:
            self.logger.info(
                f"No project_id provided, skipping Model filtering for workspace {workspace_id}",
                extra={"workspace_id": workspace_id, "data_plane_id": data_plane_id},
            )
            return agents

        try:
            self.logger.info(
                f"Fetching existing Models for project {project_id}",
                extra={
                    "workspace_id": workspace_id,
                    "project_id": project_id,
                    "data_plane_id": data_plane_id,
                },
            )

            # Query Models for this project and data plane
            models = self.models_client.get_models(
                project_id=project_id,
            )

            # Filter to only models for this data plane
            models = [m for m in models if str(m.data_plane_id) == data_plane_id]

            self.logger.info(
                f"Found {len(models)} existing Model(s) for data plane",
                extra={"num_models": len(models)},
            )

            if not models:
                # No existing models, all agents are new
                return agents

            # Filter agents
            filtered_agents = []
            for agent in agents:
                if not self._matches_existing_model(agent, models):
                    filtered_agents.append(agent)
                else:
                    self.logger.debug(
                        f"Agent {agent['name']} matches existing Model, skipping",
                        extra={"agent_name": agent["name"]},
                    )

            return filtered_agents

        except Exception as e:
            self.logger.error(
                f"Failed to filter agents against Models: {str(e)}",
                extra={"error": str(e)},
                exc_info=True,
            )
            # On error, return all agents (better to have duplicates than miss new agents)
            return agents

    def _matches_existing_model(self, agent: Dict[str, Any], models: List[Any]) -> bool:
        """Check if an agent matches any existing Model.

        Matching criteria:
        1. Same data_plane_id
        2. Same name
        3. Exact match on tools and sub_agents
        """
        agent_tools = set(t["name"] for t in agent.get("tools", []))
        agent_sub_agents = set(s["name"] for s in agent.get("sub_agents", []))

        for model in models:
            # Must be same data plane
            if agent["data_plane_id"] != str(model.data_plane_id):
                continue

            # Name match + tools/sub_agents match
            if agent["name"] == model.name:
                model_tools = set(t.name for t in model.tools)
                model_sub_agents = set(s.name for s in model.sub_agents)

                # Exact match on tools and sub_agents
                if agent_tools == model_tools and agent_sub_agents == model_sub_agents:
                    return True

        return False

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

            # Create UnregisteredAgent objects
            agent_objects = [UnregisteredAgent(**agent) for agent in agents_payload]

            self.logger.info(f"Publishing {len(agent_objects)} agents to App Plane")

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
