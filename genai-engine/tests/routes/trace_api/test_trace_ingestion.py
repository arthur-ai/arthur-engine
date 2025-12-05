import json
from unittest.mock import patch

import pytest
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue
from opentelemetry.proto.trace.v1.trace_pb2 import ResourceSpans, ScopeSpans, Status

from db_models import DatabaseSpan
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)
from tests.routes.trace_api.conftest import _create_base_trace_request, _create_span

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


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
# CORE TRACE INGESTION TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_trace_api_receive_traces_with_resource_attributes(
    client: GenaiEngineTestClientBase,
    sample_trace_api_protobuf,
):
    """Test trace ingestion via API with resource attributes for task ID extraction."""

    # Test spans with task IDs in resource attributes (should be accepted)
    status_code, response_text = client.trace_api_receive_traces(
        sample_trace_api_protobuf,
    )
    assert status_code == 200

    response_json = json.loads(response_text)
    assert response_json["total_spans"] == 1
    assert response_json["accepted_spans"] == 1
    assert response_json["rejected_spans"] == 0
    assert response_json["status"] == "success"


@pytest.mark.unit_tests
def test_trace_api_receive_traces_missing_task_id(
    client: GenaiEngineTestClientBase,
):
    """Test trace ingestion with missing task ID should be accepted (unregistered trace)."""

    # Create trace without task ID in resource attributes
    trace_request, resource_span, scope_span = _create_base_trace_request(task_id=None)

    # Create a span without a task ID
    span = _create_span(
        trace_id=b"missing_task_id_trace_api",
        span_id=b"missing_task_id_span_api",
        name="missing_task_id_guardrail_span_api",
        span_type="GUARDRAIL",
    )

    scope_span.spans.append(span)
    resource_span.scope_spans.append(scope_span)
    trace_request.resource_spans.append(resource_span)

    # Send the trace
    status_code, response_text = client.trace_api_receive_traces(
        trace_request.SerializeToString(),
    )
    assert status_code == 200

    response_json = json.loads(response_text)
    assert response_json["accepted_spans"] == 1
    assert response_json["rejected_spans"] == 0
    assert response_json["status"] == "success"


@pytest.mark.unit_tests
def test_trace_api_receive_traces_multiple_spans(
    client: GenaiEngineTestClientBase,
):
    """Test ingesting trace with multiple spans including parent-child relationships."""

    # Create trace with task ID in resource attributes
    task_id = "multi_span_task_api"
    trace_id = b"multi_span_trace_api"
    parent_span_id = b"parent_span_api"
    child_span_id = b"child_span_api"

    trace_request, resource_span, scope_span = _create_base_trace_request(
        task_id=task_id,
    )

    # Create parent span
    parent_span = _create_span(
        trace_id=trace_id,
        span_id=parent_span_id,
        name="parent_span_api",
        span_type="LLM",
        model_name="gpt-4-turbo",
    )

    # Create child span
    child_span = _create_span(
        trace_id=trace_id,
        parent_span_id=parent_span_id,
        span_id=child_span_id,
        name="child_span_api",
        span_type="CHAIN",
        status=Status(message="ok", code=Status.STATUS_CODE_OK),
    )

    # Add spans in order that tests SQLAlchemy handling of optional parent_span_id
    scope_span.spans.append(child_span)  # Child first
    scope_span.spans.append(parent_span)  # Parent second
    resource_span.scope_spans.append(scope_span)
    trace_request.resource_spans.append(resource_span)

    # Send the trace
    status_code, response_text = client.trace_api_receive_traces(
        trace_request.SerializeToString(),
    )
    assert status_code == 200

    response_json = json.loads(response_text)
    assert response_json["total_spans"] == 2
    assert response_json["accepted_spans"] == 2
    assert response_json["rejected_spans"] == 0
    assert response_json["status"] == "success"


@pytest.mark.unit_tests
def test_trace_api_receive_traces_error_handling(
    client: GenaiEngineTestClientBase,
    sample_trace_api_protobuf,
):
    """Test error handling in trace API ingestion endpoint."""

    # Test invalid protobuf
    invalid_trace = b"invalid_protobuf_data_api"
    status_code, response_text = client.trace_api_receive_traces(invalid_trace)
    assert status_code == 400
    assert "Invalid protobuf message format" in json.loads(response_text)["detail"]

    # Test server error using patch
    with patch(
        "repositories.span_repository.SpanRepository.create_traces",
        side_effect=Exception("API Test error"),
    ):
        status_code, response_text = client.trace_api_receive_traces(
            sample_trace_api_protobuf,
        )
        assert status_code == 500
        assert "API Test error" in json.loads(response_text)["detail"]


@pytest.mark.unit_tests
def test_trace_api_resource_attributes_processing(
    client: GenaiEngineTestClientBase,
    sample_trace_api_protobuf,
):
    """Test resource attributes processing including task ID extraction and version injection."""

    # Send trace
    status_code, response_text = client.trace_api_receive_traces(
        sample_trace_api_protobuf,
    )
    assert status_code == 200

    # Query the trace using API to verify processing
    status_code, traces_response = client.trace_api_list_traces_metadata(
        task_ids=["api_task_123"],
    )
    assert status_code == 200

    assert traces_response.count == 1
    assert len(traces_response.traces) == 1

    # Get the full trace to check spans
    trace_id = traces_response.traces[0].trace_id
    status_code, trace_data = client.trace_api_get_trace_by_id(trace_id)
    assert status_code == 200

    # Check that all spans have the correct task ID and version
    all_spans = get_all_spans_from_traces([trace_data])
    for span in all_spans:
        # Verify task ID extraction
        assert span.task_id == "api_task_123"
        # Verify version injection
        assert "arthur_span_version" in span.raw_data
        assert span.raw_data["arthur_span_version"] == "arthur_span_v1"


@pytest.mark.unit_tests
def test_trace_api_session_id_and_status_code_processing(
    client: GenaiEngineTestClientBase,
):
    """Test session_id and status_code extraction and normalization during trace ingestion."""

    # Test cases: (session_id, status_code, expected_normalized_status)
    test_cases = [
        ("session_api_123", Status.STATUS_CODE_OK, "Ok"),
        ("session_api_456", Status.STATUS_CODE_ERROR, "Error"),
        (None, Status.STATUS_CODE_OK, "Ok"),  # No session_id
    ]

    for i, (session_id, status_code, expected_status) in enumerate(test_cases):
        # Use unique task ID for each test case
        task_id = f"session_status_api_test_{i}"

        # Create trace request for this test case
        trace_request, resource_span, scope_span = _create_base_trace_request(
            task_id=task_id,
        )

        # Create span with specific session_id and status_code
        span = _create_span(
            trace_id=f"trace_session_api_test_{i}".encode(),
            span_id=f"span_session_api_test_{i}".encode(),
            name=f"test_span_api_{i}",
            span_type="LLM",
            status=Status(code=status_code),
            session_id=session_id,
        )

        scope_span.spans.append(span)
        resource_span.scope_spans.append(scope_span)
        trace_request.resource_spans.append(resource_span)

        # Send the trace
        status_code, response_text = client.trace_api_receive_traces(
            trace_request.SerializeToString(),
        )
        assert status_code == 200

        # Query the database to verify processing
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

        # Verify session_id is correctly stored
        assert (
            db_span.session_id == session_id
        ), f"Expected session_id {session_id}, got {db_span.session_id}"

        # Verify status_code is correctly normalized and stored
        assert (
            db_span.status_code == expected_status
        ), f"Expected status_code {expected_status}, got {db_span.status_code}"


@pytest.mark.unit_tests
def test_trace_api_batch_ingestion_performance(
    client: GenaiEngineTestClientBase,
):
    """Test batch ingestion of multiple traces with multiple spans each."""

    # Create a large trace request with multiple traces
    task_id = "batch_test_api"
    trace_request, resource_span, scope_span = _create_base_trace_request(
        task_id=task_id,
    )

    # Create multiple traces with multiple spans each
    for trace_num in range(3):
        trace_id_bytes = f"batch_trace_api_{trace_num}".encode()

        # Create 2 spans per trace
        for span_num in range(2):
            span = _create_span(
                trace_id=trace_id_bytes,
                span_id=f"batch_span_api_{trace_num}_{span_num}".encode(),
                name=f"batch_span_{trace_num}_{span_num}",
                span_type="LLM" if span_num == 0 else "CHAIN",
                parent_span_id=(
                    f"batch_span_api_{trace_num}_0".encode() if span_num == 1 else None
                ),
            )
            scope_span.spans.append(span)

    resource_span.scope_spans.append(scope_span)
    trace_request.resource_spans.append(resource_span)

    # Send the batch
    status_code, response_text = client.trace_api_receive_traces(
        trace_request.SerializeToString(),
    )
    assert status_code == 200

    response_json = json.loads(response_text)
    assert response_json["total_spans"] == 6  # 3 traces * 2 spans each
    assert response_json["accepted_spans"] == 6
    assert response_json["rejected_spans"] == 0
    assert response_json["status"] == "success"

    # Verify traces were created correctly
    status_code, traces_data = client.trace_api_list_traces_metadata(task_ids=[task_id])
    assert status_code == 200
    assert traces_data.count == 3  # 3 traces created


@pytest.mark.unit_tests
def test_trace_api_token_count_calculation_from_messages(
    client: GenaiEngineTestClientBase,
):
    """Test that token counts and costs are calculated from messages when not provided."""

    # Create a trace with messages but no token count/cost attributes
    task_id = "token_calc_test_api"
    trace_request, resource_span, scope_span = _create_base_trace_request(
        task_id=task_id,
    )

    span = _create_span(
        trace_id=b"token_calc_trace_api",
        span_id=b"token_calc_span_api",
        name="token_calc_span",
        span_type="LLM",
        model_name="gpt-4-0613",
    )

    # Add input and output messages manually (no token count attributes)
    span.attributes.extend(
        [
            KeyValue(
                key="llm.input_messages.0.message.role",
                value=AnyValue(string_value="user"),
            ),
            KeyValue(
                key="llm.input_messages.0.message.content",
                value=AnyValue(string_value="Hello, how are you?"),
            ),
            KeyValue(
                key="llm.output_messages.0.message.role",
                value=AnyValue(string_value="assistant"),
            ),
            KeyValue(
                key="llm.output_messages.0.message.content",
                value=AnyValue(string_value="I'm doing well, thank you for asking!"),
            ),
        ],
    )

    scope_span.spans.append(span)
    resource_span.scope_spans.append(scope_span)
    trace_request.resource_spans.append(resource_span)

    # Send the trace
    status_code, response_text = client.trace_api_receive_traces(
        trace_request.SerializeToString(),
    )
    assert status_code == 200

    db_session = override_get_db_session()
    db_spans = (
        db_session.query(DatabaseSpan).filter(DatabaseSpan.task_id == task_id).all()
    )
    assert len(db_spans) == 1

    db_span = db_spans[0]

    assert db_span.prompt_token_count == 13
    assert db_span.completion_token_count == 17
    assert db_span.total_token_count == 30

    assert db_span.prompt_token_cost == 0.00039
    assert db_span.completion_token_cost == 0.00102
    assert db_span.total_token_cost == 0.00141
