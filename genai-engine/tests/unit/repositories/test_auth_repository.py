import base64
import datetime
import uuid
from unittest.mock import MagicMock

import bcrypt
import pytest
from arthur_common.models.enums import APIKeysRolesEnum

from db_models import DatabaseApiKey
from repositories.api_key_repository import ApiKeyRepository
from schemas.internal_schemas import ApiKey


@pytest.mark.unit_tests
def test_validate_key_with_invalid_key():
    api_key_repo = ApiKeyRepository(db_session=None)
    with pytest.raises(AttributeError):
        api_key_repo.validate_key("test")


@pytest.mark.unit_tests
def test_validate_key_with_mocked_db_result():
    # Create a mock DatabaseApiKey object
    mock_db_api_key = None

    # Mock the database session and query chain
    db_session = MagicMock()
    mock_query = MagicMock()
    mock_filter1 = MagicMock()
    mock_filter2 = MagicMock()

    # Set up the query chain
    db_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_filter1
    mock_filter1.filter.return_value = mock_filter2
    mock_filter2.first.return_value = mock_db_api_key

    api_key_repo = ApiKeyRepository(db_session=db_session)

    # Create a valid API key format
    api_key = base64.b64encode(b"test_api_key_id:test_key_value").decode("utf-8")

    # Note: This test will fail because bcrypt.checkpw will fail with mocked hash
    # You would need to either mock bcrypt.checkpw or use a real hash
    result = api_key_repo.validate_key(api_key)

    # Verify the query was called correctly
    db_session.query.assert_called_once_with(DatabaseApiKey)
    mock_query.filter.assert_called_once()
    mock_filter1.filter.assert_called_once()
    assert result is None


@pytest.mark.unit_tests
def test_validate_key_with_real_hash():
    # Create a real bcrypt hash for testing
    test_key_value = "test_key_value"
    real_hash = bcrypt.hashpw(
        test_key_value.encode("utf-8"),
        bcrypt.gensalt(rounds=9),
    ).decode("utf-8")

    # Create a mock DatabaseApiKey object with real hash
    mock_db_api_key = MagicMock(spec=DatabaseApiKey)
    mock_db_api_key.id = "test_api_key_id"
    mock_db_api_key.key_hash = real_hash
    mock_db_api_key.description = "Test API Key"
    mock_db_api_key.roles = ["admin"]
    mock_db_api_key.is_active = True
    mock_db_api_key.created_at = datetime.datetime(2026, 1, 1)
    mock_db_api_key.deactivated_at = None
    mock_db_api_key.org_id = None

    # Mock the database session and query chain
    db_session = MagicMock()
    mock_query = MagicMock()
    mock_filter1 = MagicMock()
    mock_filter2 = MagicMock()

    # Set up the query chain
    db_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_filter1
    mock_filter1.filter.return_value = mock_filter2
    mock_filter2.first.return_value = mock_db_api_key

    api_key_repo = ApiKeyRepository(db_session=db_session)

    # Create a valid API key format
    api_key = base64.b64encode(
        f"test_api_key_id:{test_key_value}".encode("utf-8"),
    ).decode("utf-8")

    result = api_key_repo.validate_key(api_key)

    # Now the result should be a valid ApiKey object
    assert result is not None
    assert result.id == "test_api_key_id"
    assert result.description == "Test API Key"
    assert result.roles == ["admin"]


@pytest.mark.unit_tests
def test_api_key_from_database_model_propagates_org_id_when_set():
    """Tenant key (api_keys.org_id non-null) surfaces org_id on the ApiKey schema."""
    org_id = uuid.uuid4()
    db_api_key = MagicMock(spec=DatabaseApiKey)
    db_api_key.id = "tenant-key-id"
    db_api_key.key_hash = "hash"
    db_api_key.description = "tenant key"
    db_api_key.is_active = True
    db_api_key.created_at = datetime.datetime(2026, 1, 1)
    db_api_key.deactivated_at = None
    db_api_key.roles = ["TENANT-USER"]
    db_api_key.org_id = org_id

    api_key = ApiKey._from_database_model(db_api_key)

    assert api_key.org_id == org_id


@pytest.mark.unit_tests
def test_api_key_from_database_model_org_id_none_for_admin_keys():
    """Admin key (api_keys.org_id IS NULL) yields org_id=None — existing behavior."""
    db_api_key = MagicMock(spec=DatabaseApiKey)
    db_api_key.id = "admin-key-id"
    db_api_key.key_hash = "hash"
    db_api_key.description = "admin key"
    db_api_key.is_active = True
    db_api_key.created_at = datetime.datetime(2026, 1, 1)
    db_api_key.deactivated_at = None
    db_api_key.roles = ["ORG_ADMIN"]
    db_api_key.org_id = None

    api_key = ApiKey._from_database_model(db_api_key)

    assert api_key.org_id is None


@pytest.mark.unit_tests
def test_get_user_representation_propagates_org_id_as_org_scope():
    """ApiKey.org_id flows into User.org_scope so multi_validator can pick it up."""
    org_id = uuid.uuid4()
    api_key = ApiKey(
        id="tenant-key-id",
        is_active=True,
        created_at=datetime.datetime(2026, 1, 1),
        roles=["TENANT-USER"],
        org_id=org_id,
    )

    user = api_key.get_user_representation()

    assert user.org_scope == org_id


@pytest.mark.unit_tests
def test_get_user_representation_org_scope_none_for_admin_key():
    """Admin ApiKey (org_id=None) yields User.org_scope=None — cross-org access."""
    api_key = ApiKey(
        id="admin-key-id",
        is_active=True,
        created_at=datetime.datetime(2026, 1, 1),
        roles=["ORG_ADMIN"],
        org_id=None,
    )

    user = api_key.get_user_representation()

    assert user.org_scope is None


@pytest.mark.unit_tests
def test_create_api_key_persists_org_id(monkeypatch):
    """create_api_key(org_id=X) passes org_id through to the DatabaseApiKey row."""
    db_session = MagicMock()
    # Zero existing keys so we pass the max_api_key_limit gate.
    db_session.query.return_value.filter.return_value.count.return_value = 0

    # Bypass pydantic validation — create_api_key constructs DatabaseApiKey but
    # doesn't commit, so SQLAlchemy defaults aren't applied yet. Return a thin
    # stand-in that exposes the underlying ORM row for inspection.
    class _Stub:
        def __init__(self, db_api_key):
            self.db = db_api_key

        def set_key(self, key):
            pass

    monkeypatch.setattr(
        ApiKey, "_from_database_model", staticmethod(lambda db: _Stub(db))
    )
    repo = ApiKeyRepository(db_session=db_session)
    org_id = uuid.uuid4()
    repo.create_api_key(
        description="tenant key",
        roles=[APIKeysRolesEnum.TASK_ADMIN],
        org_id=org_id,
    )

    added = db_session.add.call_args[0][0]
    assert isinstance(added, DatabaseApiKey)
    assert added.org_id == org_id


@pytest.mark.unit_tests
def test_create_api_key_defaults_to_none_org_id_for_admin(monkeypatch):
    """create_api_key() without org_id (admin path) leaves the column NULL."""
    db_session = MagicMock()
    db_session.query.return_value.filter.return_value.count.return_value = 0

    class _Stub:
        def __init__(self, db_api_key):
            self.db = db_api_key

        def set_key(self, key):
            pass

    monkeypatch.setattr(
        ApiKey, "_from_database_model", staticmethod(lambda db: _Stub(db))
    )
    repo = ApiKeyRepository(db_session=db_session)
    repo.create_api_key(
        description="admin key",
        roles=[APIKeysRolesEnum.ORG_ADMIN],
    )

    added = db_session.add.call_args[0][0]
    assert isinstance(added, DatabaseApiKey)
    assert added.org_id is None
