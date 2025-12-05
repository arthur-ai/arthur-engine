import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal
from uuid import UUID

from arthur_client.api_bindings import ApiClient, DataPlanesV1Api, TasksV1Api
from arthur_client.auth import (
    ArthurClientCredentialsAPISession,
    ArthurOAuthSessionAPIConfiguration,
    ArthurOIDCMetadata,
)
from genai_client import SpansApi, TasksApi
from genai_client.models import SearchTasksRequest
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


class FetchUnregisteredAgentsJobExecutor:
    def __init__(
        self,
        data_planes_client: DataPlanesV1Api,
        tasks_client: TasksV1Api,
        logger: logging.Logger,
    ) -> None:
        self.data_planes_client = data_planes_client
        self.tasks_client = tasks_client
        self.logger = logger

    def execute(self, job_spec: FetchUnregisteredAgentsJobSpec) -> None:
        """Execute the fetch unregistered agents job."""
        self.logger.info(
            f"Fetching unregistered agents for data plane {job_spec.data_plane_id}"
        )

        # Get the data plane to determine infrastructure
        data_plane = self.data_planes_client.get_data_plane(
            data_plane_id=str(job_spec.data_plane_id)
        )

        # Create engine internal connector to call genai-engine APIs
        # Note: This assumes the ml-engine has access to genai-engine
        # We'll need to configure this properly
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
            unregistered_spans, all_tasks, data_plane.infrastructure.value
        )

        # Cache the results via API
        self._cache_results(job_spec.data_plane_id, unregistered_agents_data)

        self.logger.info(
            f"Successfully cached unregistered agents for data plane {job_spec.data_plane_id}"
        )

    def _fetch_unregistered_spans(self, connector: EngineInternalConnector) -> List[Dict[str, Any]]:
        """Fetch unregistered root spans from genai-engine."""
        try:
            # Call the unregistered spans endpoint
            # The endpoint is /api/v1/traces/spans/unregistered
            # We need to use the spans client from the connector
            response = connector._spans_client.get_unregistered_root_spans(
                page=0,
                page_size=1000,  # Get all unregistered spans
            )
            
            # Convert to list of dicts
            unregistered_spans = []
            for group in response.groups:
                unregistered_spans.append({
                    "span_name": group.span_name,
                    "count": group.count,
                })
            
            return unregistered_spans
        except Exception as e:
            self.logger.error(f"Failed to fetch unregistered spans: {e}")
            return []

    def _fetch_all_tasks(self, connector: EngineInternalConnector) -> List[Dict[str, Any]]:
        """Fetch all tasks from genai-engine."""
        try:
            # Call the tasks search endpoint
            # The endpoint is /api/v2/tasks/search
            search_request = SearchTasksRequest()
            response = connector._tasks_client.search_tasks(
                search_tasks_request=search_request,
                page=0,
                page_size=1000,  # Get all tasks
            )
            
            # Convert to list of dicts
            tasks = []
            for task in response.tasks:
                tasks.append({
                    "task_id": task.id,
                    "task_name": task.name,
                })
            
            return tasks
        except Exception as e:
            self.logger.error(f"Failed to fetch tasks: {e}")
            return []

    def _format_unregistered_agents(
        self,
        unregistered_spans: List[Dict[str, Any]],
        all_tasks: List[Dict[str, Any]],
        infrastructure: str,
    ) -> List[Dict[str, Any]]:
        """Format unregistered agents data for caching."""
        # Create a set of task IDs for quick lookup
        task_ids = {task["task_id"] for task in all_tasks if task.get("task_id")}
        
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
                "infrastructure": infrastructure,
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
                "num_spans": 0,  # We don't have span count for tasks
                "infrastructure": infrastructure,
            }
            agents.append(agent_data)
        
        return agents

    def _cache_results(
        self, data_plane_id: UUID, unregistered_agents_data: List[Dict[str, Any]]
    ) -> None:
        """Cache the results via the app_plane API."""
        try:
            # Create API client for app_plane
            ssl_verify = Config.get_bool("KEYCLOAK_SSL_VERIFY", True)
            sess = ArthurClientCredentialsAPISession(
                client_id=Config.settings.ARTHUR_CLIENT_ID,
                client_secret=Config.settings.ARTHUR_CLIENT_SECRET,
                metadata=ArthurOIDCMetadata(
                    arthur_host=Config.settings.ARTHUR_API_HOST,
                    verify_ssl=ssl_verify,
                ),
                verify=ssl_verify,
            )
            client = ApiClient(
                configuration=ArthurOAuthSessionAPIConfiguration(
                    session=sess,
                    verify_ssl=ssl_verify,
                )
            )
            
            # We need to get the workspace_id from the data plane
            data_plane = self.data_planes_client.get_data_plane(
                data_plane_id=str(data_plane_id)
            )
            workspace_id = data_plane.workspace_id
            
            # Call the cache endpoint using requests
            import requests
            
            cache_url = f"{Config.settings.ARTHUR_API_HOST}/v1/workspaces/{workspace_id}/unregistered_agents/cache/{data_plane_id}"
            
            # Get auth token from session
            token = sess.get_access_token()
            
            response = requests.put(
                cache_url,
                json={"unregistered_agents_data": unregistered_agents_data},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                verify=ssl_verify,
            )
            response.raise_for_status()
            
        except Exception as e:
            self.logger.error(f"Failed to cache unregistered agents: {e}")
            raise

