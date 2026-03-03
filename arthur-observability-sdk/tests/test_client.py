"""Tests for Arthur class initialization, validation, and env-var resolution."""

import pytest

from arthur_observability_sdk.arthur import Arthur

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_arthur_requires_task_or_service_name():
    """Constructing Arthur with neither task_id, task_name, nor service_name raises ValueError."""
    with pytest.raises(ValueError, match="Arthur requires at least one of"):
        Arthur(api_key="test-key", enable_telemetry=False)


def test_arthur_accepts_task_id_only():
    arthur = Arthur(task_id="uuid-1234", api_key="test-key", enable_telemetry=False)
    assert arthur._task_id == "uuid-1234"
    arthur.shutdown()


def test_arthur_accepts_task_name_only():
    arthur = Arthur(task_name="my-task", api_key="test-key", enable_telemetry=False)
    assert arthur._task_name == "my-task"
    arthur.shutdown()


def test_arthur_accepts_service_name_only():
    arthur = Arthur(service_name="my-service", api_key="test-key", enable_telemetry=False)
    assert arthur._service_name == "my-service"
    arthur.shutdown()


def test_arthur_accepts_both_task_id_and_service_name():
    arthur = Arthur(
        task_id="uuid-1234",
        service_name="my-service",
        api_key="test-key",
        enable_telemetry=False,
    )
    assert arthur._task_id == "uuid-1234"
    assert arthur._service_name == "my-service"
    arthur.shutdown()


# ---------------------------------------------------------------------------
# Env-var resolution
# ---------------------------------------------------------------------------


def test_api_key_from_env(monkeypatch):
    monkeypatch.setenv("ARTHUR_API_KEY", "env-api-key")
    arthur = Arthur(service_name="svc", enable_telemetry=False)
    assert arthur._api_key == "env-api-key"
    arthur.shutdown()


def test_api_key_param_overrides_env(monkeypatch):
    monkeypatch.setenv("ARTHUR_API_KEY", "env-api-key")
    arthur = Arthur(api_key="param-key", service_name="svc", enable_telemetry=False)
    assert arthur._api_key == "param-key"
    arthur.shutdown()


def test_base_url_from_env(monkeypatch):
    monkeypatch.setenv("ARTHUR_BASE_URL", "http://custom-host:9090")
    arthur = Arthur(service_name="svc", api_key="k", enable_telemetry=False)
    assert arthur._base_url == "http://custom-host:9090"
    arthur.shutdown()


def test_base_url_param_default():
    arthur = Arthur(service_name="svc", api_key="k", enable_telemetry=False)
    assert arthur._base_url == "http://localhost:3030"
    arthur.shutdown()


def test_otlp_endpoint_defaults_to_base_url_traces():
    arthur = Arthur(
        service_name="svc",
        api_key="k",
        base_url="http://my-host:3030",
        enable_telemetry=False,
    )
    assert arthur._otlp_endpoint == "http://my-host:3030/api/v1/traces"
    arthur.shutdown()


def test_otlp_endpoint_custom():
    arthur = Arthur(
        service_name="svc",
        api_key="k",
        otlp_endpoint="http://otel-collector:4318/v1/traces",
        enable_telemetry=False,
    )
    assert arthur._otlp_endpoint == "http://otel-collector:4318/v1/traces"
    arthur.shutdown()


# ---------------------------------------------------------------------------
# Missing optional dependency raises ImportError with helpful message
# ---------------------------------------------------------------------------


def test_instrument_missing_dependency_raises_import_error(mocker):
    arthur = Arthur(service_name="svc", api_key="k", enable_telemetry=False)
    mocker.patch("importlib.import_module", side_effect=ImportError("no module"))
    with pytest.raises(ImportError, match="pip install arthur-observability-sdk"):
        arthur.instrument_langchain()
    arthur.shutdown()
