from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from db_models import (
    DatabaseServiceNameTaskMapping,
    DatabaseSpan,
    DatabaseTask,
    DatabaseTraceMetadata,
)
from repositories.service_name_mapping_repository import ServiceNameMappingRepository


@pytest.mark.unit_tests
def test_create_mapping_success():
    """Test successful creation of service name mapping with retroactive updates."""
    # Setup
    db_session = MagicMock()
    resource_metadata_repo = MagicMock()
    repo = ServiceNameMappingRepository(db_session, resource_metadata_repo)

    service_name = "test-service"
    task_id = "task-123"

    # Mock task exists
    mock_task = MagicMock(spec=DatabaseTask)
    mock_task.id = task_id
    db_session.query.return_value.filter.return_value.filter.return_value.first.return_value = (
        mock_task
    )

    # Mock no existing mapping
    with patch.object(repo, "get_mapping", return_value=None):
        # Mock retroactive update
        with patch.object(repo, "_retroactive_update_traces", return_value=5):
            # Execute
            mapping, traces_updated = repo.create_mapping(service_name, task_id)

            # Verify
            assert mapping.service_name == service_name
            assert mapping.task_id == task_id
            assert traces_updated == 5

            db_session.add.assert_called_once()
            db_session.commit.assert_called_once()


@pytest.mark.unit_tests
def test_create_mapping_task_not_found():
    """Test creating mapping fails when task doesn't exist."""
    # Setup
    db_session = MagicMock()
    repo = ServiceNameMappingRepository(db_session)

    service_name = "test-service"
    task_id = "non-existent-task"

    # Mock task doesn't exist
    db_session.query.return_value.filter.return_value.filter.return_value.first.return_value = (
        None
    )

    # Execute & Verify
    with pytest.raises(HTTPException) as exc_info:
        repo.create_mapping(service_name, task_id)

    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()


@pytest.mark.unit_tests
def test_create_mapping_already_exists():
    """Test creating mapping fails when mapping already exists."""
    # Setup
    db_session = MagicMock()
    repo = ServiceNameMappingRepository(db_session)

    service_name = "test-service"
    task_id = "task-123"

    # Mock task exists
    mock_task = MagicMock(spec=DatabaseTask)
    db_session.query.return_value.filter.return_value.filter.return_value.first.return_value = (
        mock_task
    )

    # Mock existing mapping
    existing_mapping = MagicMock(spec=DatabaseServiceNameTaskMapping)
    existing_mapping.task_id = "existing-task"
    with patch.object(repo, "get_mapping", return_value=existing_mapping):
        # Execute & Verify
        with pytest.raises(HTTPException) as exc_info:
            repo.create_mapping(service_name, task_id)

        assert exc_info.value.status_code == 409
        assert "already exists" in exc_info.value.detail.lower()


@pytest.mark.unit_tests
def test_retroactive_update_traces():
    """Test retroactive trace updates from system task when creating mapping."""
    # Setup
    db_session = MagicMock()
    resource_metadata_repo = MagicMock()
    repo = ServiceNameMappingRepository(db_session, resource_metadata_repo)

    service_name = "test-service"
    task_id = "task-123"

    # Mock system task ID
    with patch("repositories.service_name_mapping_repository.get_system_task_id", return_value="system-task-id"):
        # Mock resource IDs
        resource_metadata_repo.get_resource_ids_by_service_name.return_value = [
            "res1",
            "res2",
        ]

        # Mock trace IDs query (traces currently in system task)
        mock_trace_query_result = [("trace1",), ("trace2",), ("trace3",)]
        db_session.execute.return_value.fetchall.return_value = mock_trace_query_result

        # Execute
        traces_updated = repo._retroactive_update_traces(service_name, task_id)

        # Verify
        assert traces_updated == 3

        # Verify execute was called 3 times (1 select + 2 updates)
        assert db_session.execute.call_count == 3


@pytest.mark.unit_tests
def test_retroactive_update_traces_no_resources():
    """Test retroactive update when no resources found."""
    # Setup
    db_session = MagicMock()
    resource_metadata_repo = MagicMock()
    repo = ServiceNameMappingRepository(db_session, resource_metadata_repo)

    service_name = "test-service"
    task_id = "task-123"

    # Mock system task ID
    with patch("repositories.service_name_mapping_repository.get_system_task_id", return_value="system-task-id"):
        # Mock no resources found
        resource_metadata_repo.get_resource_ids_by_service_name.return_value = []

        # Execute
        traces_updated = repo._retroactive_update_traces(service_name, task_id)

        # Verify
        assert traces_updated == 0
        db_session.execute.assert_not_called()


@pytest.mark.unit_tests
def test_retroactive_update_traces_no_system_task_traces():
    """Test retroactive update when no traces in system task."""
    # Setup
    db_session = MagicMock()
    resource_metadata_repo = MagicMock()
    repo = ServiceNameMappingRepository(db_session, resource_metadata_repo)

    service_name = "test-service"
    task_id = "task-123"

    # Mock system task ID
    with patch("repositories.service_name_mapping_repository.get_system_task_id", return_value="system-task-id"):
        # Mock resources found
        resource_metadata_repo.get_resource_ids_by_service_name.return_value = [
            "res1",
            "res2",
        ]

        # Mock no traces in system task
        db_session.execute.return_value.fetchall.return_value = []

        # Execute
        traces_updated = repo._retroactive_update_traces(service_name, task_id)

        # Verify
        assert traces_updated == 0
        # execute called once for the SELECT query
        assert db_session.execute.call_count == 1


@pytest.mark.unit_tests
def test_get_mapping_found():
    """Test getting existing mapping."""
    # Setup
    db_session = MagicMock()
    repo = ServiceNameMappingRepository(db_session)

    service_name = "test-service"
    mock_mapping = MagicMock(spec=DatabaseServiceNameTaskMapping)
    mock_mapping.service_name = service_name

    db_session.query.return_value.filter.return_value.first.return_value = mock_mapping

    # Execute
    result = repo.get_mapping(service_name)

    # Verify
    assert result == mock_mapping


@pytest.mark.unit_tests
def test_get_mapping_not_found():
    """Test getting non-existent mapping."""
    # Setup
    db_session = MagicMock()
    repo = ServiceNameMappingRepository(db_session)

    db_session.query.return_value.filter.return_value.first.return_value = None

    # Execute
    result = repo.get_mapping("non-existent")

    # Verify
    assert result is None


@pytest.mark.unit_tests
def test_list_mappings():
    """Test listing mappings with pagination."""
    # Setup
    db_session = MagicMock()
    repo = ServiceNameMappingRepository(db_session)

    mock_mappings = [
        MagicMock(spec=DatabaseServiceNameTaskMapping),
        MagicMock(spec=DatabaseServiceNameTaskMapping),
    ]

    mock_query = MagicMock()
    db_session.query.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.count.return_value = 10
    mock_query.limit.return_value.offset.return_value.all.return_value = mock_mappings

    # Execute
    results, total_count = repo.list_mappings(page=0, page_size=20)

    # Verify
    assert results == mock_mappings
    assert total_count == 10


@pytest.mark.unit_tests
def test_update_mapping_success():
    """Test successful update of mapping with retroactive reassignment."""
    # Setup
    db_session = MagicMock()
    repo = ServiceNameMappingRepository(db_session)

    service_name = "test-service"
    old_task_id = "old-task"
    new_task_id = "new-task"

    # Mock existing mapping
    mock_mapping = MagicMock(spec=DatabaseServiceNameTaskMapping)
    mock_mapping.task_id = old_task_id
    with patch.object(repo, "get_mapping", return_value=mock_mapping):
        # Mock new task exists
        mock_task = MagicMock(spec=DatabaseTask)
        db_session.query.return_value.filter.return_value.filter.return_value.first.return_value = (
            mock_task
        )

        # Mock reassignment
        with patch.object(repo, "_reassign_traces", return_value=3):
            # Execute
            mapping, traces_updated = repo.update_mapping(service_name, new_task_id)

            # Verify
            assert mapping.task_id == new_task_id
            assert traces_updated == 3
            db_session.commit.assert_called_once()


@pytest.mark.unit_tests
def test_update_mapping_not_found():
    """Test updating non-existent mapping."""
    # Setup
    db_session = MagicMock()
    repo = ServiceNameMappingRepository(db_session)

    with patch.object(repo, "get_mapping", return_value=None):
        # Execute & Verify
        with pytest.raises(HTTPException) as exc_info:
            repo.update_mapping("non-existent", "task-123")

        assert exc_info.value.status_code == 404


@pytest.mark.unit_tests
def test_update_mapping_new_task_not_found():
    """Test updating mapping with non-existent new task."""
    # Setup
    db_session = MagicMock()
    repo = ServiceNameMappingRepository(db_session)

    mock_mapping = MagicMock(spec=DatabaseServiceNameTaskMapping)
    with patch.object(repo, "get_mapping", return_value=mock_mapping):
        # Mock new task doesn't exist
        db_session.query.return_value.filter.return_value.filter.return_value.first.return_value = (
            None
        )

        # Execute & Verify
        with pytest.raises(HTTPException) as exc_info:
            repo.update_mapping("test-service", "non-existent-task")

        assert exc_info.value.status_code == 404


@pytest.mark.unit_tests
def test_reassign_traces():
    """Test reassigning traces from old task to new task."""
    # Setup
    db_session = MagicMock()
    resource_metadata_repo = MagicMock()
    repo = ServiceNameMappingRepository(db_session, resource_metadata_repo)

    service_name = "test-service"
    old_task_id = "old-task"
    new_task_id = "new-task"

    # Mock resource IDs
    resource_metadata_repo.get_resource_ids_by_service_name.return_value = [
        "res1",
        "res2",
    ]

    # Mock trace IDs with old task
    mock_trace_query_result = [("trace1",), ("trace2",)]
    db_session.execute.return_value.fetchall.return_value = mock_trace_query_result

    # Execute
    traces_updated = repo._reassign_traces(service_name, old_task_id, new_task_id)

    # Verify
    assert traces_updated == 2
    assert db_session.execute.call_count == 3  # 1 select + 2 updates


@pytest.mark.unit_tests
def test_delete_mapping_success():
    """Test successful deletion of mapping."""
    # Setup
    db_session = MagicMock()
    repo = ServiceNameMappingRepository(db_session)

    mock_mapping = MagicMock(spec=DatabaseServiceNameTaskMapping)
    with patch.object(repo, "get_mapping", return_value=mock_mapping):
        # Execute
        repo.delete_mapping("test-service")

        # Verify
        db_session.delete.assert_called_once_with(mock_mapping)
        db_session.commit.assert_called_once()


@pytest.mark.unit_tests
def test_delete_mapping_not_found():
    """Test deleting non-existent mapping."""
    # Setup
    db_session = MagicMock()
    repo = ServiceNameMappingRepository(db_session)

    with patch.object(repo, "get_mapping", return_value=None):
        # Execute & Verify
        with pytest.raises(HTTPException) as exc_info:
            repo.delete_mapping("non-existent")

        assert exc_info.value.status_code == 404


