import logging

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from auth.api_key_validator_client import APIKeyValidatorClient
from auth.ApiKeyValidator.APIKeyvalidatorCreator import APIKeyValidatorCreator
from auth.authorization_header_elements import (
    get_bearer_access_token_from_cookie_or_header,
)
from auth.jwk_client import JWKClient
from auth.utils import http_bearer_scheme
from dependencies import get_api_key_validator_client, get_db_session, get_jwk_client
from schemas.enums import ActorKind
from schemas.internal_schemas import User
from utils.constants import ON_BEHALF_OF_HEADER

logger = logging.getLogger(__name__)


class MultiMethodValidator:
    def __init__(self, api_key_validator_creators: list[APIKeyValidatorCreator]):
        self.api_key_validator_creators = api_key_validator_creators

    # Unused creds variable enables the authorization of requests on the docs site through some FastAPI magic, don't remove it
    async def validate_api_multi_auth(
        self,
        request: Request,
        jwk_client: JWKClient = Depends(get_jwk_client),
        token: str = Depends(get_bearer_access_token_from_cookie_or_header),
        api_key_validator_client: APIKeyValidatorClient = Depends(
            get_api_key_validator_client,
        ),
        db_session: Session = Depends(get_db_session),
        creds: HTTPAuthorizationCredentials = Depends(http_bearer_scheme),
    ) -> User | None:
        """Method responsible to check if user has a proper authentication token (header or cookie).

        Args:
            jwk_client (JWKClient, optional): Client responsible for validation JWT Token. Defaults to Depends(get_jwk_client).
            token (str, optional): Token that will be validated. Defaults to Depends(get_bearer_access_token_from_cookie_or_header).
            api_key_validator_client (APIKeyValidatorClient, optional): Client that will validate API key. Defaults to Depends( get_api_key_validator_client, ).
            db_session (Session, optional): Session to Database. Defaults to Depends(get_db_session).
            creds (HTTPAuthorizationCredentials, optional): Unused creds variable enables the authorization of requests on the docs site through some FastAPI magic, don't remove it. Defaults to Depends(http_bearer_scheme).

        Raises:
            oauth_error: Raises when validation of OAuth token failed.

        Returns:
            User: Authorized user.
        """
        try:
            if user := api_key_validator_client.validate(
                self.api_key_validator_creators,
                token,
                db_session,
            ):
                # Only the admin key may name the person it acts for: it is held by
                # the control plane, which already authenticated that person. The
                # header is ignored for every other credential. Copy rather than
                # mutate: validated users can be shared through the key cache.
                if user.kind == ActorKind.MASTER_KEY:
                    user = user.model_copy(
                        update={
                            "on_behalf_of": request.headers.get(ON_BEHALF_OF_HEADER)
                            or None,
                        },
                    )
                request.state.user_id = user.id
                request.state.org_scope = user.org_scope
                request.state.actor = user.to_actor()
                return user
        except Exception as e:
            logger.warning(
                f"Trying Oauth Token validation. API Key validation failed: {str(e)}",
            )
        finally:
            db_session.close()

        # If API key validation fails, try oauth validation. JWT users are always
        # cross-org admins in v1 — org_scope stays None.
        try:
            if jwk_client and (user := jwk_client.validate(token)):
                request.state.user_id = user.id
                request.state.org_scope = user.org_scope
                request.state.actor = user.to_actor()
                return user
        except Exception as oauth_error:
            raise oauth_error

        return None
