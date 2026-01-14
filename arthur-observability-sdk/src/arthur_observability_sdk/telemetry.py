"""
Telemetry handler for initializing Arthur observability tracing.

This module provides the TelemetryHandler class for setting up OpenTelemetry tracing
with Arthur's OTLP endpoint. This is typically used internally by ArthurClient.
"""

import sys
import warnings
from pathlib import Path
from typing import Optional, Dict, Any

from opentelemetry import trace as trace_api
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor, SpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource


class TelemetryHandler:
    """Handler for Arthur observability tracing setup and teardown."""

    _initialized: bool = False
    _tracer_provider: Optional[TracerProvider] = None
    _span_processor: Optional[SpanProcessor] = None

    @staticmethod
    def _get_default_service_name() -> str:
        """
        Derive a default service name from the calling script.

        Returns the name based on the main Python file being executed,
        in Python module notation (e.g., "my_agent.app")

        Returns:
            Service name string, or "arthur-service" if unable to determine.
        """
        try:
            # Get the main module's file path
            main_module = sys.modules.get('__main__')
            if main_module and hasattr(main_module, '__file__') and main_module.__file__:
                file_path = Path(main_module.__file__).resolve()

                # Get the parent directory name and file name (without .py extension)
                parent_dir = file_path.parent.name
                file_stem = file_path.stem

                # If in root or unclear structure, just use filename
                if parent_dir in ('', '.', '..'):
                    return file_stem

                # Return in Python module notation: directory.filename
                return f"{parent_dir}.{file_stem}"

        except Exception:
            # If anything goes wrong, fall back to default
            pass

        return "arthur-service"

    @classmethod
    def init(
        cls,
        task_id: str,
        api_key: str,
        base_url: str = "https://app.arthur.ai",
        service_name: Optional[str] = None,
        use_simple_processor: bool = False,
        resource_attributes: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> None:
        """
        Initialize Arthur observability tracing.

        This sets up OpenTelemetry with an OTLP exporter pointing to Arthur's endpoint.
        The tracer provider can only be initialized once per process.

        Note: This is typically called by ArthurClient, not directly by users.

        Args:
            task_id: Arthur task ID (required).
            api_key: Arthur API key (required).
            base_url: Arthur base URL. Defaults to "https://app.arthur.ai".
            service_name: Service name for traces. If not provided, automatically
                         derives the name from the calling script (e.g., "my_agent.app").
            use_simple_processor: If True, uses SimpleSpanProcessor for immediate
                                 span export (useful for testing/debugging).
                                 If False (default), uses BatchSpanProcessor for
                                 efficient batched exports (recommended for production).
            resource_attributes: Additional resource attributes to include.
            **kwargs: Additional configuration options (reserved for future use).

        Raises:
            RuntimeError: If TelemetryHandler is already initialized.

        Example:
            >>> from arthur_observability_sdk.telemetry import TelemetryHandler
            >>> TelemetryHandler.init(
            ...     task_id="my-task-id",
            ...     api_key="my-api-key",
            ...     base_url="https://app.arthur.ai",
            ...     service_name="my-service"
            ... )
        """
        if cls._initialized:
            warnings.warn(
                "TelemetryHandler is already initialized. "
                "Call TelemetryHandler.shutdown() first to reinitialize.",
                UserWarning
            )
            return

        # Use provided service name or derive from script
        service_name = service_name or cls._get_default_service_name()

        # Build resource attributes
        attrs: Dict[str, Any] = {
            "service.name": service_name,
            "arthur.task": task_id,
        }
        if resource_attributes:
            attrs.update(resource_attributes)

        resource = Resource.create(attrs)

        # Create tracer provider
        cls._tracer_provider = TracerProvider(resource=resource)

        # Configure OTLP exporter with Arthur endpoint
        otlp_endpoint = f"{base_url.rstrip('/')}/v1/traces"
        headers = {
            "Authorization": f"Bearer {api_key}",
        }

        otlp_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            headers=headers
        )

        # Add span processor (batch by default, simple if requested)
        if use_simple_processor:
            cls._span_processor = SimpleSpanProcessor(otlp_exporter)
        else:
            cls._span_processor = BatchSpanProcessor(otlp_exporter)

        cls._tracer_provider.add_span_processor(cls._span_processor)

        # Set as global tracer provider
        trace_api.set_tracer_provider(cls._tracer_provider)

        cls._initialized = True

    @classmethod
    def shutdown(cls, timeout_millis: int = 30000) -> bool:
        """
        Shutdown the tracer provider and flush any pending spans.

        This should be called when your application is shutting down to ensure
        all spans are exported before exit.

        Args:
            timeout_millis: Maximum time to wait for shutdown in milliseconds.
                           Defaults to 30000 (30 seconds).

        Returns:
            True if shutdown was successful, False otherwise.

        Example:
            >>> from arthur_observability_sdk.telemetry import TelemetryHandler
            >>> TelemetryHandler.shutdown()
        """
        if not cls._initialized:
            warnings.warn(
                "TelemetryHandler is not initialized. Nothing to shutdown.",
                UserWarning
            )
            return False

        success = True
        if cls._tracer_provider:
            success = cls._tracer_provider.shutdown()

        cls._initialized = False
        cls._tracer_provider = None
        cls._span_processor = None

        return success

    @classmethod
    def is_initialized(cls) -> bool:
        """
        Check if TelemetryHandler is currently initialized.

        Returns:
            True if initialized, False otherwise.
        """
        return cls._initialized
