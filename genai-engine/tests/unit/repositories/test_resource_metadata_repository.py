import hashlib
import json
import uuid
from unittest.mock import MagicMock

import pytest

from db_models import DatabaseResourceMetadata
from repositories.resource_metadata_repository import ResourceMetadataRepository


@pytest.mark.unit_tests
def test_generate_resource_id_deterministic():
    """Test that resource ID generation is deterministic for same attributes."""
    repo = ResourceMetadataRepository(db_session=None)

    attributes1 = {"service.name": "my-service", "host.name": "host1"}
    attributes2 = {"service.name": "my-service", "host.name": "host1"}

    id1 = repo._generate_resource_id(attributes1)
    id2 = repo._generate_resource_id(attributes2)

    assert id1 == id2
    assert isinstance(uuid.UUID(id1), uuid.UUID)


@pytest.mark.unit_tests
def test_generate_resource_id_different_for_different_attributes():
    """Test that different attributes generate different resource IDs."""
    repo = ResourceMetadataRepository(db_session=None)

    attributes1 = {"service.name": "service1", "host.name": "host1"}
    attributes2 = {"service.name": "service2", "host.name": "host2"}

    id1 = repo._generate_resource_id(attributes1)
    id2 = repo._generate_resource_id(attributes2)

    assert id1 != id2


@pytest.mark.unit_tests
def test_generate_resource_id_order_independent():
    """Test that attribute order doesn't affect resource ID generation."""
    repo = ResourceMetadataRepository(db_session=None)

    # Different order, same content
    attributes1 = {"service.name": "my-service", "host.name": "host1", "version": "1.0"}
    attributes2 = {"version": "1.0", "host.name": "host1", "service.name": "my-service"}

    id1 = repo._generate_resource_id(attributes1)
    id2 = repo._generate_resource_id(attributes2)

    assert id1 == id2


@pytest.mark.unit_tests
def test_create_or_get_resource_creates_new():
    """Test creating a new resource when it doesn't exist."""
    # Mock database session
    db_session = MagicMock()
    mock_query = MagicMock()
    mock_filter = MagicMock()

    db_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_filter
    mock_filter.first.return_value = None  # Resource doesn't exist

    repo = ResourceMetadataRepository(db_session=db_session)

    attributes = {"service.name": "my-service", "host.name": "host1"}
    service_name = "my-service"

    resource_id = repo.create_or_get_resource(attributes, service_name)

    # Verify resource was added
    db_session.add.assert_called_once()
    db_session.commit.assert_called_once()

    # Verify the added resource has correct attributes
    added_resource = db_session.add.call_args[0][0]
    assert added_resource.service_name == service_name
    assert added_resource.resource_attributes == attributes
    assert isinstance(uuid.UUID(resource_id), uuid.UUID)


@pytest.mark.unit_tests
def test_create_or_get_resource_returns_existing():
    """Test returning existing resource when it already exists."""
    attributes = {"service.name": "my-service", "host.name": "host1"}
    service_name = "my-service"

    # Generate the deterministic resource ID for these attributes
    repo_temp = ResourceMetadataRepository(db_session=None)
    expected_resource_id = repo_temp._generate_resource_id(attributes)

    # Mock existing resource with the deterministic ID
    mock_resource = MagicMock(spec=DatabaseResourceMetadata)
    mock_resource.id = expected_resource_id

    # Mock database session
    db_session = MagicMock()
    mock_query = MagicMock()
    mock_filter = MagicMock()

    db_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_filter
    mock_filter.first.return_value = mock_resource  # Resource exists

    repo = ResourceMetadataRepository(db_session=db_session)

    resource_id = repo.create_or_get_resource(attributes, service_name)

    # Verify resource was NOT added (already exists)
    db_session.add.assert_not_called()
    db_session.commit.assert_not_called()

    # Verify we got the existing resource ID
    assert resource_id == expected_resource_id


@pytest.mark.unit_tests
def test_get_by_id():
    """Test retrieving resource by ID."""
    test_id = str(uuid.uuid4())

    # Mock resource
    mock_resource = MagicMock(spec=DatabaseResourceMetadata)
    mock_resource.id = test_id

    # Mock database session
    db_session = MagicMock()
    mock_query = MagicMock()
    mock_filter = MagicMock()

    db_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_filter
    mock_filter.first.return_value = mock_resource

    repo = ResourceMetadataRepository(db_session=db_session)

    result = repo.get_by_id(test_id)

    assert result == mock_resource
    db_session.query.assert_called_once_with(DatabaseResourceMetadata)


@pytest.mark.unit_tests
def test_get_by_service_name():
    """Test retrieving resources by service name."""
    service_name = "test-service"

    # Mock resources
    mock_resources = [
        MagicMock(spec=DatabaseResourceMetadata),
        MagicMock(spec=DatabaseResourceMetadata),
    ]

    # Mock database session
    db_session = MagicMock()
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_order_by = MagicMock()
    mock_limit = MagicMock()

    db_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_filter
    mock_filter.order_by.return_value = mock_order_by
    mock_order_by.limit.return_value = mock_limit
    mock_limit.all.return_value = mock_resources

    repo = ResourceMetadataRepository(db_session=db_session)

    results = repo.get_by_service_name(service_name, limit=100)

    assert results == mock_resources
    assert len(results) == 2
    mock_limit.all.assert_called_once()


@pytest.mark.unit_tests
def test_get_resource_ids_by_service_name():
    """Test retrieving only resource IDs by service name."""
    service_name = "test-service"
    test_ids = [str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())]

    # Mock database results (tuples of IDs)
    mock_results = [(id,) for id in test_ids]

    # Mock database session
    db_session = MagicMock()
    mock_query = MagicMock()
    mock_filter = MagicMock()

    db_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_filter
    mock_filter.all.return_value = mock_results

    repo = ResourceMetadataRepository(db_session=db_session)

    result_ids = repo.get_resource_ids_by_service_name(service_name)

    assert result_ids == test_ids
    assert len(result_ids) == 3


@pytest.mark.unit_tests
def test_create_or_get_resource_with_none_service_name():
    """Test creating resource with None service name."""
    # Mock database session
    db_session = MagicMock()
    mock_query = MagicMock()
    mock_filter = MagicMock()

    db_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_filter
    mock_filter.first.return_value = None  # Resource doesn't exist

    repo = ResourceMetadataRepository(db_session=db_session)

    attributes = {"host.name": "host1", "version": "1.0"}
    service_name = None

    resource_id = repo.create_or_get_resource(attributes, service_name)

    # Verify resource was added
    db_session.add.assert_called_once()

    # Verify the added resource has None service_name
    added_resource = db_session.add.call_args[0][0]
    assert added_resource.service_name is None
    assert added_resource.resource_attributes == attributes
