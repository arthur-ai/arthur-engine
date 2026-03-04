"""
Executor for discovering agents from GCP data planes.

This executor:
1. Triggers synchronous polling to fetch up-to-date trace data
2. Fetches enriched agent tasks from GenAI Engine and publishes to the Agents API
"""

import logging
from typing import List

from arthur_client.api_bindings import Agent as ScopeAgent
from arthur_client.api_bindings import (
    AgentsV1Api,
    DiscoverAgentsJobSpec,
    Job,
    PutAgents,
)
from genai_client import (
    AgentDiscoveryApi,
    ApiClient,
    Configuration,
    EnrichedTaskResponse,
    TasksApi,
)


class DiscoverAgentsExecutor:
    def __init__(
        self,
        agents_client: AgentsV1Api,
        logger: logging.Logger,
        genai_engine_url: str,
        genai_engine_api_key: str,
    ) -> None:
        self.agents_client = agents_client
        self.logger = logger
        self.genai_engine_url = genai_engine_url
        self.genai_engine_api_key = genai_engine_api_key

    def execute(self, job: Job, job_spec: DiscoverAgentsJobSpec) -> None:
        """Execute agent discovery job.

        Triggers synchronous polling then fetches enriched agent-tasks and
        syncs them to the Agents API.
        """
        workspace_id = str(job_spec.workspace_id)
        data_plane_id = str(job_spec.data_plane_id)

        self.logger.info(
            f"Starting agent discovery for workspace {workspace_id}, "
            f"data plane {data_plane_id}",
            extra={
                "workspace_id": workspace_id,
                "data_plane_id": data_plane_id,
            },
        )

        try:
            self._trigger_synchronous_polling()
            enriched_tasks = self._fetch_enriched_agent_tasks()
            self._publish_to_agents_api(workspace_id, data_plane_id, enriched_tasks)
        except Exception as e:
            self.logger.error(
                f"Agents API sync failed for data plane {data_plane_id}: {e}",
                extra={"data_plane_id": data_plane_id, "error": str(e)},
                exc_info=True,
            )
            raise

        self.logger.info(
            f"Agent discovery completed for data plane {data_plane_id}",
            extra={"workspace_id": workspace_id, "data_plane_id": data_plane_id},
        )

    def _trigger_synchronous_polling(self) -> None:
        """Trigger synchronous polling to ensure trace data is fetched before querying agent-tasks."""
        self.logger.info("Triggering synchronous agent polling")

        config = Configuration(
            host=self.genai_engine_url,
            access_token=self.genai_engine_api_key,
        )

        with ApiClient(config) as api_client:
            api = AgentDiscoveryApi(api_client)
            response = (
                api.execute_all_agent_polling_api_v1_agent_polling_execute_all_post(
                    wait_for_completion=True,
                    timeout=120,  # 2 minute timeout
                )
            )

        self.logger.info(
            f"Synchronous polling completed: discovered={response.discovered}, "
            f"traces_fetched={response.traces_fetched}",
            extra={
                "discovered": response.discovered,
                "traces_fetched": response.traces_fetched,
            },
        )

    def _fetch_enriched_agent_tasks(self) -> List[EnrichedTaskResponse]:
        """Fetch enriched agent tasks from the GenAI Engine agent-tasks endpoint."""
        config = Configuration(
            host=self.genai_engine_url,
            access_token=self.genai_engine_api_key,
        )

        with ApiClient(config) as api_client:
            api = TasksApi(api_client)
            enriched_tasks: List[EnrichedTaskResponse] = (
                api.get_agent_tasks_api_v2_agent_tasks_get()
            )

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
