from fastapi import Depends, HTTPException
from starlette import status

from dependencies import get_jwk_client

from .authorization_header_elements import get_bearer_access_token_from_cookie_or_header
from .jwk_client import JWKClient


def validate_token(
    token: str = Depends(get_bearer_access_token_from_cookie_or_header),
    jwk_client: JWKClient = Depends(get_jwk_client),
):
    if loaded_user := jwk_client.validate(token):
        return loaded_user
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={"full_stacktrace": "false"},
        )
