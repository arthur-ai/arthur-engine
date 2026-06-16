import pytest
from fastapi import HTTPException

from auth.jwk_client import JWKClient
from auth.oauth_validator import validate_token


@pytest.mark.unit_tests
def test_validate_token_undefined_token():
    with pytest.raises(HTTPException) as exc:
        validate_token(
            token="undefined",
            jwk_client=JWKClient("https://example.com/.well-known/jwks.json"),
        )
    assert exc.value.status_code == 401
