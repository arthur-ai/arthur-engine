from unittest.mock import patch

import pytest

from tests.clients.base_test_client import GenaiEngineTestClientBase

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def get_all_spans_from_trace(trace):
    """Helper function to extract all spans from a trace response."""
    spans = []
    for root_span in trace.root_spans:
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


def find_span_by_kind(spans, span_kind):
    """Helper function to find the first span matching the given kind."""
    matching_spans = find_spans_by_kind(spans, span_kind)
    return matching_spans[0] if matching_spans else None


# ============================================================================
# TRACE METADATA LIST TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_list_traces_metadata_functionality(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test trace metadata listing functionality for single and multiple tasks."""

    # Test single task
    status_code, data = client.trace_api_list_traces_metadata(task_ids=["api_task1"])
    assert status_code == 200
    assert data.count == 3  # api_trace1, api_trace2, api_trace4 belong to api_task1
    assert len(data.traces) == 3

    # Verify metadata structure
    for trace_metadata in data.traces:
        assert trace_metadata.trace_id and isinstance(trace_metadata.trace_id, str)
        assert trace_metadata.task_id and isinstance(trace_metadata.task_id, str)
        assert trace_metadata.user_id is not None  # Should have user_id
        assert trace_metadata.start_time is not None
        assert trace_metadata.end_time is not None
        assert (
            trace_metadata.span_count is not None
            and isinstance(trace_metadata.span_count, int)
            and trace_metadata.span_count >= 0
        )
        # Verify new fields are present
        assert hasattr(trace_metadata, "input_content")
        assert hasattr(trace_metadata, "output_content")
        # Verify token count/cost fields are present (may be None if no LLM spans)
        assert hasattr(trace_metadata, "prompt_token_count")
        assert hasattr(trace_metadata, "completion_token_count")
        assert hasattr(trace_metadata, "total_token_count")
        assert hasattr(trace_metadata, "prompt_token_cost")
        assert hasattr(trace_metadata, "completion_token_cost")
        assert hasattr(trace_metadata, "total_token_cost")

    # Verify specific traces have expected input/output content and token data
    trace1 = next((t for t in data.traces if t.trace_id == "api_trace1"), None)
    if trace1:
        assert trace1.input_content == "What is the weather like today?"
        assert (
            trace1.output_content
            == "I don't have access to real-time weather information."
        )
        # Trace1 has api_span1 (LLM with tokens) and api_span2 (CHAIN, no tokens)
        # Should aggregate tokens from api_span1 only
        assert trace1.prompt_token_count == 100
        assert trace1.completion_token_count == 50
        assert trace1.total_token_count == 150
        assert trace1.prompt_token_cost == 0.001
        assert trace1.completion_token_cost == 0.002
        assert trace1.total_token_cost == 0.003

    trace2 = next((t for t in data.traces if t.trace_id == "api_trace2"), None)
    if trace2:
        # Verify JSON content - should be stringified
        import json

        expected_input = {
            "question": "Follow-up question",
            "context": "previous conversation",
        }
        expected_output = {"answer": "Follow-up response", "sources": ["doc1", "doc2"]}
        assert json.loads(trace2.input_content) == expected_input
        assert json.loads(trace2.output_content) == expected_output
        # Trace2 has only api_span3 (LLM with tokens)
        assert trace2.prompt_token_count == 200
        assert trace2.completion_token_count == 100
        assert trace2.total_token_count == 300
        assert trace2.prompt_token_cost == 0.002
        assert trace2.completion_token_cost == 0.003
        assert trace2.total_token_cost == 0.005

    # Test multiple tasks
    status_code, data = client.trace_api_list_traces_metadata(
        task_ids=["api_task1", "api_task2"],
    )
    assert status_code == 200
    assert data.count == 4  # All 4 traces
    assert len(data.traces) == 4

    # Verify we have traces from both tasks
    task_ids = {trace.task_id for trace in data.traces}
    assert task_ids == {"api_task1", "api_task2"}


@pytest.mark.unit_tests
def test_list_traces_metadata_filtering_by_user_ids(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test filtering traces by user IDs."""

    # Filter traces by user1
    status_code, data = client.trace_api_list_traces_metadata(
        task_ids=["api_task1"],
        user_ids=["user1"],
    )
    assert status_code == 200
    assert data.count == 3  # user1 has 3 traces in api_task1
    assert len(data.traces) == 3

    # Verify all traces belong to user1
    for trace in data.traces:
        assert trace.user_id == "user1"
        assert trace.task_id == "api_task1"

    # Filter by multiple users
    status_code, data = client.trace_api_list_traces_metadata(
        task_ids=["api_task1", "api_task2"],
        user_ids=["user1", "user2"],
    )
    assert status_code == 200
    assert data.count == 4  # user1 has 3 traces, user2 has 1 trace
    assert len(data.traces) == 4

    # Verify we have traces from both users
    user_ids = {trace.user_id for trace in data.traces}
    assert user_ids == {"user1", "user2"}

    # Filter by non-existent user
    status_code, data = client.trace_api_list_traces_metadata(
        task_ids=["api_task1"],
        user_ids=["non_existent_user"],
    )
    assert status_code == 200
    assert data.count == 0
    assert len(data.traces) == 0


@pytest.mark.unit_tests
def test_trace_metadata_validation_and_individual_retrieval(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test validation errors and individual trace retrieval."""

    # Test validation errors
    # Empty task_ids (should return 400)
    status_code, response = client.trace_api_list_traces_metadata(task_ids=[])
    assert status_code == 400

    # Non-existent task (should return 200 with 0 results)
    status_code, data = client.trace_api_list_traces_metadata(
        task_ids=["non_existent_task"],
    )
    assert status_code == 200
    assert data.count == 0
    assert len(data.traces) == 0

    # Test individual trace retrieval
    status_code, traces_response = client.trace_api_list_traces_metadata(
        task_ids=["api_task1"],
    )
    assert status_code == 200

    traces = traces_response.traces
    trace_id = traces[0].trace_id

    # Get the specific trace
    status_code, trace_data = client.trace_api_get_trace_by_id(trace_id)
    assert status_code == 200
    assert trace_data.trace_id == trace_id
    assert isinstance(trace_data.root_spans, list)
    assert trace_data.start_time is not None
    assert trace_data.end_time is not None

    # Verify nested span structure
    assert len(trace_data.root_spans) >= 1
    for root_span in trace_data.root_spans:
        assert root_span.span_id and isinstance(root_span.span_id, str)
        assert root_span.span_kind and isinstance(root_span.span_kind, str)
        assert isinstance(
            root_span.children,
            list,
        )  # Should have children array (even if empty)


@pytest.mark.unit_tests
def test_get_trace_by_id_with_nested_structure(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test trace retrieval with proper nested structure."""

    # Get trace1 which has parent-child relationship (api_span1 -> api_span2)
    status_code, trace_data = client.trace_api_get_trace_by_id("api_trace1")
    assert status_code == 200
    assert trace_data.trace_id == "api_trace1"

    # Verify trace-level input_content and output_content
    assert hasattr(trace_data, "input_content")
    assert hasattr(trace_data, "output_content")
    assert trace_data.input_content == "What is the weather like today?"
    assert (
        trace_data.output_content
        == "I don't have access to real-time weather information."
    )

    # Verify nested structure
    assert len(trace_data.root_spans) == 1  # One root span
    root_span = trace_data.root_spans[0]

    assert root_span.span_id == "api_span1"
    assert root_span.span_kind == "LLM"
    assert len(root_span.children) == 1  # Has one child

    # Verify root span has input_content and output_content
    assert hasattr(root_span, "input_content")
    assert hasattr(root_span, "output_content")
    assert root_span.input_content == "What is the weather like today?"
    assert (
        root_span.output_content
        == "I don't have access to real-time weather information."
    )

    child_span = root_span.children[0]
    assert child_span.span_id == "api_span2"
    assert child_span.span_kind == "CHAIN"
    assert child_span.parent_span_id == "api_span1"
    assert len(child_span.children) == 0  # No grandchildren

    # Child spans should also have input_content/output_content fields
    assert hasattr(child_span, "input_content")
    assert hasattr(child_span, "output_content")


@pytest.mark.unit_tests
def test_get_trace_by_id_with_existing_metrics(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test trace retrieval includes existing metrics but doesn't compute new ones."""

    # Get trace1 which has existing metrics
    status_code, trace_data = client.trace_api_get_trace_by_id("api_trace1")
    assert status_code == 200
    all_spans = get_all_spans_from_trace(trace_data)

    # Find LLM spans which should have metrics
    llm_spans = find_spans_by_kind(all_spans, "LLM")
    assert len(llm_spans) >= 1

    llm_span = llm_spans[0]
    assert hasattr(llm_span, "metric_results")
    assert (
        llm_span.metric_results is not None and len(llm_span.metric_results) > 0
    )  # Should have existing metrics

    # Verify metric structure
    for metric in llm_span.metric_results:
        assert hasattr(metric, "metric_type")
        assert hasattr(metric, "prompt_tokens")
        assert hasattr(metric, "completion_tokens")
        assert hasattr(metric, "latency_ms")


@pytest.mark.unit_tests
def test_get_trace_by_id_not_found(
    client: GenaiEngineTestClientBase,
):
    """Test retrieving non-existent trace returns 404."""

    status_code, response_data = client.trace_api_get_trace_by_id("non_existent_trace")
    assert status_code == 404
    assert "not found" in response_data.lower()


# ============================================================================
# COMPUTE TRACE METRICS TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_compute_trace_metrics_basic_functionality(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test computing missing metrics for a trace."""

    # Get a trace that should have metrics computed
    status_code, trace_data = client.trace_api_compute_trace_metrics("api_trace2")
    assert status_code == 200
    assert trace_data.trace_id == "api_trace2"

    # Verify trace-level input_content and output_content are present after metrics computation
    assert hasattr(trace_data, "input_content")
    assert hasattr(trace_data, "output_content")
    # api_trace2 has JSON input/output - verify exact content
    assert (
        trace_data.input_content
        == '{"question": "Follow-up question", "context": "previous conversation"}'
    )
    assert (
        trace_data.output_content
        == '{"answer": "Follow-up response", "sources": ["doc1", "doc2"]}'
    )

    # Verify structure is the same as regular trace
    assert isinstance(trace_data.root_spans, list)
    all_spans = get_all_spans_from_trace(trace_data)

    # Find LLM spans which should have metrics computed
    llm_spans = find_spans_by_kind(all_spans, "LLM")
    assert len(llm_spans) >= 1

    llm_span = llm_spans[0]
    assert hasattr(llm_span, "metric_results")  # Field exists, but may be None or list
    # Note: May or may not have metrics depending on whether they were computed or existed

    # Verify LLM spans have input_content and output_content after metrics computation
    assert hasattr(llm_span, "input_content")
    assert hasattr(llm_span, "output_content")


@pytest.mark.unit_tests
def test_compute_trace_metrics_not_found(
    client: GenaiEngineTestClientBase,
):
    """Test computing metrics for non-existent trace returns 404."""

    status_code, response_data = client.trace_api_compute_trace_metrics(
        "non_existent_trace",
    )
    assert status_code == 404
    assert "not found" in response_data.lower()


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================


@pytest.mark.unit_tests
def test_list_traces_metadata_empty_results(
    client: GenaiEngineTestClientBase,
):
    """Test listing traces with no results."""

    status_code, data = client.trace_api_list_traces_metadata(
        task_ids=["non_existent_task"],
    )
    assert status_code == 200

    assert data.count == 0
    assert len(data.traces) == 0


@pytest.mark.unit_tests
def test_trace_api_error_handling(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test various error conditions in trace API."""

    # Test server error in metadata listing
    with patch(
        "repositories.span_repository.SpanRepository.get_traces_metadata",
        side_effect=Exception("Database error"),
    ):
        status_code, _ = client.trace_api_list_traces_metadata(task_ids=["api_task1"])
        assert status_code == 500

    # Test server error in trace retrieval
    with patch(
        "repositories.span_repository.SpanRepository.get_trace_by_id",
        side_effect=Exception("Database error"),
    ):
        status_code, _ = client.trace_api_get_trace_by_id("api_trace1")
        assert status_code == 500
