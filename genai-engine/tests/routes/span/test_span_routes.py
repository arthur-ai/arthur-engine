import json
import uuid
from unittest.mock import patch

import pytest

from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.mark.unit_tests
def test_receive_traces_happy_path(
    client: GenaiEngineTestClientBase,
    sample_openinference_trace,
):
    # Test with valid trace data
    status_code, response = client.receive_traces(sample_openinference_trace)
    assert status_code == 200
    # The response might be empty or a simple JSON object
    assert json.loads(response) == {
        "total_spans": 2,
        "accepted_spans": 2,
        "rejected_spans": 0,
        "rejection_reasons": [],
        "status": "success",
    }


@pytest.mark.unit_tests
def test_receive_traces_invalid_protobuf(client: GenaiEngineTestClientBase):
    # Test with invalid protobuf data
    invalid_trace = b"invalid_protobuf_data"

    status_code, response = client.receive_traces(invalid_trace)
    assert status_code == 400
    assert any(
        error_msg in response
        for error_msg in [
            "Invalid protobuf message format",
            "error parsing the body",
            "decode error",
            "json_invalid",
        ]
    )


@pytest.mark.unit_tests
def test_receive_traces_server_error(
    client: GenaiEngineTestClientBase,
    sample_openinference_trace,
):
    # Test with data that causes server error
    with patch(
        "repositories.span_repository.SpanRepository.create_traces",
        side_effect=Exception("Test error"),
    ):
        status_code, response = client.receive_traces(sample_openinference_trace)
        assert status_code == 500
        assert "Test error" in response or "An internal error occurred" in response


@pytest.mark.unit_tests
def test_receive_traces_response_types(
    client: GenaiEngineTestClientBase,
    sample_mixed_spans_trace,
    sample_all_rejected_spans_trace,
):
    # Test mixed spans - all spans should now be accepted
    status_code, response = client.receive_traces(sample_mixed_spans_trace)
    assert status_code == 200  # Success - all spans accepted
    response_json = json.loads(response)
    assert response_json["status"] == "success"
    assert response_json["accepted_spans"] == 2  # All spans accepted
    assert response_json["rejected_spans"] == 0  # No spans rejected

    # Test all spans without task IDs and without parent IDs - should all be accepted now
    status_code, response = client.receive_traces(sample_all_rejected_spans_trace)
    assert status_code == 200  # Success - all spans accepted
    response_json = json.loads(response)
    assert response_json["status"] == "success"
    assert response_json["accepted_spans"] == 2  # All spans accepted
    assert response_json["rejected_spans"] == 0  # No spans rejected


@pytest.mark.unit_tests
def test_spans_missing_task_id(
    client: GenaiEngineTestClientBase,
    sample_span_missing_task_id,
):
    # Test with a span missing task ID and no parent ID - should be accepted now
    status_code, response = client.receive_traces(sample_span_missing_task_id)
    response_json = json.loads(response)

    # Verify that the span was accepted
    assert status_code == 200  # Success
    assert response_json["accepted_spans"] == 1
    assert response_json["rejected_spans"] == 0
    assert response_json["status"] == "success"


@pytest.mark.unit_tests
def test_spans_with_parent_id_but_no_task_id(
    client: GenaiEngineTestClientBase,
    sample_span_with_parent_id,
):
    # Test with a span that has a parent ID but no task ID - should be accepted
    status_code, response = client.receive_traces(sample_span_with_parent_id)
    response_json = json.loads(response)

    # Verify that the span was accepted
    assert status_code == 200
    assert response_json["accepted_spans"] == 1
    assert response_json["rejected_spans"] == 0
    assert response_json["status"] == "success"


@pytest.mark.unit_tests
def test_span_version_injection(
    client: GenaiEngineTestClientBase,
    sample_openinference_trace,
):
    """Test that spans have the expected version injected into their raw data."""
    status_code, response = client.receive_traces(sample_openinference_trace)
    assert status_code == 200

    # Query the spans to verify version injection
    status_code, response = client.query_spans_with_metrics(task_ids=["test_task"])
    assert status_code == 200

    # Check that all spans have the expected version
    for span in response.spans:
        assert "arthur_span_version" in span.raw_data
        assert span.raw_data["arthur_span_version"] == "arthur_span_v1"


@pytest.mark.unit_tests
def test_query_spans_basic(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test basic spans query with existing metrics."""
    # Test basic query with task IDs
    status_code, response = client.query_spans(task_ids=["task1"])
    assert status_code == 200
    assert response.count == 2  # task1 has 2 spans
    assert len(response.spans) == 2
    assert all(span.task_id == "task1" for span in response.spans)

    # Verify that spans have metric_results field (even if empty)
    for span in response.spans:
        assert hasattr(span, "metric_results")


@pytest.mark.unit_tests
def test_query_spans_with_trace_ids(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test spans query with trace IDs filter."""
    # First get some spans to find trace IDs
    status_code, response = client.query_spans(task_ids=["task1"])
    assert status_code == 200
    assert len(response.spans) > 0

    trace_ids = [span.trace_id for span in response.spans]

    # Query by trace IDs
    status_code, response = client.query_spans(trace_ids=trace_ids)
    assert status_code == 200
    assert len(response.spans) > 0
    assert all(span.trace_id in trace_ids for span in response.spans)


@pytest.mark.unit_tests
def test_query_spans_with_span_ids(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test spans query with span IDs filter."""
    # First get some spans to find span IDs
    status_code, response = client.query_spans(task_ids=["task1"])
    assert status_code == 200
    assert len(response.spans) > 0

    span_ids = [span.span_id for span in response.spans]

    # Query by span IDs
    status_code, response = client.query_spans(span_ids=span_ids)
    assert status_code == 200
    assert len(response.spans) > 0
    assert all(span.span_id in span_ids for span in response.spans)


@pytest.mark.unit_tests
def test_query_spans_with_existing_metrics(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test spans query with existing metrics but no new computation."""
    # First create some spans with metrics
    status_code, response = client.query_spans_with_metrics(task_ids=["task1"])
    assert status_code == 200
    assert len(response.spans) > 0

    # Now query with existing metrics (should return the same metrics without recomputing)
    status_code, response = client.query_spans(task_ids=["task1"])
    assert status_code == 200
    assert len(response.spans) > 0

    # Verify that spans have metric_results field
    for span in response.spans:
        assert hasattr(span, "metric_results")
        # Should have existing metrics from the previous computation
        assert len(span.metric_results) > 0


@pytest.mark.unit_tests
def test_compute_span_metrics_success(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test computing metrics for a single span."""
    # First get a span ID
    status_code, response = client.query_spans(task_ids=["task1"])
    assert status_code == 200
    assert len(response.spans) > 0

    span_id = response.spans[0].id

    # Compute metrics for this span
    status_code, response = client.compute_span_metrics(span_id)
    assert status_code == 200
    assert response.count == 1
    assert len(response.spans) == 1
    assert response.spans[0].id == span_id

    # Verify that the span has metrics
    assert hasattr(response.spans[0], "metric_results")
    assert len(response.spans[0].metric_results) > 0


@pytest.mark.unit_tests
def test_compute_span_metrics_not_found(
    client: GenaiEngineTestClientBase,
):
    """Test computing metrics for a non-existent span."""
    non_existent_span_id = str(uuid.uuid4())

    status_code, response = client.compute_span_metrics(non_existent_span_id)
    assert status_code == 400
    assert "not found" in response.lower()


@pytest.mark.unit_tests
def test_compute_span_metrics_non_llm_span(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test computing metrics for a non-LLM span (should fail)."""
    # Get a span and modify it to be non-LLM in the database
    status_code, response = client.query_spans(task_ids=["task1"])
    assert status_code == 200
    assert len(response.spans) > 0

    span_id = response.spans[0].id

    # Modify the span to be non-LLM in the database
    from tests.conftest import override_get_db_session

    db_session = override_get_db_session()
    from db_models.db_models import DatabaseSpan

    span = db_session.query(DatabaseSpan).filter(DatabaseSpan.id == span_id).first()
    if span:
        span.span_kind = "internal"  # Change to non-LLM span kind
        db_session.commit()

    # Try to compute metrics for this non-LLM span
    status_code, response = client.compute_span_metrics(span_id)
    assert status_code == 400
    assert "not an LLM span" in response.lower()


@pytest.mark.unit_tests
def test_compute_span_metrics_no_task_id(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test computing metrics for a span without task_id (should fail)."""
    # Get a span and remove its task_id in the database
    status_code, response = client.query_spans(task_ids=["task1"])
    assert status_code == 200
    assert len(response.spans) > 0

    span_id = response.spans[0].id

    # Remove the task_id from the span in the database
    from tests.conftest import override_get_db_session

    db_session = override_get_db_session()
    from db_models.db_models import DatabaseSpan

    span = db_session.query(DatabaseSpan).filter(DatabaseSpan.id == span_id).first()
    if span:
        span.task_id = None  # Remove task_id
        db_session.commit()

    # Try to compute metrics for this span without task_id
    status_code, response = client.compute_span_metrics(span_id)
    assert status_code == 400
    assert "has no task_id" in response.lower()


@pytest.mark.unit_tests
def test_query_spans_with_metrics_happy_path(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test traces/metrics/ endpoint - computes metrics for all LLM spans in traces."""
    # Test basic query with task IDs
    status_code, response = client.query_spans_with_metrics(task_ids=["task1"])
    assert status_code == 200
    assert response.count == 2  # task1 has 2 spans
    assert len(response.spans) == 2
    assert all(span.task_id == "task1" for span in response.spans)

    # Verify that spans have metric_results field with computed metrics
    for span in response.spans:
        assert hasattr(span, "metric_results")
        # Should have computed metrics for LLM spans
        if span.span_kind == "LLM":
            assert len(span.metric_results) > 0


@pytest.mark.unit_tests
def test_query_spans_with_metrics_multiple_task_ids(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test traces/metrics/ endpoint with multiple task IDs."""
    # Test querying spans for multiple tasks
    status_code, response = client.query_spans_with_metrics(task_ids=["task1", "task2"])
    assert status_code == 200
    assert response.count == 4  # task1 has 2 spans, task2 has 2 spans
    assert len(response.spans) == 4
    task_ids = {span.task_id for span in response.spans}
    assert task_ids == {"task1", "task2"}


@pytest.mark.unit_tests
def test_query_spans_with_metrics_missing_task_ids(client: GenaiEngineTestClientBase):
    """Test traces/metrics/ endpoint with missing task IDs (should return 400)."""
    # Test with missing task IDs (should return 400)
    status_code, response = client.query_spans_with_metrics(task_ids=[])
    assert status_code == 400
    response_json = json.loads(response)
    assert "Field required" in response_json["detail"]


@pytest.mark.unit_tests
def test_span_features_extraction(
    client: GenaiEngineTestClientBase,
    sample_llm_span_with_features,
):
    """Test that span features are extracted and computed on-demand for LLM spans."""
    # Store the span with features
    status_code, response = client.receive_traces(sample_llm_span_with_features)
    assert status_code == 200
    response_json = json.loads(response)
    assert response_json["accepted_spans"] == 1
    assert response_json["rejected_spans"] == 0

    # Query the span to verify features are computed on-demand
    status_code, response = client.query_spans(task_ids=["test_task"])
    assert status_code == 200
    assert response.count == 1
    assert len(response.spans) == 1

    span = response.spans[0]

    # Verify span features are computed on-demand
    assert span.system_prompt == "You are a helpful assistant."
    assert span.user_query == "What is the weather like today?"
    assert span.response == "I don't have access to real-time weather information."
    assert span.context is not None
    assert len(span.context) == 1
    assert span.context[0]["role"] == "user"
    assert span.context[0]["content"] == "What is the weather like today?"

    # Verify span kind is set correctly
    assert span.span_kind == "LLM"

    # Verify version is present in raw_data
    assert "arthur_span_version" in span.raw_data
    assert span.raw_data["arthur_span_version"] == "arthur_span_v1"
