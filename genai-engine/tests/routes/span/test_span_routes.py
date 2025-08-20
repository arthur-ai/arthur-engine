import json
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from tests.clients.base_test_client import GenaiEngineTestClientBase

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

"""Helper functions for span route tests."""


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


def find_spans_by_kind(spans, span_kind):
    """Helper function to find all spans matching the given kind."""
    return [span for span in spans if span.span_kind == span_kind]


def find_span_by_kind(spans, span_kind):
    """Helper function to find the first span matching the given kind."""
    matching_spans = find_spans_by_kind(spans, span_kind)
    return matching_spans[0] if matching_spans else None


# ============================================================================
# RECEIVE TRACES TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_receive_traces_accepts_all_spans(
    client: GenaiEngineTestClientBase,
    sample_openinference_trace,
    sample_span_missing_task_id,
):
    """Test that receive_traces accepts all spans regardless of attributes."""

    # Test normal spans with task IDs
    status_code, response = client.receive_traces(sample_openinference_trace)
    assert status_code == 200
    response_json = json.loads(response)
    assert response_json["total_spans"] == 2
    assert response_json["accepted_spans"] == 2
    assert response_json["rejected_spans"] == 0
    assert response_json["status"] == "success"

    # Test spans without task IDs
    status_code, response = client.receive_traces(sample_span_missing_task_id)
    assert status_code == 200
    response_json = json.loads(response)
    assert response_json["accepted_spans"] == 1
    assert response_json["rejected_spans"] == 0


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
def test_span_version_injection(
    client: GenaiEngineTestClientBase,
    sample_openinference_trace,
):
    """Test that spans have version injected."""
    status_code, response = client.receive_traces(sample_openinference_trace)
    assert status_code == 200

    # Query the spans to verify version injection
    # Only query by parent's task_id since child doesn't have task_id
    status_code, response = client.query_traces(
        task_ids=["task_id_706172656e745f7370616e5f69645f373839"],
    )
    assert status_code == 200

    # Check that all spans have the expected version
    all_spans = get_all_spans_from_traces(response.traces)
    for span in all_spans:
        assert "arthur_span_version" in span.raw_data
        assert span.raw_data["arthur_span_version"] == "arthur_span_v1"


# ============================================================================
# QUERY TRACES TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_query_traces_basic_functionality(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test basic query functionality."""

    # Test basic query
    status_code, response = client.query_traces(task_ids=["task2"])
    assert status_code == 200
    assert response.count == len(response.traces) == 1

    # Verify trace structure
    trace = response.traces[0]
    assert trace.trace_id == "trace2"
    assert len(trace.root_spans) == 1
    assert trace.root_spans[0].span_kind == "AGENT"
    assert len(trace.root_spans[0].children) == 1
    assert trace.root_spans[0].children[0].span_kind == "RETRIEVER"

    # Test pagination
    status_code, response = client.query_traces(task_ids=["task1"], page=0, page_size=1)
    assert status_code == 200
    assert response.count == len(response.traces) == 1

    # Test time filtering
    now = datetime.now()
    status_code, response = client.query_traces(
        task_ids=["task1"],
        start_time=now - timedelta(days=3),
        end_time=now + timedelta(days=1),
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 1


@pytest.mark.unit_tests
def test_query_traces_edge_cases(
    client: GenaiEngineTestClientBase,
):
    """Test edge cases for query_traces."""

    # Test with invalid filters (should return empty results, not errors)
    status_code, response = client.query_traces(
        task_ids=["task1"],
        trace_ids=["invalid_trace_id"],
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 0

    status_code, response = client.query_traces(task_ids=["invalid_task_id"])
    assert status_code == 200
    assert response.count == len(response.traces) == 0

    # Test missing task_ids
    status_code, response = client.query_traces(task_ids=[])
    assert status_code == 400
    response_json = json.loads(response)
    assert "Field required" in response_json["detail"]


@pytest.mark.unit_tests
def test_query_traces_span_features(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test span feature extraction."""

    status_code, response = client.query_traces(task_ids=["task1"])
    assert status_code == 200
    assert response.count == len(response.traces) == 1

    all_spans = get_all_spans_from_traces(response.traces)
    llm_span = find_span_by_kind(all_spans, "LLM")
    assert llm_span is not None

    # Verify LLM span features
    assert llm_span.system_prompt == "You are a helpful assistant."
    assert llm_span.user_query == "What is the weather like today?"
    assert llm_span.response == "I don't have access to real-time weather information."
    assert llm_span.span_kind == "LLM"
    assert "arthur_span_version" in llm_span.raw_data

    # Test non-LLM span features (should not be extracted)
    non_llm_span = find_span_by_kind(all_spans, "CHAIN")
    assert non_llm_span is not None
    assert non_llm_span.system_prompt is None
    assert non_llm_span.user_query is None
    assert non_llm_span.response is None
    assert non_llm_span.context is None
    assert non_llm_span.span_kind == "CHAIN"


@pytest.mark.unit_tests
def test_query_traces_sorting(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test trace sorting behavior."""

    # Test default sorting (descending)
    status_code, response = client.query_traces(task_ids=["task1", "task2"])
    assert status_code == 200
    assert response.count == len(response.traces) == 2

    # Verify traces are sorted by start_time DESCENDING (most recent first)
    trace_ids = [trace.trace_id for trace in response.traces]
    # task2 spans are newer, so trace2 should be first
    assert trace_ids[0] == "trace2"
    assert trace_ids[1] == "trace1"

    # Verify start_times are in descending order
    for i in range(len(response.traces) - 1):
        assert response.traces[i].start_time >= response.traces[i + 1].start_time

    # Test explicit descending sorting
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"], sort="desc"
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 2

    # Verify traces are sorted by start_time DESCENDING
    trace_ids = [trace.trace_id for trace in response.traces]
    assert trace_ids[0] == "trace2"
    assert trace_ids[1] == "trace1"

    # Test ascending sorting
    status_code, response = client.query_traces(task_ids=["task1", "task2"], sort="asc")
    assert status_code == 200
    assert response.count == len(response.traces) == 2

    # Verify traces are sorted by start_time ASCENDING (oldest first)
    trace_ids = [trace.trace_id for trace in response.traces]
    assert trace_ids[0] == "trace1"
    assert trace_ids[1] == "trace2"

    # Verify start_times are in ascending order
    for i in range(len(response.traces) - 1):
        assert response.traces[i].start_time <= response.traces[i + 1].start_time


# ============================================================================
# QUERY TRACES WITH METRICS TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_query_traces_with_metrics(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test the traces/metrics/ endpoint functionality."""

    # Test basic query with metrics computation
    status_code, response = client.query_traces_with_metrics(task_ids=["task1"])
    assert status_code == 200
    assert response.count == len(response.traces) == 1

    all_spans = get_all_spans_from_traces(response.traces)
    assert len(all_spans) == 2

    # Verify trace structure
    trace = response.traces[0]
    assert trace.trace_id == "trace1"
    assert len(trace.root_spans) == 1
    assert trace.root_spans[0].span_kind == "LLM"
    assert len(trace.root_spans[0].children) == 1
    assert trace.root_spans[0].children[0].span_kind == "CHAIN"

    # Verify metrics are computed for LLM spans
    for span in all_spans:
        assert hasattr(span, "metric_results")
        if span.span_kind == "LLM":
            assert len(span.metric_results) > 0

    # Test missing task IDs
    status_code, response = client.query_traces_with_metrics(task_ids=[])
    assert status_code == 400
    response_json = json.loads(response)
    assert "Field required" in response_json["detail"]


@pytest.mark.unit_tests
def test_query_traces_with_metrics_sorting(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test trace sorting behavior with metrics endpoint."""

    # Test default sorting (descending)
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1", "task2"]
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 2

    # Verify traces are sorted by start_time DESCENDING (most recent first)
    trace_ids = [trace.trace_id for trace in response.traces]
    # task2 spans are newer, so trace2 should be first
    assert trace_ids[0] == "trace2"
    assert trace_ids[1] == "trace1"

    # Verify start_times are in descending order
    for i in range(len(response.traces) - 1):
        assert response.traces[i].start_time >= response.traces[i + 1].start_time

    # Test explicit descending sorting
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1", "task2"], sort="desc"
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 2

    # Verify traces are sorted by start_time DESCENDING
    trace_ids = [trace.trace_id for trace in response.traces]
    assert trace_ids[0] == "trace2"
    assert trace_ids[1] == "trace1"

    # Test ascending sorting
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1", "task2"], sort="asc"
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 2

    # Verify traces are sorted by start_time ASCENDING (oldest first)
    trace_ids = [trace.trace_id for trace in response.traces]
    assert trace_ids[0] == "trace1"
    assert trace_ids[1] == "trace2"

    # Verify start_times are in ascending order
    for i in range(len(response.traces) - 1):
        assert response.traces[i].start_time <= response.traces[i + 1].start_time

    # test pagination default sort page 0
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1", "task2"], sort="desc", page_size=1
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 1
    assert response.traces[0].trace_id == "trace2"
    most_recent_trace = response.traces[0]

    # test pagination default sort page 1
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1", "task2"], sort="desc", page_size=1, page=1
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 1
    assert response.traces[0].trace_id == "trace1"

    # test pagination reverse sort
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1", "task2"], sort="asc", page_size=1
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 1
    assert response.traces[0].trace_id == "trace1"
    oldest_trace = response.traces[0]

    # test pagination reverse sort
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1", "task2"], sort="asc", page_size=1, page=1
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 1
    assert response.traces[0].trace_id == "trace2"

    # test pagination with time filters, filtering out the most recent trace
    # so only trace 1 should be returned
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1", "task2"],
        end_time=most_recent_trace.start_time - timedelta(seconds=1),
        sort="desc",
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 1
    assert response.traces[0].trace_id == "trace1"

    # test pagination with time filters, filtering out the oldest trace
    # so only trace 2 should be returned
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1", "task2"],
        start_time=oldest_trace.end_time + timedelta(seconds=1),
        sort="desc",
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 1
    assert response.traces[0].trace_id == "trace2"


@pytest.mark.unit_tests
def test_metrics_computation_error_handling(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test error handling during metrics computation."""

    with patch(
        "repositories.span_repository.get_metrics_engine",
        side_effect=Exception("Metrics engine error"),
    ):
        # This should not fail the entire request, just skip metrics computation
        status_code, response = client.query_traces_with_metrics(task_ids=["task2"])
        assert status_code == 200
        assert response.count > 0

        # Extract spans and verify they are returned but without metrics
        all_spans = get_all_spans_from_traces(response.traces)
        for span in all_spans:
            if span.span_kind == "LLM":
                assert hasattr(span, "metric_results")
                assert len(span.metric_results) == 0


# ============================================================================
# COMPUTE SPAN METRICS TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_compute_span_metrics(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test the span/{span_id}/metrics endpoint."""

    # Get a span ID - specifically get an LLM span
    status_code, response = client.query_traces(task_ids=["task1"])
    assert status_code == 200
    assert response.count > 0

    all_spans = get_all_spans_from_traces(response.traces)
    llm_span = find_span_by_kind(all_spans, "LLM")
    assert llm_span is not None
    span_id = llm_span.span_id

    # Test successful metrics computation
    status_code, response = client.query_span_metrics(span_id)
    assert status_code == 200
    assert response.span_id == span_id

    # Verify that the span has metrics
    assert hasattr(response, "metric_results")
    assert len(response.metric_results) > 0

    # Test non-existent span
    non_existent_span_id = "non_existent_span_id"
    status_code, response = client.query_span_metrics(non_existent_span_id)
    assert status_code == 400
    assert "not found" in response.lower()


# ============================================================================
# NESTED STRUCTURE TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_nested_structure_basic(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test basic nested structure functionality using existing fixture."""

    # Query by task1 to get the LLM span and its child
    status_code, response = client.query_traces(task_ids=["task1"])
    assert status_code == 200
    assert response.count == len(response.traces) == 1

    trace = response.traces[0]
    assert len(trace.root_spans) == 1

    # Verify parent-child relationship for Trace1
    root_span = trace.root_spans[0]
    assert root_span.span_kind == "LLM"
    assert root_span.span_id == "span1"
    assert len(root_span.children) == 1

    child = root_span.children[0]
    assert child.span_kind == "CHAIN"
    assert child.span_id == "span2"
    assert child.parent_span_id == root_span.span_id
    assert len(child.children) == 0

    # Query by task2 to get the AGENT span and its child
    status_code, response = client.query_traces(task_ids=["task2"])
    assert status_code == 200
    assert response.count == len(response.traces) == 1

    trace = response.traces[0]
    assert len(trace.root_spans) == 1

    # Verify parent-child relationship for Trace2
    root_span = trace.root_spans[0]
    assert root_span.span_kind == "AGENT"
    assert root_span.span_id == "span3"
    assert len(root_span.children) == 1

    child = root_span.children[0]
    assert child.span_kind == "RETRIEVER"
    assert child.span_id == "span4"
    assert child.parent_span_id == root_span.span_id
    assert len(child.children) == 0

    # Verify total spans in each trace
    all_spans_trace1 = get_all_spans_from_traces([trace])
    assert len(all_spans_trace1) == 2  # LLM + CHAIN spans


@pytest.mark.unit_tests
def test_nested_structure_with_metrics(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test that nested structure includes metrics in the appropriate spans."""

    status_code, response = client.query_traces_with_metrics(task_ids=["task1"])
    assert status_code == 200
    assert response.count == len(response.traces) == 1

    trace = response.traces[0]
    root_span = trace.root_spans[0]
    child_span = root_span.children[0]

    # Verify that the LLM span has metrics
    if root_span.span_kind == "LLM":
        assert len(root_span.metric_results) > 0
        # Verify metric result structure
        metric_result = root_span.metric_results[0]
        assert hasattr(metric_result, "metric_type")
        assert hasattr(metric_result, "prompt_tokens")
        assert hasattr(metric_result, "completion_tokens")
        assert hasattr(metric_result, "latency_ms")

    # Verify that non-LLM spans don't have metrics
    if child_span.span_kind != "LLM":
        assert len(child_span.metric_results) == 0

    # Test multiple traces structure
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1", "task2"],
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 2

    # Verify trace IDs
    trace_ids = {trace.trace_id for trace in response.traces}
    assert trace_ids == {"trace1", "trace2"}


@pytest.mark.unit_tests
def test_span_ordering_within_traces(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test that spans within traces are always sorted by start_time in ascending order."""

    status_code, response = client.query_traces(task_ids=["task1", "task2"])
    assert status_code == 200
    assert response.count == len(response.traces) == 2

    for trace in response.traces:
        # Verify root spans are sorted by start_time (ascending)
        if len(trace.root_spans) > 1:
            for i in range(len(trace.root_spans) - 1):
                assert (
                    trace.root_spans[i].start_time <= trace.root_spans[i + 1].start_time
                )

        # Verify children within each span are sorted by start_time (ascending)
        for root_span in trace.root_spans:
            if len(root_span.children) > 1:
                for i in range(len(root_span.children) - 1):
                    assert (
                        root_span.children[i].start_time
                        <= root_span.children[i + 1].start_time
                    )

    # Test with metrics endpoint as well
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1", "task2"]
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 2

    for trace in response.traces:
        # Verify root spans are sorted by start_time (ascending)
        if len(trace.root_spans) > 1:
            for i in range(len(trace.root_spans) - 1):
                assert (
                    trace.root_spans[i].start_time <= trace.root_spans[i + 1].start_time
                )

        # Verify children within each span are sorted by start_time (ascending)
        for root_span in trace.root_spans:
            if len(root_span.children) > 1:
                for i in range(len(root_span.children) - 1):
                    assert (
                        root_span.children[i].start_time
                        <= root_span.children[i + 1].start_time
                    )
