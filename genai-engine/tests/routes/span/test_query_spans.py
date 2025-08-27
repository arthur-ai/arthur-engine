from datetime import datetime, timedelta

import pytest

from tests.clients.base_test_client import GenaiEngineTestClientBase


# Helper functions
def assert_valid_span_response(response):
    """Assert response has valid span structure."""
    assert response.count >= 0
    assert len(response.spans) == response.count
    for span in response.spans:
        assert hasattr(span, "id")
        assert hasattr(span, "trace_id")
        assert hasattr(span, "span_id")
        assert hasattr(span, "span_kind")
        assert hasattr(span, "task_id")
        assert hasattr(span, "metric_results")


def assert_spans_match_types(spans, expected_types):
    """Assert all spans have span_kind in expected_types."""
    expected_set = (
        set(expected_types) if isinstance(expected_types, list) else {expected_types}
    )
    for span in spans:
        assert span.span_kind in expected_set


def assert_spans_in_time_range(spans, start_time=None, end_time=None):
    """Assert all spans are within the specified time range."""
    for span in spans:
        if start_time:
            assert span.start_time >= start_time
        if end_time:
            assert span.start_time <= end_time


def assert_sorted_spans(spans, ascending=False):
    """Assert spans are sorted by start_time."""
    for i in range(len(spans) - 1):
        if ascending:
            assert spans[i].start_time <= spans[i + 1].start_time
        else:
            assert spans[i].start_time >= spans[i + 1].start_time


@pytest.mark.unit_tests
def test_query_spans_basic_functionality(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test basic query spans functionality."""
    # Test single and multiple task IDs
    for task_ids in [["task1"], ["task1", "task2"]]:
        status_code, response = client.query_spans(task_ids=task_ids)
        assert status_code == 200
        assert response.count > 0
        assert_valid_span_response(response)


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "span_types,should_have_results",
    [
        (["LLM"], True),
        (["AGENT"], True),
        (["LLM", "AGENT", "CHAIN"], True),
        (["EMBEDDING"], False),  # No EMBEDDING spans in test data
    ],
)
def test_query_spans_with_span_type_filtering(
    client: GenaiEngineTestClientBase,
    create_test_spans,
    span_types,
    should_have_results,
):
    """Test span type filtering functionality."""
    status_code, response = client.query_spans(
        task_ids=["task1", "task2"],
        span_types=span_types,
    )
    assert status_code == 200
    assert_valid_span_response(response)

    if should_have_results:
        assert response.count > 0
        assert_spans_match_types(response.spans, span_types)
    else:
        assert response.count == 0


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "span_types,expected_status,should_contain",
    [
        (
            ["INVALID_SPAN_TYPE"],
            400,
            ["Invalid span_types received", "INVALID_SPAN_TYPE"],
        ),
        (
            ["LLM", "INVALID_TYPE", "ANOTHER_INVALID"],
            400,
            ["Invalid span_types received", "INVALID_TYPE", "ANOTHER_INVALID"],
        ),
        ([], 200, []),
        (
            [
                "TOOL",
                "CHAIN",
                "LLM",
                "RETRIEVER",
                "EMBEDDING",
                "AGENT",
                "RERANKER",
                "UNKNOWN",
                "GUARDRAIL",
                "EVALUATOR",
            ],
            200,
            [],
        ),
        (None, 200, []),
    ],
)
def test_query_spans_span_type_validation(
    client: GenaiEngineTestClientBase,
    create_test_spans,
    span_types,
    expected_status,
    should_contain,
):
    """Test span type validation with both valid and invalid span types."""
    status_code, response = client.query_spans(
        task_ids=["task1", "task2"],
        span_types=span_types,
    )
    assert status_code == expected_status

    if expected_status == 400:
        response_text = response if isinstance(response, str) else str(response)
        for text in should_contain:
            assert text in response_text
    else:
        assert_valid_span_response(response)
        if span_types and len(span_types) > 0:
            assert_spans_match_types(response.spans, span_types)


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "page,page_size,expected_max_spans",
    [
        (0, 1, 1),
        (1, 1, 1),
        (0, 2, 2),
    ],
)
def test_query_spans_pagination(
    client: GenaiEngineTestClientBase,
    create_test_spans,
    page,
    page_size,
    expected_max_spans,
):
    """Test pagination functionality."""
    status_code, response = client.query_spans(
        task_ids=["task1", "task2"],
        page=page,
        page_size=page_size,
    )
    assert status_code == 200
    assert_valid_span_response(response)
    assert len(response.spans) <= expected_max_spans


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "sort_order,ascending",
    [
        (None, False),  # Default is descending
        ("desc", False),  # Explicit descending
        ("asc", True),  # Explicit ascending
    ],
)
def test_query_spans_sorting(
    client: GenaiEngineTestClientBase,
    create_test_spans,
    sort_order,
    ascending,
):
    """Test sorting functionality."""
    kwargs = {"task_ids": ["task1", "task2"]}
    if sort_order:
        kwargs["sort"] = sort_order

    status_code, response = client.query_spans(**kwargs)
    assert status_code == 200
    assert_valid_span_response(response)

    if len(response.spans) > 1:
        assert_sorted_spans(response.spans, ascending=ascending)


@pytest.mark.unit_tests
def test_query_spans_time_filtering(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test time filtering functionality."""
    now = datetime.now()

    # Test various time filter combinations
    test_cases = [
        (now - timedelta(days=3), None),  # start_time only
        (None, now + timedelta(days=1)),  # end_time only
        (now - timedelta(days=3), now + timedelta(days=1)),  # both
        (now + timedelta(days=5), now + timedelta(days=6)),  # excludes all
    ]

    for start_time, end_time in test_cases:
        status_code, response = client.query_spans(
            task_ids=["task1", "task2"],
            start_time=start_time,
            end_time=end_time,
        )
        assert status_code == 200
        assert_valid_span_response(response)
        assert_spans_in_time_range(response.spans, start_time, end_time)


@pytest.mark.unit_tests
def test_query_spans_combined_filters(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test combining multiple filters."""
    now = datetime.now()

    # Test span type + time filters
    status_code, response = client.query_spans(
        task_ids=["task1", "task2"],
        span_types=["LLM"],
        start_time=now - timedelta(days=3),
        end_time=now + timedelta(days=1),
    )
    assert status_code == 200
    assert_valid_span_response(response)
    assert_spans_match_types(response.spans, ["LLM"])
    assert_spans_in_time_range(
        response.spans,
        now - timedelta(days=3),
        now + timedelta(days=1),
    )

    # Test all filters combined
    status_code, response = client.query_spans(
        task_ids=["task1", "task2"],
        span_types=["LLM", "AGENT"],
        start_time=now - timedelta(days=3),
        end_time=now + timedelta(days=1),
        page=0,
        page_size=1,
        sort="desc",
    )
    assert status_code == 200
    assert_valid_span_response(response)
    assert len(response.spans) <= 1
    if response.spans:
        assert_spans_match_types(response.spans, ["LLM", "AGENT"])
        assert_spans_in_time_range(
            response.spans,
            now - timedelta(days=3),
            now + timedelta(days=1),
        )


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "task_ids,expected_status,expected_count",
    [
        ([], 400, None),  # Missing task_ids
        (["invalid_task_id"], 200, 0),  # Invalid task_ids
        (
            ["task1"],
            200,
            0,
        ),  # Valid task but no matching spans (using EMBEDDING filter)
    ],
)
def test_query_spans_edge_cases(
    client: GenaiEngineTestClientBase,
    task_ids,
    expected_status,
    expected_count,
):
    """Test edge cases for query_spans."""
    kwargs = {"task_ids": task_ids}
    if expected_count == 0:  # Add filter that returns no results
        kwargs["span_types"] = ["EMBEDDING"]

    status_code, response = client.query_spans(**kwargs)
    assert status_code == expected_status

    if expected_status == 200:
        assert_valid_span_response(response)
        if expected_count is not None:
            assert response.count == expected_count


@pytest.mark.unit_tests
def test_query_spans_metrics_and_structure(
    client: GenaiEngineTestClientBase,
    create_test_spans,
):
    """Test that existing metrics are included and response structure differs from traces."""
    # Query spans and traces for comparison
    status_code, spans_response = client.query_spans(task_ids=["task1", "task2"])
    status_code_traces, traces_response = client.query_traces(
        task_ids=["task1", "task2"],
    )

    assert status_code == 200
    assert status_code_traces == 200

    # Verify spans response structure (flat)
    assert hasattr(spans_response, "spans")
    for span in spans_response.spans:
        assert hasattr(span, "span_id") and hasattr(span, "span_kind")
        assert not hasattr(span, "children")  # Flat structure

        # Check metrics for LLM spans
        if span.span_kind == "LLM" and span.metric_results:
            for metric in span.metric_results:
                assert all(
                    hasattr(metric, attr)
                    for attr in [
                        "metric_type",
                        "prompt_tokens",
                        "completion_tokens",
                        "latency_ms",
                    ]
                )

    # Verify traces response structure (nested)
    assert hasattr(traces_response, "traces")
    for trace in traces_response.traces:
        assert hasattr(trace, "trace_id") and hasattr(trace, "root_spans")
        for root_span in trace.root_spans:
            assert hasattr(root_span, "children")  # Nested structure
