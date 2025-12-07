import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal
from uuid import UUID

import requests
from arthur_client.auth import ArthurClientCredentialsAPISession
from pydantic import BaseModel, Field

from config import Config
from connectors.shield_connector import EngineInternalConnector

logger = logging.getLogger(__name__)


class FetchUnregisteredAgentsJobSpec(BaseModel):
    """Job spec for fetching unregistered agents from genai-engine."""
    job_type: Literal["fetch_unregistered_agents"] = "fetch_unregistered_agents"
    data_plane_id: UUID = Field(
        description="The id of the data plane to fetch unregistered agents from."
    )
    workspace_id: UUID = Field(
        description="The id of the workspace the data plane belongs to."
    )


class FetchUnregisteredAgentsJobExecutor:
    def __init__(
        self,
        session: ArthurClientCredentialsAPISession,
        logger: logging.Logger,
    ) -> None:
        self.session = session
        self.logger = logger

    def execute(self, job_spec: FetchUnregisteredAgentsJobSpec) -> None:
        """Execute the fetch unregistered agents job."""
        self.logger.info(
            f"Fetching unregistered agents for data plane {job_spec.data_plane_id}"
        )

        # Create engine internal connector to call genai-engine APIs
        try:
            connector = EngineInternalConnector(
                connector_config=None,  # Not needed for internal connector
                logger=self.logger,
            )
        except Exception as e:
            self.logger.error(
                f"Failed to create engine internal connector: {e}"
            )
            raise

        # Fetch unregistered root spans
        unregistered_spans = self._fetch_unregistered_spans(connector)
        
        # Fetch all tasks
        all_tasks = self._fetch_all_tasks(connector)

        # Combine and format the data
        unregistered_agents_data = self._format_unregistered_agents(
            unregistered_spans, all_tasks
        )

        # Cache the results via API
        self._cache_results(
            job_spec.workspace_id,
            job_spec.data_plane_id,
            unregistered_agents_data,
        )

        self.logger.info(
            f"Successfully cached unregistered agents for data plane {job_spec.data_plane_id}"
        )

    def _fetch_unregistered_spans(self, connector: EngineInternalConnector) -> List[Dict[str, Any]]:
        """Fetch unregistered root spans from genai-engine."""
        try:
            # Call the unregistered spans endpoint via the spans client
            # Method name from generated client: get_unregistered_root_spans_api_v1_traces_spans_unregistered_get
            response = connector._spans_client.get_unregistered_root_spans_api_v1_traces_spans_unregistered_get(
                page=0,
                page_size=1000,
            )
            
            # Convert to list of dicts
            unregistered_spans = []
            for group in response.groups:
                unregistered_spans.append({
                    "span_name": group.span_name,
                    "count": group.count,
                })
            
            self.logger.info(f"Fetched {len(unregistered_spans)} unregistered span groups")
            return unregistered_spans
        except Exception as e:
            self.logger.error(f"Failed to fetch unregistered spans: {e}")
            return []

    def _fetch_all_tasks(self, connector: EngineInternalConnector) -> List[Dict[str, Any]]:
        """Fetch all tasks from genai-engine with their span counts."""
        try:
            # Call the tasks list endpoint via the tasks client
            # Method returns List[TaskResponse] directly
            task_list = connector._tasks_client.get_all_tasks_api_v2_tasks_get()
            
            # Convert to list of dicts - task_list is already a list
            tasks = []
            for task in task_list:
                task_id = str(task.id)
                # Get span count for this task
                span_count = self._get_span_count_for_task(connector, task_id)
                tasks.append({
                    "task_id": task_id,
                    "task_name": task.name,
                    "span_count": span_count,
                })
            
            self.logger.info(f"Fetched {len(tasks)} tasks with span counts")
            return tasks
        except Exception as e:
            self.logger.error(f"Failed to fetch tasks: {e}")
            return []

    def _get_span_count_for_task(self, connector: EngineInternalConnector, task_id: str) -> int:
        """Get the span count for a specific task."""
        try:
            # Query spans for this task with page_size=1 to just get the count
            response = connector._spans_client.list_spans_metadata_api_v1_traces_spans_get(
                task_ids=[task_id],
                page=0,
                page_size=1,  # We only need the count, not the actual spans
            )
            return response.count
        except Exception as e:
            self.logger.warning(f"Failed to get span count for task {task_id}: {e}")
            return 0

    def _format_unregistered_agents(
        self,
        unregistered_spans: List[Dict[str, Any]],
        all_tasks: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Format unregistered agents data for caching."""
        # Format unregistered spans as agents
        agents = []
        for span in unregistered_spans:
            # For unregistered spans, we don't have a task_id
            agent_data = {
                "creation_source": {
                    "task_id": None,
                    "top_level_span_name": span["span_name"],
                },
                "first_detected": datetime.now(timezone.utc).isoformat(),
                "num_spans": span["count"],
            }
            agents.append(agent_data)
        
        # Format tasks as agents (tasks that might not be linked to applications)
        # Note: We'll filter out registered ones in the operator
        for task in all_tasks:
            agent_data = {
                "creation_source": {
                    "task_id": task["task_id"],
                    "top_level_span_name": None,
                },
                "first_detected": datetime.now(timezone.utc).isoformat(),
                "num_spans": task.get("span_count", 0),
            }
            agents.append(agent_data)
        
        return agents

    def _cache_results(
        self,
        workspace_id: UUID,
        data_plane_id: UUID,
        unregistered_agents_data: List[Dict[str, Any]],
    ) -> None:
        """Cache the results via the app_plane API."""
        try:
            # Call the cache endpoint
            cache_url = f"{Config.settings.ARTHUR_API_HOST}/api/v1/workspaces/{workspace_id}/unregistered_agents/cache/{data_plane_id}"
            
            self.logger.info(f"Caching {len(unregistered_agents_data)} unregistered agents to {cache_url}")
            
            # Get the access token from the session
            token = self.session.token()
            ssl_verify = Config.get_bool("KEYCLOAK_SSL_VERIFY", True)
            
            # Use requests with the auth token
            # OAuth2Token is a dict subclass, access via ["access_token"]
            response = requests.put(
                cache_url,
                json={"unregistered_agents_data": unregistered_agents_data},
                headers={
                    "Authorization": f"Bearer {token['access_token']}",
                    "Content-Type": "application/json",
                },
                verify=ssl_verify,
            )
            
            if response.status_code != 204:
                self.logger.error(f"Cache request failed with status {response.status_code}: {response.text}")
            response.raise_for_status()
            
            self.logger.info(f"Successfully cached unregistered agents data")
            
        except Exception as e:
            self.logger.error(f"Failed to cache unregistered agents: {e}")
            raise

