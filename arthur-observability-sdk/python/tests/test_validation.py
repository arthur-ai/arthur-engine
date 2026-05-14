"""Tests for Arthur.validate_prompt() and Arthur.validate_response()."""

import json
from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit_tests
from openinference.semconv.trace import SpanAttributes
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from arthur_observability_sdk._client import ArthurAPIError
from arthur_observability_sdk.arthur import Arthur

TASK_ID = "task-uuid-validation"
INFERENCE_ID = "inference-uuid-1234"
BASE_URL = "http://localhost:3030"

PROMPT_TEXT = "What is the capital of France?"
RESPONSE_TEXT = "The capital of France is Paris."
CONTEXT_TEXT = "Paris is the capital and most populous city of France."

MOCK_PROMPT_RESULT = {
    "inference_id": INFERENCE_ID,
    "rule_results": [
        {
            "id": "rule-1",
            "name": "PII Check",
            "rule_type": "PIIDataRule",
            "scope": "default",
            "result": "Pass",
            "latency_ms": 12,
        },
    ],
}

MOCK_RESPONSE_RESULT = {
    "inference_id": INFERENCE_ID,
    "rule_results": [
        {
            "id": "rule-2",
            "name": "Hallucination Check",
            "rule_type": "ModelHallucinationRuleV2",
            "scope": "task",
            "result": "Pass",
            "latency_ms": 240,
        },
    ],
}


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_arthur_with_in_memory_spans(task_id=TASK_ID):
    """
    Returns (arthur, exporter) where exporter collects all finished spans.
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
    arthur._api_client._prompts_api = MagicMock()
    arthur._api_client._tasks_api = MagicMock()
    arthur._api_client._validation_api = MagicMock()
    return arthur, exporter


def _mock_validation_response(payload: dict):
    """Build a mock ApiResponse whose .raw_data returns the JSON-encoded payload."""
    m = MagicMock()
    m.raw_data = json.dumps(payload).encode()
    return m


def _validate_prompt_method(arthur):
    return (
        arthur._api_client._validation_api.validate_prompt_endpoint_api_v2_tasks_task_id_validate_prompt_post_with_http_info
    )


def _validate_response_method(arthur):
    return (
        arthur._api_client._validation_api.validate_response_endpoint_api_v2_tasks_task_id_validate_response_inference_id_post_with_http_info
    )


# ---------------------------------------------------------------------------
# validate_prompt() — return value & request shape
# ---------------------------------------------------------------------------


def test_validate_prompt_returns_parsed_result():
    arthur, _ = _make_arthur_with_in_memory_spans()
    _validate_prompt_method(arthur).return_value = _mock_validation_response(MOCK_PROMPT_RESULT)

    result = arthur.validate_prompt(PROMPT_TEXT)
    assert result["inference_id"] == INFERENCE_ID
    assert result["rule_results"][0]["name"] == "PII Check"
    arthur.shutdown()


def test_validate_prompt_uses_instance_task_id():
    arthur, _ = _make_arthur_with_in_memory_spans(task_id=TASK_ID)
    m = _validate_prompt_method(arthur)
    m.return_value = _mock_validation_response(MOCK_PROMPT_RESULT)

    arthur.validate_prompt(PROMPT_TEXT)
    _, kwargs = m.call_args
    assert kwargs["task_id"] == TASK_ID
    assert kwargs["prompt_validation_request"].prompt == PROMPT_TEXT
    arthur.shutdown()


def test_validate_prompt_overrides_task_id():
    override_id = "other-task-uuid"
    arthur, _ = _make_arthur_with_in_memory_spans(task_id=TASK_ID)
    m = _validate_prompt_method(arthur)
    m.return_value = _mock_validation_response(MOCK_PROMPT_RESULT)

    arthur.validate_prompt(PROMPT_TEXT, task_id=override_id)
    _, kwargs = m.call_args
    assert kwargs["task_id"] == override_id
    arthur.shutdown()


def test_validate_prompt_raises_without_task_id():
    arthur = Arthur(service_name="svc", api_key="k", enable_telemetry=False)
    with pytest.raises(ValueError, match="No task_id available"):
        arthur.validate_prompt(PROMPT_TEXT)
    arthur.shutdown()


# ---------------------------------------------------------------------------
# validate_prompt() — OTel span
# ---------------------------------------------------------------------------


def test_validate_prompt_emits_guardrail_span():
    arthur, exporter = _make_arthur_with_in_memory_spans()
    _validate_prompt_method(arthur).return_value = _mock_validation_response(MOCK_PROMPT_RESULT)

    arthur.validate_prompt(PROMPT_TEXT)

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "validate_prompt"
    attrs = dict(span.attributes or {})
    assert attrs.get("openinference.span.kind") == "GUARDRAIL"
    assert attrs.get("arthur.task.id") == TASK_ID
    assert attrs.get("arthur.inference.id") == INFERENCE_ID
    assert attrs.get(SpanAttributes.INPUT_VALUE) == json.dumps({"prompt": PROMPT_TEXT})
    assert attrs.get(SpanAttributes.INPUT_MIME_TYPE) == "application/json"
    assert json.loads(attrs[SpanAttributes.OUTPUT_VALUE]) == MOCK_PROMPT_RESULT
    assert attrs.get(SpanAttributes.OUTPUT_MIME_TYPE) == "application/json"
    arthur.shutdown()


def test_validate_prompt_span_on_error():
    arthur, exporter = _make_arthur_with_in_memory_spans()
    _validate_prompt_method(arthur).side_effect = ArthurAPIError(400, "bad request")

    with pytest.raises(ArthurAPIError):
        arthur.validate_prompt(PROMPT_TEXT)

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].status.status_code.name == "ERROR"
    arthur.shutdown()


def test_validate_prompt_span_includes_session_and_user():
    arthur, exporter = _make_arthur_with_in_memory_spans()
    _validate_prompt_method(arthur).return_value = _mock_validation_response(MOCK_PROMPT_RESULT)

    with arthur.attributes(session_id="vp-session", user_id="vp-user"):
        arthur.validate_prompt(PROMPT_TEXT)

    attrs = dict(exporter.get_finished_spans()[0].attributes or {})
    assert attrs.get(SpanAttributes.SESSION_ID) == "vp-session"
    assert attrs.get(SpanAttributes.USER_ID) == "vp-user"
    arthur.shutdown()


# ---------------------------------------------------------------------------
# validate_response() — return value & request shape
# ---------------------------------------------------------------------------


def test_validate_response_returns_parsed_result():
    arthur, _ = _make_arthur_with_in_memory_spans()
    _validate_response_method(arthur).return_value = _mock_validation_response(MOCK_RESPONSE_RESULT)

    result = arthur.validate_response(
        RESPONSE_TEXT, inference_id=INFERENCE_ID, context=CONTEXT_TEXT
    )
    assert result["inference_id"] == INFERENCE_ID
    assert result["rule_results"][0]["name"] == "Hallucination Check"
    arthur.shutdown()


def test_validate_response_passes_inference_and_task_ids():
    arthur, _ = _make_arthur_with_in_memory_spans(task_id=TASK_ID)
    m = _validate_response_method(arthur)
    m.return_value = _mock_validation_response(MOCK_RESPONSE_RESULT)

    arthur.validate_response(RESPONSE_TEXT, inference_id=INFERENCE_ID, context=CONTEXT_TEXT)
    _, kwargs = m.call_args
    assert kwargs["task_id"] == TASK_ID
    assert kwargs["inference_id"] == INFERENCE_ID
    request = kwargs["response_validation_request"]
    assert request.response == RESPONSE_TEXT
    assert request.context == CONTEXT_TEXT
    arthur.shutdown()


def test_validate_response_context_optional():
    arthur, _ = _make_arthur_with_in_memory_spans()
    m = _validate_response_method(arthur)
    m.return_value = _mock_validation_response(MOCK_RESPONSE_RESULT)

    arthur.validate_response(RESPONSE_TEXT, inference_id=INFERENCE_ID)
    _, kwargs = m.call_args
    assert kwargs["response_validation_request"].context is None
    arthur.shutdown()


def test_validate_response_overrides_task_id():
    override_id = "other-task-uuid"
    arthur, _ = _make_arthur_with_in_memory_spans(task_id=TASK_ID)
    m = _validate_response_method(arthur)
    m.return_value = _mock_validation_response(MOCK_RESPONSE_RESULT)

    arthur.validate_response(RESPONSE_TEXT, inference_id=INFERENCE_ID, task_id=override_id)
    _, kwargs = m.call_args
    assert kwargs["task_id"] == override_id
    arthur.shutdown()


# ---------------------------------------------------------------------------
# validate_response() — OTel span
# ---------------------------------------------------------------------------


def test_validate_response_emits_guardrail_span():
    arthur, exporter = _make_arthur_with_in_memory_spans()
    _validate_response_method(arthur).return_value = _mock_validation_response(MOCK_RESPONSE_RESULT)

    arthur.validate_response(RESPONSE_TEXT, inference_id=INFERENCE_ID, context=CONTEXT_TEXT)

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "validate_response"
    attrs = dict(span.attributes or {})
    assert attrs.get("openinference.span.kind") == "GUARDRAIL"
    assert attrs.get("arthur.task.id") == TASK_ID
    assert attrs.get("arthur.inference.id") == INFERENCE_ID
    assert attrs.get(SpanAttributes.INPUT_VALUE) == json.dumps(
        {"response": RESPONSE_TEXT, "context": CONTEXT_TEXT}
    )
    assert attrs.get(SpanAttributes.INPUT_MIME_TYPE) == "application/json"
    assert json.loads(attrs[SpanAttributes.OUTPUT_VALUE]) == MOCK_RESPONSE_RESULT
    assert attrs.get(SpanAttributes.OUTPUT_MIME_TYPE) == "application/json"
    arthur.shutdown()


def test_validate_response_span_on_error():
    arthur, exporter = _make_arthur_with_in_memory_spans()
    _validate_response_method(arthur).side_effect = ArthurAPIError(404, "not found")

    with pytest.raises(ArthurAPIError):
        arthur.validate_response(RESPONSE_TEXT, inference_id=INFERENCE_ID)

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].status.status_code.name == "ERROR"
    arthur.shutdown()


def test_validate_response_span_includes_session_and_user():
    arthur, exporter = _make_arthur_with_in_memory_spans()
    _validate_response_method(arthur).return_value = _mock_validation_response(MOCK_RESPONSE_RESULT)

    with arthur.attributes(session_id="vr-session", user_id="vr-user"):
        arthur.validate_response(RESPONSE_TEXT, inference_id=INFERENCE_ID)

    attrs = dict(exporter.get_finished_spans()[0].attributes or {})
    assert attrs.get(SpanAttributes.SESSION_ID) == "vr-session"
    assert attrs.get(SpanAttributes.USER_ID) == "vr-user"
    arthur.shutdown()


# ---------------------------------------------------------------------------
# End-to-end: prompt -> response uses returned inference_id
# ---------------------------------------------------------------------------


def test_validate_prompt_then_response_round_trip():
    arthur, exporter = _make_arthur_with_in_memory_spans()
    _validate_prompt_method(arthur).return_value = _mock_validation_response(MOCK_PROMPT_RESULT)
    _validate_response_method(arthur).return_value = _mock_validation_response(MOCK_RESPONSE_RESULT)

    prompt_result = arthur.validate_prompt(PROMPT_TEXT)
    arthur.validate_response(
        RESPONSE_TEXT,
        inference_id=prompt_result["inference_id"],
        context=CONTEXT_TEXT,
    )

    spans = exporter.get_finished_spans()
    names = [s.name for s in spans]
    assert names == ["validate_prompt", "validate_response"]
    for span in spans:
        attrs = dict(span.attributes or {})
        assert attrs.get("openinference.span.kind") == "GUARDRAIL"
        assert attrs.get("arthur.inference.id") == INFERENCE_ID
    arthur.shutdown()
