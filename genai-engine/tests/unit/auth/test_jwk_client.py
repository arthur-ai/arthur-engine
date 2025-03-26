from dataclasses import dataclass
from unittest.mock import MagicMock

import jwt
import pytest
from auth.jwk_client import JWKClient
from schemas.custom_exceptions import (
    BadCredentialsException,
    UnableCredentialsException,
)
from schemas.internal_schemas import User

# Keys generated only for tests. Do not reuse them anywhere
PRIVATE_KEY = b"""
-----BEGIN RSA PRIVATE KEY-----
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
-----END RSA PRIVATE KEY-----
"""
PUBLIC_KEY = b"""
-----BEGIN PUBLIC KEY-----
MIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEAqQjecty/sJdSBLw+f636
tLG9WOA5AWKWpWO2Gh7mYIKLEjumQBTcm3cZok5DGFzsGKWej/0DL58UmRriYksU
By31d7gb44DQAG3eoO0adK+RzgJGpMGCSl14TY0IABXLmiAeKRDHC5xBgelfPOxh
5Y/lsWbUPLjlHJ6DoOu/TxJDj9vjD7kok+jXjILuQaZMBvCRJZI9YxeOREkj9GnS
O8ZvLd7I5Mrw2Dm3+CdU0mISuDAdL0GeJGVp6Sa0AWyrwf3jpHzbf1z3EFwVEvmH
DMw3d3Xd3r0gzebBVPo+l6QmKLBLGuMlMycurpK4/0rtGAq1yVV5dL3SuZj36tn1
46Q54PJ9GG4vuvhkcFB3MK3WKE8kx3TGDq1qCd1uBsJQS4TJ3hkkAHuPUtb6hRK6
fTLAmaCp36xP20xjUOXg/GGtMxEy4IB/Td6jKkaVmhFipeeSzQEdnZk5tJeF2sz5
xzRcs/+KBMZzd6VZA88hM5IE8qxY9VeVcTcu+Hc5+Wt8V/jrUyhMXd2Q9g7RMMjg
V08zVQ4vBs73wlth4Yuvo8Ko/4WQbd4bvGiuCcZi3LAw35289hIuGWnmie8t/uu4
QVQ93/2CroISIMKi1bdHbTHQrYTJwg8k45Zy90qz47mJiZYa6okQQzpMcOoWC5fq
T4YKjeXc1cUrJF5AIBptxy0CAwEAAQ==
-----END PUBLIC KEY-----
"""


@dataclass
class MockedJWTReturn:
    key = PUBLIC_KEY


@pytest.mark.unit_tests
def test_validate():
    jwt_access_token_raw = {"sub": "some_sub", "email": "test@example.com", "roles": []}
    jwt_access_token_encrypted = jwt.encode(
        payload=jwt_access_token_raw,
        key=PRIVATE_KEY,
        algorithm="RS256",
    )
    mock_jwks_client = MagicMock()
    mock_jwks_client.get_signing_key_from_jwt.return_value = MockedJWTReturn()
    jwk_client = JWKClient("some_url")
    jwk_client.jwks_client = mock_jwks_client
    payload = jwk_client.validate(jwt_access_token_encrypted)
    assert payload == User(
        id=jwt_access_token_raw["sub"],
        email=jwt_access_token_raw["email"],
        roles=jwt_access_token_raw["roles"],
    )


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "mocked_exception, expected_exception",
    [
        (jwt.exceptions.PyJWKClientError(), UnableCredentialsException),
        (jwt.exceptions.InvalidTokenError(), BadCredentialsException),
    ],
)
def test_validate_error_handlers(mocked_exception, expected_exception):
    mock_jwks_client = MagicMock()
    mock_jwks_client.get_signing_key_from_jwt.side_effect = mocked_exception
    jwk_client = JWKClient("some_url")
    jwk_client.jwks_client = mock_jwks_client
    with pytest.raises(expected_exception):
        payload = jwk_client.validate("some_token")
        assert isinstance(payload, dict)
        assert payload == dict()
