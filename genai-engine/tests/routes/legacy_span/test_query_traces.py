from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from tests.clients.base_test_client import GenaiEngineTestClientBase

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

"""Helper functions for trace query tests."""


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
    assert trace.root_spans[0].span_name == "Agent"
    assert len(trace.root_spans[0].children) == 1
    assert trace.root_spans[0].children[0].span_kind == "RETRIEVER"
    assert trace.root_spans[0].children[0].span_name == "Retriever"

    # Test pagination
    status_code, response = client.query_traces(task_ids=["task1"], page=0, page_size=1)
    assert status_code == 200
    assert response.count == 2
    assert len(response.traces) == 1

    # Test time filtering
    now = datetime.now()
    status_code, response = client.query_traces(
        task_ids=["task1"],
        start_time=now - timedelta(days=3),
        end_time=now + timedelta(days=1),
    )
    assert status_code == 200
    assert (
        response.count == len(response.traces) == 2
    )  # trace1 and trace3 both have task1 spans


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
    assert status_code == 400  # All validation errors now return 400
    # Should have error response
    assert response is not None


@pytest.mark.unit_tests
def test_query_traces_span_features(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test span feature extraction."""

    status_code, response = client.query_traces(task_ids=["task1"])
    assert status_code == 200
    assert (
        response.count == len(response.traces) == 2
    )  # trace1 and trace3 both have task1 spans

    all_spans = get_all_spans_from_traces(response.traces)
    llm_spans = find_spans_by_kind(all_spans, "LLM")
    assert len(llm_spans) >= 1

    # Find span1 specifically (from trace1, which has the system prompt)
    span1 = None
    for span in llm_spans:
        if span.span_id == "span1":
            span1 = span
            break

    assert span1 is not None, "Could not find span1 in the response"

    # Verify LLM span features (should be from span1 in trace1)
    assert span1.span_kind == "LLM"
    assert span1.span_name == "ChatOpenAI"
    assert "arthur_span_version" in span1.raw_data

    # Test non-LLM span features
    non_llm_span = find_span_by_kind(all_spans, "CHAIN")
    assert non_llm_span is not None
    assert non_llm_span.span_kind == "CHAIN"
    assert non_llm_span.span_name == "Chain"


@pytest.mark.unit_tests
def test_query_traces_sorting(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test trace sorting behavior."""

    # Test default sorting (descending)
    status_code, response = client.query_traces(task_ids=["task1", "task2"])
    assert status_code == 200
    assert response.count == len(response.traces) == 3

    # Verify traces are sorted by start_time DESCENDING (most recent first)
    trace_ids = [trace.trace_id for trace in response.traces]
    assert trace_ids[0] == "trace3"  # trace3 is newest (base_time + 1 hour)
    assert trace_ids[1] == "trace2"  # trace2 is middle (base_time)
    assert trace_ids[2] == "trace1"  # trace1 is oldest (base_time - 2 days)

    # Verify start_times are in descending order
    for i in range(len(response.traces) - 1):
        assert response.traces[i].start_time >= response.traces[i + 1].start_time

    # Test explicit descending sorting
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        sort="desc",
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 3

    # Verify traces are sorted by start_time DESCENDING
    trace_ids = [trace.trace_id for trace in response.traces]
    assert trace_ids[0] == "trace3"  # newest
    assert trace_ids[1] == "trace2"  # middle
    assert trace_ids[2] == "trace1"  # oldest

    # Test ascending sorting
    status_code, response = client.query_traces(task_ids=["task1", "task2"], sort="asc")
    assert status_code == 200
    assert response.count == len(response.traces) == 3

    # Verify traces are sorted by start_time ASCENDING (oldest first)
    trace_ids = [trace.trace_id for trace in response.traces]
    assert trace_ids[0] == "trace1"  # oldest
    assert trace_ids[1] == "trace2"  # middle
    assert trace_ids[2] == "trace3"  # newest

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
    assert (
        response.count == len(response.traces) == 2
    )  # trace1 and trace3 both have task1 spans

    all_spans = get_all_spans_from_traces(response.traces)
    assert len(all_spans) == 4  # span1+span2 from trace1, span5+span6 from trace3

    # Verify we have both traces
    trace_ids = {trace.trace_id for trace in response.traces}
    assert trace_ids == {"trace1", "trace3"}

    # Verify metrics are computed for LLM spans
    for span in all_spans:
        assert hasattr(span, "metric_results")
        if span.span_kind == "LLM":
            assert len(span.metric_results) > 0

    # Test missing task IDs
    status_code, response = client.query_traces_with_metrics(task_ids=[])
    assert status_code == 400  # All validation errors now return 400
    # Should have error response
    assert response is not None


@pytest.mark.unit_tests
def test_query_traces_with_metrics_sorting(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test trace sorting behavior with metrics endpoint."""

    # Test default sorting (descending)
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1", "task2"],
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 3

    # Verify traces are sorted by start_time DESCENDING (most recent first)
    trace_ids = [trace.trace_id for trace in response.traces]
    assert trace_ids[0] == "trace3"  # newest (base_time + 1 hour)
    assert trace_ids[1] == "trace2"  # middle (base_time)
    assert trace_ids[2] == "trace1"  # oldest (base_time - 2 days)

    # Verify start_times are in descending order
    for i in range(len(response.traces) - 1):
        assert response.traces[i].start_time >= response.traces[i + 1].start_time

    # Test explicit descending sorting
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1", "task2"],
        sort="desc",
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 3

    # Verify traces are sorted by start_time DESCENDING
    trace_ids = [trace.trace_id for trace in response.traces]
    assert trace_ids[0] == "trace3"  # newest
    assert trace_ids[1] == "trace2"  # middle
    assert trace_ids[2] == "trace1"  # oldest

    # Test ascending sorting
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1", "task2"],
        sort="asc",
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 3

    # Verify traces are sorted by start_time ASCENDING (oldest first)
    trace_ids = [trace.trace_id for trace in response.traces]
    assert trace_ids[0] == "trace1"  # oldest
    assert trace_ids[1] == "trace2"  # middle
    assert trace_ids[2] == "trace3"  # newest

    # Verify start_times are in ascending order
    for i in range(len(response.traces) - 1):
        assert response.traces[i].start_time <= response.traces[i + 1].start_time

    # test pagination default sort page 0
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1", "task2"],
        sort="desc",
        page_size=1,
    )
    assert status_code == 200
    assert response.count == 3  # Full size
    assert len(response.traces) == 1  # Page size
    assert response.traces[0].trace_id == "trace3"  # trace3 is now the newest
    most_recent_trace = response.traces[0]

    # test pagination default sort page 1
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1", "task2"],
        sort="desc",
        page_size=1,
        page=1,
    )
    assert status_code == 200
    assert response.count == 3
    assert len(response.traces) == 1

    assert response.traces[0].trace_id == "trace2"  # trace2 is second newest

    # test pagination reverse sort
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1", "task2"],
        sort="asc",
        page_size=1,
    )
    assert status_code == 200
    assert response.count == 3
    assert len(response.traces) == 1
    assert response.traces[0].trace_id == "trace1"
    oldest_trace = response.traces[0]

    # test pagination reverse sort
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1", "task2"],
        sort="asc",
        page_size=1,
        page=1,
    )
    assert status_code == 200
    assert response.count == 3
    assert len(response.traces) == 1
    assert response.traces[0].trace_id == "trace2"

    # test pagination with time filters, filtering out the most recent trace (trace3)
    # so trace1 and trace2 should be returned, with trace2 first in desc order
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1", "task2"],
        end_time=most_recent_trace.start_time - timedelta(seconds=1),
        sort="desc",
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 2
    assert response.traces[0].trace_id == "trace2"  # most recent of remaining
    assert response.traces[1].trace_id == "trace1"  # oldest

    # test pagination with time filters, filtering out the oldest trace (trace1)
    # so trace2 and trace3 should be returned, with trace3 first in desc order
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1", "task2"],
        start_time=oldest_trace.end_time + timedelta(seconds=1),
        sort="desc",
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 2
    assert response.traces[0].trace_id == "trace3"  # most recent of remaining
    assert response.traces[1].trace_id == "trace2"  # middle


@pytest.mark.unit_tests
def test_metrics_computation_error_handling(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test error handling during metrics computation."""

    with patch(
        "services.trace.metrics_integration_service.get_metrics_engine",
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
def test_nested_structure(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test nested structure functionality including parent-child relationships and metrics."""

    # Test basic nested structure
    status_code, response = client.query_traces(task_ids=["task1"])
    assert status_code == 200
    assert (
        response.count == len(response.traces) == 2
    )  # trace1 and trace3 both have task1 spans

    # Find trace1 specifically which has the nested structure we want to test
    trace1 = next(trace for trace in response.traces if trace.trace_id == "trace1")
    assert len(trace1.root_spans) == 1

    # Verify parent-child relationship for Trace1
    root_span = trace1.root_spans[0]
    assert root_span.span_kind == "LLM"
    assert root_span.span_name == "ChatOpenAI"
    assert root_span.span_id == "span1"
    assert len(root_span.children) == 1

    child = root_span.children[0]
    assert child.span_kind == "CHAIN"
    assert child.span_name == "Chain"
    assert child.span_id == "span2"
    assert child.parent_span_id == root_span.span_id
    assert len(child.children) == 0

    # Test nested structure with metrics
    status_code, response = client.query_traces_with_metrics(task_ids=["task1"])
    assert status_code == 200
    assert (
        response.count == len(response.traces) == 2
    )  # trace1 and trace3 both have task1 spans

    # Find trace1 specifically which has the nested structure we want to test
    trace1 = next(trace for trace in response.traces if trace.trace_id == "trace1")
    root_span = trace1.root_spans[0]
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
    assert response.count == len(response.traces) == 3

    # Verify trace IDs
    trace_ids = {trace.trace_id for trace in response.traces}
    assert trace_ids == {"trace1", "trace2", "trace3"}


@pytest.mark.unit_tests
def test_span_ordering_within_traces(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test that spans within traces are always sorted by start_time in ascending order."""

    def verify_span_ordering(traces):
        for trace in traces:
            # Verify root spans are sorted by start_time (ascending)
            if len(trace.root_spans) > 1:
                for i in range(len(trace.root_spans) - 1):
                    assert (
                        trace.root_spans[i].start_time
                        <= trace.root_spans[i + 1].start_time
                    )

            # Verify children within each span are sorted by start_time (ascending)
            for root_span in trace.root_spans:
                if len(root_span.children) > 1:
                    for i in range(len(root_span.children) - 1):
                        assert (
                            root_span.children[i].start_time
                            <= root_span.children[i + 1].start_time
                        )

    # Test with regular endpoint
    status_code, response = client.query_traces(task_ids=["task1", "task2"])
    assert status_code == 200
    assert response.count == len(response.traces) == 3  # Now includes trace3
    verify_span_ordering(response.traces)

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
        task_ids=["task1", "task2"],
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 3  # Now includes trace3

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


# ============================================================================
# TRACE ID FILTERING TESTS (Basic functionality)
# ============================================================================


@pytest.mark.unit_tests
def test_trace_query_with_trace_ids_filter(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test trace filtering by trace IDs (basic functionality)."""

    # Test single trace ID filter
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        trace_ids=["trace1"],
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 1
    assert response.traces[0].trace_id == "trace1"

    # Test multiple trace IDs filter
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        trace_ids=["trace1", "trace2"],
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 2
    trace_ids = {trace.trace_id for trace in response.traces}
    assert trace_ids == {"trace1", "trace2"}

    # Test non-existent trace ID filter
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        trace_ids=["non_existent_trace"],
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 0
