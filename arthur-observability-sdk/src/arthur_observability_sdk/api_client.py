"""
Instrumented API client wrapper for Arthur platform.

This module provides the InstrumentedArthurClient class which wraps the generated
OpenAPI client and adds custom instrumentation for specific endpoints.
"""

import json
from typing import Optional, Any
from uuid import UUID

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from arthur_observability_sdk._generated.arthur_observability_sdk._generated.api_client import ApiClient
from arthur_observability_sdk._generated.arthur_observability_sdk._generated.configuration import Configuration
from arthur_observability_sdk._generated.arthur_observability_sdk._generated.api.prompts_api import PromptsApi
from arthur_observability_sdk._generated.arthur_observability_sdk._generated.api.tasks_api import TasksApi
from arthur_observability_sdk._generated.arthur_observability_sdk._generated.models.saved_prompt_rendering_request import SavedPromptRenderingRequest
from arthur_observability_sdk._generated.arthur_observability_sdk._generated.models.variable_rendering_request import VariableRenderingRequest
from arthur_observability_sdk._generated.arthur_observability_sdk._generated.models.variable_template_value import VariableTemplateValue
from arthur_observability_sdk._generated.arthur_observability_sdk._generated.models.search_tasks_request import SearchTasksRequest
from arthur_observability_sdk._generated.arthur_observability_sdk._generated.models.new_task_request import NewTaskRequest


class InstrumentedPromptsAPI:
    """
    Instrumented API for prompt-related endpoints.

    This class wraps the generated prompt API methods and adds automatic
    span creation for specific methods like render_saved_agentic_prompt.
    """

    def __init__(self, prompts_api: PromptsApi, telemetry_enabled: bool = True):
        """
        Initialize the InstrumentedPromptsAPI.

        Args:
            prompts_api: The generated PromptsApi instance.
            telemetry_enabled: Whether telemetry/tracing is enabled.
        """
        self._api = prompts_api
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
            ApiException: If the API returns an error status code.

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
            return self._api.render_saved_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_renders_post(
                task_id=str(task_id),
                prompt_name=prompt_name,
                prompt_version=prompt_version,
                saved_prompt_rendering_request=body
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
                response = self._api.render_saved_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_renders_post(
                    task_id=str(task_id),
                    prompt_name=prompt_name,
                    prompt_version=prompt_version,
                    saved_prompt_rendering_request=body
                )

                # Set output attribute with rendered response
                try:
                    output_data = response.to_json() if hasattr(response, 'to_json') else str(response)
                    span.set_attribute("output", output_data)
                except Exception:
                    # If we can't serialize the output, skip it
                    pass

                span.set_status(Status(StatusCode.OK))
                return response

            except Exception as e:
                # Record exception in span
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise


class InstrumentedTasksAPI:
    """
    Instrumented API for task-related endpoints.

    This class wraps the generated task API methods and provides
    high-level convenience methods like get_or_create_task.
    """

    def __init__(self, tasks_api: TasksApi):
        """
        Initialize the InstrumentedTasksAPI.

        Args:
            tasks_api: The generated TasksApi instance.
        """
        self._api = tasks_api

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
            ApiException: If the API returns an error status code.
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

        try:
            search_response = self._api.search_tasks_api_v2_tasks_search_post(
                search_tasks_request=search_request,
                page_size=1
            )

            # Check if we found an existing task
            if search_response and hasattr(search_response, 'tasks') and search_response.tasks:
                # Return the ID of the first matching task
                return search_response.tasks[0].id
        except Exception:
            # If search fails, we'll try to create instead
            pass

        # No existing task found, create a new one
        create_request = NewTaskRequest(
            name=task_name,
            is_agentic=is_agentic
        )

        create_response = self._api.create_task_api_v2_tasks_post(
            new_task_request=create_request
        )

        if create_response and hasattr(create_response, 'id'):
            return create_response.id
        else:
            raise RuntimeError(
                f"Failed to create task '{task_name}'. "
                f"Response: {create_response}"
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
            **kwargs: Additional arguments passed to the underlying HTTP client.
        """
        # Create configuration
        config = Configuration(host=base_url)
        config.access_token = api_key

        # Initialize the API client
        self._api_client = ApiClient(configuration=config)
        self._telemetry_enabled = telemetry_enabled

        # Initialize generated API classes
        self._prompts_api = PromptsApi(api_client=self._api_client)
        self._tasks_api = TasksApi(api_client=self._api_client)

        # Initialize instrumented API wrappers
        self.prompts = InstrumentedPromptsAPI(self._prompts_api, telemetry_enabled)
        self.tasks = InstrumentedTasksAPI(self._tasks_api)

    @property
    def api_client(self) -> ApiClient:
        """Access the underlying generated API client for direct API calls."""
        return self._api_client

    def shutdown(self) -> None:
        """Shutdown the HTTP client and clean up resources."""
        # The openapi-generator client doesn't have an explicit close method
        # but we can access the rest client if needed
        pass
