from starlette.requests import Request as StarletteRequest

from schemas.custom_exceptions import (
    BadCredentialsException,
    RequiresAuthenticationException,
)

from . import auth_constants


def get_token_from_bearer(authorization_header: str) -> str:
    try:
        authorization_scheme, token = authorization_header.split()
    except ValueError:
        raise BadCredentialsException

    valid = authorization_scheme.lower() == "bearer" and bool(token.strip())
    if valid:
        return token
    else:
        raise BadCredentialsException


def get_bearer_access_token_from_cookie_or_header(request: StarletteRequest) -> str:
    authorization_token = request.cookies.get(auth_constants.ACCESS_TOKEN_COOKIE_NAME)
    if authorization_token is None:
        authorization_token = request.headers.get("Authorization")

    if authorization_token:
        return get_token_from_bearer(authorization_token)
    else:
        raise RequiresAuthenticationException
