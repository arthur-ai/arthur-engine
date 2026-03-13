"""
Arthur GenAI Engine API client.

Wraps the auto-generated ``arthur_genai_client`` (produced by
``scripts/generate_openapi_client.sh generate python``).

Run ``scripts/generate_openapi_client.sh generate python`` before using this module.
"""

import json
import logging
from typing import Any, Dict, Optional

from arthur_genai_client.api.prompts_api import PromptsApi
from arthur_genai_client.api.tasks_api import TasksApi
from arthur_genai_client.api_client import ApiClient
from arthur_genai_client.configuration import Configuration
from arthur_genai_client.exceptions import (
    ApiException,
)
from arthur_genai_client.models.saved_prompt_rendering_request import (
    SavedPromptRenderingRequest,
)
from arthur_genai_client.models.search_tasks_request import (
    SearchTasksRequest,
)
from arthur_genai_client.models.variable_rendering_request import (
    VariableRenderingRequest,
)
from arthur_genai_client.models.variable_template_value import (
    VariableTemplateValue,
)

logger = logging.getLogger(__name__)


class ArthurAPIError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {detail}")


def _api_exception_to_arthur(exc: ApiException) -> ArthurAPIError:
    try:
        detail = json.loads(exc.body or "{}").get("detail", exc.reason)
    except Exception:
        detail = exc.reason or str(exc)
    return ArthurAPIError(exc.status, str(detail))


class ArthurAPIClient:
    """
    Wraps Arthur GenAI Engine REST endpoints used by the SDK.

    Uses the auto-generated ``arthur_genai_client`` for all calls.
    All methods raise ``ArthurAPIError`` on non-2xx responses.
    """

    def __init__(self, base_url: str, api_key: Optional[str]) -> None:
        config = Configuration(
            host=base_url.rstrip("/"),
            access_token=api_key,
        )
        self._api_client = ApiClient(configuration=config)
        self._prompts_api = PromptsApi(api_client=self._api_client)
        self._tasks_api = TasksApi(api_client=self._api_client)

    def get_prompt_by_version(self, task_id: str, name: str, version: str) -> Dict[str, Any]:
        try:
            response = self._prompts_api.get_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_get_with_http_info(
                task_id=task_id,
                prompt_name=name,
                prompt_version=version,
            )
        except ApiException as exc:
            raise _api_exception_to_arthur(exc) from exc
        return json.loads(response.raw_data)

    def get_prompt_by_tag(self, task_id: str, name: str, tag: str) -> Dict[str, Any]:
        try:
            response = self._prompts_api.get_agentic_prompt_by_tag_api_v1_tasks_task_id_prompts_prompt_name_versions_tags_tag_get_with_http_info(
                task_id=task_id,
                prompt_name=name,
                tag=tag,
            )
        except ApiException as exc:
            raise _api_exception_to_arthur(exc) from exc
        return json.loads(response.raw_data)

    def render_prompt(
        self,
        task_id: str,
        name: str,
        version: str,
        variables: Dict[str, str],
        strict: bool = False,
    ) -> Dict[str, Any]:
        """
        POST to the renders endpoint, substituting ``variables`` into the
        prompt template.  ``version`` may be a version number, ``'latest'``,
        or a tag name — the engine accepts all three in the path.
        """
        rendering_request = SavedPromptRenderingRequest(
            completion_request=VariableRenderingRequest(
                variables=[VariableTemplateValue(name=k, value=v) for k, v in variables.items()],
                strict=strict,
            )
        )
        try:
            response = self._prompts_api.render_saved_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_renders_post_with_http_info(
                task_id=task_id,
                prompt_name=name,
                prompt_version=version,
                saved_prompt_rendering_request=rendering_request,
            )
        except ApiException as exc:
            raise _api_exception_to_arthur(exc) from exc
        return json.loads(response.raw_data)

    def resolve_task_id(self, task_name: str) -> str:
        """
        Finds the most-recently-created task whose name exactly matches
        ``task_name`` and returns its id.

        The search API uses substring matching and returns results sorted by
        ``created_at`` descending (newest first), so this method paginates
        through all matching pages until an exact match is found.

        Raises ``ValueError`` if no task with an exact name match is found.
        """
        page_size = 50
        page = 0
        while True:
            try:
                result = self._tasks_api.search_tasks_api_v2_tasks_search_post(
                    search_tasks_request=SearchTasksRequest(task_name=task_name),
                    page_size=page_size,
                    page=page,
                )
            except ApiException as exc:
                raise _api_exception_to_arthur(exc) from exc
            for task in result.tasks:
                if task.name == task_name:
                    return str(task.id)
            if page_size * (page + 1) >= result.count:
                break
            page += 1
        raise ValueError(
            f"No task with an exact name match for '{task_name}' was found. "
            f"Found {result.count} task(s) whose name contains '{task_name}' as a substring."
        )

    def close(self) -> None:
        self._api_client.rest_client.pool_manager.clear()
