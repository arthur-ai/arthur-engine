import json
from unittest.mock import patch

import pytest

from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.mark.unit_tests
def test_receive_traces_all_spans_accepted(
    client: GenaiEngineTestClientBase,
    sample_openinference_trace,
):
    """Test that all spans are accepted and stored when receiving traces."""
    status_code, response = client.receive_traces(sample_openinference_trace)
    assert status_code == 200

    response_json = json.loads(response)
    assert response_json["total_spans"] == 2
    assert response_json["accepted_spans"] == 2
    assert response_json["rejected_spans"] == 0
    assert response_json["status"] == "success"


@pytest.mark.unit_tests
def test_receive_traces_spans_without_task_id_accepted(
    client: GenaiEngineTestClientBase,
    sample_span_missing_task_id,
):
    """Test that spans without task_id are accepted and stored."""
    status_code, response = client.receive_traces(sample_span_missing_task_id)
    assert status_code == 200

    response_json = json.loads(response)
    assert response_json["accepted_spans"] == 1
    assert response_json["rejected_spans"] == 0
    assert response_json["status"] == "success"


@pytest.mark.unit_tests
def test_receive_traces_spans_with_parent_id_accepted(
    client: GenaiEngineTestClientBase,
    sample_span_with_parent_id,
):
    """Test that spans with parent_id but no task_id are accepted and stored."""
    status_code, response = client.receive_traces(sample_span_with_parent_id)
    assert status_code == 200

    response_json = json.loads(response)
    assert response_json["accepted_spans"] == 1
    assert response_json["rejected_spans"] == 0
    assert response_json["status"] == "success"


@pytest.mark.unit_tests
def test_receive_traces_all_spans_accepted_regardless_of_attributes(
    client: GenaiEngineTestClientBase,
    sample_all_rejected_spans_trace,
):
    """Test that all spans are accepted regardless of whether they have task_id or parent_id."""
    status_code, response = client.receive_traces(sample_all_rejected_spans_trace)
    assert status_code == 200

    response_json = json.loads(response)
    assert response_json["total_spans"] == 2
    assert response_json["accepted_spans"] == 2
    assert response_json["rejected_spans"] == 0
    assert response_json["status"] == "success"


@pytest.mark.unit_tests
def test_receive_traces_mixed_spans_all_accepted(
    client: GenaiEngineTestClientBase,
    sample_mixed_spans_trace,
):
    """Test that mixed spans (with and without task_id) are all accepted."""
    status_code, response = client.receive_traces(sample_mixed_spans_trace)
    assert status_code == 200

    response_json = json.loads(response)
    assert response_json["total_spans"] == 2
    assert response_json["accepted_spans"] == 2
    assert response_json["rejected_spans"] == 0
    assert response_json["status"] == "success"


@pytest.mark.unit_tests
def test_receive_traces_invalid_protobuf(
    client: GenaiEngineTestClientBase,
):
    """Test handling of invalid protobuf data."""
    invalid_trace = b"invalid_protobuf_data"

    status_code, response = client.receive_traces(invalid_trace)
    assert status_code == 400
    assert "Invalid protobuf message format" in response


@pytest.mark.unit_tests
def test_receive_traces_server_error(
    client: GenaiEngineTestClientBase,
    sample_openinference_trace,
):
    """Test handling of server errors during trace processing."""
    with patch(
        "repositories.span_repository.SpanRepository.create_traces",
        side_effect=Exception("Test error"),
    ):
        status_code, response = client.receive_traces(sample_openinference_trace)
        assert status_code == 500
        assert "Test error" in response


@pytest.mark.unit_tests
def test_span_version_injection(
    client: GenaiEngineTestClientBase,
    sample_openinference_trace,
):
    """Test that spans have the expected version injected into their raw data."""
    status_code, response = client.receive_traces(sample_openinference_trace)
    assert status_code == 200

    # Query the spans to verify version injection
    status_code, response = client.query_spans(task_ids=["test_task"])
    assert status_code == 200

    # Check that all spans have the expected version
    for span in response.spans:
        assert "arthur_span_version" in span.raw_data
        assert span.raw_data["arthur_span_version"] == "arthur_span_v1"


@pytest.mark.unit_tests
def test_span_version_injection_without_existing_version(
    client: GenaiEngineTestClientBase,
):
    """Test that spans without existing version get the version injected."""
    from datetime import datetime, timedelta

    from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue
    from opentelemetry.proto.trace.v1.trace_pb2 import Span

    from tests.conftest import override_get_db_session
    from tests.routes.span.conftest import (
        _create_base_trace_request,
        _delete_spans_from_db,
    )

    # Create a trace without the version in raw_data
    trace_request, resource_span, scope_span = _create_base_trace_request()

    # Create a span without version
    span = Span()
    span.trace_id = b"version_test_trace"
    span.span_id = b"version_test_span"
    span.name = "version_test_span"
    span.kind = Span.SPAN_KIND_INTERNAL
    span.start_time_unix_nano = int(datetime.now().timestamp() * 1e9)
    span.end_time_unix_nano = int(
        (datetime.now() + timedelta(seconds=1)).timestamp() * 1e9,
    )

    # Add basic attributes without version
    attributes = [
        KeyValue(key="openinference.span.kind", value=AnyValue(string_value="LLM")),
        KeyValue(key="llm.model_name", value=AnyValue(string_value="gpt-4")),
    ]

    # Metadata with task ID
    metadata = {
        "ls_provider": "openai",
        "ls_model_name": "gpt-4",
        "ls_model_type": "chat",
        "arthur.task": "version_test_task",
    }

    metadata_str = str(metadata).replace("'", '"')
    attributes.append(
        KeyValue(
            key="metadata",
            value=AnyValue(string_value=metadata_str),
        ),
    )

    span.attributes.extend(attributes)
    scope_span.spans.append(span)
    resource_span.scope_spans.append(scope_span)
    trace_request.resource_spans.append(resource_span)

    # Send the trace
    status_code, response = client.receive_traces(trace_request.SerializeToString())
    assert status_code == 200

    # Query the span to verify version was injected
    status_code, response = client.query_spans(task_ids=["version_test_task"])
    assert status_code == 200
    assert len(response.spans) == 1

    span = response.spans[0]
    assert "arthur_span_version" in span.raw_data
    assert span.raw_data["arthur_span_version"] == "arthur_span_v1"

    # Cleanup - use the span_id from the response span
    span_ids = [span.span_id]
    db_session = override_get_db_session()
    _delete_spans_from_db(db_session, span_ids)


@pytest.mark.unit_tests
def test_query_spans_basic(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test basic spans query - returns all spans associated with the task's trace IDs."""
    status_code, response = client.query_spans(task_ids=["task2"])
    assert status_code == 200
    assert response.count == 2
    assert len(response.spans) == 2

    trace_ids = {span.trace_id for span in response.spans}
    assert len(trace_ids) == 1
    assert "trace2" in trace_ids

    # Verify that spans have metric_results field (even if empty)
    for span in response.spans:
        if span.span_kind == "LLM":
            assert hasattr(span, "metric_results")
            assert len(span.metric_results) == 0


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

    # Query by trace IDs (must also provide task_ids)
    status_code, response = client.query_spans(task_ids=["task1"], trace_ids=trace_ids)
    assert status_code == 200
    assert len(response.spans) > 0
    assert all(span.trace_id in trace_ids for span in response.spans)


@pytest.mark.unit_tests
def test_query_spans_with_existing_metrics(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test that query_spans returns existing metrics but doesn't compute new ones."""
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
        if span.span_kind == "LLM":
            assert hasattr(span, "metric_results")
            assert len(span.metric_results) > 0


@pytest.mark.unit_tests
def test_query_spans_without_metrics_computation(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test that query_spans doesn't compute new metrics even for LLM spans without existing metrics."""
    # Query spans without any prior metric computation
    status_code, response = client.query_spans(task_ids=["task1"])
    assert status_code == 200
    assert len(response.spans) > 0

    # Verify that spans have metric_results field
    for span in response.spans:
        if span.span_kind == "LLM":
            assert hasattr(span, "metric_results")
            assert len(span.metric_results) == 1


@pytest.mark.unit_tests
def test_query_spans_without_any_filters(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test span query without any filters (should return all spans)."""
    # Query without any filters (must provide task_ids)
    status_code, response = client.query_spans(task_ids=["task1", "task2"])
    assert status_code == 200
    assert len(response.spans) > 0  # Should return some spans

    # Verify that all returned spans have the expected structure
    for span in response.spans:
        assert hasattr(span, "id")
        assert hasattr(span, "trace_id")
        assert hasattr(span, "span_id")
        assert hasattr(span, "task_id")
        assert hasattr(span, "span_kind")
        assert hasattr(span, "raw_data")
        if span.span_kind == "LLM" and span.task_id == "task1":
            assert hasattr(span, "metric_results")
            assert len(span.metric_results) == 1


@pytest.mark.unit_tests
def test_query_spans_with_invalid_filters(
    client: GenaiEngineTestClientBase,
):
    """Test span query with invalid filters (should return empty results, not errors)."""
    # Test with invalid trace ID
    status_code, response = client.query_spans(
        task_ids=["task1"],
        trace_ids=["invalid_trace_id"],
    )
    assert status_code == 200
    assert len(response.spans) == 0

    # Test with invalid task ID
    status_code, response = client.query_spans(task_ids=["invalid_task_id"])
    assert status_code == 200
    assert len(response.spans) == 0


@pytest.mark.unit_tests
def test_pagination_behavior(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test pagination behavior for span queries."""
    # Test first page
    status_code, response = client.query_spans(task_ids=["task1"], page=0, page_size=1)
    assert status_code == 200
    assert len(response.spans) == 2  # task1 has 2 spans
    assert response.count == 2


@pytest.mark.unit_tests
def test_sorting_behavior(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test sorting behavior for span queries."""
    # Test descending sort (default)
    status_code, response = client.query_spans(task_ids=["task1"], sort="desc")
    assert status_code == 200
    assert len(response.spans) == 2

    # Test ascending sort
    status_code, response = client.query_spans(task_ids=["task1"], sort="asc")
    assert status_code == 200
    assert len(response.spans) == 2


@pytest.mark.unit_tests
def test_time_filtering(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test time-based filtering for span queries."""
    from datetime import datetime, timedelta

    # Get current time
    now = datetime.now()

    # Test filtering by start time
    status_code, response = client.query_spans(
        task_ids=["task1"],
        start_time=now - timedelta(days=3),
    )
    assert status_code == 200
    assert len(response.spans) == 2  # All spans should be within this range

    # Test filtering by end time
    status_code, response = client.query_spans(
        task_ids=["task1"],
        end_time=now + timedelta(days=1),
    )
    assert status_code == 200
    assert len(response.spans) == 2  # All spans should be within this range

    # Test filtering by both start and end time
    status_code, response = client.query_spans(
        task_ids=["task1"],
        start_time=now - timedelta(days=3),
        end_time=now + timedelta(days=1),
    )
    assert status_code == 200
    assert len(response.spans) == 2  # All spans should be within this range


@pytest.mark.unit_tests
def test_span_features_extraction_llm_span(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test that LLM span features are extracted and computed on-demand."""
    # Query the LLM span to verify features are computed on-demand
    status_code, response = client.query_spans(task_ids=["task1"])
    assert status_code == 200
    assert response.count == 2  # task1 has 2 spans
    assert len(response.spans) == 2

    # Find the LLM span
    llm_span = None
    for span in response.spans:
        if span.span_kind == "LLM":
            llm_span = span
            break

    assert llm_span is not None

    # Verify span features are computed on-demand
    assert llm_span.system_prompt == "You are a helpful assistant."
    assert llm_span.user_query == "What is the weather like today?"
    assert llm_span.response == "I don't have access to real-time weather information."
    assert llm_span.context is not None
    assert len(llm_span.context) == 2
    assert llm_span.context[0]["role"] == "system"
    assert llm_span.context[0]["content"] == "You are a helpful assistant."
    assert llm_span.context[1]["role"] == "user"
    assert llm_span.context[1]["content"] == "What is the weather like today?"

    # Verify span kind is set correctly
    assert llm_span.span_kind == "LLM"

    # Verify version is present in raw_data
    assert "arthur_span_version" in llm_span.raw_data
    assert llm_span.raw_data["arthur_span_version"] == "arthur_span_v1"


@pytest.mark.unit_tests
def test_span_features_extraction_non_llm_span(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test that non-LLM spans don't have features extracted."""
    # Query spans to find a non-LLM span
    status_code, response = client.query_spans(task_ids=["task1"])
    assert status_code == 200
    assert response.count == 2
    assert len(response.spans) == 2

    # Find the non-LLM span (CHAIN span)
    non_llm_span = None
    for span in response.spans:
        if span.span_kind == "CHAIN":
            non_llm_span = span
            break

    assert non_llm_span is not None

    # Verify span features are NOT extracted for non-LLM spans
    assert non_llm_span.system_prompt is None
    assert non_llm_span.user_query is None
    assert non_llm_span.response is None
    assert non_llm_span.context is None

    # Verify span kind is set correctly
    assert non_llm_span.span_kind == "CHAIN"

    # Verify version is present in raw_data
    assert "arthur_span_version" in non_llm_span.raw_data
    assert non_llm_span.raw_data["arthur_span_version"] == "arthur_span_v1"


@pytest.mark.unit_tests
def test_query_spans_with_metrics_happy_path(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test traces/metrics/ endpoint - computes metrics for all LLM spans in traces associated with task IDs."""
    # Test basic query with task IDs
    status_code, response = client.query_spans_with_metrics(task_ids=["task1"])
    assert status_code == 200
    assert (
        response.count == 2
    )  # task1 has 2 spans (one with task_id, one without but in same trace)
    assert len(response.spans) == 2

    # Verify that we get spans from the same trace, regardless of task_id
    trace_ids = {span.trace_id for span in response.spans}
    assert len(trace_ids) == 1  # All spans should be from the same trace
    assert "trace1" in trace_ids

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

    # Spans not associated with a task, but in the same trace are included,
    # and have a task_id of None
    assert task_ids == {None, "task1", "task2"}


@pytest.mark.unit_tests
def test_query_spans_with_metrics_missing_task_ids(
    client: GenaiEngineTestClientBase,
):
    """Test traces/metrics/ endpoint with missing task IDs (should return 400)."""
    # Test with missing task IDs (should return 400)
    status_code, response = client.query_spans_with_metrics(task_ids=[])
    assert status_code == 400
    response_json = json.loads(response)
    assert "Field required" in response_json["detail"]


@pytest.mark.unit_tests
def test_metrics_computation_only_for_llm_spans(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test that metrics are only computed for LLM spans, not other span types."""
    # Query spans with metrics computation
    status_code, response = client.query_spans_with_metrics(task_ids=["task1", "task2"])
    assert status_code == 200
    assert len(response.spans) > 0

    # Verify that only LLM spans have computed metrics
    llm_spans = [span for span in response.spans if span.span_kind == "LLM"]
    non_llm_spans = [span for span in response.spans if span.span_kind != "LLM"]

    # LLM spans should have computed metrics
    for span in llm_spans:
        assert len(span.metric_results) > 0

    # Non-LLM spans should not have computed metrics
    for span in non_llm_spans:
        assert len(span.metric_results) == 0


@pytest.mark.unit_tests
def test_metrics_computation_error_handling(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test error handling during metrics computation."""
    # Mock the metrics engine to raise an exception
    with patch(
        "repositories.span_repository.get_metrics_engine",
        side_effect=Exception("Metrics engine error"),
    ):
        # This should not fail the entire request, just skip metrics computation
        status_code, response = client.query_spans_with_metrics(task_ids=["task2"])
        assert status_code == 200
        assert len(response.spans) > 0

        # Spans should be returned but without metrics
        for span in response.spans:
            if span.span_kind == "LLM":
                assert hasattr(span, "metric_results")
                assert len(span.metric_results) == 0


@pytest.mark.unit_tests
def test_compute_span_metrics_success(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test computing metrics for a single span."""
    # First get a span ID - specifically get an LLM span
    status_code, response = client.query_spans(task_ids=["task1"])
    assert status_code == 200
    assert len(response.spans) > 0

    # Find an LLM span specifically
    llm_span = None
    for span in response.spans:
        if span.span_kind == "LLM":
            llm_span = span
            break

    assert llm_span is not None, "No LLM span found in test data"
    span_id = llm_span.span_id

    # Compute metrics for this span
    status_code, response = client.compute_span_metrics(span_id)
    assert status_code == 200
    assert response.count == 1
    assert len(response.spans) == 1
    assert response.spans[0].span_id == span_id  # Compare span_id, not id

    # Verify that the span has metrics
    assert hasattr(response.spans[0], "metric_results")
    assert len(response.spans[0].metric_results) > 0


@pytest.mark.unit_tests
def test_compute_span_metrics_not_found(
    client: GenaiEngineTestClientBase,
):
    """Test computing metrics for a non-existent span."""
    non_existent_span_id = "non_existent_span_id"  # Use a string span_id

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

    span_id = response.spans[0].span_id  # Use span_id, not id

    # Modify the span to be non-LLM in the database
    from tests.conftest import override_get_db_session

    db_session = override_get_db_session()
    from db_models.db_models import DatabaseSpan

    span = (
        db_session.query(DatabaseSpan).filter(DatabaseSpan.span_id == span_id).first()
    )
    if span:
        span.span_kind = "internal"  # Change to non-LLM span kind
        db_session.commit()

    # Try to compute metrics for this non-LLM span
    status_code, response = client.compute_span_metrics(span_id)
    assert status_code == 400
    assert "is not an llm span" in response.lower()


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

    # Find an LLM span specifically
    llm_span = None
    for span in response.spans:
        if span.span_kind == "LLM":
            llm_span = span
            break

    assert llm_span is not None, "No LLM span found in test data"
    span_id = llm_span.span_id

    # Remove the task_id from the span in the database
    from tests.conftest import override_get_db_session

    db_session = override_get_db_session()
    from db_models.db_models import DatabaseSpan

    span = (
        db_session.query(DatabaseSpan).filter(DatabaseSpan.span_id == span_id).first()
    )
    if span:
        span.task_id = None  # Remove task_id but keep it as LLM span
        db_session.commit()

    # Try to compute metrics for this span without task_id
    status_code, response = client.compute_span_metrics(span_id)
    assert status_code == 400
    assert "has no task_id" in response.lower()


@pytest.mark.unit_tests
def test_query_spans_missing_task_ids(
    client: GenaiEngineTestClientBase,
):
    """Test that query_spans endpoint requires task_ids."""
    # Test with empty task_ids list (should return 422 due to min_length=1)
    status_code, response = client.query_spans(task_ids=[])
    assert status_code == 400
    response_json = json.loads(response)
    assert "Field required" in response_json["detail"]
