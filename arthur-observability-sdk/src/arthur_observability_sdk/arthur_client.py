"""
Unified Arthur SDK client.

This module provides the ArthurClient class, which serves as the main entry point
for the Arthur Observability SDK. It integrates API bindings with telemetry/tracing.
"""

import os
from typing import Optional, Dict, Any

from .telemetry import TelemetryHandler
from .api_client import InstrumentedArthurClient


class ArthurClient:
    """
    Main client for Arthur Observability SDK.

    This client provides unified access to Arthur's API endpoints and telemetry/tracing
    capabilities. Initialize once and use throughout your application.

    Attributes:
        client: Access to Arthur API endpoints (e.g., client.prompts.render_saved_agentic_prompt(...))
        telemetry: Access to telemetry handler for advanced configuration
        task_id: The Arthur task ID

    Example:
        >>> from arthur_observability_sdk import ArthurClient
        >>>
        >>> arthur = ArthurClient(
        ...     task_id="550e8400-e29b-41d4-a716-446655440000",
        ...     api_key="your-api-key",
        ...     service_name="my-recommendation-service"
        ... )
        >>>
        >>> # Use API bindings
        >>> prompt = arthur.client.prompts.render_saved_agentic_prompt(
        ...     task_id=arthur.task_id,
        ...     prompt_name="email_template",
        ...     prompt_version="latest",
        ...     variables={"customer_name": "Alice"}
        ... )
        >>>
        >>> # Use context for session tracking
        >>> from arthur_observability_sdk import context
        >>> with context(session_id="session-123", user_id="user-456"):
        ...     # API calls here will include session/user in spans
        ...     pass
    """

    def __init__(
        self,
        task_id: Optional[str] = None,
        task_name: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        service_name: Optional[str] = None,
        enable_telemetry: bool = True,
        use_simple_processor: bool = False,
        resource_attributes: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize the Arthur client with API and telemetry configuration.

        You can specify either task_id or task_name. If task_name is provided,
        the client will automatically fetch or create the task.

        Args:
            task_id: Arthur task ID. Falls back to ARTHUR_TASK_ID env var.
                    If not provided, task_name must be specified.
            task_name: Arthur task name. If provided, will automatically fetch
                      or create a task with this name. Falls back to ARTHUR_TASK_NAME env var.
            api_key: Arthur API key. Falls back to ARTHUR_API_KEY env var.
            base_url: Arthur base URL. Falls back to ARTHUR_BASE_URL env var.
                      Defaults to "https://app.arthur.ai" if not provided.
            service_name: Service name for traces. If not provided, automatically
                         derives the name from the calling script.
            enable_telemetry: Whether to enable OpenTelemetry tracing. Defaults to True.
            use_simple_processor: If True, uses SimpleSpanProcessor for immediate
                                 span export (useful for testing/debugging).
                                 If False (default), uses BatchSpanProcessor.
            resource_attributes: Additional resource attributes to include in traces.
            **kwargs: Additional configuration options passed to HTTP client.

        Raises:
            ValueError: If required parameters (task_id/task_name, api_key) are missing.

        Example (with task_id):
            >>> arthur = ArthurClient(
            ...     task_id="550e8400-e29b-41d4-a716-446655440000",
            ...     api_key="my-api-key",
            ...     base_url="https://app.arthur.ai",
            ...     service_name="my-service",
            ...     enable_telemetry=True
            ... )

        Example (with task_name - automatically creates/fetches task):
            >>> arthur = ArthurClient(
            ...     task_name="my-timezone-agent",
            ...     api_key="my-api-key",
            ...     base_url="https://app.arthur.ai",
            ...     service_name="my-service",
            ...     enable_telemetry=True
            ... )
        """
        # Get configuration from parameters or environment variables
        task_id = task_id or os.getenv("ARTHUR_TASK_ID")
        task_name = task_name or os.getenv("ARTHUR_TASK_NAME")
        api_key = api_key or os.getenv("ARTHUR_API_KEY")
        base_url = base_url or os.getenv("ARTHUR_BASE_URL", "https://app.arthur.ai")

        # Validate that we have either task_id or task_name
        if not task_id and not task_name:
            raise ValueError(
                "Either task_id or task_name is required. "
                "Provide as a parameter or set ARTHUR_TASK_ID/ARTHUR_TASK_NAME environment variable."
            )
        if not api_key:
            raise ValueError(
                "api_key is required. Provide it as a parameter or set ARTHUR_API_KEY environment variable."
            )

        self._enable_telemetry = enable_telemetry
        self._base_url = base_url

        # Initialize API client first (needed for task_name resolution)
        # Note: We initialize without telemetry first to avoid circular dependency
        self.client = InstrumentedArthurClient(
            api_key=api_key,
            base_url=base_url,
            telemetry_enabled=False,  # Temporarily disabled
            **kwargs
        )

        # Resolve task_id from task_name if needed
        if task_name and not task_id:
            print(f"🔍 Resolving task ID for task name: '{task_name}'...")
            task_id = self.client.tasks.get_or_create_task(
                task_name=task_name,
                is_agentic=True
            )
            print(f"✅ Using task ID: {task_id}")

        # Store the resolved task_id
        self.task_id = task_id

        # Now initialize telemetry with the resolved task_id
        if enable_telemetry:
            TelemetryHandler.init(
                task_id=self.task_id,
                api_key=api_key,
                base_url=base_url,
                service_name=service_name,
                use_simple_processor=use_simple_processor,
                resource_attributes=resource_attributes
            )

            # Update the client to enable telemetry now that it's initialized
            self.client._telemetry_enabled = True
            self.client.prompts._telemetry_enabled = True

    @property
    def telemetry(self) -> type[TelemetryHandler]:
        """
        Access the telemetry handler for advanced configuration.

        Returns:
            The TelemetryHandler class for managing tracing.

        Example:
            >>> arthur = ArthurClient(...)
            >>> if arthur.telemetry.is_initialized():
            ...     print("Telemetry active")
            >>> arthur.telemetry.shutdown()
        """
        return TelemetryHandler

    def shutdown(self) -> None:
        """
        Shutdown the client and clean up resources.

        This will flush any pending telemetry spans and close HTTP connections.
        Should be called when your application is shutting down.

        Example:
            >>> arthur = ArthurClient(...)
            >>> # ... use the client ...
            >>> arthur.shutdown()
        """
        # Shutdown telemetry if it was enabled
        if self._enable_telemetry and TelemetryHandler.is_initialized():
            TelemetryHandler.shutdown()

        # Shutdown API client
        self.client.shutdown()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - automatically shutdown."""
        self.shutdown()
        return False
