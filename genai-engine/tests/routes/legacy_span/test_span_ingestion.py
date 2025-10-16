import json
from unittest.mock import patch

import pytest
from opentelemetry.proto.trace.v1.trace_pb2 import (
    Status,
)

from tests.clients.base_test_client import GenaiEngineTestClientBase
from tests.routes.legacy_span.conftest import _create_base_trace_request, _create_span

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


@pytest.mark.unit_tests
def test_session_id_and_status_code_processing(
    client: GenaiEngineTestClientBase,
):
    """Test session_id and status_code extraction and normalization during span ingestion."""

    # Test cases: (session_id, status_code, expected_normalized_status)
    test_cases = [
        ("session_123", Status.STATUS_CODE_OK, "Ok"),
        ("session_456", Status.STATUS_CODE_ERROR, "Error"),
        ("session_789", Status.STATUS_CODE_UNSET, "Unset"),
        (None, Status.STATUS_CODE_OK, "Ok"),  # No session_id
    ]

    for i, (session_id, status_code, expected_status) in enumerate(test_cases):
        # Use unique task ID for each test case
        task_id = f"session_status_test_task_{i}"

        # Create trace request for this test case
        trace_request, resource_span, scope_span = _create_base_trace_request(
            task_id=task_id,
        )

        # Create span with specific session_id and status_code using helper function
        span = _create_span(
            trace_id=f"trace_session_test_{i}".encode(),
            span_id=f"span_session_test_{i}".encode(),
            name=f"test_span_{i}",
            span_type="LLM",
            status=Status(code=status_code),
            session_id=session_id,
        )

        scope_span.spans.append(span)
        resource_span.scope_spans.append(scope_span)
        trace_request.resource_spans.append(resource_span)

        # Send the trace
        ingestion_status, ingestion_response = client.receive_traces(
            trace_request.SerializeToString(),
        )
        assert ingestion_status == 200

        # Query the database directly to check if session_id and status_code were stored
        from db_models import DatabaseSpan
        from tests.clients.base_test_client import override_get_db_session

        db_session = override_get_db_session()

        # Find the span in the database by task_id
        db_spans = (
            db_session.query(DatabaseSpan).filter(DatabaseSpan.task_id == task_id).all()
        )
        assert (
            len(db_spans) == 1
        ), f"Expected 1 span, found {len(db_spans)} for task_id {task_id}"

        db_span = db_spans[0]

        # Verify session_id is correctly stored in database
        assert (
            db_span.session_id == session_id
        ), f"Expected session_id {session_id}, got {db_span.session_id} in database"

        # Verify status_code is correctly normalized and stored in database
        assert (
            db_span.status_code == expected_status
        ), f"Expected status_code {expected_status}, got {db_span.status_code} in database"
