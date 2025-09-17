import json
from unittest.mock import patch

import pytest

from tests.clients.base_test_client import GenaiEngineTestClientBase

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

"""Helper functions for span ingestion tests."""


def get_all_spans_from_traces(traces):
    """Helper function to extract all spans from traces response."""
    spans = []
    for trace in traces:
        for root_span in trace.root_spans:
            spans.extend(get_all_spans_from_nested_span(root_span))
    return spans


def get_all_spans_from_nested_span(nested_span):
    """Helper function to extract all spans from a nested span structure recursively."""
    spans = [nested_span]
    for child in nested_span.children:
        spans.extend(get_all_spans_from_nested_span(child))
    return spans


# ============================================================================
# RECEIVE TRACES TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_receive_traces_with_resource_attributes(
    client: GenaiEngineTestClientBase,
    sample_openinference_trace,
    sample_span_missing_task_id,
    sample_openinference_trace_multiple_spans,
):
    """Test receive_traces with resource attributes for task ID extraction."""

    # Test spans with task IDs in resource attributes (should be accepted)
    status_code, response = client.receive_traces(sample_openinference_trace)
    assert status_code == 200
    response_json = json.loads(response)
    assert response_json["total_spans"] == 1
    assert response_json["accepted_spans"] == 1
    assert response_json["rejected_spans"] == 0
    assert response_json["status"] == "success"

    # Test spans without task IDs in resource attributes (should be rejected)
    status_code, response = client.receive_traces(sample_span_missing_task_id)
    assert status_code == 422
    response_json = json.loads(response)
    assert response_json["accepted_spans"] == 0
    assert response_json["rejected_spans"] == 1
    assert (
        "Missing or invalid task ID in resource attributes"
        in response_json["rejection_reasons"][0]
    )

    # test inserting trace with spans with and without parent_span_id
    status_code, response = client.receive_traces(
        sample_openinference_trace_multiple_spans,
    )
    assert status_code == 200
    response_json = json.loads(response)
    assert response_json["total_spans"] == 2
    assert response_json["accepted_spans"] == 2
    assert response_json["rejected_spans"] == 0
    assert response_json["status"] == "success"


@pytest.mark.unit_tests
def test_receive_traces_error_handling(
    client: GenaiEngineTestClientBase,
    sample_openinference_trace,
):
    """Test error handling in receive_traces endpoint."""

    # Test invalid protobuf
    invalid_trace = b"invalid_protobuf_data"
    status_code, response = client.receive_traces(invalid_trace)
    assert status_code == 400
    assert "Invalid protobuf message format" in response

    # Test server error
    with patch(
        "repositories.span_repository.SpanRepository.create_traces",
        side_effect=Exception("Test error"),
    ):
        status_code, response = client.receive_traces(sample_openinference_trace)
        assert status_code == 500
        assert "Test error" in response


@pytest.mark.unit_tests
def test_resource_attributes_processing(
    client: GenaiEngineTestClientBase,
    sample_openinference_trace,
):
    """Test resource attributes processing including task ID extraction and version injection."""
    status_code, response = client.receive_traces(sample_openinference_trace)
    assert status_code == 200

    # Query the spans to verify processing
    status_code, response = client.query_traces(
        task_ids=["task_id_123"],
    )
    assert status_code == 200

    # Check that all spans have the correct task ID and version
    all_spans = get_all_spans_from_traces(response.traces)
    for span in all_spans:
        # Verify task ID extraction
        assert span.task_id == "task_id_123"
        # Verify version injection
        assert "arthur_span_version" in span.raw_data
        assert span.raw_data["arthur_span_version"] == "arthur_span_v1"
