from typing import Generator
from unittest.mock import patch

import pytest
from arthur_common.models.response_schemas import ApiKeyResponse

from auth.api_key_validator_client import APIKeyValidatorClient
from auth.ApiKeyValidator.APIKeyValidator import APIKeyValidator
from auth.ApiKeyValidator.APIKeyvalidatorCreator import APIKeyValidatorCreator
from auth.ApiKeyValidator.enums import APIKeyValidatorType
from config.config import Config
from schemas.custom_exceptions import UnableCredentialsException
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)
from tests.clients.unit_test_client import get_genai_engine_test_client

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


@pytest.mark.unit_tests
@pytest.mark.api_key_tests
def test_create_api_key(api_key: ApiKeyResponse):
    assert api_key is not None
    assert api_key.id is not None
    assert api_key.is_active is not None
    assert api_key.description is not None
    assert api_key.description == API_KEY_DESCRIPTION
    assert api_key.is_active is True
    assert api_key.created_at is not None
    assert api_key.message is not None


@pytest.mark.unit_tests
@pytest.mark.api_key_tests
def test_create_api_key_no_description():
    status_code, api_key = client.create_api_key()
    assert status_code == 200

    assert api_key is not None
    assert api_key.id is not None
    assert api_key.is_active is not None
    assert api_key.description == ""
    assert api_key.is_active is True
    assert api_key.created_at is not None
    assert api_key.message is not None
    status_code = client.deactivate_api_key(api_key)
    assert status_code == 204


@pytest.mark.unit_tests
@pytest.mark.api_key_tests
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


@pytest.mark.unit_tests
@pytest.mark.api_key_tests
def test_deactivate_api_key(api_key: ApiKeyResponse):
    status_code = client.deactivate_api_key(api_key)
    assert status_code == 204


@pytest.mark.unit_tests
@pytest.mark.api_key_tests
def test_create_max_active_keys():
    client.clear_existing_user_keys()
    api_keys = []
    for _ in range(Config.max_api_key_limit()):
        status_code, api_key = client.create_api_key()
        assert status_code == 200
        api_keys.append(api_key)

    status_code, _ = client.create_api_key()

    # Expects a 400 status code because maximum active keys reached
    assert status_code == 400

    for key in api_keys:
        status_code = client.deactivate_api_key(key)
        assert status_code == 204


@pytest.mark.unit_tests
@pytest.mark.api_key_tests
def test_get_all_active_keys(api_key: ApiKeyResponse):
    status_code, api_key_2 = client.create_api_key(description=API_KEY_DESCRIPTION)
    assert status_code == 200
    status_code, api_keys = client.get_api_keys()
    assert status_code == 200

    assert api_key.id in (key.id for key in api_keys)
    assert api_key_2.id in (key.id for key in api_keys)
    for key in api_keys:
        if api_key.id == key.id:
            assert_get_key(api_key, key)
        else:
            assert_get_key(api_key_2, key)
    status_code = client.deactivate_api_key(api_key)
    assert status_code == 204
    status_code = client.deactivate_api_key(api_key_2)
    assert status_code == 204


@pytest.mark.unit_tests
def test_api_key_is_valid_raise_exception():
    with patch(
        "auth.ApiKeyValidator.UserGenAPIKeyValidator.UserGenAPIKeyValidator.api_key_is_valid",
    ) as api_key_validator_mock:
        api_key_validator_mock.side_effect = Exception()
        key_validator_client = APIKeyValidatorClient(api_key_cache=None)

        with pytest.raises(UnableCredentialsException) as exception_info:
            key_validator_client.validate(
                api_key_validator_creators=[
                    APIKeyValidatorCreator(APIKeyValidatorType.USER_GEN),
                ],
                api_key="some_key",
                db_session=override_get_db_session(),
            )
            assert exception_info.status_code == 500
            assert exception_info.detail == "Unable to verify credentials"
