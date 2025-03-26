from dataclasses import dataclass

import jwt
from schemas.custom_exceptions import (
    BadCredentialsException,
    UnableCredentialsException,
)
from schemas.internal_schemas import User
from utils.users import get_user_info_from_payload


@dataclass
class JWKClient:
    """Perform JSON Web Token (JWT) validation using PyJWT"""

    def __init__(self, jwks_uri: str):
        self.jwks_client = jwt.PyJWKClient(jwks_uri)
        self.algorithm = "RS256"

    def validate(self, jwt_access_token: str) -> User | None:
        try:
            payload = dict()
            if not jwt_access_token == "undefined":
                jwt_signing_key = self.jwks_client.get_signing_key_from_jwt(
                    jwt_access_token,
                ).key
                payload = jwt.decode(
                    jwt_access_token,
                    jwt_signing_key,
                    algorithms=[self.algorithm],
                    options={"verify_signature": True, "verify_aud": False},
                )
                return get_user_info_from_payload(payload)
            return None
        except jwt.exceptions.PyJWKClientError:
            raise UnableCredentialsException
        except jwt.exceptions.InvalidTokenError:
            raise BadCredentialsException
