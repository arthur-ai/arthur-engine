import os
import time
from enum import Enum
from unittest.mock import patch

import pytest
from schemas.common_schemas import LLMTokenConsumption
from schemas.custom_exceptions import LLMTokensPerPeriodRateLimitException
from scorer import llm_client
from utils.utils import (
    get_auth_logout_uri,
    get_auth_metadata_uri,
    get_jwks_uri,
    get_postgres_connection_string,
    is_api_only_mode_enabled,
)

@pytest.mark.parametrize(
    "exceeds",
    [True, False],
)
@pytest.mark.unit_tests
def test_rate_limiter(exceeds: bool):
    limit = 1000
    expiration = 0.1
    rate_limiter = llm_client.LLMTokensPerPeriodRateLimiter(
        rate_limit=limit,
        period_seconds=expiration,
    )
    for i in range(5):
        rate_limiter.add_request(
            LLMTokenConsumption(
                prompt_tokens=limit // 5 + 1 if exceeds else -1,
                completion_tokens=0,
            ),
        )
    if exceeds:
        try:
            rate_limiter.request_allowed()
        except Exception as e:
            assert type(e) == LLMTokensPerPeriodRateLimitException
        # After requests leave the window, it should be available again
        time.sleep(expiration)
        assert rate_limiter.request_allowed()
    else:
        assert rate_limiter.request_allowed()


class UserType(str, Enum):
    ADMIN = "admin"
    NON_ADMIN = "non_admin"
    NO_NAME = "no_name"


@patch("utils.utils.get_env_var")
def test_is_api_only_mode_enabled(mock_get_env_var):
    assert not is_api_only_mode_enabled()

    mock_get_env_var.side_effect = ["true"]
    assert not is_api_only_mode_enabled()

    mock_get_env_var.side_effect = ["enabled"]
    assert is_api_only_mode_enabled()

    mock_get_env_var.side_effect = ["disabled"]
    assert not is_api_only_mode_enabled()


@patch.dict(
    os.environ,
    {
        "POSTGRES_USER": "dummy_user",
        "POSTGRES_PASSWORD": "dummy_password",
        "POSTGRES_URL": "dummy_url",
        "POSTGRES_PORT": "123456",
        "POSTGRES_DB": "dummy_db",
    },
    clear=True,
)
@pytest.mark.unit_tests
def test_get_postgres_connection_string():
    result = get_postgres_connection_string(use_ssl=True, ssl_key_path="some_dummy")
    assert (
        result
        == "postgresql+psycopg2://dummy_user:dummy_password@dummy_url:123456/dummy_db?sslmode=verify-full&sslrootcert=some_dummy"
    )


@patch.dict(
    os.environ,
    {
        "KEYCLOAK_HOST_URI": "dummy_kc_uri",
        "KEYCLOAK_REALM": "dummy_realm",
    },
    clear=True,
)
@pytest.mark.unit_tests
def test_get_jwks_uri():
    result = get_jwks_uri()
    assert result == "dummy_kc_uri/realms/dummy_realm/protocol/openid-connect/certs"


@patch.dict(
    os.environ,
    {
        "KEYCLOAK_HOST_URI": "dummy_kc_uri",
        "KEYCLOAK_REALM": "dummy_realm",
    },
    clear=True,
)
@pytest.mark.unit_tests
def test_get_auth_metadata_uri():
    result = get_auth_metadata_uri()
    assert result == "dummy_kc_uri/realms/dummy_realm/.well-known/openid-configuration"


@patch.dict(
    os.environ,
    {
        "KEYCLOAK_HOST_URI": "dummy_kc_uri",
        "KEYCLOAK_REALM": "dummy_realm",
        "AUTH_CLIENT_ID": "dummy_client_id",
    },
    clear=True,
)
@pytest.mark.parametrize(
    "redirect_uri, id_token, expected_result",
    [
        (
            "dummy_redirect_url",
            "dummy_id_token",
            "dummy_kc_uri/realms/dummy_realm/protocol/openid-connect/logout?post_logout_redirect_uri=dummy_redirect_url&client_id=dummy_client_id&id_token_hint=dummy_id_token",
        ),
        (
            "dummy_redirect_url",
            None,
            "dummy_kc_uri/realms/dummy_realm/protocol/openid-connect/logout?post_logout_redirect_uri=dummy_redirect_url&client_id=dummy_client_id",
        ),
    ],
)
@pytest.mark.unit_tests
def test_get_auth_logout_uri(redirect_uri, id_token, expected_result):
    result = get_auth_logout_uri(redirect_uri=redirect_uri, id_token=id_token)
    assert result == expected_result
