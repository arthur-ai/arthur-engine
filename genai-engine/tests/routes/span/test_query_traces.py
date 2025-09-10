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
    assert response.count == len(response.traces) == 1

    all_spans = get_all_spans_from_traces(response.traces)
    llm_span = find_span_by_kind(all_spans, "LLM")
    assert llm_span is not None

    # Verify LLM span features
    assert llm_span.system_prompt == "You are a helpful assistant."
    assert llm_span.user_query == "What is the weather like today?"
    assert llm_span.response == "I don't have access to real-time weather information."
    assert llm_span.span_kind == "LLM"
    assert llm_span.span_name == "ChatOpenAI"
    assert "arthur_span_version" in llm_span.raw_data

    # Test non-LLM span features (should not be extracted)
    non_llm_span = find_span_by_kind(all_spans, "CHAIN")
    assert non_llm_span is not None
    assert non_llm_span.system_prompt is None
    assert non_llm_span.user_query is None
    assert non_llm_span.response is None
    assert non_llm_span.context is None
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
    assert response.count == len(response.traces) == 2

    # Verify traces are sorted by start_time DESCENDING (most recent first)
    trace_ids = [trace.trace_id for trace in response.traces]
    assert trace_ids[0] == "trace2"  # task2 spans are newer
    assert trace_ids[1] == "trace1"

    # Verify start_times are in descending order
    for i in range(len(response.traces) - 1):
        assert response.traces[i].start_time >= response.traces[i + 1].start_time

    # Test explicit descending sorting
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        sort="desc",
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
    assert trace.root_spans[0].span_name == "ChatOpenAI"
    assert len(trace.root_spans[0].children) == 1
    assert trace.root_spans[0].children[0].span_kind == "CHAIN"
    assert trace.root_spans[0].children[0].span_name == "Chain"

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
        task_ids=["task1", "task2"],
        sort="desc",
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 2

    # Verify traces are sorted by start_time DESCENDING
    trace_ids = [trace.trace_id for trace in response.traces]
    assert trace_ids[0] == "trace2"
    assert trace_ids[1] == "trace1"

    # Test ascending sorting
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1", "task2"],
        sort="asc",
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
        task_ids=["task1", "task2"],
        sort="desc",
        page_size=1,
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 1
    assert response.traces[0].trace_id == "trace2"
    most_recent_trace = response.traces[0]

    # test pagination default sort page 1
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1", "task2"],
        sort="desc",
        page_size=1,
        page=1,
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 1
    assert response.traces[0].trace_id == "trace1"

    # test pagination reverse sort
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1", "task2"],
        sort="asc",
        page_size=1,
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 1
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
        "services.metrics_integration_service.get_metrics_engine",
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
    assert response.count == len(response.traces) == 1

    trace = response.traces[0]
    assert len(trace.root_spans) == 1

    # Verify parent-child relationship for Trace1
    root_span = trace.root_spans[0]
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
    assert response.count == len(response.traces) == 2
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


# ============================================================================
# COMPREHENSIVE TRACE FILTERING TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_trace_query_with_trace_ids_filter(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test trace filtering by trace IDs."""

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


@pytest.mark.unit_tests
def test_trace_query_with_time_filters(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test trace filtering by time range."""
    now = datetime.now()

    # Test start_time filter - should return traces that start after the filter
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        start_time=now
        - timedelta(days=1, hours=1),  # Between task1 (2 days ago) and task2 (today)
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 1
    assert response.traces[0].trace_id == "trace2"  # Only task2 should be returned

    # Test end_time filter - should return traces that end before the filter
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        end_time=now - timedelta(hours=1),  # Before task2 (today)
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 1
    assert response.traces[0].trace_id == "trace1"  # Only task1 should be returned

    # Test both start_time and end_time filters
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        start_time=now - timedelta(days=3),
        end_time=now + timedelta(days=1),
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 2

    # Test time range that excludes all traces
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        start_time=now + timedelta(days=1),
        end_time=now + timedelta(days=2),
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 0


@pytest.mark.unit_tests
def test_trace_query_with_tool_name_filter(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test trace filtering by tool name."""

    # Note: The create_test_spans fixture doesn't create TOOL spans with specific tool names
    # so we test with non-existent tool names to verify filtering works
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        tool_name="test_tool",
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 0

    # Test with different tool name
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        tool_name="another_tool",
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 0


@pytest.mark.unit_tests
def test_trace_query_with_relevance_filters(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test trace filtering by query and response relevance scores."""

    # Test query relevance filters
    # Note: These should return empty results since we don't have relevance scores
    # in the test data that match these specific values
    test_cases = [
        {"query_relevance_eq": 0.85},
        {"query_relevance_gt": 0.8},
        {"query_relevance_gte": 0.85},
        {"query_relevance_lt": 0.9},
        {"query_relevance_lte": 0.85},
        {"response_relevance_eq": 0.85},
        {"response_relevance_gt": 0.8},
        {"response_relevance_gte": 0.85},
        {"response_relevance_lt": 0.9},
        {"response_relevance_lte": 0.85},
    ]

    for filter_params in test_cases:
        status_code, response = client.query_traces(
            task_ids=["task1", "task2"],
            **filter_params,
        )
        assert status_code == 200
        # These should return empty results or traces that match the filter
        assert response.count == len(response.traces)


@pytest.mark.unit_tests
def test_trace_query_with_tool_classification_filters(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test trace filtering by tool classification (tool_selection and tool_usage)."""

    # Test tool selection filter
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        tool_selection="CORRECT",  # ToolClassEnum.CORRECT
    )
    assert status_code == 200
    # Should return empty results since test data doesn't have tool classification metrics
    assert response.count == len(response.traces)

    # Test tool usage filter
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        tool_usage="INCORRECT",  # ToolClassEnum.INCORRECT
    )
    assert status_code == 200
    # Should return empty results since test data doesn't have tool classification metrics
    assert response.count == len(response.traces)


@pytest.mark.unit_tests
def test_trace_query_with_duration_filters(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test trace filtering by duration."""

    # Test duration filters
    # Note: Test spans have 1 second duration, so we test around that value
    test_cases = [
        {"trace_duration_eq": 1.0},  # Exactly 1 second
        {"trace_duration_gt": 0.5},  # Greater than 0.5 seconds
        {"trace_duration_gte": 1.0},  # Greater than or equal to 1 second
        {"trace_duration_lt": 2.0},  # Less than 2 seconds
        {"trace_duration_lte": 1.0},  # Less than or equal to 1 second
    ]

    for filter_params in test_cases:
        status_code, response = client.query_traces(
            task_ids=["task1", "task2"],
            **filter_params,
        )
        assert status_code == 200
        # Should return results that match the duration filter
        assert response.count == len(response.traces)


@pytest.mark.unit_tests
def test_trace_query_with_combined_filters(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test trace filtering with multiple filters combined."""
    now = datetime.now()

    # Test combining time and trace ID filters
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        trace_ids=["trace1"],
        start_time=now - timedelta(days=3),
        end_time=now + timedelta(days=1),
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 1
    assert response.traces[0].trace_id == "trace1"

    # Test combining time and duration filters
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        start_time=now - timedelta(days=3),
        end_time=now + timedelta(days=1),
        trace_duration_gte=0.5,
        trace_duration_lte=2.0,
    )
    assert status_code == 200
    # Should return traces that match both time and duration criteria
    assert response.count == len(response.traces)

    # Test combining relevance filters with time filters
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        start_time=now - timedelta(days=3),
        end_time=now + timedelta(days=1),
        query_relevance_gte=0.0,
        response_relevance_gte=0.0,
    )
    assert status_code == 200
    # Should return traces that match all criteria
    assert response.count == len(response.traces)


@pytest.mark.unit_tests
def test_trace_query_filter_validation(
    client: GenaiEngineTestClientBase,
):
    """Test validation of trace query filter parameters."""

    # Test invalid relevance score values (should be between 0 and 1)
    invalid_relevance_cases = [
        {"query_relevance_eq": -0.1},
        {"query_relevance_gt": 1.1},
        {"response_relevance_gte": -0.5},
        {"response_relevance_lt": 2.0},
    ]

    for filter_params in invalid_relevance_cases:
        status_code, response = client.query_traces(task_ids=["task1"], **filter_params)
        # Should return validation error
        assert status_code == 422 or status_code == 400

    # Test invalid duration values (should be positive)
    invalid_duration_cases = [
        {"trace_duration_eq": -1.0},
        {"trace_duration_gt": 0.0},  # Should be > 0
        {"trace_duration_gte": -0.5},
    ]

    for filter_params in invalid_duration_cases:
        status_code, response = client.query_traces(task_ids=["task1"], **filter_params)
        # Should return validation error
        assert status_code == 422 or status_code == 400


@pytest.mark.unit_tests
def test_trace_query_metrics_endpoint_with_filters(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test the traces/metrics/ endpoint with various filters."""
    now = datetime.now()

    # Test basic filtering with metrics computation
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1"],
        start_time=now - timedelta(days=3),
        end_time=now + timedelta(days=1),
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 1

    # Verify metrics are computed
    all_spans = get_all_spans_from_traces(response.traces)
    for span in all_spans:
        if span.span_kind == "LLM":
            assert len(span.metric_results) > 0

    # Test with trace ID filter and metrics
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1", "task2"],
        trace_ids=["trace2"],
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 1
    assert response.traces[0].trace_id == "trace2"

    # Test with duration filter and metrics
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1", "task2"],
        trace_duration_gte=0.5,
        trace_duration_lte=2.0,
    )
    assert status_code == 200
    # Should return traces that match duration criteria with metrics computed
    assert response.count == len(response.traces)


@pytest.mark.unit_tests
def test_trace_query_pagination_with_filters(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test pagination behavior with various filters applied."""
    now = datetime.now()

    # Test pagination with time filter
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        start_time=now - timedelta(days=3),
        end_time=now + timedelta(days=1),
        page=0,
        page_size=1,
        sort="desc",
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 1
    # Should return most recent trace first
    assert response.traces[0].trace_id == "trace2"

    # Test second page with time filter
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        start_time=now - timedelta(days=3),
        end_time=now + timedelta(days=1),
        page=1,
        page_size=1,
        sort="desc",
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 1
    # Should return older trace on second page
    assert response.traces[0].trace_id == "trace1"

    # Test pagination with ascending sort and filters
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        start_time=now - timedelta(days=3),
        end_time=now + timedelta(days=1),
        page=0,
        page_size=1,
        sort="asc",
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 1
    # Should return oldest trace first with ascending sort
    assert response.traces[0].trace_id == "trace1"

    # Test with metrics endpoint as well
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1", "task2"],
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


# ============================================================================
# COMPREHENSIVE TRACE FILTERING TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_trace_query_with_trace_ids_filter(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test trace filtering by trace IDs."""

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


@pytest.mark.unit_tests
def test_trace_query_with_time_filters(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test trace filtering by time range."""
    now = datetime.now()

    # Test start_time filter - should return traces that start after the filter
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        start_time=now
        - timedelta(days=1, hours=1),  # Between task1 (2 days ago) and task2 (today)
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 1
    assert response.traces[0].trace_id == "trace2"  # Only task2 should be returned

    # Test end_time filter - should return traces that end before the filter
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        end_time=now - timedelta(hours=1),  # Before task2 (today)
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 1
    assert response.traces[0].trace_id == "trace1"  # Only task1 should be returned

    # Test both start_time and end_time filters
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        start_time=now - timedelta(days=3),
        end_time=now + timedelta(days=1),
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 2

    # Test time range that excludes all traces
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        start_time=now + timedelta(days=1),
        end_time=now + timedelta(days=2),
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 0


@pytest.mark.unit_tests
def test_trace_query_with_tool_name_filter(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test trace filtering by tool name."""

    # Note: The create_test_spans fixture doesn't create TOOL spans with specific tool names
    # so we test with non-existent tool names to verify filtering works
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        tool_name="test_tool",
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 0

    # Test with different tool name
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        tool_name="another_tool",
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 0


@pytest.mark.unit_tests
def test_trace_query_with_relevance_filters(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test trace filtering by query and response relevance scores."""

    # Test query relevance filters
    # Note: These should return empty results since we don't have relevance scores
    # in the test data that match these specific values
    test_cases = [
        {"query_relevance_eq": 0.85},
        {"query_relevance_gt": 0.8},
        {"query_relevance_gte": 0.85},
        {"query_relevance_lt": 0.9},
        {"query_relevance_lte": 0.85},
        {"response_relevance_eq": 0.85},
        {"response_relevance_gt": 0.8},
        {"response_relevance_gte": 0.85},
        {"response_relevance_lt": 0.9},
        {"response_relevance_lte": 0.85},
    ]

    for filter_params in test_cases:
        status_code, response = client.query_traces(
            task_ids=["task1", "task2"],
            **filter_params,
        )
        assert status_code == 200
        # These should return empty results or traces that match the filter
        assert response.count == len(response.traces)


@pytest.mark.unit_tests
def test_trace_query_with_tool_classification_filters(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test trace filtering by tool classification (tool_selection and tool_usage)."""

    # Test tool selection filter
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        tool_selection="CORRECT",  # ToolClassEnum.CORRECT
    )
    assert status_code == 200
    # Should return empty results since test data doesn't have tool classification metrics
    assert response.count == len(response.traces)

    # Test tool usage filter
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        tool_usage="INCORRECT",  # ToolClassEnum.INCORRECT
    )
    assert status_code == 200
    # Should return empty results since test data doesn't have tool classification metrics
    assert response.count == len(response.traces)


@pytest.mark.unit_tests
def test_trace_query_with_duration_filters(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test trace filtering by duration."""

    # Test duration filters
    # Note: Test spans have 1 second duration, so we test around that value
    test_cases = [
        {"trace_duration_eq": 1.0},  # Exactly 1 second
        {"trace_duration_gt": 0.5},  # Greater than 0.5 seconds
        {"trace_duration_gte": 1.0},  # Greater than or equal to 1 second
        {"trace_duration_lt": 2.0},  # Less than 2 seconds
        {"trace_duration_lte": 1.0},  # Less than or equal to 1 second
    ]

    for filter_params in test_cases:
        status_code, response = client.query_traces(
            task_ids=["task1", "task2"],
            **filter_params,
        )
        assert status_code == 200
        # Should return results that match the duration filter
        assert response.count == len(response.traces)


@pytest.mark.unit_tests
def test_trace_query_with_combined_filters(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test trace filtering with multiple filters combined."""
    now = datetime.now()

    # Test combining time and trace ID filters
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        trace_ids=["trace1"],
        start_time=now - timedelta(days=3),
        end_time=now + timedelta(days=1),
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 1
    assert response.traces[0].trace_id == "trace1"

    # Test combining time and duration filters
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        start_time=now - timedelta(days=3),
        end_time=now + timedelta(days=1),
        trace_duration_gte=0.5,
        trace_duration_lte=2.0,
    )
    assert status_code == 200
    # Should return traces that match both time and duration criteria
    assert response.count == len(response.traces)

    # Test combining relevance filters with time filters
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        start_time=now - timedelta(days=3),
        end_time=now + timedelta(days=1),
        query_relevance_gte=0.0,
        response_relevance_gte=0.0,
    )
    assert status_code == 200
    # Should return traces that match all criteria
    assert response.count == len(response.traces)


@pytest.mark.unit_tests
def test_trace_query_filter_validation(
    client: GenaiEngineTestClientBase,
):
    """Test validation of trace query filter parameters."""

    # Test invalid relevance score values (should be between 0 and 1)
    invalid_relevance_cases = [
        {"query_relevance_eq": -0.1},
        {"query_relevance_gt": 1.1},
        {"response_relevance_gte": -0.5},
        {"response_relevance_lt": 2.0},
    ]

    for filter_params in invalid_relevance_cases:
        status_code, response = client.query_traces(task_ids=["task1"], **filter_params)
        # Should return validation error
        assert status_code == 422 or status_code == 400

    # Test invalid duration values (should be positive)
    invalid_duration_cases = [
        {"trace_duration_eq": -1.0},
        {"trace_duration_gt": 0.0},  # Should be > 0
        {"trace_duration_gte": -0.5},
    ]

    for filter_params in invalid_duration_cases:
        status_code, response = client.query_traces(task_ids=["task1"], **filter_params)
        # Should return validation error
        assert status_code == 422 or status_code == 400


@pytest.mark.unit_tests
def test_trace_query_metrics_endpoint_with_filters(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test the traces/metrics/ endpoint with various filters."""
    now = datetime.now()

    # Test basic filtering with metrics computation
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1"],
        start_time=now - timedelta(days=3),
        end_time=now + timedelta(days=1),
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 1

    # Verify metrics are computed
    all_spans = get_all_spans_from_traces(response.traces)
    for span in all_spans:
        if span.span_kind == "LLM":
            assert len(span.metric_results) > 0

    # Test with trace ID filter and metrics
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1", "task2"],
        trace_ids=["trace2"],
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 1
    assert response.traces[0].trace_id == "trace2"

    # Test with duration filter and metrics
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1", "task2"],
        trace_duration_gte=0.5,
        trace_duration_lte=2.0,
    )
    assert status_code == 200
    # Should return traces that match duration criteria with metrics computed
    assert response.count == len(response.traces)


@pytest.mark.unit_tests
def test_trace_query_pagination_with_filters(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test pagination behavior with various filters applied."""
    now = datetime.now()

    # Test pagination with time filter
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        start_time=now - timedelta(days=3),
        end_time=now + timedelta(days=1),
        page=0,
        page_size=1,
        sort="desc",
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 1
    # Should return most recent trace first
    assert response.traces[0].trace_id == "trace2"

    # Test second page with time filter
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        start_time=now - timedelta(days=3),
        end_time=now + timedelta(days=1),
        page=1,
        page_size=1,
        sort="desc",
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 1
    # Should return older trace on second page
    assert response.traces[0].trace_id == "trace1"

    # Test pagination with ascending sort and filters
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        start_time=now - timedelta(days=3),
        end_time=now + timedelta(days=1),
        page=0,
        page_size=1,
        sort="asc",
    )
    assert status_code == 200
    assert response.count == len(response.traces) == 1
    # Should return oldest trace first with ascending sort
    assert response.traces[0].trace_id == "trace1"
