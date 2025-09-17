import json
from datetime import datetime, timedelta

import pytest

from tests.clients.base_test_client import GenaiEngineTestClientBase

# ============================================================================
# HELPER FUNCTIONS (reused from test_query_traces.py)
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


def find_spans_by_kind(spans, span_kind):
    """Helper function to find all spans matching the given kind."""
    return [span for span in spans if span.span_kind == span_kind]


def find_span_by_kind(spans, span_kind):
    """Helper function to find the first span matching the given kind."""
    matching_spans = find_spans_by_kind(spans, span_kind)
    return matching_spans[0] if matching_spans else None


# ============================================================================
# FILTERING TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_trace_query_with_span_types_filter(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test trace filtering by span types."""

    # Test single span type filter - LLM spans (should return trace1 and trace3)
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        span_types=["LLM"],
    )
    assert status_code == 200
    assert response.count == 2
    assert len(response.traces) == 2
    trace_ids = {trace.trace_id for trace in response.traces}
    assert trace_ids == {"trace1", "trace3"}

    # Verify that returned traces contain LLM spans
    all_spans = get_all_spans_from_traces(response.traces)
    llm_spans = find_spans_by_kind(all_spans, "LLM")
    assert len(llm_spans) == 2  # One LLM span in each trace

    # Test single span type filter - AGENT spans (should return only trace2)
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        span_types=["AGENT"],
    )
    assert status_code == 200
    assert response.count == 1
    assert len(response.traces) == 1
    assert response.traces[0].trace_id == "trace2"

    # Verify that returned trace contains AGENT spans
    all_spans = get_all_spans_from_traces(response.traces)
    agent_spans = find_spans_by_kind(all_spans, "AGENT")
    assert len(agent_spans) == 1

    # Test multiple span types filter (should return all three traces)
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        span_types=["LLM", "AGENT"],
    )
    assert status_code == 200
    assert response.count == 3
    assert len(response.traces) == 3
    trace_ids = {trace.trace_id for trace in response.traces}
    assert trace_ids == {"trace1", "trace2", "trace3"}

    # Test with CHAIN span type (should return only trace1)
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        span_types=["CHAIN"],
    )
    assert status_code == 200
    assert response.count == 1
    assert len(response.traces) == 1
    assert response.traces[0].trace_id == "trace1"

    # Test with RETRIEVER span type (should return only trace2)
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        span_types=["RETRIEVER"],
    )
    assert status_code == 200
    assert response.count == 1
    assert len(response.traces) == 1
    assert response.traces[0].trace_id == "trace2"

    # Test with TOOL span type (should return only trace3)
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        span_types=["TOOL"],
    )
    assert status_code == 200
    assert response.count == 1
    assert len(response.traces) == 1
    assert response.traces[0].trace_id == "trace3"

    # Test with multiple span types including TOOL (both traces have LLM, trace3 has TOOL)
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        span_types=["LLM", "TOOL"],
    )
    assert status_code == 200
    assert response.count == 2
    assert len(response.traces) == 2
    trace_ids = {trace.trace_id for trace in response.traces}
    assert trace_ids == {"trace1", "trace3"}

    # Test with span type that doesn't exist in test data
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        span_types=["EMBEDDING"],
    )
    assert status_code == 200
    assert response.count == 0
    assert len(response.traces) == 0


@pytest.mark.unit_tests
def test_trace_query_with_time_filters(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test trace filtering by time range."""
    now = datetime.now()

    # Test start_time filter - should return trace2 and trace3 (recent traces)
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        start_time=now - timedelta(days=1, hours=1),
    )
    assert status_code == 200
    assert response.count == 2
    assert len(response.traces) == 2
    trace_ids = {trace.trace_id for trace in response.traces}
    assert trace_ids == {"trace2", "trace3"}

    # Test end_time filter - should return only trace1 (old trace)
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        end_time=now - timedelta(hours=1),
    )
    assert status_code == 200
    assert response.count == 1
    assert len(response.traces) == 1
    assert response.traces[0].trace_id == "trace1"

    # Test both start_time and end_time filters - should return all traces
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        start_time=now - timedelta(days=3),
        end_time=now + timedelta(days=1),
    )
    assert status_code == 200
    assert response.count == 3
    assert len(response.traces) == 3
    trace_ids = {trace.trace_id for trace in response.traces}
    assert trace_ids == {"trace1", "trace2", "trace3"}

    # Test time range that excludes all traces
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        start_time=now + timedelta(days=1),
        end_time=now + timedelta(days=2),
    )
    assert status_code == 200
    assert response.count == 0
    assert len(response.traces) == 0


@pytest.mark.unit_tests
def test_trace_query_with_tool_name_filter(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test trace filtering by tool name."""

    # Test with existing tool name - should return trace3 which has the test_tool
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        tool_name="test_tool",
    )
    assert status_code == 200
    assert response.count == 1
    assert len(response.traces) == 1
    assert response.traces[0].trace_id == "trace3"

    # Test with non-existent tool name - should return empty
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        tool_name="another_tool",
    )
    assert status_code == 200
    assert response.count == 0
    assert len(response.traces) == 0

    # Test tool name filtering combined with span types
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        tool_name="test_tool",
        span_types=["TOOL"],
    )
    assert status_code == 200
    assert response.count == 1
    assert len(response.traces) == 1
    assert response.traces[0].trace_id == "trace3"


@pytest.mark.unit_tests
def test_trace_query_with_relevance_filters(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test trace filtering by query and response relevance scores."""

    # Test query_relevance >= 0.8 - should return only trace1 (score 0.85)
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        query_relevance_gte=0.8,
    )
    assert status_code == 200
    assert response.count == 1
    assert len(response.traces) == 1
    assert response.traces[0].trace_id == "trace1"

    # Test query_relevance >= 0.5 - should return both trace1 (0.85) and trace3 (0.45)
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        query_relevance_gte=0.4,
    )
    assert status_code == 200
    assert response.count == 2
    assert len(response.traces) == 2
    trace_ids = {trace.trace_id for trace in response.traces}
    assert trace_ids == {"trace1", "trace3"}

    # Test response_relevance > 0.9 - should return only trace1 (score 0.92)
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        response_relevance_gt=0.9,
    )
    assert status_code == 200
    assert response.count == 1
    assert len(response.traces) == 1
    assert response.traces[0].trace_id == "trace1"

    # Test response_relevance >= 0.3 - should return both traces
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        response_relevance_gte=0.3,
    )
    assert status_code == 200
    assert response.count == 2
    assert len(response.traces) == 2
    trace_ids = {trace.trace_id for trace in response.traces}
    assert trace_ids == {"trace1", "trace3"}

    # Test very high threshold - should return empty
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        query_relevance_gte=0.95,
    )
    assert status_code == 200
    assert response.count == 0
    assert len(response.traces) == 0


@pytest.mark.unit_tests
def test_trace_query_with_duration_filters(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test trace filtering by duration."""

    # Test duration >= 5 - should return trace1 (~1 day) and trace2 (~31s), filter out trace3 (~4s)
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        trace_duration_gte=5,
    )
    assert status_code == 200
    assert response.count == 2
    assert len(response.traces) == 2
    trace_ids = {trace.trace_id for trace in response.traces}
    assert trace_ids == {"trace1", "trace2"}

    # Test duration <= 40 - should return trace2 (31 seconds) and trace3 (4 seconds)
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        trace_duration_lte=40,
    )
    assert status_code == 200
    assert response.count == 2
    assert len(response.traces) == 2
    trace_ids = {trace.trace_id for trace in response.traces}
    assert trace_ids == {"trace2", "trace3"}

    # Test duration >= 30 - should return trace1 and trace2 (but not trace3)
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        trace_duration_gte=30,
    )
    assert status_code == 200
    assert response.count == 2
    assert len(response.traces) == 2
    trace_ids = {trace.trace_id for trace in response.traces}
    assert trace_ids == {"trace1", "trace2"}

    # Test duration > 3600 - should return only trace1 (1 day duration)
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        trace_duration_gt=3600,
    )
    assert status_code == 200
    assert response.count == 1
    assert len(response.traces) == 1
    assert response.traces[0].trace_id == "trace1"


@pytest.mark.unit_tests
def test_trace_query_with_combined_filters(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test trace filtering with multiple filters combined."""
    now = datetime.now()

    # Test combining span_types with time and duration filters - should return both LLM traces
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        span_types=["LLM"],
        start_time=now - timedelta(days=3),
        end_time=now + timedelta(days=1),
        trace_duration_gte=1,
    )

    assert status_code == 200
    assert response.count == 2
    assert len(response.traces) == 2
    trace_ids = {trace.trace_id for trace in response.traces}
    assert trace_ids == {"trace1", "trace3"}

    # Test combining span_types with restrictive time filter - should return only trace3 (recent)
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        span_types=["LLM"],
        start_time=now - timedelta(hours=1),  # Only recent traces
    )
    assert status_code == 200
    assert response.count == 1
    assert len(response.traces) == 1
    assert response.traces[0].trace_id == "trace3"

    # Test combining multiple span types with duration filter - should return only trace3 (short duration)
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        span_types=["LLM", "AGENT"],
        trace_duration_lte=10,
    )
    assert status_code == 200
    assert response.count == 1
    assert len(response.traces) == 1
    trace_ids = {trace.trace_id for trace in response.traces}
    assert trace_ids == {"trace3"}

    # Test combining span_types with tool_name filter - should return trace3
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        span_types=["LLM", "TOOL"],
        tool_name="test_tool",
    )
    assert status_code == 200
    assert response.count == 1
    assert len(response.traces) == 1
    assert response.traces[0].trace_id == "trace3"

    # Test combining relevance filters with span types - should return trace1 (high score)
    status_code, response = client.query_traces(
        task_ids=["task1", "task2"],
        span_types=["LLM"],
        query_relevance_gte=0.8,
    )
    assert status_code == 200
    assert response.count == 1
    assert len(response.traces) == 1
    assert response.traces[0].trace_id == "trace1"


@pytest.mark.unit_tests
def test_trace_query_filter_validation(
    client: GenaiEngineTestClientBase,
):
    """Test validation of trace query filter parameters."""

    # Test invalid relevance score values (should be between 0 and 1)
    status_code, response = client.query_traces(
        task_ids=["task1"],
        query_relevance_eq=-0.1,
    )
    assert status_code in [400, 422]

    # Test invalid duration values (should be positive)
    status_code, response = client.query_traces(
        task_ids=["task1"],
        trace_duration_eq=-1,
    )
    assert status_code in [400, 422]


@pytest.mark.unit_tests
def test_traces_metrics_endpoint_with_filters(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test the traces/metrics/ endpoint with various filters."""

    # Test with span_types filter and metrics computation - should return trace1 and trace3 (both have task1 spans and LLM spans)
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1"],
        span_types=["LLM"],
    )
    assert status_code == 200
    assert response.count == 2
    assert len(response.traces) == 2
    trace_ids = {trace.trace_id for trace in response.traces}
    assert trace_ids == {"trace1", "trace3"}

    all_spans = get_all_spans_from_traces(response.traces)
    llm_spans = find_spans_by_kind(all_spans, "LLM")
    assert len(llm_spans) == 2  # One from trace1, one from trace3

    # Verify metrics are computed for LLM spans
    for span in llm_spans:
        assert hasattr(span, "metric_results")
        assert len(span.metric_results) > 0

    # Test with AGENT span type and metrics - should return trace2 but no metrics
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task2"],
        span_types=["AGENT"],
    )
    assert status_code == 200
    assert response.count == 1
    assert len(response.traces) == 1
    assert response.traces[0].trace_id == "trace2"

    # AGENT spans don't get metrics computed (only LLM spans do)
    all_spans = get_all_spans_from_traces(response.traces)
    agent_spans = find_spans_by_kind(all_spans, "AGENT")
    assert len(agent_spans) == 1

    # Test with time filter and metrics - should return both trace1 and trace3 (both have task1 spans)
    now = datetime.now()
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1"],
        start_time=now - timedelta(days=3),
        end_time=now + timedelta(days=1),
    )
    assert status_code == 200
    assert response.count == 2
    assert len(response.traces) == 2
    trace_ids = {trace.trace_id for trace in response.traces}
    assert trace_ids == {"trace1", "trace3"}


@pytest.mark.unit_tests
def test_trace_query_with_tool_selection_filters(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test trace filtering by tool selection scores."""

    # Test tool_selection = CORRECT (1) - should return trace1 which has CORRECT tool selection
    status_code, response = client.query_traces(
        task_ids=["task1"],
        tool_selection=1,  # CORRECT
    )
    assert status_code == 200
    assert response.count == 1
    assert len(response.traces) == 1
    assert response.traces[0].trace_id == "trace1"

    # Test tool_selection = INCORRECT (0) - should return trace3 which has INCORRECT tool selection
    status_code, response = client.query_traces(
        task_ids=["task1"],
        tool_selection=0,  # INCORRECT
    )
    assert status_code == 200
    assert response.count == 1
    assert len(response.traces) == 1
    assert response.traces[0].trace_id == "trace3"

    # Test tool_selection = NA (2) - should return empty since no spans have NA tool selection
    status_code, response = client.query_traces(
        task_ids=["task1"],
        tool_selection=2,  # NA
    )
    assert status_code == 200
    assert response.count == 0
    assert len(response.traces) == 0

    # Test with task that has LLM spans but different tool selection scores
    status_code, response = client.query_traces(
        task_ids=["task1"],
        tool_selection=1,  # CORRECT - should return trace1
    )
    assert status_code == 200
    assert response.count == 1
    assert response.traces[0].trace_id == "trace1"


@pytest.mark.unit_tests
def test_trace_query_with_tool_usage_filters(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test trace filtering by tool usage scores."""

    # Test tool_usage = CORRECT (1) - should return trace1 which has CORRECT tool usage
    status_code, response = client.query_traces(
        task_ids=["task1"],
        tool_usage=1,  # CORRECT
    )
    assert status_code == 200
    assert response.count == 1
    assert len(response.traces) == 1
    assert response.traces[0].trace_id == "trace1"

    # Test tool_usage = INCORRECT (0) - should return trace3 which has INCORRECT tool usage
    status_code, response = client.query_traces(
        task_ids=["task1"],
        tool_usage=0,  # INCORRECT
    )
    assert status_code == 200
    assert response.count == 1
    assert len(response.traces) == 1
    assert response.traces[0].trace_id == "trace3"

    # Test tool_usage = NA (2) - should return empty since no spans have NA tool usage
    status_code, response = client.query_traces(
        task_ids=["task1"],
        tool_usage=2,  # NA
    )
    assert status_code == 200
    assert response.count == 0
    assert len(response.traces) == 0


@pytest.mark.unit_tests
def test_trace_query_with_combined_tool_filters(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test trace filtering with both tool selection and tool usage filters."""

    # Test both tool_selection and tool_usage = CORRECT - should return trace1
    status_code, response = client.query_traces(
        task_ids=["task1"],
        tool_selection=1,  # CORRECT
        tool_usage=1,  # CORRECT
    )
    assert status_code == 200
    assert response.count == 1
    assert len(response.traces) == 1
    assert response.traces[0].trace_id == "trace1"

    # Test both tool_selection and tool_usage = INCORRECT - should return trace3
    status_code, response = client.query_traces(
        task_ids=["task1"],
        tool_selection=0,  # INCORRECT
        tool_usage=0,  # INCORRECT
    )
    assert status_code == 200
    assert response.count == 1
    assert len(response.traces) == 1
    assert response.traces[0].trace_id == "trace3"

    # Test conflicting requirements - tool_selection CORRECT and tool_usage INCORRECT
    # Should return empty since no trace has this combination
    status_code, response = client.query_traces(
        task_ids=["task1"],
        tool_selection=1,  # CORRECT
        tool_usage=0,  # INCORRECT
    )
    assert status_code == 200
    assert response.count == 0
    assert len(response.traces) == 0

    # Test conflicting requirements - tool_selection INCORRECT and tool_usage CORRECT
    # Should return empty since no trace has this combination
    status_code, response = client.query_traces(
        task_ids=["task1"],
        tool_selection=0,  # INCORRECT
        tool_usage=1,  # CORRECT
    )
    assert status_code == 200
    assert response.count == 0
    assert len(response.traces) == 0


@pytest.mark.unit_tests
def test_trace_query_with_tool_filters_and_other_filters(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test trace filtering with tool filters combined with other filters."""

    # Test tool_selection with span_types filter
    status_code, response = client.query_traces(
        task_ids=["task1"],
        span_types=["LLM"],
        tool_selection=1,  # CORRECT
    )
    assert status_code == 200
    assert response.count == 1
    assert len(response.traces) == 1
    assert response.traces[0].trace_id == "trace1"

    # Test tool_usage with relevance filters
    status_code, response = client.query_traces(
        task_ids=["task1"],
        query_relevance_gte=0.8,  # High relevance (trace1)
        tool_usage=1,  # CORRECT
    )
    assert status_code == 200
    assert response.count == 1
    assert len(response.traces) == 1
    assert response.traces[0].trace_id == "trace1"

    # Test tool filters with time range
    now = datetime.now()
    status_code, response = client.query_traces(
        task_ids=["task1"],
        start_time=now - timedelta(days=3),
        end_time=now + timedelta(days=1),
        tool_selection=0,  # INCORRECT
    )
    assert status_code == 200
    assert response.count == 1
    assert len(response.traces) == 1
    assert response.traces[0].trace_id == "trace3"

    # Test restrictive combination that should return no results
    status_code, response = client.query_traces(
        task_ids=["task1"],
        query_relevance_gte=0.8,  # High relevance (trace1 only)
        tool_selection=0,  # INCORRECT (trace3 only)
    )
    assert status_code == 200
    assert response.count == 0
    assert len(response.traces) == 0


@pytest.mark.unit_tests
def test_tool_filters_with_metrics_endpoint(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test tool filters with the traces/metrics endpoint."""

    # Test tool_selection filter with metrics computation
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1"],
        tool_selection=1,  # CORRECT
    )
    assert status_code == 200
    assert response.count == 1
    assert len(response.traces) == 1
    assert response.traces[0].trace_id == "trace1"

    # Verify metrics are computed for the LLM span
    all_spans = get_all_spans_from_traces(response.traces)
    llm_spans = find_spans_by_kind(all_spans, "LLM")
    assert len(llm_spans) == 1

    # Check that the LLM span has metric results including tool selection
    llm_span = llm_spans[0]
    assert hasattr(llm_span, "metric_results")
    assert len(llm_span.metric_results) > 0

    # Check for tool selection metric in the results
    tool_selection_metrics = [
        result
        for result in llm_span.metric_results
        if result.metric_type == "ToolSelection"
    ]
    assert len(tool_selection_metrics) == 1

    # Verify the tool selection metric details
    tool_metric = tool_selection_metrics[0]
    details = json.loads(tool_metric.details) if tool_metric.details else {}
    assert details["tool_selection"]["tool_selection"] == 1  # CORRECT
    assert details["tool_selection"]["tool_usage"] == 1  # CORRECT

    # Test tool_usage filter with metrics computation
    status_code, response = client.query_traces_with_metrics(
        task_ids=["task1"],
        tool_usage=0,  # INCORRECT
    )
    assert status_code == 200
    assert response.count == 1
    assert len(response.traces) == 1
    assert response.traces[0].trace_id == "trace3"

    # Verify metrics for trace3
    all_spans = get_all_spans_from_traces(response.traces)
    llm_spans = find_spans_by_kind(all_spans, "LLM")
    assert len(llm_spans) == 1

    llm_span = llm_spans[0]
    tool_selection_metrics = [
        result
        for result in llm_span.metric_results
        if result.metric_type == "ToolSelection"
    ]
    assert len(tool_selection_metrics) == 1

    tool_metric = tool_selection_metrics[0]
    details = json.loads(tool_metric.details) if tool_metric.details else {}
    assert details["tool_selection"]["tool_selection"] == 0  # INCORRECT
    assert details["tool_selection"]["tool_usage"] == 0  # INCORRECT
