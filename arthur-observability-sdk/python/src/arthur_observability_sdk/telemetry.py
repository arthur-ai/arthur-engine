import logging
from typing import Any, Dict, Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)


def setup_telemetry(
    service_name: str,
    otlp_endpoint: str,
    api_key: Optional[str],
    resource_attributes: Optional[Dict[str, Any]] = None,
) -> TracerProvider:
    """
    Creates and registers a global TracerProvider with OTLP export.

    Args:
        service_name: Value for the OTel resource ``service.name`` attribute.
        otlp_endpoint: Full URL of the OTLP HTTP traces endpoint.
        api_key: Bearer token sent in the ``Authorization`` header, or None.
        resource_attributes: Additional OTel resource attributes to merge in.

    Returns:
        The configured ``TracerProvider`` (also set as the global provider).
    """
    attrs: Dict[str, Any] = {SERVICE_NAME: service_name}
    if resource_attributes:
        attrs.update(resource_attributes)

    resource = Resource.create(attrs)

    headers: Dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        if not otlp_endpoint.startswith("https://"):
            logger.warning(
                "API key is configured but OTLP endpoint (%s) is not HTTPS. "
                "Credentials will be sent in plaintext.",
                otlp_endpoint,
            )

    exporter = OTLPSpanExporter(endpoint=otlp_endpoint, headers=headers)
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)
    logger.debug(
        "OTel TracerProvider configured (endpoint=%s, service=%s)", otlp_endpoint, service_name
    )
    return provider
