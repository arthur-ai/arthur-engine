from unittest.mock import patch

import pytest

from tests.clients.base_test_client import GenaiEngineTestClientBase

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def assert_valid_user_metadata_response(users):
    """Assert response has valid user metadata structure."""
    for user in users:
        assert user.user_id and isinstance(user.user_id, str)
        assert user.task_id and isinstance(user.task_id, str)
        assert (
            user.span_count is not None
            and isinstance(user.span_count, int)
            and user.span_count >= 0
        )
        assert user.earliest_start_time is not None
        assert user.latest_end_time is not None
        assert isinstance(user.session_ids, list)
        assert isinstance(user.trace_ids, list)
        assert (
            user.session_count is not None
            and isinstance(user.session_count, int)
            and user.session_count >= 0
        )
        assert (
            user.trace_count is not None
            and isinstance(user.trace_count, int)
            and user.trace_count >= 0
        )


def assert_valid_user_sessions_response(sessions):
    """Assert response has valid user sessions structure."""
    for session in sessions:
        assert session.session_id and isinstance(session.session_id, str)
        assert session.task_id and isinstance(session.task_id, str)
        assert (
            session.span_count is not None
            and isinstance(session.span_count, int)
            and session.span_count >= 0
        )
        assert session.earliest_start_time is not None
        assert session.latest_end_time is not None
        assert isinstance(session.trace_ids, list)
        assert (
            session.trace_count is not None
            and isinstance(session.trace_count, int)
            and session.trace_count >= 0
        )


def assert_valid_user_traces_response(traces):
    """Assert response has valid user traces structure."""
    for trace in traces:
        assert trace.trace_id and isinstance(trace.trace_id, str)
        assert trace.task_id and isinstance(trace.task_id, str)
        assert trace.start_time is not None
        assert trace.end_time is not None
        assert (
            trace.span_count is not None
            and isinstance(trace.span_count, int)
            and trace.span_count >= 0
        )


# ============================================================================
# USER METADATA LIST TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_list_users_metadata_basic_functionality(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test basic user metadata listing functionality."""

    # Test single task - should return user1 with api_task1 data
    status_code, data = client.trace_api_list_users_metadata(task_ids=["api_task1"])
    assert status_code == 200
    assert data.count == 1  # Only user1 has api_task1 traces
    assert len(data.users) == 1

    # Verify user metadata structure
    assert_valid_user_metadata_response(data.users)

    user = data.users[0]
    assert user.user_id == "user1"
    assert user.task_id == "api_task1"
    assert user.span_count == 4  # user1 has 4 spans (span1, span2, span3, span6)
    assert user.session_count == 1  # user1 has 1 session (session1)
    assert (
        user.trace_count == 3
    )  # user1 has 3 traces (api_trace1, api_trace2, api_trace4)
    assert user.earliest_start_time is not None
    assert user.latest_end_time is not None


@pytest.mark.unit_tests
def test_list_users_metadata_multiple_tasks(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test listing users for multiple tasks."""

    # Use trace_api method for proper response handling
    status_code, data = client.trace_api_list_users_metadata(
        task_ids=["api_task1", "api_task2"],
    )
    assert status_code == 200

    assert data.count == 2  # user1 (api_task1) and user2 (api_task2)
    assert len(data.users) == 2

    # Verify we have users from both tasks
    user_data = {(u.user_id, u.task_id) for u in data.users}
    expected_users = {("user1", "api_task1"), ("user2", "api_task2")}
    assert user_data == expected_users


@pytest.mark.unit_tests
def test_list_users_metadata_sorting(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test user metadata sorting by earliest_start_time."""

    # Test default sorting (descending)
    status_code, data = client.trace_api_list_users_metadata(
        task_ids=["api_task1", "api_task2"],
    )
    assert status_code == 200
    assert data.count == 2  # user1 and user2
    assert len(data.users) == 2
    users = data.users

    # Verify we have the expected users
    user_data = {(u.user_id, u.task_id) for u in users}
    expected_users = {("user1", "api_task1"), ("user2", "api_task2")}
    assert user_data == expected_users

    # Verify descending order (most recent first)
    for i in range(len(users) - 1):
        current_time = users[i].earliest_start_time
        next_time = users[i + 1].earliest_start_time
        assert current_time >= next_time


@pytest.mark.unit_tests
def test_list_users_metadata_pagination(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test user metadata pagination."""

    # Test first page
    status_code, data = client.trace_api_list_users_metadata(
        task_ids=["api_task1", "api_task2"],
        page=0,
        page_size=1,
    )
    assert status_code == 200
    assert data.count == 2  # Total count
    assert len(data.users) == 1  # Page size


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
def test_list_users_metadata_validation_errors(
    client: GenaiEngineTestClientBase,
    task_ids,
    expected_status,
):
    """Test validation errors for user metadata listing."""

    status_code, response = client.trace_api_list_users_metadata(task_ids=task_ids)
    assert status_code == expected_status

    if expected_status == 200:
        # Should have valid response structure even with no results
        assert (
            response.count is not None
            and isinstance(response.count, int)
            and response.count >= 0
        )
        assert isinstance(response.users, list)
        if task_ids == ["non_existent_task"]:
            assert response.count == 0
    # For 400 status, response will be error text


@pytest.mark.unit_tests
def test_list_users_metadata_empty_results(
    client: GenaiEngineTestClientBase,
):
    """Test listing users with no results."""

    status_code, data = client.trace_api_list_users_metadata(
        task_ids=["non_existent_task"],
    )
    assert status_code == 200
    assert data.count == 0
    assert len(data.users) == 0


# ============================================================================
# USER SESSIONS RETRIEVAL TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_get_user_sessions_basic_functionality(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test retrieving sessions for a specific user."""

    # Get sessions for user1
    status_code, data = client.trace_api_get_user_sessions("user1")
    assert status_code == 200
    assert data.user_id == "user1"
    assert data.count == 1  # user1 has 1 session (session1)
    assert len(data.sessions) == 1

    # Verify sessions structure
    assert_valid_user_sessions_response(data.sessions)

    # Verify session belongs to user1
    session = data.sessions[0]
    assert session.session_id == "session1"
    assert session.task_id == "api_task1"


@pytest.mark.unit_tests
def test_get_user_sessions_not_found(
    client: GenaiEngineTestClientBase,
):
    """Test retrieving sessions for non-existent user returns empty results."""

    status_code, response_data = client.trace_api_get_user_sessions(
        "non_existent_user",
    )
    assert status_code == 200  # Empty results are OK, not 404
    # Verify empty response structure
    assert response_data.user_id == "non_existent_user"
    assert response_data.count == 0
    assert len(response_data.sessions) == 0


@pytest.mark.unit_tests
def test_get_user_sessions_pagination(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test user sessions pagination."""

    # Test pagination with small page size
    status_code, data = client.trace_api_get_user_sessions("user1", page=0, page_size=1)
    assert status_code == 200
    assert data.user_id == "user1"
    assert data.count == 1  # Total sessions for user1
    assert (
        len(data.sessions) == 1
    )  # Page size and actual count match since user1 has only 1 session

    # Verify the specific session
    session = data.sessions[0]
    assert session.session_id == "session1"
    assert session.task_id == "api_task1"


# ============================================================================
# USER TRACES RETRIEVAL TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_get_user_traces_basic_functionality(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test retrieving traces for a specific user."""

    # Get traces for user1
    status_code, data = client.trace_api_get_user_traces("user1")
    assert status_code == 200
    assert data.user_id == "user1"
    assert data.count == 3  # user1 has 3 traces (api_trace1, api_trace2, api_trace4)
    assert len(data.traces) == 3

    # Verify traces structure
    assert_valid_user_traces_response(data.traces)

    # Verify we have the expected traces
    trace_ids = {trace.trace_id for trace in data.traces}
    expected_trace_ids = {"api_trace1", "api_trace2", "api_trace4"}
    assert trace_ids == expected_trace_ids

    # Verify all traces belong to user1's task
    for trace in data.traces:
        assert trace.task_id == "api_task1"  # user1 is associated with api_task1


@pytest.mark.unit_tests
def test_get_user_traces_not_found(
    client: GenaiEngineTestClientBase,
):
    """Test retrieving traces for non-existent user returns empty results."""

    status_code, response_data = client.trace_api_get_user_traces(
        "non_existent_user",
    )
    assert status_code == 200  # Empty results are OK, not 404
    # Verify empty response structure
    assert response_data.user_id == "non_existent_user"
    assert response_data.count == 0
    assert len(response_data.traces) == 0


@pytest.mark.unit_tests
def test_get_user_traces_sorting(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test user traces sorting by start_time."""

    # Test default sorting (descending)
    status_code, data = client.trace_api_get_user_traces("user1")
    assert status_code == 200
    assert data.user_id == "user1"
    assert data.count == 3  # user1 has 3 traces total
    assert len(data.traces) == 3
    traces = data.traces

    # Verify we have the expected traces
    trace_ids = {trace.trace_id for trace in traces}
    expected_trace_ids = {"api_trace1", "api_trace2", "api_trace4"}
    assert trace_ids == expected_trace_ids

    # Verify descending order (most recent first)
    for i in range(len(traces) - 1):
        current_time = traces[i].start_time
        next_time = traces[i + 1].start_time
        assert current_time >= next_time


@pytest.mark.unit_tests
def test_get_user_traces_pagination(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test user traces pagination."""

    # Test pagination with small page size
    status_code, data = client.trace_api_get_user_traces("user1", page=0, page_size=1)
    assert status_code == 200
    assert data.user_id == "user1"
    assert data.count == 3  # Total count - user1 has 3 traces
    assert len(data.traces) == 1  # Page size


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================


@pytest.mark.unit_tests
def test_user_api_error_handling(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test various error conditions in user API."""

    # Test server error in user metadata listing
    with patch(
        "repositories.span_repository.SpanRepository.get_users_metadata",
        side_effect=Exception("Database error"),
    ):
        status_code, _ = client.trace_api_list_users_metadata(task_ids=["api_task1"])
        assert status_code == 500

    # Test server error in user sessions retrieval
    with patch(
        "repositories.span_repository.SpanRepository.get_user_sessions",
        side_effect=Exception("Database error"),
    ):
        status_code, _ = client.trace_api_get_user_sessions("user1")
        assert status_code == 500

    # Test server error in user traces retrieval
    with patch(
        "repositories.span_repository.SpanRepository.get_user_traces",
        side_effect=Exception("Database error"),
    ):
        status_code, _ = client.trace_api_get_user_traces("user1")
        assert status_code == 500


@pytest.mark.unit_tests
def test_user_aggregation_consistency(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test consistency between user metadata and actual user data."""

    # Get user metadata
    status_code, users_response = client.trace_api_list_users_metadata(
        task_ids=["api_task1"],
    )
    assert status_code == 200

    user_metadata = users_response.users[0]
    user_id = user_metadata.user_id

    # Get actual user sessions
    status_code, user_sessions = client.trace_api_get_user_sessions(user_id)
    assert status_code == 200

    # Get actual user traces
    status_code, user_traces = client.trace_api_get_user_traces(user_id)
    assert status_code == 200

    # Verify consistency between metadata and actual data
    assert user_sessions.count == user_metadata.session_count
    assert user_traces.count == user_metadata.trace_count

    # Verify session IDs match
    actual_session_ids = {session.session_id for session in user_sessions.sessions}
    expected_session_ids = set(user_metadata.session_ids)
    assert actual_session_ids == expected_session_ids

    # Verify trace IDs match
    actual_trace_ids = {trace.trace_id for trace in user_traces.traces}
    expected_trace_ids = set(user_metadata.trace_ids)
    assert actual_trace_ids == expected_trace_ids
