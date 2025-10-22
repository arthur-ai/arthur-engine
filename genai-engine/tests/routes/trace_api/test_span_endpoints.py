from unittest.mock import patch

import pytest

from tests.clients.base_test_client import GenaiEngineTestClientBase

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def assert_valid_span_metadata_response(spans):
    """Assert response has valid span metadata structure."""
    for span in spans:
        assert span.span_id and isinstance(span.span_id, str)
        assert span.trace_id and isinstance(span.trace_id, str)
        assert span.span_kind and isinstance(span.span_kind, str)
        assert span.task_id and isinstance(span.task_id, str)
        assert span.user_id is not None  # Should have user_id
        assert span.start_time is not None
        assert span.end_time is not None


def assert_valid_span_full_response(span):
    """Assert response has valid full span structure."""
    assert span.span_id and isinstance(span.span_id, str)
    assert span.trace_id and isinstance(span.trace_id, str)
    assert span.span_kind and isinstance(span.span_kind, str)
    assert span.task_id and isinstance(span.task_id, str)
    assert span.start_time is not None
    assert span.end_time is not None
    assert span.raw_data and isinstance(span.raw_data, dict)
    assert hasattr(span, "metric_results")  # Can be None or list


def assert_spans_match_types(spans, expected_types):
    """Assert all spans have span_kind in expected_types."""
    expected_set = (
        set(expected_types) if isinstance(expected_types, list) else {expected_types}
    )
    for span in spans:
        assert span.span_kind in expected_set


# ============================================================================
# SPAN METADATA LIST TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_list_spans_metadata_basic_functionality(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test basic span metadata listing functionality."""

    # Test single task
    status_code, data = client.trace_api_list_spans_metadata(task_ids=["api_task1"])
    assert status_code == 200
    assert data.count > 0
    assert len(data.spans) > 0

    # Verify metadata structure
    assert_valid_span_metadata_response(data.spans)

    # Verify all spans belong to requested task
    for span in data.spans:
        assert span.task_id == "api_task1"


@pytest.mark.unit_tests
def test_list_spans_metadata_multiple_tasks(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test listing spans for multiple tasks."""

    status_code, data = client.trace_api_list_spans_metadata(
        task_ids=["api_task1", "api_task2"],
    )
    assert status_code == 200
    assert data.count == 6  # Total spans across both tasks
    assert len(data.spans) == 6

    # Verify we have spans from both tasks
    task_ids = {span.task_id for span in data.spans}
    assert task_ids == {"api_task1", "api_task2"}


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "span_types,expected_count",
    [
        (["LLM"], 2),  # api_span1 and api_span3
        (["CHAIN"], 1),  # api_span2
        (["AGENT"], 1),  # api_span4
        (["LLM", "CHAIN"], 3),  # api_span1, api_span2, api_span3
        (["EMBEDDING"], 0),  # No EMBEDDING spans
    ],
)
def test_list_spans_metadata_with_span_type_filtering(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
    span_types,
    expected_count,
):
    """Test span type filtering functionality."""

    status_code, data = client.trace_api_list_spans_metadata(
        task_ids=["api_task1", "api_task2"],
        span_types=span_types,
    )
    assert status_code == 200
    assert data.count == expected_count
    assert len(data.spans) == expected_count

    if expected_count > 0:
        assert_spans_match_types(data.spans, span_types)


@pytest.mark.unit_tests
def test_list_spans_metadata_pagination_sorting_and_validation(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test span metadata pagination, sorting, and validation."""

    # Test pagination
    status_code, data = client.trace_api_list_spans_metadata(
        task_ids=["api_task1", "api_task2"],
        page=0,
        page_size=2,
    )
    assert status_code == 200
    assert data.count == 6  # Total count
    assert len(data.spans) <= 2  # Page size (might be less if last page)

    # Test sorting
    status_code, data = client.trace_api_list_spans_metadata(
        task_ids=["api_task1", "api_task2"],
        sort="desc",
    )
    assert status_code == 200
    if len(data.spans) > 1:
        # Verify descending order by start_time
        for i in range(len(data.spans) - 1):
            current_time = data.spans[i].start_time
            next_time = data.spans[i + 1].start_time
            assert current_time >= next_time

    # Test validation errors
    # Empty task_ids (should return 400)
    status_code, response = client.trace_api_list_spans_metadata(task_ids=[])
    assert status_code == 400

    # Non-existent task (should return 200 with 0 results)
    status_code, data = client.trace_api_list_spans_metadata(
        task_ids=["non_existent_task"],
    )
    assert status_code == 200
    assert data.count == 0
    assert len(data.spans) == 0


# ============================================================================
# INDIVIDUAL SPAN RETRIEVAL TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_get_span_by_id_basic_functionality(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test retrieving individual span by ID."""

    # First get a span ID from the metadata list
    status_code, spans_response = client.trace_api_list_spans_metadata(
        task_ids=["api_task1"],
    )
    assert status_code == 200

    spans = spans_response.spans
    span_id = spans[0].span_id

    # Get the specific span
    status_code, span_data = client.trace_api_get_span_by_id(span_id)
    assert status_code == 200
    assert span_data.span_id == span_id
    assert_valid_span_full_response(span_data)


@pytest.mark.unit_tests
def test_get_span_by_id_comprehensive(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test span retrieval with metrics, features, and error handling."""

    # Test successful span retrieval with metrics and features
    status_code, span_data = client.trace_api_get_span_by_id("api_span1")
    assert status_code == 200
    assert span_data.span_id == "api_span1"
    assert span_data.span_kind == "LLM"

    # Should have existing metrics
    assert hasattr(span_data, "metric_results")
    if span_data.metric_results:  # May have metrics
        for metric in span_data.metric_results:
            assert hasattr(metric, "metric_type")
            assert hasattr(metric, "prompt_tokens")
            assert hasattr(metric, "completion_tokens")
            assert hasattr(metric, "latency_ms")

    # Verify LLM span features are extracted
    assert span_data.system_prompt == "You are a helpful assistant."
    assert span_data.user_query == "What is the weather like today?"
    assert span_data.response == "I don't have access to real-time weather information."

    # Test non-existent span
    status_code, response_data = client.trace_api_get_span_by_id("non_existent_span")
    assert status_code == 404
    assert "not found" in response_data.lower()

    # Get non-LLM span
    status_code, span_data = client.trace_api_get_span_by_id("api_span2")
    assert status_code == 200
    assert span_data.span_kind == "CHAIN"
    # Non-LLM spans should not have these features
    assert getattr(span_data, "system_prompt", None) is None
    assert getattr(span_data, "user_query", None) is None
    assert getattr(span_data, "response", None) is None


# ============================================================================
# COMPUTE SPAN METRICS TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_compute_span_metrics_comprehensive(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test computing span metrics with success and error cases."""

    # Test successful metrics computation
    status_code, span_data = client.trace_api_compute_span_metrics("api_span1")
    assert status_code == 200
    assert span_data.span_id == "api_span1"
    assert span_data.span_kind == "LLM"

    # Should have the same structure as regular span response
    assert_valid_span_full_response(span_data)

    # Test non-existent span
    status_code, response_data = client.trace_api_compute_span_metrics(
        "non_existent_span",
    )
    assert status_code == 404
    assert "not found" in response_data.lower()


@pytest.mark.unit_tests
def test_compute_span_metrics_non_llm_span(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test computing metrics for non-LLM span should return validation error."""

    # Try to compute metrics for CHAIN span (not LLM)
    status_code, response_data = client.trace_api_compute_span_metrics("api_span2")
    assert status_code == 400
    assert "not an LLM span" in response_data


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================


@pytest.mark.unit_tests
def test_span_api_error_handling_and_edge_cases(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test error handling and edge cases in span API."""

    # Test empty results
    status_code, data = client.trace_api_list_spans_metadata(
        task_ids=["non_existent_task"],
    )
    assert status_code == 200
    assert data.count == 0
    assert len(data.spans) == 0

    # Test server error in span metadata listing
    with patch(
        "repositories.span_repository.SpanRepository.query_spans",
        side_effect=Exception("Database error"),
    ):
        status_code, _ = client.trace_api_list_spans_metadata(task_ids=["api_task1"])
        assert status_code == 500

    # Test server error in span retrieval
    with patch(
        "repositories.span_repository.SpanRepository.get_span_by_id",
        side_effect=Exception("Database error"),
    ):
        status_code, _ = client.trace_api_get_span_by_id("api_span1")
        assert status_code == 500
