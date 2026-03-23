"""Tests for Arthur class initialization, validation, and env-var resolution."""

from unittest.mock import MagicMock

import pytest

import arthur_genai_client.models as _genai_models
from arthur_observability_sdk._client import ArthurAPIClient
from arthur_observability_sdk.arthur import Arthur

pytestmark = pytest.mark.unit_tests


# ---------------------------------------------------------------------------
# Generated client sanity check
# ---------------------------------------------------------------------------

# These are the response model classes that api_client.py resolves via
# getattr(arthur_genai_client.models, klass) during HTTP response
# deserialization.  If models/__init__.py is empty (e.g. after a failed or
# partial client regeneration), this lookup silently raises AttributeError at
# runtime — exactly the failure mode seen when calling get_prompt().
_REQUIRED_RESPONSE_MODELS = [
    "AgenticPrompt",
    "AgenticPromptVersionListResponse",
    "RenderedPromptResponse",
]


@pytest.mark.parametrize("model_name", _REQUIRED_RESPONSE_MODELS)
def test_generated_client_response_model_is_accessible(model_name):
    """arthur_genai_client.models must export response classes used by api_client.py.

    A missing export means models/__init__.py was not properly generated.
    Fix by running: ./scripts/generate_openapi_client.sh generate python
    """
    assert hasattr(_genai_models, model_name), (
        f"arthur_genai_client.models.{model_name} is not accessible. "
        f"The generated client's models/__init__.py is likely empty or stale. "
        f"Regenerate with: ./scripts/generate_openapi_client.sh generate python"
    )


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


def test_base_url_param_overrides_env(monkeypatch):
    monkeypatch.setenv("ARTHUR_BASE_URL", "http://env-host:9090")
    arthur = Arthur(
        service_name="svc",
        api_key="k",
        base_url="http://explicit-host:8080",
        enable_telemetry=False,
    )
    assert arthur._base_url == "http://explicit-host:8080"
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
# resolve_task_id pagination
# ---------------------------------------------------------------------------


def _make_task(name: str, task_id: str) -> MagicMock:
    t = MagicMock()
    t.name = name
    t.id = task_id
    return t


def _make_search_result(tasks, count: int) -> MagicMock:
    r = MagicMock()
    r.tasks = tasks
    r.count = count
    return r


def _make_api_client() -> ArthurAPIClient:
    client = ArthurAPIClient.__new__(ArthurAPIClient)
    client._tasks_api = MagicMock()
    return client


def test_resolve_task_id_found_on_first_page():
    client = _make_api_client()
    client._tasks_api.search_tasks_api_v2_tasks_search_post.return_value = _make_search_result(
        [_make_task("my-task", "uuid-1")], count=1
    )
    assert client.resolve_task_id("my-task") == "uuid-1"
    client._tasks_api.search_tasks_api_v2_tasks_search_post.assert_called_once()


def test_resolve_task_id_skips_substring_matches_on_first_page():
    """Tasks whose names only contain the target as a substring must be skipped."""
    client = _make_api_client()
    # First page: 50 substring matches, no exact match; second page: exact match
    page1_tasks = [_make_task(f"my-task-{i}", f"uuid-sub-{i}") for i in range(50)]
    page2_tasks = [_make_task("my-task", "uuid-exact")]
    client._tasks_api.search_tasks_api_v2_tasks_search_post.side_effect = [
        _make_search_result(page1_tasks, count=51),
        _make_search_result(page2_tasks, count=51),
    ]
    assert client.resolve_task_id("my-task") == "uuid-exact"
    assert client._tasks_api.search_tasks_api_v2_tasks_search_post.call_count == 2


def test_resolve_task_id_raises_when_not_found():
    client = _make_api_client()
    client._tasks_api.search_tasks_api_v2_tasks_search_post.return_value = _make_search_result(
        [_make_task("my-task-v2", "uuid-1")], count=1
    )
    with pytest.raises(ValueError, match="No task with an exact name match"):
        client.resolve_task_id("my-task")


def test_resolve_task_id_raises_includes_substring_count():
    client = _make_api_client()
    client._tasks_api.search_tasks_api_v2_tasks_search_post.return_value = _make_search_result(
        [_make_task("my-task-v2", "uuid-1")], count=3
    )
    with pytest.raises(ValueError, match="3 task"):
        client.resolve_task_id("my-task")


def test_resolve_task_id_does_not_fetch_beyond_last_page():
    """Pagination must stop once all results are exhausted."""
    client = _make_api_client()
    # 2 pages of 50; exact match absent
    page_tasks = [_make_task(f"my-task-{i}", f"uuid-{i}") for i in range(50)]
    client._tasks_api.search_tasks_api_v2_tasks_search_post.side_effect = [
        _make_search_result(page_tasks, count=60),
        _make_search_result(page_tasks[:10], count=60),
    ]
    with pytest.raises(ValueError):
        client.resolve_task_id("my-task")
    assert client._tasks_api.search_tasks_api_v2_tasks_search_post.call_count == 2


# ---------------------------------------------------------------------------
# Missing optional dependency raises ImportError with helpful message
# ---------------------------------------------------------------------------


def test_instrument_missing_dependency_raises_import_error(mocker):
    arthur = Arthur(service_name="svc", api_key="k", enable_telemetry=False)
    mocker.patch("importlib.import_module", side_effect=ImportError("no module"))
    with pytest.raises(ImportError, match="pip install arthur-ai-observability-sdk"):
        arthur.instrument_langchain()
    arthur.shutdown()
