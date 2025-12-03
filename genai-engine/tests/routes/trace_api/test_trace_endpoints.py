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


# ============================================================================
# UNREGISTERED TRACES ENDPOINT TESTS
# ============================================================================
# Note: Tests for trace ingestion without task_id are in:
# - test_trace_api_receive_traces_missing_task_id (test_trace_ingestion.py)
# - test_receive_traces_with_resource_attributes (legacy_span/test_span_ingestion.py)
# These will be updated after implementing support for traces without task_id


@pytest.mark.unit_tests
def test_get_unregistered_root_spans_grouped(
    client: GenaiEngineTestClientBase,
):
    """Test getting grouped root spans for traces without task_id via endpoint."""
    from tests.routes.trace_api.conftest import (
        _create_base_trace_request,
        _create_span,
    )

    # Create 5 traces without task_id with 3 distinct span_name groups:
    # Group 1: "AppA" - 2 traces (trace1, trace2) with 2 root spans total
    # Group 2: "AppB" - 2 traces (trace3, trace4) with 2 root spans total
    # Group 3: "AppC" - 1 trace (trace5) with 1 root span total

    # Group 1: AppA - Trace 1
    trace_request1, resource_span1, scope_span1 = _create_base_trace_request(
        task_id=None,
    )
    span1 = _create_span(
        trace_id=b"unregistered_endpoint_trace1",
        span_id=b"unregistered_endpoint_span1",
        name="AppA",
        span_type="LLM",
    )
    scope_span1.spans.append(span1)
    resource_span1.scope_spans.append(scope_span1)
    trace_request1.resource_spans.append(resource_span1)

    # Group 1: AppA - Trace 2
    trace_request2, resource_span2, scope_span2 = _create_base_trace_request(
        task_id=None,
    )
    span2 = _create_span(
        trace_id=b"unregistered_endpoint_trace2",
        span_id=b"unregistered_endpoint_span2",
        name="AppA",
        span_type="LLM",
    )
    scope_span2.spans.append(span2)
    resource_span2.scope_spans.append(scope_span2)
    trace_request2.resource_spans.append(resource_span2)

    # Group 2: AppB - Trace 3
    trace_request3, resource_span3, scope_span3 = _create_base_trace_request(
        task_id=None,
    )
    span3 = _create_span(
        trace_id=b"unregistered_endpoint_trace3",
        span_id=b"unregistered_endpoint_span3",
        name="AppB",
        span_type="LLM",
    )
    scope_span3.spans.append(span3)
    resource_span3.scope_spans.append(scope_span3)
    trace_request3.resource_spans.append(resource_span3)

    # Group 2: AppB - Trace 4
    trace_request4, resource_span4, scope_span4 = _create_base_trace_request(
        task_id=None,
    )
    span4 = _create_span(
        trace_id=b"unregistered_endpoint_trace4",
        span_id=b"unregistered_endpoint_span4",
        name="AppB",
        span_type="LLM",
    )
    scope_span4.spans.append(span4)
    resource_span4.scope_spans.append(scope_span4)
    trace_request4.resource_spans.append(resource_span4)

    # Group 3: AppC - Trace 5
    trace_request5, resource_span5, scope_span5 = _create_base_trace_request(
        task_id=None,
    )
    span5 = _create_span(
        trace_id=b"unregistered_endpoint_trace5",
        span_id=b"unregistered_endpoint_span5",
        name="AppC",
        span_type="LLM",
    )
    scope_span5.spans.append(span5)
    resource_span5.scope_spans.append(scope_span5)
    trace_request5.resource_spans.append(resource_span5)

    # Send all 5 traces
    status_code1, _ = client.trace_api_receive_traces(
        trace_request1.SerializeToString(),
    )
    status_code2, _ = client.trace_api_receive_traces(
        trace_request2.SerializeToString(),
    )
    status_code3, _ = client.trace_api_receive_traces(
        trace_request3.SerializeToString(),
    )
    status_code4, _ = client.trace_api_receive_traces(
        trace_request4.SerializeToString(),
    )
    status_code5, _ = client.trace_api_receive_traces(
        trace_request5.SerializeToString(),
    )

    # All traces should be accepted
    assert status_code1 == 200, "Trace 1 should be accepted"
    assert status_code2 == 200, "Trace 2 should be accepted"
    assert status_code3 == 200, "Trace 3 should be accepted"
    assert status_code4 == 200, "Trace 4 should be accepted"
    assert status_code5 == 200, "Trace 5 should be accepted"

    # Call the unregistered traces endpoint
    status_code, response = client.trace_api_get_unregistered_root_spans()

    # Verify response status code
    # Note: This will fail initially (404) until we implement the endpoint
    assert status_code == 200, f"Expected 200, got {status_code}. Response: {response}"

    # Handle both dict (current) and object (future schema) responses
    if isinstance(response, dict):
        # Response is a dict (before schema is implemented)
        assert "groups" in response, "Response should have 'groups' key"
        assert "total_count" in response, "Response should have 'total_count' key"
        groups = response["groups"]
        total_count = response["total_count"]
    else:
        # Response is an object (after schema is implemented)
        groups = response.groups
        total_count = response.total_count

    # Verify we have 3 groups
    assert (
        len(groups) == 3
    ), f"Expected 3 groups, got {len(groups)}. Groups: {groups}"

    # Verify each group has the correct structure
    for group in groups:
        if isinstance(group, dict):
            assert "span_name" in group, "Group should have 'span_name' key"
            assert "count" in group, "Group should have 'count' key"
        else:
            assert hasattr(group, "span_name"), "Group should have 'span_name' attribute"
            assert hasattr(group, "count"), "Group should have 'count' attribute"

    # Helper function to get group value
    def get_group_value(group, key):
        return group[key] if isinstance(group, dict) else getattr(group, key)

    # Find groups by span_name and verify counts
    group_a = next(
        (g for g in groups if get_group_value(g, "span_name") == "AppA"), None
    )
    assert group_a is not None, "Group 'AppA' not found"
    assert (
        get_group_value(group_a, "count") == 2
    ), f"Expected AppA count=2, got {get_group_value(group_a, 'count')}"

    group_b = next(
        (g for g in groups if get_group_value(g, "span_name") == "AppB"), None
    )
    assert group_b is not None, "Group 'AppB' not found"
    assert (
        get_group_value(group_b, "count") == 2
    ), f"Expected AppB count=2, got {get_group_value(group_b, 'count')}"

    group_c = next(
        (g for g in groups if get_group_value(g, "span_name") == "AppC"), None
    )
    assert group_c is not None, "Group 'AppC' not found"
    assert (
        get_group_value(group_c, "count") == 1
    ), f"Expected AppC count=1, got {get_group_value(group_c, 'count')}"

    # Verify total_count equals total number of distinct traces (5)
    # Since each trace has one root span, total_count should equal the number of traces
    assert (
        total_count == 5
    ), f"Expected total_count=5 (total distinct traces), got {total_count}"

    # Verify groups are ordered by count descending (most common first)
    # AppA and AppB both have count=2, AppC has count=1
    # So AppA and AppB should come before AppC
    counts = [get_group_value(g, "count") for g in groups]
    assert counts == sorted(
        counts, reverse=True
    ), f"Groups should be ordered by count descending. Got: {counts}"


@pytest.mark.unit_tests
def test_get_unregistered_root_spans_grouped_with_pagination(
    client: GenaiEngineTestClientBase,
):
    """Test pagination for unregistered root spans endpoint."""
    from tests.routes.trace_api.conftest import (
        _create_base_trace_request,
        _create_span,
    )

    # Create 10 traces without task_id with 5 distinct span_name groups:
    # Use unique span names to avoid conflicts with other tests
    # Group 1: "PaginationAppA" - 3 traces (count=3)
    # Group 2: "PaginationAppB" - 3 traces (count=3)
    # Group 3: "PaginationAppC" - 2 traces (count=2)
    # Group 4: "PaginationAppD" - 1 trace (count=1)
    # Group 5: "PaginationAppE" - 1 trace (count=1)

    # Get baseline count before creating test traces
    status_code, baseline_response = client.trace_api_get_unregistered_root_spans(
        page=0, page_size=1
    )
    assert status_code == 200
    baseline_total_count = (
        baseline_response.total_count 
        if hasattr(baseline_response, "total_count") 
        else baseline_response["total_count"]
    )

    span_names = [
        "PaginationAppA", "PaginationAppA", "PaginationAppA",
        "PaginationAppB", "PaginationAppB", "PaginationAppB",
        "PaginationAppC", "PaginationAppC",
        "PaginationAppD",
        "PaginationAppE"
    ]
    
    for i, span_name in enumerate(span_names):
        trace_request, resource_span, scope_span = _create_base_trace_request(
            task_id=None,
        )
        span = _create_span(
            trace_id=f"pagination_test_trace_{i}".encode(),
            span_id=f"pagination_test_span_{i}".encode(),
            name=span_name,
            span_type="LLM",
        )
        scope_span.spans.append(span)
        resource_span.scope_spans.append(scope_span)
        trace_request.resource_spans.append(resource_span)
        
        status_code, _ = client.trace_api_receive_traces(
            trace_request.SerializeToString(),
        )
        assert status_code == 200, f"Trace {i} should be accepted"

    # Helper function to get group value
    def get_group_value(group, key):
        return group[key] if isinstance(group, dict) else getattr(group, key)

    # Test 1: First page with page_size=2 (should get top 2 groups)
    status_code, response = client.trace_api_get_unregistered_root_spans(
        page=0, page_size=2
    )
    assert status_code == 200, f"Expected 200, got {status_code}. Response: {response}"
    
    groups = response.groups if hasattr(response, "groups") else response["groups"]
    total_count = response.total_count if hasattr(response, "total_count") else response["total_count"]
    
    # Should get 2 groups (PaginationAppA and PaginationAppB, both with count=3)
    assert len(groups) == 2, f"Expected 2 groups on first page, got {len(groups)}"
    # total_count should be baseline + 10 (our test traces)
    expected_total_count = baseline_total_count + 10
    assert total_count == expected_total_count, f"Expected total_count={expected_total_count} (baseline {baseline_total_count} + 10), got {total_count}"
    
    # Verify we got the top groups (ordered by count descending)
    assert get_group_value(groups[0], "count") == 3, "First group should have count=3"
    assert get_group_value(groups[1], "count") == 3, "Second group should have count=3"
    # Verify span names are from our test data
    assert get_group_value(groups[0], "span_name") in ["PaginationAppA", "PaginationAppB"], "First group should be PaginationAppA or PaginationAppB"
    assert get_group_value(groups[1], "span_name") in ["PaginationAppA", "PaginationAppB"], "Second group should be PaginationAppA or PaginationAppB"

    # Test 2: Second page with page_size=2 (should get next 2 groups)
    status_code, response = client.trace_api_get_unregistered_root_spans(
        page=1, page_size=2
    )
    assert status_code == 200, f"Expected 200, got {status_code}. Response: {response}"
    
    groups = response.groups if hasattr(response, "groups") else response["groups"]
    total_count = response.total_count if hasattr(response, "total_count") else response["total_count"]
    
    # Should get 2 groups (may include groups from other tests)
    assert len(groups) == 2, f"Expected 2 groups on second page, got {len(groups)}"
    # total_count should be baseline + 10 (our test traces)
    expected_total_count = baseline_total_count + 10
    assert total_count == expected_total_count, f"Expected total_count={expected_total_count} (baseline {baseline_total_count} + 10), got {total_count}"
    
    # Filter to only our Pagination groups to avoid interference from other tests
    pagination_groups = [g for g in groups if get_group_value(g, "span_name").startswith("Pagination")]
    
    # Note: Pagination groups may or may not appear on this specific page depending on ordering
    # We'll verify all our Pagination groups exist in a later test
    # Just verify that if Pagination groups are present, they have correct counts
    for pagination_group in pagination_groups:
        span_name = get_group_value(pagination_group, "span_name")
        count = get_group_value(pagination_group, "count")
        if span_name == "PaginationAppC":
            assert count == 2, f"PaginationAppC should have count=2, got {count}"
        elif span_name in ["PaginationAppD", "PaginationAppE"]:
            assert count == 1, f"{span_name} should have count=1, got {count}"

    # Test 3: Third page with page_size=2 (should get next groups)
    status_code, response = client.trace_api_get_unregistered_root_spans(
        page=2, page_size=2
    )
    assert status_code == 200, f"Expected 200, got {status_code}. Response: {response}"
    
    groups = response.groups if hasattr(response, "groups") else response["groups"]
    total_count = response.total_count if hasattr(response, "total_count") else response["total_count"]
    
    # total_count should be baseline + 10 (our test traces)
    expected_total_count = baseline_total_count + 10
    assert total_count == expected_total_count, f"Expected total_count={expected_total_count} (baseline {baseline_total_count} + 10), got {total_count}"
    
    # Filter to only our Pagination groups
    pagination_groups = [g for g in groups if get_group_value(g, "span_name").startswith("Pagination")]
    
    # We should have at least one Pagination group with count=1 (PaginationAppD or PaginationAppE)
    if len(pagination_groups) > 0:
        pagination_counts = [get_group_value(g, "count") for g in pagination_groups]
        # At least one should have count=1
        assert 1 in pagination_counts, f"Expected at least one Pagination group with count=1, got {pagination_counts}"

    # Test 4: Page beyond available data (should return empty list but same total_count)
    status_code, response = client.trace_api_get_unregistered_root_spans(
        page=10, page_size=2
    )
    assert status_code == 200, f"Expected 200, got {status_code}. Response: {response}"
    
    groups = response.groups if hasattr(response, "groups") else response["groups"]
    total_count = response.total_count if hasattr(response, "total_count") else response["total_count"]
    
    assert len(groups) == 0, f"Expected 0 groups on page beyond data, got {len(groups)}"
    # total_count should be baseline + 10 (our test traces)
    expected_total_count = baseline_total_count + 10
    assert total_count == expected_total_count, f"Expected total_count={expected_total_count} (baseline {baseline_total_count} + 10) even on empty page, got {total_count}"

    # Test 5: Large page_size (should get all groups)
    status_code, response = client.trace_api_get_unregistered_root_spans(
        page=0, page_size=100
    )
    assert status_code == 200, f"Expected 200, got {status_code}. Response: {response}"
    
    groups = response.groups if hasattr(response, "groups") else response["groups"]
    total_count = response.total_count if hasattr(response, "total_count") else response["total_count"]
    
    # Should get at least our 5 groups (may be more from other tests)
    pagination_groups = [g for g in groups if get_group_value(g, "span_name").startswith("Pagination")]
    assert len(pagination_groups) == 5, f"Expected 5 Pagination groups with large page_size, got {len(pagination_groups)}"
    # Verify our test groups are present
    pagination_span_names = [get_group_value(g, "span_name") for g in pagination_groups]
    assert "PaginationAppA" in pagination_span_names, "PaginationAppA should be present"
    assert "PaginationAppB" in pagination_span_names, "PaginationAppB should be present"
    assert "PaginationAppC" in pagination_span_names, "PaginationAppC should be present"
    assert "PaginationAppD" in pagination_span_names, "PaginationAppD should be present"
    assert "PaginationAppE" in pagination_span_names, "PaginationAppE should be present"
    # total_count should be baseline + 10 (our test traces)
    expected_total_count = baseline_total_count + 10
    assert total_count == expected_total_count, f"Expected total_count={expected_total_count} (baseline {baseline_total_count} + 10), got {total_count}"
