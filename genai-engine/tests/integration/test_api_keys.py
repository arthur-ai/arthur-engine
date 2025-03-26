from typing import Generator

import pytest
from auth.ApiKeyValidator.APIKeyValidator import APIKeyValidator
from schemas.response_schemas import ApiKeyResponse
from tests.clients.base_test_client import GenaiEngineTestClientBase
from tests.clients.integration_test_client import get_genai_engine_test_client

API_KEY_DESCRIPTION = "Test Description"

client: GenaiEngineTestClientBase = None


# If we set this client at the global level, pytest will initialize a client for every module.
# As part of the initialization, we delete / create api keys. If all clients are created sequentially,
# will cause the key deactivations of the next to overwrite the key creation of the previous. Use a module
# scoped fixture to initialize a new client for each module, after the tests of the previous module have run
@pytest.fixture(scope="module", autouse=True)
def initialize_client():
    global client
    client = get_genai_engine_test_client(create_user_key=False)


class FakeApiKeyValidator(APIKeyValidator):
    def api_key_is_valid(self, key: str) -> bool:
        raise Exception


@pytest.fixture
def api_key() -> Generator[ApiKeyResponse, None, None]:
    status_code, key = client.create_api_key(description=API_KEY_DESCRIPTION)
    assert status_code == 200
    yield key
    client.deactivate_api_key(key)


@pytest.mark.integration_tests
def test_create_api_key(api_key: ApiKeyResponse):
    assert api_key is not None
    assert api_key.id is not None
    assert api_key.is_active is not None
    assert api_key.description is not None
    assert api_key.description == API_KEY_DESCRIPTION
    assert api_key.is_active is True
    assert api_key.created_at is not None
    assert api_key.message is not None


@pytest.mark.integration_tests
def test_create_api_key_no_description():
    status_code, api_key = client.create_api_key()
    assert status_code == 200

    assert api_key is not None
    assert api_key.id is not None
    assert api_key.is_active is not None
    assert api_key.description is None
    assert api_key.is_active is True
    assert api_key.created_at is not None
    assert api_key.message is not None
    status_code = client.deactivate_api_key(api_key)
    assert status_code == 204


@pytest.mark.integration_tests
def test_read_api_key(api_key: ApiKeyResponse):
    status_code, api_key_resp = client.get_api_key_by_id(api_key.id)
    assert status_code == 200

    assert_get_key(api_key, api_key_resp)
    status_code = client.deactivate_api_key(api_key)
    assert status_code == 204


def assert_get_key(api_key: ApiKeyResponse, response: ApiKeyResponse):
    assert response.id is not None
    assert response.id == api_key.id
    assert api_key.description is not None
    assert api_key.description == API_KEY_DESCRIPTION
    assert response.is_active is True
    assert response.created_at is not None
    assert response.created_at == api_key.created_at
    assert response.message is not None
    assert response.message == ""


@pytest.mark.integration_tests
def test_deactivate_api_key(api_key: ApiKeyResponse):
    status_code = client.deactivate_api_key(api_key)
    assert status_code == 204
