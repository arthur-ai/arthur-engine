"""Tests for OTel TracerProvider setup in telemetry.py."""

import pytest
from unittest.mock import MagicMock, patch

pytestmark = pytest.mark.unit_tests

from opentelemetry.sdk.trace import TracerProvider

from arthur_observability_sdk.arthur import Arthur
from arthur_observability_sdk.telemetry import setup_telemetry

# ---------------------------------------------------------------------------
# setup_telemetry() unit tests
# ---------------------------------------------------------------------------


def test_tracer_provider_created():
    """setup_telemetry returns a TracerProvider."""
    with patch("arthur_observability_sdk.telemetry.OTLPSpanExporter") as mock_exporter_cls:
        mock_exporter_cls.return_value = MagicMock()
        provider = setup_telemetry(
            service_name="test-service",
            otlp_endpoint="http://localhost:4318/v1/traces",
            api_key="test-key",
        )
        assert isinstance(provider, TracerProvider)


def test_otlp_endpoint_receives_auth_header():
    """setup_telemetry passes Authorization header to OTLPSpanExporter."""
    with patch("arthur_observability_sdk.telemetry.OTLPSpanExporter") as mock_exporter_cls:
        mock_exporter_cls.return_value = MagicMock()
        setup_telemetry(
            service_name="test-service",
            otlp_endpoint="http://localhost:4318/v1/traces",
            api_key="my-secret-key",
        )
        _, kwargs = mock_exporter_cls.call_args
        assert kwargs["headers"]["Authorization"] == "Bearer my-secret-key"


def test_otlp_endpoint_no_auth_header_when_no_key():
    """setup_telemetry does not add Authorization header when api_key is None."""
    with patch("arthur_observability_sdk.telemetry.OTLPSpanExporter") as mock_exporter_cls:
        mock_exporter_cls.return_value = MagicMock()
        setup_telemetry(
            service_name="test-service",
            otlp_endpoint="http://localhost:4318/v1/traces",
            api_key=None,
        )
        _, kwargs = mock_exporter_cls.call_args
        assert "Authorization" not in kwargs["headers"]


def test_custom_resource_attributes():
    """setup_telemetry merges custom resource attributes into the Resource."""
    with (
        patch("arthur_observability_sdk.telemetry.OTLPSpanExporter") as mock_exporter_cls,
        patch("arthur_observability_sdk.telemetry.Resource") as mock_resource_cls,
    ):
        mock_exporter_cls.return_value = MagicMock()
        mock_resource_cls.create.return_value = MagicMock()
        setup_telemetry(
            service_name="test-service",
            otlp_endpoint="http://localhost:4318/v1/traces",
            api_key=None,
            resource_attributes={"deployment.environment": "staging", "team": "ml"},
        )
        call_kwargs = mock_resource_cls.create.call_args[0][0]
        assert call_kwargs["service.name"] == "test-service"
        assert call_kwargs["deployment.environment"] == "staging"
        assert call_kwargs["team"] == "ml"


# ---------------------------------------------------------------------------
# Arthur.shutdown() tests
# ---------------------------------------------------------------------------


def test_shutdown_calls_provider_shutdown():
    """Arthur.shutdown() calls TracerProvider.shutdown()."""
    with patch("arthur_observability_sdk.telemetry.OTLPSpanExporter") as mock_exporter_cls:
        mock_exporter_cls.return_value = MagicMock()
        arthur = Arthur(service_name="svc", api_key="k", enable_telemetry=True)
        provider_mock = MagicMock()
        arthur._tracer_provider = provider_mock
        arthur.shutdown()
        provider_mock.shutdown.assert_called_once()


def test_shutdown_noop_when_telemetry_disabled():
    """Arthur.shutdown() does not raise when telemetry is disabled."""
    arthur = Arthur(service_name="svc", api_key="k", enable_telemetry=False)
    arthur.shutdown()  # should not raise


def test_otlp_endpoint_defaults_to_base_url_v1_traces():
    """OTLP endpoint defaults to {base_url}/v1/traces."""
    with patch("arthur_observability_sdk.telemetry.OTLPSpanExporter") as mock_exporter_cls:
        mock_exporter_cls.return_value = MagicMock()
        arthur = Arthur(
            service_name="svc",
            api_key="k",
            base_url="http://arthur-engine:3030",
        )
        _, kwargs = mock_exporter_cls.call_args
        assert kwargs["endpoint"] == "http://arthur-engine:3030/api/v1/traces"
        arthur.shutdown()
