from datetime import datetime, timedelta

import pytest

from schemas.internal_schemas import AgenticAnnotation
from schemas.request_schemas import AgenticAnnotationRequest
from tests.clients.base_test_client import GenaiEngineTestClientBase

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def get_all_spans_from_traces(traces):
    """Helper function to extract all spans from traces response."""
    spans = []
    for trace in traces:
        for root_span in trace.get("root_spans", []):
            spans.extend(get_all_spans_from_nested_span(root_span))
    return spans


def get_all_spans_from_nested_span(nested_span):
    """Helper function to extract all spans from a nested span structure recursively."""
    spans = [nested_span]
    for child in getattr(nested_span, "children", []):
        spans.extend(get_all_spans_from_nested_span(child))
    return spans


def find_spans_by_kind(spans, span_kind):
    """Helper function to find all spans matching the given kind."""
    return [span for span in spans if getattr(span, "span_kind", None) == span_kind]


# ============================================================================
# CORE TRACE FILTERING TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_trace_metadata_filtering_by_span_types(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test trace metadata filtering by span types."""

    # Filter by LLM spans
    status_code, data = client.trace_api_list_traces_metadata(
        task_ids=["api_task1", "api_task2"],
        span_types=["LLM"],
    )
    assert status_code == 200
    assert data.count >= 2  # Should have traces with LLM spans

    # Filter by AGENT spans
    status_code, data = client.trace_api_list_traces_metadata(
        task_ids=["api_task1", "api_task2"],
        span_types=["AGENT"],
    )
    assert status_code == 200
    assert data.count == 1  # Only api_trace3 has AGENT span
    assert data.traces[0].trace_id == "api_trace3"


@pytest.mark.unit_tests
def test_trace_metadata_filtering_by_time_range(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test trace metadata filtering by time range."""

    now = datetime.now()

    # Filter by start_time - should return recent traces
    status_code, data = client.trace_api_list_traces_metadata(
        task_ids=["api_task1", "api_task2"],
        start_time=now - timedelta(hours=2),
    )
    assert status_code == 200
    assert data.count >= 1  # Should have recent traces

    # Verify all returned traces are within time range
    for trace_metadata in data.traces:
        trace_start = trace_metadata.start_time
        assert trace_start >= (now - timedelta(hours=2))


@pytest.mark.unit_tests
def test_trace_metadata_pagination(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test basic pagination for trace metadata."""

    # Get first page
    status_code, data = client.trace_api_list_traces_metadata(
        task_ids=["api_task1", "api_task2"],
        page=0,
        page_size=2,
    )
    assert status_code == 200
    assert data.count == 4  # Total count
    assert len(data.traces) == 2  # Page size

    first_page_ids = {trace.trace_id for trace in data.traces}

    # Get second page
    status_code, data = client.trace_api_list_traces_metadata(
        task_ids=["api_task1", "api_task2"],
        page=1,
        page_size=2,
    )
    assert status_code == 200
    assert data.count == 4  # Total count unchanged
    assert len(data.traces) == 2  # Page size

    second_page_ids = {trace.trace_id for trace in data.traces}

    # Verify no overlap between pages
    assert first_page_ids.isdisjoint(second_page_ids)


@pytest.mark.unit_tests
def test_trace_metadata_sorting(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test trace metadata sorting by start_time."""

    # Test descending sort (default)
    status_code, data = client.trace_api_list_traces_metadata(
        task_ids=["api_task1", "api_task2"],
        sort="desc",
    )
    assert status_code == 200
    assert len(data.traces) > 1

    # Verify descending order by checking if traces are sorted
    # Extract start times and check if they're in descending order
    start_times = [trace.start_time for trace in data.traces]
    for i in range(len(start_times) - 1):
        assert (
            start_times[i] >= start_times[i + 1]
        ), f"Traces not in descending order: {start_times[i]} should be >= {start_times[i + 1]}"


@pytest.mark.unit_tests
def test_get_trace_requests_return_annotation_info(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test filtering by annotation score."""
    # Add a positive annotation to the trace
    annotation_request = AgenticAnnotationRequest(
        annotation_score=1,
        annotation_description="Test annotation",
    )
    status_code, response = client.trace_api_annotate_trace(
        "api_trace1",
        annotation_request,
    )
    assert status_code == 200
    assert isinstance(response, AgenticAnnotation)
    assert response.trace_id == "api_trace1"
    assert response.annotation_score == 1
    assert response.annotation_description == "Test annotation"

    # Add a negative annotation to a different trace
    annotation_request = AgenticAnnotationRequest(
        annotation_score=0,
        annotation_description="Disliked annotation",
    )
    status_code, response = client.trace_api_annotate_trace(
        "api_trace2",
        annotation_request,
    )
    assert status_code == 200
    assert isinstance(response, AgenticAnnotation)
    assert response.trace_id == "api_trace2"
    assert response.annotation_score == 0
    assert response.annotation_description == "Disliked annotation"

    #########################################################################################
    # Assert filtering by annotation score works
    #########################################################################################

    # Test filtering without annotation score
    status_code, data = client.trace_api_list_traces_metadata(
        task_ids=["api_task1"],
    )
    assert status_code == 200
    assert len(data.traces) == 3

    # Test filtering on only positive annotation scores
    status_code, data = client.trace_api_list_traces_metadata(
        task_ids=["api_task1"],
        annotation_score=1,
    )
    assert status_code == 200
    assert len(data.traces) == 1
    assert data.traces[0].trace_id == "api_trace1"
    assert data.traces[0].annotation.annotation_score == 1
    assert data.traces[0].annotation.annotation_description == "Test annotation"

    # Test filtering on only negative annotation scores
    status_code, data = client.trace_api_list_traces_metadata(
        task_ids=["api_task1"],
        annotation_score=0,
    )
    assert status_code == 200
    assert len(data.traces) == 1
    assert data.traces[0].trace_id == "api_trace2"
    assert data.traces[0].annotation.annotation_score == 0
    assert data.traces[0].annotation.annotation_description == "Disliked annotation"

    # Cleanup
    status_code, _ = client.trace_api_delete_annotation_from_trace("api_trace1")
    assert status_code == 204
    status_code, _ = client.trace_api_delete_annotation_from_trace("api_trace2")
    assert status_code == 204


# ============================================================================
# CORE SPAN FILTERING TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_span_metadata_filtering_by_types(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test span metadata filtering by span types."""

    # Filter by LLM spans
    status_code, data = client.trace_api_list_spans_metadata(
        task_ids=["api_task1", "api_task2"],
        span_types=["LLM"],
    )
    assert status_code == 200
    assert data.count == 2  # api_span1 and api_span3

    for span in data.spans:
        assert span.span_kind == "LLM"

    # Filter by multiple types
    status_code, data = client.trace_api_list_spans_metadata(
        task_ids=["api_task1", "api_task2"],
        span_types=["LLM", "CHAIN"],
    )
    assert status_code == 200
    assert data.count == 3  # LLM + CHAIN spans

    for span in data.spans:
        assert span.span_kind in ["LLM", "CHAIN"]


@pytest.mark.unit_tests
def test_span_metadata_filtering_by_tool_name(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test span metadata filtering by tool name."""

    # Filter by existing tool name
    status_code, data = client.trace_api_list_spans_metadata(
        task_ids=["api_task1", "api_task2"],
        tool_name="test_tool",
    )
    assert status_code == 200
    assert data.count == 1  # Only api_span6 has this tool name

    for span in data.spans:
        assert span.span_kind == "TOOL"
        # The span name should match the tool name for TOOL spans
        assert span.span_name == "test_tool"

    # Filter by non-existent tool name
    status_code, data = client.trace_api_list_spans_metadata(
        task_ids=["api_task1", "api_task2"],
        tool_name="non_existent_tool",
    )
    assert status_code == 200
    assert data.count == 0


@pytest.mark.unit_tests
def test_span_metadata_filtering_by_time_range(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test span metadata filtering by time range."""
    now = datetime.now()

    # Filter by start_time - should return recent spans
    status_code, data = client.trace_api_list_spans_metadata(
        task_ids=["api_task1", "api_task2"],
        start_time=now - timedelta(hours=2),
    )
    assert status_code == 200
    assert data.count >= 1  # Should have recent spans

    # Verify all returned spans are within time range
    for span in data.spans:
        assert span.start_time >= (now - timedelta(hours=2))

    # Filter by end_time - should return older spans
    status_code, data = client.trace_api_list_spans_metadata(
        task_ids=["api_task1", "api_task2"],
        end_time=now - timedelta(hours=1),
    )
    assert status_code == 200
    # Should have some older spans (depending on test data timing)


@pytest.mark.unit_tests
def test_span_metadata_filtering_with_relevance_scores(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test span metadata filtering by relevance scores."""

    # Filter by high query relevance - should return spans with high scores
    status_code, data = client.trace_api_list_spans_metadata(
        task_ids=["api_task1", "api_task2"],
        query_relevance_gte=0.8,
    )
    assert status_code == 200
    # Should return spans that have query relevance >= 0.8

    # Filter by response relevance
    status_code, data = client.trace_api_list_spans_metadata(
        task_ids=["api_task1", "api_task2"],
        response_relevance_gt=0.9,
    )
    assert status_code == 200
    # Should return spans with response relevance > 0.9


@pytest.mark.unit_tests
def test_span_metadata_filtering_with_tool_selection(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test span metadata filtering by tool selection metrics."""

    # Filter by correct tool selection
    status_code, data = client.trace_api_list_spans_metadata(
        task_ids=["api_task1", "api_task2"],
        tool_selection=1,  # CORRECT
    )
    assert status_code == 200
    # Should return spans with correct tool selection

    # Filter by incorrect tool usage
    status_code, data = client.trace_api_list_spans_metadata(
        task_ids=["api_task1", "api_task2"],
        tool_usage=0,  # INCORRECT
    )
    assert status_code == 200
    # Should return spans with incorrect tool usage


@pytest.mark.unit_tests
def test_span_metadata_combined_filtering(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test span metadata with combined filters."""

    # Combine span types with tool name filtering
    status_code, data = client.trace_api_list_spans_metadata(
        task_ids=["api_task1", "api_task2"],
        span_types=["LLM", "TOOL"],
        tool_name="test_tool",
    )
    assert status_code == 200
    # Should return LLM spans AND TOOL spans with the specific tool name

    # Combine span types with relevance filtering
    status_code, data = client.trace_api_list_spans_metadata(
        task_ids=["api_task1", "api_task2"],
        span_types=["LLM"],
        query_relevance_gte=0.5,
    )
    assert status_code == 200
    # Should return only LLM spans with query relevance >= 0.5

    for span in data.spans:
        assert span.span_kind == "LLM"

    # Combine time range with span types
    now = datetime.now()
    status_code, data = client.trace_api_list_spans_metadata(
        task_ids=["api_task1", "api_task2"],
        span_types=["LLM", "CHAIN"],
        start_time=now - timedelta(days=1),
        end_time=now + timedelta(hours=1),
    )
    assert status_code == 200

    for span in data.spans:
        assert span.span_kind in ["LLM", "CHAIN"]
        assert span.start_time >= (now - timedelta(days=1))
        assert span.start_time <= (now + timedelta(hours=1))


@pytest.mark.unit_tests
def test_span_metadata_sorting(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test span metadata sorting by start_time."""

    # Test descending sort (default)
    status_code, data = client.trace_api_list_spans_metadata(
        task_ids=["api_task1", "api_task2"],
        sort="desc",
    )
    assert status_code == 200
    assert len(data.spans) > 1

    # Verify descending order
    start_times = [span.start_time for span in data.spans]
    for i in range(len(start_times) - 1):
        assert (
            start_times[i] >= start_times[i + 1]
        ), f"Spans not in descending order: {start_times[i]} should be >= {start_times[i + 1]}"

    # Test ascending sort
    status_code, data = client.trace_api_list_spans_metadata(
        task_ids=["api_task1", "api_task2"],
        sort="asc",
    )
    assert status_code == 200
    assert len(data.spans) > 1

    # Verify ascending order
    start_times = [span.start_time for span in data.spans]
    for i in range(len(start_times) - 1):
        assert (
            start_times[i] <= start_times[i + 1]
        ), f"Spans not in ascending order: {start_times[i]} should be <= {start_times[i + 1]}"


@pytest.mark.unit_tests
def test_span_metadata_pagination(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test span metadata pagination consistency."""

    # Get all spans in one request
    status_code, spans_response = client.trace_api_list_spans_metadata(
        task_ids=["api_task1", "api_task2"],
        page_size=100,
    )
    assert status_code == 200

    all_spans_single = spans_response.spans
    total_count = spans_response.count

    # Get same spans using pagination
    all_spans_paginated = []
    page = 0
    page_size = 2

    while len(all_spans_paginated) < total_count:
        status_code, data = client.trace_api_list_spans_metadata(
            task_ids=["api_task1", "api_task2"],
            page=page,
            page_size=page_size,
        )
        assert status_code == 200
        assert data.count == total_count  # Total count should be consistent

        if not data.spans:
            break

        all_spans_paginated.extend(data.spans)
        page += 1

    # Verify we got the same spans
    assert len(all_spans_single) == len(all_spans_paginated)

    single_ids = {span.span_id for span in all_spans_single}
    paginated_ids = {span.span_id for span in all_spans_paginated}
    assert single_ids == paginated_ids


@pytest.mark.unit_tests
def test_span_metadata_filter_validation_edge_cases(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test span metadata filtering validation and edge cases."""

    # Test filtering with incompatible combinations
    # LLM metric filters without LLM spans should return empty results
    status_code, data = client.trace_api_list_spans_metadata(
        task_ids=["api_task1", "api_task2"],
        span_types=["CHAIN"],  # Non-LLM span type
        query_relevance_gte=0.5,  # LLM metric filter
    )
    assert status_code == 200
    assert data.count == 0  # Should return no results due to incompatible filters

    # Test tool_name filter without TOOL spans
    status_code, data = client.trace_api_list_spans_metadata(
        task_ids=["api_task1", "api_task2"],
        span_types=["LLM"],  # Non-TOOL span type
        tool_name="test_tool",  # Tool filter
    )
    assert status_code == 200
    assert data.count == 0  # Should return no results due to incompatible filters

    # Test with very restrictive filters
    status_code, data = client.trace_api_list_spans_metadata(
        task_ids=["api_task1", "api_task2"],
        query_relevance_gte=0.99,  # Very high threshold
        response_relevance_gte=0.99,  # Very high threshold
        tool_selection=1,  # CORRECT
        tool_usage=1,  # CORRECT
    )
    assert status_code == 200
    # Should return very few or no results due to restrictive filters

    # Test empty task_ids - should return validation error
    status_code, response = client.trace_api_list_spans_metadata(
        task_ids=[],
    )
    assert status_code == 400  # Should return validation error


# ============================================================================
# VALIDATION AND ERROR HANDLING TESTS
# ============================================================================


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "task_ids,expected_status",
    [
        ([], 400),  # Empty task_ids should return 400
        (
            ["non_existent_task"],
            200,
        ),  # Non-existent task should return 200 with 0 results
    ],
)
def test_filtering_validation_errors(
    client: GenaiEngineTestClientBase,
    task_ids,
    expected_status,
):
    """Test validation errors for filtering parameters."""

    status_code, response = client.trace_api_list_traces_metadata(task_ids=task_ids)
    assert status_code == expected_status

    if expected_status == 200:
        # Should have valid response structure even with no results
        assert (
            response.count is not None
            and isinstance(response.count, int)
            and response.count >= 0
        )
        assert isinstance(response.traces, list)
        if task_ids == ["non_existent_task"]:
            assert response.count == 0
    # For 400 status, response will be error text


@pytest.mark.unit_tests
def test_filtering_with_no_results(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test filtering that returns no results."""

    # Filter by non-existent task
    status_code, data = client.trace_api_list_traces_metadata(
        task_ids=["non_existent_task"],
    )
    assert status_code == 200
    assert data.count == 0
    assert len(data.traces) == 0

    # Filter by future time range
    future_time = datetime.now() + timedelta(days=1)
    status_code, data = client.trace_api_list_traces_metadata(
        task_ids=["api_task1", "api_task2"],
        start_time=future_time,
    )
    assert status_code == 200
    assert data.count == 0
    assert len(data.traces) == 0


@pytest.mark.unit_tests
def test_filtering_consistency_across_endpoints(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test that filtering works consistently across different endpoints."""

    # Filter traces by task
    status_code, trace_data = client.trace_api_list_traces_metadata(
        task_ids=["api_task1"],
    )
    assert status_code == 200

    # Filter spans by same task
    status_code, span_data = client.trace_api_list_spans_metadata(
        task_ids=["api_task1"],
    )
    assert status_code == 200
    task1_spans = span_data.spans

    # Verify consistency - all spans should belong to traces we found
    trace_ids = {trace.trace_id for trace in trace_data.traces}
    for span in task1_spans:
        assert span.trace_id in trace_ids
        assert span.task_id == "api_task1"
