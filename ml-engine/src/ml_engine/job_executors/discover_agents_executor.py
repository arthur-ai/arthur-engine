"""
Executor for discovering agents from GCP data planes.

This executor:
1. Calls GenAI Engine API to discover agents from infrastructure
2. Filters discovered agents against existing Models
3. Publishes filtered agents to the Arthur platform as UnregisteredAgents
4. Fetches enriched agent tasks from GenAI Engine and publishes to the Agents API
"""

import logging
from typing import Any, Dict, List

from arthur_client.api_bindings import Agent as ScopeAgent
from arthur_client.api_bindings import (
    AgentsV1Api,
    DiscoverAgentsJobSpec,
    Job,
    ModelsV1Api,
    PutAgents,
    PutUnregisteredAgents,
    UnregisteredAgent,
    UnregisteredAgentsV1Api,
)
from genai_client import (
    AgentDiscoveryApi,
    ApiClient,
    Configuration,
    DiscoverAgentsRequest,
    EnrichedTaskResponse,
    TasksApi,
)


class DiscoverAgentsExecutor:
    def __init__(
        self,
        unregistered_agents_client: UnregisteredAgentsV1Api,
        agents_client: AgentsV1Api,
        models_client: ModelsV1Api,
        logger: logging.Logger,
        genai_engine_url: str,
        genai_engine_api_key: str,
    ) -> None:
        self.unregistered_agents_client = unregistered_agents_client
        self.agents_client = agents_client
        self.models_client = models_client
        self.logger = logger
        self.genai_engine_url = genai_engine_url
        self.genai_engine_api_key = genai_engine_api_key

    # ------------------------------------------------------------------
    # Top-level orchestration
    # ------------------------------------------------------------------

    def execute(self, job: Job, job_spec: DiscoverAgentsJobSpec) -> None:
        """Execute agent discovery job.

        Orchestrates four phases:
        1. Discover agents via the GenAI Engine
        2. Filter discovered agents against existing Models
        3. Publish new agents to the UnregisteredAgents API
        4. Fetch enriched agent-tasks and sync to the Agents API
        """
        workspace_id = str(job_spec.workspace_id)
        data_plane_id = str(job_spec.data_plane_id)
        project_id = str(job_spec.project_id) if job_spec.project_id else None
        lookback_hours = job_spec.lookback_hours

        self.logger.info(
            f"Starting agent discovery for workspace {workspace_id}, "
            f"data plane {data_plane_id}, lookback {lookback_hours} hours",
            extra={
                "workspace_id": workspace_id,
                "data_plane_id": data_plane_id,
                "lookback_hours": lookback_hours,
            },
        )

        # Phases 1-3: discover, filter, publish unregistered agents.
        # Best-effort – failure is logged but does not prevent phase 4.
        try:
            discovered_agents = self._discover_agents_from_genai_engine(
                data_plane_id, lookback_hours
            )
            filtered_agents = self._filter_against_existing_models(
                discovered_agents, workspace_id, data_plane_id, project_id
            )
            self._publish_unregistered_agents(workspace_id, filtered_agents)
        except Exception as e:
            self.logger.error(
                f"Agent discovery failed for data plane {data_plane_id} (non-fatal): {e}",
                extra={"data_plane_id": data_plane_id, "error": str(e)},
                exc_info=True,
            )

        # Phase 4: fetch enriched tasks and sync to Agents API.
        # Best-effort – failure is logged but does not abort the job.
        try:
            enriched_tasks = self._fetch_enriched_agent_tasks()
            self._publish_to_agents_api(workspace_id, data_plane_id, enriched_tasks)
        except Exception as e:
            self.logger.error(
                f"Agents API sync failed for data plane {data_plane_id} (non-fatal): {e}",
                extra={"data_plane_id": data_plane_id, "error": str(e)},
                exc_info=True,
            )

        self.logger.info(
            f"Agent discovery completed for data plane {data_plane_id}",
            extra={"workspace_id": workspace_id, "data_plane_id": data_plane_id},
        )

    # ------------------------------------------------------------------
    # Phase 1 – Discover agents from GenAI Engine
    # ------------------------------------------------------------------

    def _discover_agents_from_genai_engine(
        self, data_plane_id: str, lookback_hours: int
    ) -> List[Dict[str, Any]]:
        """Call the GenAI Engine discovery endpoint and return raw agent dicts."""
        self.logger.info(
            "Calling GenAI Engine for agent discovery",
            extra={
                "genai_engine_url": self.genai_engine_url,
                "data_plane_id": data_plane_id,
                "lookback_hours": lookback_hours,
            },
        )

        config = Configuration(
            host=self.genai_engine_url,
            access_token=self.genai_engine_api_key,
        )

        with ApiClient(config) as api_client:
            api = AgentDiscoveryApi(api_client)
            request = DiscoverAgentsRequest(
                data_plane_id=data_plane_id,
                lookback_hours=lookback_hours,
            )
            response = api.discover_agents_api_v1_discover_agents_post(request)

        agents = [agent.model_dump(exclude_none=False) for agent in response.agents]

        self.logger.info(
            f"Discovered {len(agents)} agent(s) from GenAI Engine",
            extra={"num_discovered": len(agents)},
        )
        return agents

    # ------------------------------------------------------------------
    # Phase 2 – Filter against existing Models
    # ------------------------------------------------------------------

    def _filter_against_existing_models(
        self,
        agents: List[Dict[str, Any]],
        workspace_id: str,
        data_plane_id: str,
        project_id: str | None,
    ) -> List[Dict[str, Any]]:
        """Remove agents that already match a registered Model.

        Returns all agents unmodified when *project_id* is ``None`` or when
        the Model lookup fails (better to duplicate than to miss new agents).
        """
        if not agents:
            return agents

        if not project_id:
            self.logger.info(
                f"No project_id provided, skipping Model filtering for workspace {workspace_id}",
                extra={"workspace_id": workspace_id, "data_plane_id": data_plane_id},
            )
            return agents

        try:
            models = self.models_client.get_models(project_id=project_id)
            models = [m for m in models if str(m.data_plane_id) == data_plane_id]

            self.logger.info(
                f"Found {len(models)} existing Model(s) for data plane",
                extra={"num_models": len(models)},
            )

            if not models:
                return agents

            filtered = [
                a for a in agents if not self._matches_existing_model(a, models)
            ]

            self.logger.info(
                f"Filtered to {len(filtered)} new agent(s) "
                f"(from {len(agents)} discovered)",
                extra={"num_discovered": len(agents), "num_filtered": len(filtered)},
            )
            return filtered

        except Exception as e:
            self.logger.error(
                f"Failed to filter agents against Models: {e}",
                extra={"error": str(e)},
                exc_info=True,
            )
            return agents

    def _matches_existing_model(self, agent: Dict[str, Any], models: List[Any]) -> bool:
        """Return True if *agent* matches any existing Model by name, tools and sub-agents."""
        agent_tools = set(t["name"] for t in agent.get("tools", []))
        agent_sub_agents = set(s["name"] for s in agent.get("sub_agents", []))

        for model in models:
            if agent["data_plane_id"] != str(model.data_plane_id):
                continue
            if agent["name"] == model.name:
                model_tools = set(t.name for t in model.tools)
                model_sub_agents = set(s.name for s in model.sub_agents)
                if agent_tools == model_tools and agent_sub_agents == model_sub_agents:
                    return True
        return False

    # ------------------------------------------------------------------
    # Phase 3 – Publish to UnregisteredAgents API
    # ------------------------------------------------------------------

    def _publish_unregistered_agents(
        self, workspace_id: str, agents_payload: List[Dict[str, Any]]
    ) -> None:
        """Publish discovered agents to the UnregisteredAgents API."""
        if not agents_payload:
            self.logger.info("No new agents to publish to UnregisteredAgents API")
            return

        agent_objects = [UnregisteredAgent(**agent) for agent in agents_payload]
        put_request = PutUnregisteredAgents(unregistered_agents=agent_objects)

        self.unregistered_agents_client.put_unregistered_agents(
            workspace_id=workspace_id,
            put_unregistered_agents=put_request,
        )

        self.logger.info(
            f"Published {len(agent_objects)} agent(s) to UnregisteredAgents API",
            extra={"workspace_id": workspace_id, "num_published": len(agent_objects)},
        )

    # ------------------------------------------------------------------
    # Phase 4 – Fetch enriched tasks and publish to Agents API
    # ------------------------------------------------------------------

    def _fetch_enriched_agent_tasks(self) -> List[EnrichedTaskResponse]:
        """Fetch enriched agent tasks from the GenAI Engine agent-tasks endpoint."""
        config = Configuration(
            host=self.genai_engine_url,
            access_token=self.genai_engine_api_key,
        )

        with ApiClient(config) as api_client:
            api = TasksApi(api_client)
            enriched_tasks = api.get_agent_tasks_api_v2_agent_tasks_get()

        self.logger.info(
            f"Fetched {len(enriched_tasks)} enriched agent task(s) from GenAI Engine",
            extra={"num_tasks": len(enriched_tasks)},
        )
        return enriched_tasks

    def _publish_to_agents_api(
        self,
        workspace_id: str,
        data_plane_id: str,
        enriched_tasks: List[EnrichedTaskResponse],
    ) -> None:
        """Convert enriched tasks to Agent objects and upsert via the Agents API."""
        if not enriched_tasks:
            self.logger.info("No enriched tasks to publish to Agents API")
            return

        agent_objects = [
            self._convert_enriched_task_to_agent(task, data_plane_id)
            for task in enriched_tasks
        ]

        put_request = PutAgents(agents=agent_objects)
        response = self.agents_client.put_agents(
            workspace_id=workspace_id,
            put_agents=put_request,
        )

        self.logger.info(
            f"Published {len(response.agents)} agent(s) to Agents API",
            extra={"workspace_id": workspace_id, "num_upserted": len(response.agents)},
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _convert_enriched_task_to_agent(
        enriched_task: EnrichedTaskResponse,
        data_plane_id: str,
    ) -> ScopeAgent:
        """Convert a genai_client EnrichedTaskResponse to an arthur_client Agent.

        Bridges between the two auto-generated client libraries by converting
        via dict representation and remapping fields.
        """
        task_dict = enriched_task.to_dict()

        agent_dict = {
            "name": task_dict.get("name"),
            "task_id": task_dict.get("id"),
            "data_plane_id": data_plane_id,
            "creation_source": task_dict.get("creation_source"),
            "model_id": None,
            "num_spans": task_dict.get("num_spans") or 0,
            "is_autocreated": task_dict.get("is_autocreated", True),
            "rules": task_dict.get("rules") or [],
            "last_fetched": task_dict.get("last_fetched"),
            "tools": task_dict.get("tools") or [],
            "sub_agents": task_dict.get("sub_agents") or [],
            "llm_models": task_dict.get("models") or [],
            "data_sources": task_dict.get("data_sources") or [],
        }

        return ScopeAgent.from_dict(agent_dict)
