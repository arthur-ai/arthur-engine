"""
Instrumented API client wrapper for Arthur platform.

This module provides the InstrumentedArthurClient class which wraps the generated
OpenAPI client and adds custom instrumentation for specific endpoints.
"""

import json
from typing import Optional, Any, TYPE_CHECKING
from uuid import UUID

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from ._generated.client import AuthenticatedClient
from ._generated.api.prompts import (
    render_saved_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_renders_post as render_prompt_module
)
from ._generated.api.tasks import (
    search_tasks_api_v2_tasks_search_post as search_tasks_module,
    create_task_api_v2_tasks_post as create_task_module
)
from ._generated.models.saved_prompt_rendering_request import SavedPromptRenderingRequest
from ._generated.models.variable_rendering_request import VariableRenderingRequest
from ._generated.models.variable_template_value import VariableTemplateValue
from ._generated.models.search_tasks_request import SearchTasksRequest
from ._generated.models.new_task_request import NewTaskRequest
from ._generated.types import UNSET, Unset

if TYPE_CHECKING:
    from ._generated import models


class PromptsAPI:
    """
    Instrumented API for prompt-related endpoints.

    This class wraps the generated prompt API methods and adds automatic
    span creation for specific methods like render_saved_agentic_prompt.
    """

    def __init__(self, client: AuthenticatedClient, telemetry_enabled: bool = True):
        """
        Initialize the PromptsAPI.

        Args:
            client: The authenticated API client.
            telemetry_enabled: Whether telemetry/tracing is enabled.
        """
        self._client = client
        self._telemetry_enabled = telemetry_enabled

    def render_saved_agentic_prompt(
        self,
        task_id: UUID,
        prompt_name: str,
        prompt_version: str,
        variables: Optional[dict[str, Any]] = None,
    ) -> Any:
        """
        Render a saved agentic prompt with template variables.

        This method automatically creates a span for prompt templating when
        telemetry is enabled, following OpenInference semantic conventions.

        Args:
            task_id: The UUID of the Arthur task.
            prompt_name: The name of the prompt to render.
            prompt_version: The version of the prompt ('latest', version number, tag, or datetime).
            variables: Dictionary of template variables to render in the prompt.

        Returns:
            The rendered prompt object (AgenticPrompt).

        Raises:
            httpx.HTTPStatusError: If the API returns an error status code.
            httpx.TimeoutException: If the request times out.

        Example:
            >>> client = ArthurClient(...)
            >>> prompt = client.client.prompts.render_saved_agentic_prompt(
            ...     task_id=UUID("..."),
            ...     prompt_name="email_template",
            ...     prompt_version="latest",
            ...     variables={"customer_name": "Alice", "order_id": "12345"}
            ... )
        """
        # Prepare request body
        # Convert dict variables to list of VariableTemplateValue objects
        variable_list = [
            VariableTemplateValue(name=k, value=str(v))
            for k, v in (variables or {}).items()
        ]

        variable_rendering = VariableRenderingRequest(
            variables=variable_list if variable_list else None
        )

        body = SavedPromptRenderingRequest(
            completion_request=variable_rendering
        )

        # If telemetry is disabled, call the API directly without instrumentation
        if not self._telemetry_enabled:
            return render_prompt_module.sync_detailed(
                task_id=task_id,
                prompt_name=prompt_name,
                prompt_version=prompt_version,
                client=self._client,
                body=body
            )

        # Create span for prompt templating
        tracer = trace.get_tracer(__name__)

        with tracer.start_as_current_span(
            f"template prompt: {prompt_name}",
            kind=trace.SpanKind.CLIENT
        ) as span:
            try:
                # Set input attributes
                input_data = {
                    "prompt_name": prompt_name,
                    "prompt_version": prompt_version,
                    "task_id": str(task_id),
                    "variables": variables or {}
                }
                span.set_attribute("input", json.dumps(input_data))

                # Set metadata
                metadata = {
                    "type": "prompt_templating",
                    "source": "arthur"
                }
                span.set_attribute("metadata", json.dumps(metadata))

                # Set additional Arthur-specific attributes
                span.set_attribute("arthur.prompt.name", prompt_name)
                span.set_attribute("arthur.prompt.version", prompt_version)
                span.set_attribute("arthur.task.id", str(task_id))

                # Call the underlying generated API method
                response = render_prompt_module.sync_detailed(
                    task_id=task_id,
                    prompt_name=prompt_name,
                    prompt_version=prompt_version,
                    client=self._client,
                    body=body
                )

                # Check if the response was successful
                if response.status_code == 200 and response.parsed:
                    # Set output attribute with rendered messages
                    # Note: The response may not have a .parsed attribute if generation had warnings
                    # In that case, we'll use the raw content
                    try:
                        output_data = response.content.decode('utf-8') if response.content else "{}"
                        span.set_attribute("output", output_data)
                    except Exception:
                        # If we can't decode the output, skip it
                        pass

                    span.set_status(Status(StatusCode.OK))
                else:
                    # Set error status if request failed
                    span.set_status(
                        Status(StatusCode.ERROR, f"HTTP {response.status_code}")
                    )

                return response

            except Exception as e:
                # Record exception in span
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise


class TasksAPI:
    """
    Instrumented API for task-related endpoints.

    This class wraps the generated task API methods and provides
    high-level convenience methods like get_or_create_task.
    """

    def __init__(self, client: AuthenticatedClient):
        """
        Initialize the TasksAPI.

        Args:
            client: The authenticated API client.
        """
        self._client = client

    def get_or_create_task(
        self,
        task_name: str,
        is_agentic: bool = True
    ) -> str:
        """
        Get a task ID by name, or create a new task if it doesn't exist.

        This method first searches for tasks with the given name. If found,
        it returns the ID of the first matching task. If not found, it creates
        a new task with the given name and returns its ID.

        Args:
            task_name: The name of the task to find or create.
            is_agentic: Whether the task is agentic (only used when creating).
                       Defaults to True.

        Returns:
            The task ID (UUID string) of the found or newly created task.

        Raises:
            httpx.HTTPStatusError: If the API returns an error status code.
            httpx.TimeoutException: If the request times out.
            RuntimeError: If task creation/retrieval fails unexpectedly.

        Example:
            >>> client = ArthurClient(api_key="...")
            >>> task_id = client.client.tasks.get_or_create_task(
            ...     task_name="my-timezone-agent",
            ...     is_agentic=True
            ... )
            >>> print(f"Using task: {task_id}")
        """
        # Search for existing tasks with this name
        search_request = SearchTasksRequest(
            task_name=task_name,
            is_agentic=is_agentic
        )

        search_response = search_tasks_module.sync_detailed(
            client=self._client,
            body=search_request,
            page_size=1
        )

        # Check if we found an existing task
        if search_response.status_code == 200 and search_response.parsed:
            tasks = search_response.parsed.tasks
            if tasks and len(tasks) > 0:
                # Return the ID of the first matching task
                return tasks[0].id

        # No existing task found, create a new one
        create_request = NewTaskRequest(
            name=task_name,
            is_agentic=is_agentic
        )

        create_response = create_task_module.sync_detailed(
            client=self._client,
            body=create_request
        )

        if create_response.status_code == 200 and create_response.parsed:
            return create_response.parsed.id
        else:
            raise RuntimeError(
                f"Failed to create task '{task_name}'. "
                f"Status: {create_response.status_code}, "
                f"Response: {create_response.content}"
            )


class InstrumentedArthurClient:
    """
    Instrumented wrapper around the generated Arthur API client.

    This class provides access to all generated API endpoints while adding
    custom instrumentation for specific methods that require span creation.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://app.arthur.ai",
        telemetry_enabled: bool = True,
        **kwargs
    ):
        """
        Initialize the instrumented Arthur API client.

        Args:
            api_key: Arthur API key for authentication.
            base_url: Base URL for the Arthur API.
            telemetry_enabled: Whether to enable telemetry/tracing for instrumented methods.
            **kwargs: Additional arguments passed to the underlying httpx client.
        """
        # Initialize the generated authenticated client
        self._base_client = AuthenticatedClient(
            base_url=base_url,
            token=api_key,
            **kwargs
        )
        self._telemetry_enabled = telemetry_enabled

        # Initialize instrumented API wrappers
        self.prompts = PromptsAPI(self._base_client, telemetry_enabled)
        self.tasks = TasksAPI(self._base_client)

    @property
    def base_client(self) -> AuthenticatedClient:
        """Access the underlying generated client for direct API calls."""
        return self._base_client

    def shutdown(self) -> None:
        """Shutdown the HTTP client and clean up resources."""
        self._base_client.get_httpx_client().close()
