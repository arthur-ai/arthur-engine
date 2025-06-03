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
from utils.markdown_parser import MarkdownParser

CURRDIR = os.path.dirname(os.path.abspath(__file__))
markdown_parser = MarkdownParser()

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


@pytest.mark.parametrize(
    ("source_str", "target_strs"),
    [
        [
            """Mackenzie Caquatto (born August 20, 1994) is an American former artistic gymnast.
            She was a member of the U.S. Women's Gymnastics team, and competed at the 2012 Summer Olympics in London. Caquatto was born in Naperville, Illinois, and began gymnastics at the age of three. """,  # noqa
            [
                "Mackenzie Caquatto (born August 20, 1994) is an American former artistic gymnast.",  # noqa
                "She was a member of the US Women's Gymnastics team, and competed at the 2012 Summer Olympics in London.",  # noqa
                "Caquatto was born in Naperville, Illinois, and began gymnastics at the age of three.",
            ],
        ],
        [
            "I lived on Blvd. Exelmans in the 16th arrondissement. It was next to the St. Helen Church.",
            [
                "I lived on Blvd Exelmans in the 16th arrondissement.",
                "It was next to the St Helen Church.",
            ],
        ],
    ],
)
@pytest.mark.unit_tests
def test_custom_test_parser(source_str: str, target_strs: list[str]):
    chunked = markdown_parser.parse_markdown(source_str)
    assert len(chunked) == len(target_strs)
    for chunk in chunked:
        assert chunk in target_strs


@pytest.mark.parametrize(
    ("source_str", "target_str"),
    [
        [
            """Will strip all the *code like python: print('hello world')*""",
            """Will strip all the code like python: print('hello world')""",
        ],
        [
            """### Will strip all the `code like python: print('hello world')`""",
            """Will strip all the code like python: print('hello world')""",
        ],
        [
            """[![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/facebook/react/blob/main/LICENSE)""",
            """GitHub license https://img.shields.io/badge/license-MIT-blue.svg https://github.com/facebook/react/blob/main/LICENSE""",
        ],
        [
            """ <https://en.wikipedia.org/wiki/Hobbit#Lifestyle>""",
            """https://en.wikipedia.org/wiki/Hobbit#Lifestyle""",
        ],
        [
            """![The San Juan Mountains are beautiful!](/assets/images/san-juan-mountains.jpg "San Juan Mountains")""",
            """The San Juan Mountains are beautiful! /assets/images/san-juan-mountains.jpg - San Juan Mountains""",
        ],
        [
            """1. Ingredients

    - spaghetti
    - marinara sauce
        * 14.5 ounce - for 8 servings
        * with oregano and garlic
    - salt - himalayan

2. Cooking

   - Bring water to boil, add a pinch of salt and spaghetti. Cook until pasta is **tender**.

3. Serve

   - Drain the pasta on a plate. Add heated sauce.

   - > No man is lonely eating spaghetti; it requires so much attention.

   - Bon appetit!""",
            """Ingredients spaghetti marinara sauce 14.5 ounce - for 8 servings with oregano and garlic salt - himalayan
Cooking Bring water to boil, add a pinch of salt and spaghetti. Cook until pasta is tender
Serve Drain the pasta on a plate. Add heated sauce No man is lonely eating spaghetti; it requires so much attention Bon appetit""",
        ],
        [
            """* Item1
* Item2
* Item3""",
            """Item1
Item2
Item3""",
        ],
        [
            open(os.path.join(CURRDIR, "test_data", "test_README.md"), "r").read(),
            open(os.path.join(CURRDIR, "test_data", "target_README.txt"), "r").read(),
        ],
    ],
)
@pytest.mark.unit_tests
def test_strip_markdown(source_str: str, target_str: str):
    stripped = markdown_parser.strip_markdown(source_str)
    assert stripped == target_str.strip()


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
