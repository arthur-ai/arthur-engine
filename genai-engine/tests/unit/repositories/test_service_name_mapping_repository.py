import logging
import uuid

import pytest

from db_models import DatabaseServiceNameTaskMapping, DatabaseTask
from repositories.service_name_mapping_repository import ServiceNameMappingRepository
from tests.clients.base_test_client import override_get_db_session

LOGGER = logging.getLogger(__name__)


@pytest.fixture(scope="function")
def test_task():
    """Create a test task for mapping tests."""
    from datetime import datetime

    db_session = override_get_db_session()
    task_id = str(uuid.uuid4())
    current_time = datetime.now()
    task = DatabaseTask(
        id=task_id,
        name="Test Task for Service Mapping",
        created_at=current_time,
        updated_at=current_time,
        is_agentic=True,
        archived=False,
    )
    db_session.add(task)
    db_session.commit()
    yield task
    # Cleanup
    db_session.query(DatabaseTask).filter(DatabaseTask.id == task_id).delete()
    db_session.commit()


@pytest.fixture(scope="function")
def test_task_2():
    """Create a second test task for mapping tests."""
    from datetime import datetime

    db_session = override_get_db_session()
    task_id = str(uuid.uuid4())
    current_time = datetime.now()
    task = DatabaseTask(
        id=task_id,
        name="Test Task 2 for Service Mapping",
        created_at=current_time,
        updated_at=current_time,
        is_agentic=True,
        archived=False,
    )
    db_session.add(task)
    db_session.commit()
    yield task
    # Cleanup
    db_session.query(DatabaseTask).filter(DatabaseTask.id == task_id).delete()
    db_session.commit()


# ============================================================================
# CREATE MAPPING TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_create_mapping_success(test_task):
    """Test successful creation of a service name mapping."""
    db_session = override_get_db_session()
    repo = ServiceNameMappingRepository(db_session)

    service_name = "test-service-1"
    mapping = repo.create_mapping(service_name, test_task.id)

    assert mapping.service_name == service_name
    assert mapping.task_id == test_task.id
    assert mapping.created_at is not None

    # Verify mapping exists in database
    db_mapping = (
        db_session.query(DatabaseServiceNameTaskMapping)
        .filter(DatabaseServiceNameTaskMapping.service_name == service_name)
        .first()
    )
    assert db_mapping is not None
    assert db_mapping.task_id == test_task.id

    # Cleanup
    db_session.delete(mapping)
    db_session.commit()


@pytest.mark.unit_tests
def test_create_mapping_idempotent(test_task):
    """Test that creating the same mapping twice returns existing mapping."""
    db_session = override_get_db_session()
    repo = ServiceNameMappingRepository(db_session)

    service_name = "test-service-idempotent"

    # Create mapping first time
    mapping1 = repo.create_mapping(service_name, test_task.id)
    assert mapping1.service_name == service_name
    assert mapping1.task_id == test_task.id

    # Create same mapping again - should return existing
    mapping2 = repo.create_mapping(service_name, test_task.id)
    assert mapping2.service_name == mapping1.service_name
    assert mapping2.task_id == mapping1.task_id
    assert mapping2.created_at == mapping1.created_at

    # Verify only one mapping exists in database
    count = (
        db_session.query(DatabaseServiceNameTaskMapping)
        .filter(DatabaseServiceNameTaskMapping.service_name == service_name)
        .count()
    )
    assert count == 1

    # Cleanup
    db_session.delete(mapping1)
    db_session.commit()


@pytest.mark.unit_tests
def test_create_mapping_different_service_names_same_task(test_task):
    """Test that multiple service names can map to the same task."""
    db_session = override_get_db_session()
    repo = ServiceNameMappingRepository(db_session)

    service_name_1 = "test-service-multi-1"
    service_name_2 = "test-service-multi-2"

    mapping1 = repo.create_mapping(service_name_1, test_task.id)
    mapping2 = repo.create_mapping(service_name_2, test_task.id)

    assert mapping1.task_id == test_task.id
    assert mapping2.task_id == test_task.id
    assert mapping1.service_name != mapping2.service_name

    # Cleanup
    db_session.delete(mapping1)
    db_session.delete(mapping2)
    db_session.commit()


# ============================================================================
# GET TASK ID BY SERVICE NAME TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_get_task_id_by_service_name_found(test_task):
    """Test retrieving task_id for an existing service name mapping."""
    db_session = override_get_db_session()
    repo = ServiceNameMappingRepository(db_session)

    service_name = "test-service-found"
    repo.create_mapping(service_name, test_task.id)

    task_id = repo.get_task_id_by_service_name(service_name)
    assert task_id == test_task.id

    # Cleanup
    mapping = repo.get_mapping(service_name)
    db_session.delete(mapping)
    db_session.commit()


@pytest.mark.unit_tests
def test_get_task_id_by_service_name_not_found():
    """Test retrieving task_id for non-existent service name returns None."""
    db_session = override_get_db_session()
    repo = ServiceNameMappingRepository(db_session)

    service_name = "test-service-not-found"
    task_id = repo.get_task_id_by_service_name(service_name)
    assert task_id is None


# ============================================================================
# MAPPING EXISTS TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_mapping_exists_true(test_task):
    """Test that mapping_exists returns True for existing mapping."""
    db_session = override_get_db_session()
    repo = ServiceNameMappingRepository(db_session)

    service_name = "test-service-exists"
    repo.create_mapping(service_name, test_task.id)

    assert repo.mapping_exists(service_name) is True

    # Cleanup
    mapping = repo.get_mapping(service_name)
    db_session.delete(mapping)
    db_session.commit()


@pytest.mark.unit_tests
def test_mapping_exists_false():
    """Test that mapping_exists returns False for non-existent mapping."""
    db_session = override_get_db_session()
    repo = ServiceNameMappingRepository(db_session)

    service_name = "test-service-not-exists"
    assert repo.mapping_exists(service_name) is False


# ============================================================================
# GET MAPPING TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_get_mapping_full_record(test_task):
    """Test retrieving full mapping record with relationships."""
    db_session = override_get_db_session()
    repo = ServiceNameMappingRepository(db_session)

    service_name = "test-service-full-record"
    created_mapping = repo.create_mapping(service_name, test_task.id)

    mapping = repo.get_mapping(service_name)
    assert mapping is not None
    assert mapping.service_name == service_name
    assert mapping.task_id == test_task.id
    assert mapping.created_at == created_mapping.created_at

    # Verify relationship is loaded
    assert mapping.task is not None
    assert mapping.task.id == test_task.id
    assert mapping.task.name == test_task.name

    # Cleanup
    db_session.delete(mapping)
    db_session.commit()


@pytest.mark.unit_tests
def test_get_mapping_not_found():
    """Test that get_mapping returns None for non-existent service name."""
    db_session = override_get_db_session()
    repo = ServiceNameMappingRepository(db_session)

    service_name = "test-service-get-mapping-not-found"
    mapping = repo.get_mapping(service_name)
    assert mapping is None


# ============================================================================
# GET ALL MAPPINGS TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_get_all_mappings(test_task, test_task_2):
    """Test retrieving all service name mappings."""
    db_session = override_get_db_session()
    repo = ServiceNameMappingRepository(db_session)

    service_name_1 = "test-service-all-1"
    service_name_2 = "test-service-all-2"

    mapping1 = repo.create_mapping(service_name_1, test_task.id)
    mapping2 = repo.create_mapping(service_name_2, test_task_2.id)

    all_mappings = repo.get_all_mappings()

    # Should contain at least our two test mappings
    assert len(all_mappings) >= 2

    # Find our test mappings
    found_mapping1 = next(
        (m for m in all_mappings if m.service_name == service_name_1),
        None,
    )
    found_mapping2 = next(
        (m for m in all_mappings if m.service_name == service_name_2),
        None,
    )

    assert found_mapping1 is not None
    assert found_mapping1.task_id == test_task.id
    assert found_mapping2 is not None
    assert found_mapping2.task_id == test_task_2.id

    # Cleanup
    db_session.delete(mapping1)
    db_session.delete(mapping2)
    db_session.commit()


@pytest.mark.unit_tests
def test_get_all_mappings_respects_limit(test_task):
    """Test that get_all_mappings respects the limit parameter."""
    db_session = override_get_db_session()
    repo = ServiceNameMappingRepository(db_session)

    # Create multiple mappings
    mappings = []
    for i in range(5):
        service_name = f"test-service-limit-{i}"
        mapping = repo.create_mapping(service_name, test_task.id)
        mappings.append(mapping)

    # Get with limit
    limited_mappings = repo.get_all_mappings(limit=3)
    assert len(limited_mappings) <= 3

    # Cleanup
    for mapping in mappings:
        db_session.delete(mapping)
    db_session.commit()


# ============================================================================
# DELETE MAPPING TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_delete_mapping_success(test_task):
    """Test successful deletion of a service name mapping."""
    db_session = override_get_db_session()
    repo = ServiceNameMappingRepository(db_session)

    service_name = "test-service-delete"
    repo.create_mapping(service_name, test_task.id)

    # Verify mapping exists
    assert repo.mapping_exists(service_name) is True

    # Delete mapping
    result = repo.delete_mapping(service_name)
    assert result is True

    # Verify mapping no longer exists
    assert repo.mapping_exists(service_name) is False


@pytest.mark.unit_tests
def test_delete_mapping_not_found():
    """Test that deleting non-existent mapping returns False."""
    db_session = override_get_db_session()
    repo = ServiceNameMappingRepository(db_session)

    service_name = "test-service-delete-not-found"
    result = repo.delete_mapping(service_name)
    assert result is False
