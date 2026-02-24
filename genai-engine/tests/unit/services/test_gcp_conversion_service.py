"""Unit tests for GcpConversionService and GCP span_kind extraction in SpanRepository."""

from unittest.mock import MagicMock, patch

import pytest
from openinference.semconv.trace import SpanAttributes

from services.trace.gcp_conversion_service import GcpConversionService
from utils import trace as trace_utils


# ---------------------------------------------------------------------------
# GcpConversionService._determine_span_kind
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "labels,expected_kind",
    [
        ({"gen_ai.agent.name": "my-agent"}, "AGENT"),
        ({"gen_ai.tool.name": "search"}, "TOOL"),
        ({"gen_ai.request.model": "gemini-pro"}, "LLM"),
        ({SpanAttributes.LLM_MODEL_NAME: "gpt-4"}, "LLM"),
        ({"custom.label": "value"}, "UNKNOWN"),
        # Priority: AGENT > TOOL > LLM
        ({"gen_ai.agent.name": "my-agent", "gen_ai.tool.name": "search"}, "AGENT"),
        ({"gen_ai.tool.name": "search", "gen_ai.request.model": "gpt-4"}, "TOOL"),
    ],
)
def test_determine_span_kind(labels, expected_kind):
    service = GcpConversionService()
    assert service._determine_span_kind(labels) == expected_kind


# ---------------------------------------------------------------------------
# After convert_gcp_labels_to_openinference, dotted keys are exploded into
# nested dicts. Verify that get_nested_value (used in span_repository after
# the fix) can read them, while flat .get() cannot.
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "labels,expected_kind",
    [
        ({"gen_ai.agent.name": "my-agent"}, "AGENT"),
        ({"gen_ai.tool.name": "search"}, "TOOL"),
        ({"gen_ai.request.model": "gemini-pro"}, "LLM"),
        ({"custom.label": "value"}, "UNKNOWN"),
    ],
)
def test_span_kind_survives_key_explosion(labels, expected_kind):
    service = GcpConversionService()
    attributes = service.convert_gcp_labels_to_openinference(labels)

    # Flat .get() must NOT find it — the key was exploded into a nested dict.
    assert attributes.get(SpanAttributes.OPENINFERENCE_SPAN_KIND) is None
    # get_nested_value must find it — this is the fix in span_repository.
    assert (
        trace_utils.get_nested_value(attributes, SpanAttributes.OPENINFERENCE_SPAN_KIND)
        == expected_kind
    )


@pytest.mark.unit_tests
def test_session_id_survives_key_explosion():
    service = GcpConversionService()
    attributes = service.convert_gcp_labels_to_openinference(
        {"gen_ai.conversation.id": "sess-abc"}
    )

    assert attributes.get(SpanAttributes.SESSION_ID) is None
    assert (
        trace_utils.get_nested_value(attributes, SpanAttributes.SESSION_ID)
        == "sess-abc"
    )


# ---------------------------------------------------------------------------
# SpanRepository.create_traces_from_gcp — span_kind on DatabaseSpan
# ---------------------------------------------------------------------------


def _ingest_gcp_trace(labels: dict) -> list:
    from repositories.span_repository import SpanRepository

    mock_session = MagicMock()
    repo = SpanRepository(mock_session, MagicMock(), MagicMock())
    gcp_trace = {
        "traceId": "abc123",
        "spans": [
            {
                "spanId": "1",
                "name": "test-span",
                "startTime": "2026-01-01T00:00:00Z",
                "endTime": "2026-01-01T00:00:01Z",
                "labels": labels,
            }
        ],
    }
    with patch.object(repo.trace_ingestion_service, "_store_spans"):
        spans, _ = repo.create_traces_from_gcp(gcp_trace, task_id="task-1")
    return spans


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "labels,expected_kind",
    [
        ({"gen_ai.agent.name": "orchestrator"}, "AGENT"),
        ({"gen_ai.tool.name": "calculator"}, "TOOL"),
        ({"gen_ai.request.model": "gemini-1.5-pro"}, "LLM"),
        ({}, "UNKNOWN"),
    ],
)
def test_create_traces_from_gcp_sets_correct_span_kind(labels, expected_kind):
    spans = _ingest_gcp_trace(labels)
    assert len(spans) == 1
    assert spans[0].span_kind == expected_kind
    # span_kind column and raw_data must agree
    raw_kind = trace_utils.get_nested_value(
        spans[0].raw_data.get("attributes", {}),
        SpanAttributes.OPENINFERENCE_SPAN_KIND,
    )
    assert spans[0].span_kind == raw_kind


@pytest.mark.unit_tests
def test_create_traces_from_gcp_sets_session_id():
    spans = _ingest_gcp_trace(
        {"gen_ai.conversation.id": "sess-xyz", "gen_ai.request.model": "gpt-4"}
    )
    assert spans[0].session_id == "sess-xyz"
