from unittest.mock import patch

import pytest

from tests.clients.base_test_client import GenaiEngineTestClientBase

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def assert_valid_session_metadata_response(sessions):
    """Assert response has valid session metadata structure."""
    for session in sessions:
        assert session.session_id and isinstance(session.session_id, str)
        assert session.task_id and isinstance(session.task_id, str)
        assert session.user_id is not None  # Should have user_id
        assert (
            session.span_count is not None
            and isinstance(session.span_count, int)
            and session.span_count >= 0
        )
        assert session.earliest_start_time is not None
        assert session.latest_end_time is not None
        # Verify token count/cost fields are present (may be None if no LLM spans)
        assert hasattr(session, "prompt_token_count")
        assert hasattr(session, "completion_token_count")
        assert hasattr(session, "total_token_count")
        assert hasattr(session, "prompt_token_cost")
        assert hasattr(session, "completion_token_cost")
        assert hasattr(session, "total_token_cost")


def assert_valid_session_traces_response(traces):
    """Assert response has valid session traces structure."""
    for trace in traces:
        assert trace.trace_id and isinstance(trace.trace_id, str)
        assert trace.start_time is not None
        assert trace.end_time is not None
        assert hasattr(trace, "root_spans") and isinstance(trace.root_spans, list)


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
    for child in getattr(nested_span, "children", []):
        spans.extend(get_all_spans_from_nested_span(child))
    return spans


def find_spans_by_kind(spans, span_kind):
    """Helper function to find all spans matching the given kind."""
    return [span for span in spans if getattr(span, "span_kind", None) == span_kind]


# ============================================================================
# SESSION METADATA LIST TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_list_sessions_metadata_functionality(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test session metadata listing functionality for single and multiple tasks."""

    # Test single task
    status_code, data = client.trace_api_list_sessions_metadata(task_ids=["api_task1"])
    assert status_code == 200
    assert data.count == 1  # Only session1 has api_task1 traces
    assert len(data.sessions) == 1

    # Verify session metadata structure
    assert_valid_session_metadata_response(data.sessions)

    session = data.sessions[0]
    assert session.session_id == "session1"
    assert session.task_id == "api_task1"
    assert session.span_count > 0
    assert session.earliest_start_time is not None
    assert session.latest_end_time is not None
    # Session1 has api_trace1 (span1: 100/50/150, span2: None) and api_trace2 (span3: 200/100/300)
    # Total: 300 prompt, 150 completion, 450 total
    assert session.prompt_token_count == 300
    assert session.completion_token_count == 150
    assert session.total_token_count == 450
    assert session.prompt_token_cost == 0.003  # 0.001 + 0.002
    assert session.completion_token_cost == 0.005  # 0.002 + 0.003
    assert session.total_token_cost == 0.008  # 0.003 + 0.005

    # Test multiple tasks
    status_code, data = client.trace_api_list_sessions_metadata(
        task_ids=["api_task1", "api_task2"],
    )
    assert status_code == 200
    assert data.count == 2  # session1 (api_task1) and session2 (api_task2)
    assert len(data.sessions) == 2

    # Verify we have sessions from both tasks
    session_data = {(s.session_id, s.task_id) for s in data.sessions}
    expected_sessions = {("session1", "api_task1"), ("session2", "api_task2")}
    assert session_data == expected_sessions


@pytest.mark.unit_tests
def test_list_sessions_metadata_filtering_by_user_ids(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test filtering sessions by user IDs."""

    # Filter sessions by user1
    status_code, data = client.trace_api_list_sessions_metadata(
        task_ids=["api_task1"],
        user_ids=["user1"],
    )
    assert status_code == 200
    assert data.count == 1  # user1 has 1 session in api_task1
    assert len(data.sessions) == 1

    # Verify session belongs to user1
    session = data.sessions[0]
    assert session.user_id == "user1"
    assert session.task_id == "api_task1"
    assert session.session_id == "session1"

    # Filter by multiple users
    status_code, data = client.trace_api_list_sessions_metadata(
        task_ids=["api_task1", "api_task2"],
        user_ids=["user1", "user2"],
    )
    assert status_code == 200
    assert data.count == 2  # user1 has 1 session, user2 has 1 session
    assert len(data.sessions) == 2

    # Verify we have sessions from both users
    user_ids = {session.user_id for session in data.sessions}
    assert user_ids == {"user1", "user2"}

    # Filter by non-existent user
    status_code, data = client.trace_api_list_sessions_metadata(
        task_ids=["api_task1"],
        user_ids=["non_existent_user"],
    )
    assert status_code == 200
    assert data.count == 0
    assert len(data.sessions) == 0


@pytest.mark.unit_tests
def test_list_sessions_metadata_sorting_pagination_and_validation(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test session metadata sorting, pagination, and validation."""

    # Test default sorting (descending)
    status_code, data = client.trace_api_list_sessions_metadata(
        task_ids=["api_task1", "api_task2"],
    )
    assert status_code == 200
    sessions = data.sessions

    # Verify descending order (most recent first)
    for i in range(len(sessions) - 1):
        current_time = sessions[i].earliest_start_time
        next_time = sessions[i + 1].earliest_start_time
        assert current_time >= next_time

    # Test pagination
    status_code, data = client.trace_api_list_sessions_metadata(
        task_ids=["api_task1", "api_task2"],
        page=0,
        page_size=1,
    )
    assert status_code == 200
    assert data.count == 2  # Total count
    assert len(data.sessions) == 1  # Page size

    # Test validation errors
    # Empty task_ids (should return 400)
    status_code, response = client.trace_api_list_sessions_metadata(task_ids=[])
    assert status_code == 400

    # Non-existent task (should return 200 with 0 results)
    status_code, data = client.trace_api_list_sessions_metadata(
        task_ids=["non_existent_task"],
    )
    assert status_code == 200
    assert data.count == 0
    assert len(data.sessions) == 0


@pytest.mark.unit_tests
def test_list_sessions_metadata_empty_results(
    client: GenaiEngineTestClientBase,
):
    """Test listing sessions with no results."""

    status_code, data = client.trace_api_list_sessions_metadata(
        task_ids=["non_existent_task"],
    )
    assert status_code == 200
    assert data.count == 0
    assert len(data.sessions) == 0


# ============================================================================
# SESSION TRACES RETRIEVAL TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_get_session_traces_basic_functionality(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test retrieving traces for a specific session."""

    # Get traces for session1
    status_code, data = client.trace_api_get_session_traces("session1")
    assert status_code == 200
    assert data.session_id == "session1"
    assert data.count == 2  # session1 has 2 traces (api_trace1, api_trace2)
    assert len(data.traces) == 2

    # Verify traces structure
    assert_valid_session_traces_response(data.traces)

    # Verify all traces belong to session1
    for trace in data.traces:
        # Get all spans to check session_id
        all_spans = get_all_spans_from_traces([trace])
        for span in all_spans:
            if getattr(
                span,
                "session_id",
                None,
            ):  # Some spans might not have session_id
                assert span.session_id == "session1"


@pytest.mark.unit_tests
def test_get_session_traces_with_existing_metrics(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test session traces include existing metrics but don't compute new ones."""

    status_code, data = client.trace_api_get_session_traces("session1")
    assert status_code == 200
    all_spans = get_all_spans_from_traces(data.traces)

    # Find LLM spans which should have metrics
    llm_spans = find_spans_by_kind(all_spans, "LLM")
    assert len(llm_spans) >= 1

    for llm_span in llm_spans:
        assert hasattr(
            llm_span,
            "metric_results",
        )  # Field exists, but may be None or list
        # May or may not have existing metrics depending on span


@pytest.mark.unit_tests
def test_get_session_traces_not_found(
    client: GenaiEngineTestClientBase,
):
    """Test retrieving traces for non-existent session returns 404."""

    status_code, response_data = client.trace_api_get_session_traces(
        "non_existent_session",
    )
    assert status_code == 404
    assert "not found" in response_data.lower()


@pytest.mark.unit_tests
def test_get_session_traces_nested_structure(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test session traces have proper nested structure."""

    status_code, data = client.trace_api_get_session_traces("session1")
    assert status_code == 200

    # Find trace1 which has nested structure
    trace1 = next((t for t in data.traces if t.trace_id == "api_trace1"), None)
    assert trace1 is not None

    # Verify nested structure
    assert len(trace1.root_spans) == 1
    root_span = trace1.root_spans[0]

    assert root_span.span_id == "api_span1"
    assert root_span.span_kind == "LLM"
    assert len(root_span.children) == 1

    child_span = root_span.children[0]
    assert child_span.span_id == "api_span2"
    assert child_span.span_kind == "CHAIN"
    assert child_span.parent_span_id == "api_span1"


# ============================================================================
# COMPUTE SESSION METRICS TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_compute_session_metrics_basic_functionality(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test computing missing metrics for session traces."""

    status_code, data = client.trace_api_compute_session_metrics("session1")
    assert status_code == 200
    assert data.session_id == "session1"
    assert data.count == 2  # Same number of traces

    # Verify structure is the same as regular session traces
    assert_valid_session_traces_response(data.traces)


@pytest.mark.unit_tests
def test_compute_session_metrics_not_found(
    client: GenaiEngineTestClientBase,
):
    """Test computing metrics for non-existent session returns 404."""

    status_code, response_data = client.trace_api_compute_session_metrics(
        "non_existent_session",
    )
    assert status_code == 404
    assert "not found" in response_data.lower()


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================


@pytest.mark.unit_tests
def test_session_api_error_handling(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test various error conditions in session API."""

    # Test server error in session metadata listing
    with patch(
        "repositories.span_repository.SpanRepository.get_sessions_metadata",
        side_effect=Exception("Database error"),
    ):
        status_code, _ = client.trace_api_list_sessions_metadata(task_ids=["api_task1"])
        assert status_code == 500

    # Test server error in session traces retrieval
    with patch(
        "repositories.span_repository.SpanRepository.get_session_traces",
        side_effect=Exception("Database error"),
    ):
        status_code, _ = client.trace_api_get_session_traces("session1")
        assert status_code == 500


@pytest.mark.unit_tests
def test_session_aggregation_consistency(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test consistency between session metadata and actual session traces."""

    # Get session metadata
    status_code, sessions_response = client.trace_api_list_sessions_metadata(
        task_ids=["api_task1"],
    )
    assert status_code == 200

    session_metadata = sessions_response.sessions[0]
    session_id = session_metadata.session_id

    # Get actual session traces
    status_code, session_traces = client.trace_api_get_session_traces(session_id)
    assert status_code == 200

    # Verify consistency
    actual_trace_count = session_traces.count
    expected_span_count = session_metadata.span_count

    # Count actual spans in traces
    all_spans = get_all_spans_from_traces(session_traces.traces)
    actual_span_count = len(all_spans)

    assert actual_span_count == expected_span_count
