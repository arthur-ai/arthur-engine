import base64
from unittest.mock import MagicMock

import pytest

from db_models import DatabaseApiKey
from repositories.api_key_repository import ApiKeyRepository


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
    import bcrypt

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
