"""Tests for Arthur.get_prompt() and Arthur.render_prompt() — API calls + PROMPT spans."""

import json
from unittest.mock import MagicMock, patch

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from arthur_observability_sdk.arthur import Arthur
from arthur_observability_sdk._client import ArthurAPIError


TASK_ID = "task-uuid-0001"
PROMPT_NAME = "TestPrompt"
BASE_URL = "http://localhost:3030"

MOCK_PROMPT = {
    "name": PROMPT_NAME,
    "messages": [{"role": "user", "content": "Hello {{ topic }}"}],
    "model_name": "gpt-4o",
    "model_provider": "openai",
    "version": 2,
    "variables": ["topic"],
    "tags": ["latest"],
    "config": None,
    "created_at": "2025-01-01T00:00:00",
    "deleted_at": None,
}

RENDERED_PROMPT = {
    **MOCK_PROMPT,
    "messages": [{"role": "user", "content": "Hello quantum computing"}],
}


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

def _make_arthur_with_in_memory_spans(task_id=TASK_ID):
    """
    Returns (arthur, exporter) where exporter collects all finished spans.
    Telemetry is enabled but backed by an in-memory exporter (no real OTLP).
    The generated API objects are replaced with MagicMocks so tests can
    configure return values without making real HTTP calls.
    """
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    arthur = Arthur(
        task_id=task_id,
        api_key="test-key",
        base_url=BASE_URL,
        enable_telemetry=False,
    )
    arthur._tracer_provider = provider
    # Replace the generated API objects with mocks — no real network calls
    arthur._api_client._prompts_api = MagicMock()
    arthur._api_client._tasks_api = MagicMock()
    return arthur, exporter


def _mock_prompt_response(prompt_data: dict):
    """Build a mock ApiResponse whose .raw_data is the JSON-encoded prompt."""
    mock_resp = MagicMock()
    mock_resp.raw_data = json.dumps(prompt_data).encode()
    return mock_resp


# ---------------------------------------------------------------------------
# get_prompt() — routing
# ---------------------------------------------------------------------------

def test_get_prompt_by_version():
    arthur, _ = _make_arthur_with_in_memory_spans()
    arthur._api_client._prompts_api.get_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_get_with_http_info.return_value = _mock_prompt_response(MOCK_PROMPT)

    result = arthur.get_prompt(PROMPT_NAME, version="2")
    assert result["name"] == PROMPT_NAME
    assert result["version"] == 2
    arthur.shutdown()


def test_get_prompt_default_version_is_latest():
    arthur, _ = _make_arthur_with_in_memory_spans()
    m = arthur._api_client._prompts_api.get_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_get_with_http_info
    m.return_value = _mock_prompt_response(MOCK_PROMPT)

    arthur.get_prompt(PROMPT_NAME)
    _, kwargs = m.call_args
    assert kwargs["prompt_version"] == "latest"
    arthur.shutdown()


def test_get_prompt_by_tag():
    arthur, _ = _make_arthur_with_in_memory_spans()
    m = arthur._api_client._prompts_api.get_agentic_prompt_by_tag_api_v1_tasks_task_id_prompts_prompt_name_versions_tags_tag_get_with_http_info
    m.return_value = _mock_prompt_response(MOCK_PROMPT)

    result = arthur.get_prompt(PROMPT_NAME, tag="latest")
    assert result["tags"] == ["latest"]
    _, kwargs = m.call_args
    assert kwargs["tag"] == "latest"
    arthur.shutdown()


def test_get_prompt_uses_instance_task_id():
    arthur, _ = _make_arthur_with_in_memory_spans(task_id=TASK_ID)
    m = arthur._api_client._prompts_api.get_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_get_with_http_info
    m.return_value = _mock_prompt_response(MOCK_PROMPT)

    arthur.get_prompt(PROMPT_NAME)
    _, kwargs = m.call_args
    assert kwargs["task_id"] == TASK_ID
    arthur.shutdown()


def test_get_prompt_overrides_task_id():
    override_id = "other-task-uuid"
    arthur, _ = _make_arthur_with_in_memory_spans(task_id=TASK_ID)
    m = arthur._api_client._prompts_api.get_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_get_with_http_info
    m.return_value = _mock_prompt_response(MOCK_PROMPT)

    arthur.get_prompt(PROMPT_NAME, task_id=override_id)
    _, kwargs = m.call_args
    assert kwargs["task_id"] == override_id
    arthur.shutdown()


# ---------------------------------------------------------------------------
# get_prompt() — OTel span
# ---------------------------------------------------------------------------

def test_get_prompt_emits_prompt_span():
    arthur, exporter = _make_arthur_with_in_memory_spans()
    arthur._api_client._prompts_api.get_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_get_with_http_info.return_value = _mock_prompt_response(MOCK_PROMPT)

    arthur.get_prompt(PROMPT_NAME)

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    attrs = dict(spans[0].attributes or {})
    assert attrs.get("openinference.span.kind") == "PROMPT"
    assert attrs.get("arthur.prompt.name") == PROMPT_NAME
    assert attrs.get("arthur.task.id") == TASK_ID
    assert "llm.prompt_template.version" in attrs
    assert "llm.prompt_template.template" in attrs
    assert "llm.prompt_template.variables" in attrs
    assert attrs.get("output.mime_type") == "application/json"
    arthur.shutdown()


def test_get_prompt_span_records_version():
    arthur, exporter = _make_arthur_with_in_memory_spans()
    arthur._api_client._prompts_api.get_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_get_with_http_info.return_value = _mock_prompt_response({**MOCK_PROMPT, "version": 3})

    arthur.get_prompt(PROMPT_NAME, version="3")

    attrs = dict(exporter.get_finished_spans()[0].attributes or {})
    assert attrs.get("llm.prompt_template.version") == "3"
    arthur.shutdown()


def test_get_prompt_span_on_error():
    arthur, exporter = _make_arthur_with_in_memory_spans()
    arthur._api_client._prompts_api.get_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_get_with_http_info.side_effect = ArthurAPIError(404, "not found")

    with pytest.raises(ArthurAPIError):
        arthur.get_prompt(PROMPT_NAME)

    spans = exporter.get_finished_spans()
    assert spans[0].status.status_code.name == "ERROR"
    arthur.shutdown()


# ---------------------------------------------------------------------------
# get_prompt() — no task_id
# ---------------------------------------------------------------------------

def test_get_prompt_raises_without_task_id():
    arthur = Arthur(service_name="svc", api_key="k", enable_telemetry=False)
    with pytest.raises(ValueError, match="No task_id available"):
        arthur.get_prompt("some-prompt")
    arthur.shutdown()


# ---------------------------------------------------------------------------
# render_prompt() — routing
# ---------------------------------------------------------------------------

def test_render_prompt_by_version():
    arthur, _ = _make_arthur_with_in_memory_spans()
    m = arthur._api_client._prompts_api.render_saved_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_renders_post_with_http_info
    m.return_value = _mock_prompt_response(RENDERED_PROMPT)

    result = arthur.render_prompt(PROMPT_NAME, version="2", variables={"topic": "quantum computing"})
    assert result["messages"][0]["content"] == "Hello quantum computing"
    _, kwargs = m.call_args
    assert kwargs["prompt_version"] == "2"
    arthur.shutdown()


def test_render_prompt_by_tag_uses_tag_as_version_segment():
    arthur, _ = _make_arthur_with_in_memory_spans()
    m = arthur._api_client._prompts_api.render_saved_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_renders_post_with_http_info
    m.return_value = _mock_prompt_response(RENDERED_PROMPT)

    arthur.render_prompt(PROMPT_NAME, tag="latest", variables={"topic": "AI"})
    _, kwargs = m.call_args
    assert kwargs["prompt_version"] == "latest"
    arthur.shutdown()


def test_render_prompt_default_version_is_latest():
    arthur, _ = _make_arthur_with_in_memory_spans()
    m = arthur._api_client._prompts_api.render_saved_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_renders_post_with_http_info
    m.return_value = _mock_prompt_response(RENDERED_PROMPT)

    arthur.render_prompt(PROMPT_NAME, variables={"topic": "AI"})
    _, kwargs = m.call_args
    assert kwargs["prompt_version"] == "latest"
    arthur.shutdown()


def test_render_prompt_sends_variables_in_request():
    arthur, _ = _make_arthur_with_in_memory_spans()
    m = arthur._api_client._prompts_api.render_saved_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_renders_post_with_http_info
    m.return_value = _mock_prompt_response(RENDERED_PROMPT)

    arthur.render_prompt(PROMPT_NAME, variables={"topic": "climate change"})

    _, kwargs = m.call_args
    rendering_req = kwargs["saved_prompt_rendering_request"]
    variable_names = [v.name for v in rendering_req.completion_request.variables]
    variable_values = [v.value for v in rendering_req.completion_request.variables]
    assert "topic" in variable_names
    assert "climate change" in variable_values
    arthur.shutdown()


# ---------------------------------------------------------------------------
# render_prompt() — OTel span
# ---------------------------------------------------------------------------

def test_render_prompt_emits_prompt_span():
    arthur, exporter = _make_arthur_with_in_memory_spans()
    arthur._api_client._prompts_api.render_saved_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_renders_post_with_http_info.return_value = _mock_prompt_response(RENDERED_PROMPT)

    arthur.render_prompt(PROMPT_NAME, variables={"topic": "AI"})

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    attrs = dict(spans[0].attributes or {})
    assert attrs.get("openinference.span.kind") == "PROMPT"
    assert attrs.get("arthur.prompt.name") == PROMPT_NAME
    assert attrs.get("arthur.task.id") == TASK_ID
    assert attrs.get("llm.prompt_template.version") == "latest"
    assert "llm.prompt_template.variables" in attrs
    assert "llm.prompt_template.template" in attrs
    arthur.shutdown()


def test_render_prompt_span_on_error():
    arthur, exporter = _make_arthur_with_in_memory_spans()
    arthur._api_client._prompts_api.render_saved_agentic_prompt_api_v1_tasks_task_id_prompts_prompt_name_versions_prompt_version_renders_post_with_http_info.side_effect = ArthurAPIError(422, "missing variable")

    with pytest.raises(ArthurAPIError):
        arthur.render_prompt(PROMPT_NAME, variables={})

    assert exporter.get_finished_spans()[0].status.status_code.name == "ERROR"
    arthur.shutdown()
