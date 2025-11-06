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
        # Verify token count/cost fields are present (may be None if no LLM spans)
        assert hasattr(user, "prompt_token_count")
        assert hasattr(user, "completion_token_count")
        assert hasattr(user, "total_token_count")
        assert hasattr(user, "prompt_token_cost")
        assert hasattr(user, "completion_token_cost")
        assert hasattr(user, "total_token_cost")


def assert_valid_user_details_response(user_details):
    """Assert response has valid user details structure."""
    assert user_details.user_id and isinstance(user_details.user_id, str)
    assert user_details.task_id and isinstance(user_details.task_id, str)
    assert (
        user_details.span_count is not None
        and isinstance(user_details.span_count, int)
        and user_details.span_count >= 0
    )
    # Verify token count/cost fields are present (may be None if no LLM spans)
    assert hasattr(user_details, "prompt_token_count")
    assert hasattr(user_details, "completion_token_count")
    assert hasattr(user_details, "total_token_count")
    assert hasattr(user_details, "prompt_token_cost")
    assert hasattr(user_details, "completion_token_cost")
    assert hasattr(user_details, "total_token_cost")
    assert user_details.earliest_start_time is not None
    assert user_details.latest_end_time is not None
    assert isinstance(user_details.session_ids, list)
    assert isinstance(user_details.trace_ids, list)
    assert (
        user_details.session_count is not None
        and isinstance(user_details.session_count, int)
        and user_details.session_count >= 0
    )
    assert (
        user_details.trace_count is not None
        and isinstance(user_details.trace_count, int)
        and user_details.trace_count >= 0
    )


# ============================================================================
# USER METADATA LIST TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_list_users_metadata_functionality(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test user metadata listing functionality for single and multiple tasks."""

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
    # User1 has traces with token data:
    # - api_trace1: span1 (100/50/150), span2 (None)
    # - api_trace2: span3 (200/100/300)
    # - api_trace4: span6 (None - TOOL span)
    # Total: 300 prompt, 150 completion, 450 total
    assert user.prompt_token_count == 300
    assert user.completion_token_count == 150
    assert user.total_token_count == 450
    assert user.prompt_token_cost == 0.003  # 0.001 + 0.002
    assert user.completion_token_cost == 0.005  # 0.002 + 0.003
    assert user.total_token_cost == 0.008  # 0.003 + 0.005

    # Test multiple tasks
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
def test_list_users_metadata_sorting_and_pagination(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test user metadata sorting and pagination."""

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

    # Test pagination
    status_code, data = client.trace_api_list_users_metadata(
        task_ids=["api_task1", "api_task2"],
        page=0,
        page_size=1,
    )
    assert status_code == 200
    assert data.count == 2  # Total count
    assert len(data.users) == 1  # Page size


@pytest.mark.unit_tests
def test_list_users_metadata_validation_and_errors(
    client: GenaiEngineTestClientBase,
):
    """Test validation errors and edge cases for user metadata listing."""

    # Test empty task_ids (should return 400)
    status_code, response = client.trace_api_list_users_metadata(task_ids=[])
    assert status_code == 400

    # Test non-existent task (should return 200 with 0 results)
    status_code, data = client.trace_api_list_users_metadata(
        task_ids=["non_existent_task"],
    )
    assert status_code == 200
    assert data.count == 0
    assert len(data.users) == 0

    # Verify response structure is valid even with no results
    assert isinstance(data.count, int) and data.count >= 0
    assert isinstance(data.users, list)


# ============================================================================
# USER DETAILS RETRIEVAL TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_get_user_details_functionality(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test retrieving details for a specific user with various scenarios."""

    # Get details for user1
    status_code, data = client.trace_api_get_user_details(
        "user1",
        task_ids=["api_task1"],
    )
    assert status_code == 200

    # Verify user details structure
    assert_valid_user_details_response(data)

    # Verify user details match expected values
    assert data.user_id == "user1"
    assert data.task_id == "api_task1"
    assert data.span_count == 4  # user1 has 4 spans (span1, span2, span3, span6)
    assert data.session_count == 1  # user1 has 1 session (session1)
    assert (
        data.trace_count == 3
    )  # user1 has 3 traces (api_trace1, api_trace2, api_trace4)
    assert data.earliest_start_time is not None
    assert data.latest_end_time is not None

    # Verify session and trace IDs
    assert "session1" in data.session_ids
    expected_trace_ids = {"api_trace1", "api_trace2", "api_trace4"}
    assert set(data.trace_ids) == expected_trace_ids

    # Test with multiple task IDs
    status_code, data = client.trace_api_get_user_details(
        "user1",
        task_ids=["api_task1", "api_task2"],
    )
    assert status_code == 200
    assert_valid_user_details_response(data)
    assert data.user_id == "user1"
    assert data.task_id == "api_task1"  # Should match the task where user1 has data

    # Test non-existent user
    status_code, response_data = client.trace_api_get_user_details(
        "non_existent_user",
        task_ids=["api_task1"],
    )
    assert status_code == 404
    assert "not found" in response_data.lower()


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================


@pytest.mark.unit_tests
def test_user_api_error_handling_and_consistency(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test error handling and data consistency in user API."""

    # Test server error in user metadata listing
    with patch(
        "repositories.span_repository.SpanRepository.get_users_metadata",
        side_effect=Exception("Database error"),
    ):
        status_code, _ = client.trace_api_list_users_metadata(task_ids=["api_task1"])
        assert status_code == 500

    # Test server error in user details retrieval
    with patch(
        "repositories.span_repository.SpanRepository.get_user_details",
        side_effect=Exception("Database error"),
    ):
        status_code, _ = client.trace_api_get_user_details(
            "user1",
            task_ids=["api_task1"],
        )
        assert status_code == 500

    # Test consistency between user metadata and user details
    status_code, users_response = client.trace_api_list_users_metadata(
        task_ids=["api_task1"],
    )
    assert status_code == 200

    user_metadata = users_response.users[0]
    user_id = user_metadata.user_id

    # Get user details
    status_code, user_details = client.trace_api_get_user_details(
        user_id,
        task_ids=["api_task1"],
    )
    assert status_code == 200

    # Verify consistency between metadata and details
    assert user_details.user_id == user_metadata.user_id
    assert user_details.task_id == user_metadata.task_id
    assert user_details.span_count == user_metadata.span_count
    assert user_details.session_count == user_metadata.session_count
    assert user_details.trace_count == user_metadata.trace_count

    # Verify session IDs match
    assert set(user_details.session_ids) == set(user_metadata.session_ids)

    # Verify trace IDs match
    assert set(user_details.trace_ids) == set(user_metadata.trace_ids)
