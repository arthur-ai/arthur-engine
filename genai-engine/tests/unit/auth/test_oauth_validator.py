import pytest
from auth.jwk_client import JWKClient
from auth.oauth_validator import validate_token
from fastapi import HTTPException


@pytest.mark.unit_tests
def test_validate_token_undefined_token():
    with pytest.raises(HTTPException) as exc:
        validate_token(token="undefined", jwk_client=JWKClient("some_url"))
        assert exc.status_code == 401
