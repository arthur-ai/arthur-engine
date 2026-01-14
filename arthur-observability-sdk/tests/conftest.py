"""
Pytest configuration and shared fixtures for arthur-obs-sdk tests.
"""

import os
import pytest
from unittest.mock import Mock, MagicMock
from typing import Generator


@pytest.fixture(autouse=True)
def reset_tracer():
    """Reset TraceHandler state before and after each test."""
    from arthur_observability_sdk.tracer import TraceHandler

    # Reset before test
    TraceHandler._initialized = False
    TraceHandler._tracer_provider = None
    TraceHandler._span_processor = None

    yield

    # Reset after test
    try:
        TraceHandler.shutdown()
    except Exception:
        pass
    TraceHandler._initialized = False
    TraceHandler._tracer_provider = None
    TraceHandler._span_processor = None


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Provide mock environment variables for testing."""
    env_vars = {
        "ARTHUR_TASK_ID": "test-task-id",
        "ARTHUR_API_KEY": "test-api-key",
        "ARTHUR_BASE_URL": "https://test.arthur.ai",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


@pytest.fixture
def clear_env_vars(monkeypatch):
    """Clear Arthur environment variables."""
    monkeypatch.delenv("ARTHUR_TASK_ID", raising=False)
    monkeypatch.delenv("ARTHUR_API_KEY", raising=False)
    monkeypatch.delenv("ARTHUR_BASE_URL", raising=False)


@pytest.fixture
def mock_tracer_provider(mocker):
    """Mock OpenTelemetry TracerProvider."""
    mock_provider = MagicMock()
    mock_provider.add_span_processor = Mock()
    mock_provider.shutdown = Mock(return_value=True)
    mocker.patch("arthur_observability_sdk.tracer.TracerProvider", return_value=mock_provider)
    return mock_provider


@pytest.fixture
def mock_otlp_exporter(mocker):
    """Mock OTLPSpanExporter."""
    mock_exporter = MagicMock()
    mocker.patch("arthur_observability_sdk.tracer.OTLPSpanExporter", return_value=mock_exporter)
    return mock_exporter


@pytest.fixture
def mock_set_tracer_provider(mocker):
    """Mock trace_api.set_tracer_provider."""
    mock_set = Mock()
    mocker.patch("arthur_observability_sdk.tracer.trace_api.set_tracer_provider", mock_set)
    return mock_set


@pytest.fixture
def mock_resource(mocker):
    """Mock OpenTelemetry Resource."""
    mock_res = MagicMock()
    mocker.patch("arthur_observability_sdk.tracer.Resource.create", return_value=mock_res)
    return mock_res


@pytest.fixture
def mock_batch_span_processor(mocker):
    """Mock BatchSpanProcessor."""
    mock_processor = MagicMock()
    mocker.patch("arthur_observability_sdk.tracer.BatchSpanProcessor", return_value=mock_processor)
    return mock_processor


@pytest.fixture
def mock_simple_span_processor(mocker):
    """Mock SimpleSpanProcessor."""
    mock_processor = MagicMock()
    mocker.patch("arthur_observability_sdk.tracer.SimpleSpanProcessor", return_value=mock_processor)
    return mock_processor


@pytest.fixture
def mock_using_attributes(mocker):
    """Mock openinference.instrumentation.using_attributes."""
    mock_context = MagicMock()
    mock_context.__enter__ = Mock(return_value=None)
    mock_context.__exit__ = Mock(return_value=False)
    mocker.patch("arthur_observability_sdk.context.using_attributes", return_value=mock_context)
    return mock_context
