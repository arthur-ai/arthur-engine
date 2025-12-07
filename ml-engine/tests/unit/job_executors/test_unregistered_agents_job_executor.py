"""Tests for the FetchUnregisteredAgentsJobExecutor."""
from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

import pytest

from job_executors.unregistered_agents_job_executor import (
    FetchUnregisteredAgentsJobExecutor,
    FetchUnregisteredAgentsJobSpec,
)


@pytest.fixture
def mock_session():
    """Create a mock ArthurClientCredentialsAPISession."""
    session = Mock()
    session.token.return_value = {"access_token": "test_token"}
    return session


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    return Mock()


@pytest.fixture
def job_spec():
    """Create a test job spec."""
    return FetchUnregisteredAgentsJobSpec(
        data_plane_id=uuid4(),
        workspace_id=uuid4(),
    )


class TestFetchUnregisteredAgentsJobSpec:
    """Tests for the FetchUnregisteredAgentsJobSpec model."""

    def test_job_spec_has_correct_job_type(self):
        """Test that the job spec has the correct job_type."""
        spec = FetchUnregisteredAgentsJobSpec(
            data_plane_id=uuid4(),
            workspace_id=uuid4(),
        )
        assert spec.job_type == "fetch_unregistered_agents"

    def test_job_spec_requires_data_plane_id(self):
        """Test that the job spec requires a data_plane_id."""
        with pytest.raises(Exception):
            FetchUnregisteredAgentsJobSpec(workspace_id=uuid4())

    def test_job_spec_requires_workspace_id(self):
        """Test that the job spec requires a workspace_id."""
        with pytest.raises(Exception):
            FetchUnregisteredAgentsJobSpec(data_plane_id=uuid4())


class TestFetchUnregisteredAgentsJobExecutor:
    """Tests for the FetchUnregisteredAgentsJobExecutor."""

    def test_executor_init(self, mock_session, mock_logger):
        """Test that the executor initializes correctly."""
        executor = FetchUnregisteredAgentsJobExecutor(mock_session, mock_logger)
        assert executor.session == mock_session
        assert executor.logger == mock_logger

    @patch("job_executors.unregistered_agents_job_executor.EngineInternalConnector")
    @patch("job_executors.unregistered_agents_job_executor.requests")
    def test_execute_success(
        self,
        mock_requests,
        mock_connector_class,
        mock_session,
        mock_logger,
        job_spec,
    ):
        """Test successful execution of the job."""
        # Setup mock connector
        mock_connector = Mock()
        mock_connector_class.return_value = mock_connector

        # Setup mock spans response
        mock_spans_response = Mock()
        mock_spans_response.groups = [
            Mock(span_name="test_span_1", count=10),
            Mock(span_name="test_span_2", count=20),
        ]
        mock_connector._spans_client.get_unregistered_root_spans_api_v1_traces_spans_unregistered_get.return_value = (
            mock_spans_response
        )

        # Setup mock tasks response
        mock_task = Mock()
        mock_task.id = uuid4()
        mock_task.name = "test_task"
        mock_connector._tasks_client.get_all_tasks_api_v2_tasks_get.return_value = [mock_task]

        # Setup mock span count response
        mock_span_count_response = Mock()
        mock_span_count_response.count = 5
        mock_connector._spans_client.list_spans_metadata_api_v1_traces_spans_get.return_value = (
            mock_span_count_response
        )

        # Setup mock cache response
        mock_response = Mock()
        mock_response.status_code = 204
        mock_requests.put.return_value = mock_response

        # Execute
        executor = FetchUnregisteredAgentsJobExecutor(mock_session, mock_logger)
        executor.execute(job_spec)

        # Verify connector was created
        mock_connector_class.assert_called_once()

        # Verify spans were fetched
        mock_connector._spans_client.get_unregistered_root_spans_api_v1_traces_spans_unregistered_get.assert_called_once_with(
            page=0, page_size=1000
        )

        # Verify tasks were fetched
        mock_connector._tasks_client.get_all_tasks_api_v2_tasks_get.assert_called_once()

        # Verify cache endpoint was called
        mock_requests.put.assert_called_once()
        call_args = mock_requests.put.call_args
        assert f"/workspaces/{job_spec.workspace_id}/unregistered_agents/cache/{job_spec.data_plane_id}" in call_args[0][0]

    @patch("job_executors.unregistered_agents_job_executor.EngineInternalConnector")
    def test_execute_connector_creation_failure(
        self,
        mock_connector_class,
        mock_session,
        mock_logger,
        job_spec,
    ):
        """Test that connector creation failure is handled and re-raised."""
        mock_connector_class.side_effect = Exception("Connector creation failed")

        executor = FetchUnregisteredAgentsJobExecutor(mock_session, mock_logger)
        
        with pytest.raises(Exception) as exc_info:
            executor.execute(job_spec)

        assert "Connector creation failed" in str(exc_info.value)
        mock_logger.error.assert_called()

    @patch("job_executors.unregistered_agents_job_executor.EngineInternalConnector")
    @patch("job_executors.unregistered_agents_job_executor.requests")
    def test_execute_handles_empty_spans(
        self,
        mock_requests,
        mock_connector_class,
        mock_session,
        mock_logger,
        job_spec,
    ):
        """Test that the executor handles empty spans gracefully."""
        mock_connector = Mock()
        mock_connector_class.return_value = mock_connector

        # Setup empty spans response
        mock_spans_response = Mock()
        mock_spans_response.groups = []
        mock_connector._spans_client.get_unregistered_root_spans_api_v1_traces_spans_unregistered_get.return_value = (
            mock_spans_response
        )

        # Setup empty tasks response
        mock_connector._tasks_client.get_all_tasks_api_v2_tasks_get.return_value = []

        # Setup mock cache response
        mock_response = Mock()
        mock_response.status_code = 204
        mock_requests.put.return_value = mock_response

        executor = FetchUnregisteredAgentsJobExecutor(mock_session, mock_logger)
        executor.execute(job_spec)

        # Verify cache was still called with empty data
        mock_requests.put.assert_called_once()
        call_args = mock_requests.put.call_args
        assert call_args[1]["json"]["unregistered_agents_data"] == []

    @patch("job_executors.unregistered_agents_job_executor.EngineInternalConnector")
    @patch("job_executors.unregistered_agents_job_executor.requests")
    def test_execute_handles_spans_fetch_failure(
        self,
        mock_requests,
        mock_connector_class,
        mock_session,
        mock_logger,
        job_spec,
    ):
        """Test that the executor handles span fetch failure gracefully."""
        mock_connector = Mock()
        mock_connector_class.return_value = mock_connector

        # Setup spans fetch to fail
        mock_connector._spans_client.get_unregistered_root_spans_api_v1_traces_spans_unregistered_get.side_effect = (
            Exception("Span fetch failed")
        )

        # Setup tasks response
        mock_connector._tasks_client.get_all_tasks_api_v2_tasks_get.return_value = []

        # Setup mock cache response
        mock_response = Mock()
        mock_response.status_code = 204
        mock_requests.put.return_value = mock_response

        executor = FetchUnregisteredAgentsJobExecutor(mock_session, mock_logger)
        executor.execute(job_spec)

        # Verify error was logged but execution continued
        mock_logger.error.assert_called()

    @patch("job_executors.unregistered_agents_job_executor.EngineInternalConnector")
    @patch("job_executors.unregistered_agents_job_executor.requests")
    def test_execute_handles_cache_failure(
        self,
        mock_requests,
        mock_connector_class,
        mock_session,
        mock_logger,
        job_spec,
    ):
        """Test that the executor raises on cache failure."""
        mock_connector = Mock()
        mock_connector_class.return_value = mock_connector

        # Setup empty responses
        mock_spans_response = Mock()
        mock_spans_response.groups = []
        mock_connector._spans_client.get_unregistered_root_spans_api_v1_traces_spans_unregistered_get.return_value = (
            mock_spans_response
        )
        mock_connector._tasks_client.get_all_tasks_api_v2_tasks_get.return_value = []

        # Setup cache request to fail
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = Exception("Cache request failed")
        mock_requests.put.return_value = mock_response

        executor = FetchUnregisteredAgentsJobExecutor(mock_session, mock_logger)
        
        with pytest.raises(Exception) as exc_info:
            executor.execute(job_spec)

        assert "Cache request failed" in str(exc_info.value)


class TestFormatUnregisteredAgents:
    """Tests for the _format_unregistered_agents method."""

    def test_format_unregistered_spans(self, mock_session, mock_logger):
        """Test formatting of unregistered spans."""
        executor = FetchUnregisteredAgentsJobExecutor(mock_session, mock_logger)

        unregistered_spans = [
            {"span_name": "test_span", "count": 10},
        ]
        all_tasks: List[Dict[str, Any]] = []

        result = executor._format_unregistered_agents(unregistered_spans, all_tasks)

        assert len(result) == 1
        assert result[0]["creation_source"]["task_id"] is None
        assert result[0]["creation_source"]["top_level_span_name"] == "test_span"
        assert result[0]["num_spans"] == 10

    def test_format_tasks(self, mock_session, mock_logger):
        """Test formatting of tasks."""
        executor = FetchUnregisteredAgentsJobExecutor(mock_session, mock_logger)

        unregistered_spans: List[Dict[str, Any]] = []
        all_tasks = [
            {"task_id": "task-123", "task_name": "test_task", "span_count": 5},
        ]

        result = executor._format_unregistered_agents(unregistered_spans, all_tasks)

        assert len(result) == 1
        assert result[0]["creation_source"]["task_id"] == "task-123"
        assert result[0]["creation_source"]["top_level_span_name"] is None
        assert result[0]["num_spans"] == 5

    def test_format_combined(self, mock_session, mock_logger):
        """Test formatting of combined spans and tasks."""
        executor = FetchUnregisteredAgentsJobExecutor(mock_session, mock_logger)

        unregistered_spans = [
            {"span_name": "unregistered_span", "count": 10},
        ]
        all_tasks = [
            {"task_id": "task-123", "task_name": "test_task", "span_count": 5},
        ]

        result = executor._format_unregistered_agents(unregistered_spans, all_tasks)

        assert len(result) == 2
        # First item should be the unregistered span
        assert result[0]["creation_source"]["task_id"] is None
        assert result[0]["creation_source"]["top_level_span_name"] == "unregistered_span"
        # Second item should be the task
        assert result[1]["creation_source"]["task_id"] == "task-123"

