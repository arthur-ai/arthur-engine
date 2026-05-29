import logging
from uuid import UUID

from arthur_common.models.enums import APIKeysRolesEnum
from arthur_common.models.request_schemas import NewApiKeyRequest
from arthur_common.models.response_schemas import ApiKeyResponse
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import Response

from auth.ApiKeyValidator.APIKeyvalidatorCreator import APIKeyValidatorCreator
from auth.ApiKeyValidator.enums import APIKeyValidatorType
from auth.multi_validator import MultiMethodValidator
from config.config import Config
from dependencies import get_db_session
from repositories.api_key_repository import ApiKeyRepository
from routers.route_handler import GenaiEngineRoute
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import User
from utils import constants
from utils.users import permission_checker

# TENANT-USER keys are only mintable via the public tenant signup flow (UP-4430);
# admins reach this endpoint via API_KEY_WRITE and must not be able to create them.
_ADMIN_FORBIDDEN_ROLES = frozenset([constants.TENANT_USER])

api_key_validator_creators = [APIKeyValidatorCreator(APIKeyValidatorType.MASTER)]
multi_validator = MultiMethodValidator(api_key_validator_creators)
logger = logging.getLogger()

api_keys_routes = APIRouter(
    prefix="/auth/api_keys",
    route_class=GenaiEngineRoute,
    tags=["API Keys"],
)


@api_keys_routes.post(
    "/",
    response_model=ApiKeyResponse,
    description=(
        f"Generates a new API key. Up to {Config.max_api_key_limit()} active keys can exist at "
        f"the same time by default. Contact your system administrator if you need more. "
        f"Allowed roles are: "
        f"{', '.join(r.value for r in APIKeysRolesEnum if r.value not in _ADMIN_FORBIDDEN_ROLES)}."
    ),
    response_model_exclude_none=True,
)
@permission_checker(permissions=PermissionLevelsEnum.API_KEY_WRITE.value)
def create_api_key(
    new_api_key: NewApiKeyRequest,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> ApiKeyResponse:
    forbidden = {
        r.value for r in (new_api_key.roles or []) if r.value in _ADMIN_FORBIDDEN_ROLES
    }
    if forbidden:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Roles {sorted(forbidden)} cannot be assigned via this endpoint; "
                f"use the tenant signup flow."
            ),
        )
    try:
        api_key_repo = ApiKeyRepository(db_session)
        api_key = api_key_repo.create_api_key(
            description=new_api_key.description,
            roles=new_api_key.roles or [],
        )
        return api_key._to_response_model(
            message="The provided key is only available for display now. "
            "It is your responsibility to store it safely after creation. GenAI Engine "
            "will not be able to retrieve the key for you after this creation request. "
            "If you reach the maximum limit or lose old keys, you can deactivate an old "
            "key using its ID and create new keys.",
        )
    finally:
        db_session.close()


@api_keys_routes.get(
    "/{api_key_id}",
    response_model=ApiKeyResponse,
    response_model_exclude_none=True,
)
@permission_checker(permissions=PermissionLevelsEnum.API_KEY_READ.value)
def get_api_key(
    api_key_id: UUID,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> ApiKeyResponse:
    try:
        api_key_repo = ApiKeyRepository(db_session)
        api_key = api_key_repo.get_api_key_by_id(str(api_key_id))
        return api_key._to_response_model()
    finally:
        db_session.close()


@api_keys_routes.get(
    "/",
    response_model=list[ApiKeyResponse],
    response_model_exclude_none=True,
)
@permission_checker(permissions=PermissionLevelsEnum.API_KEY_READ.value)
def get_all_active_api_keys(
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> list[ApiKeyResponse]:
    try:
        api_key_repo = ApiKeyRepository(db_session)
        active_api_keys = api_key_repo.get_all_active_api_keys()
        return [api_key._to_response_model() for api_key in active_api_keys]
    finally:
        db_session.close()


@api_keys_routes.delete(
    "/deactivate/{api_key_id}",
    response_model=ApiKeyResponse,
    response_model_exclude_none=True,
)
@permission_checker(permissions=PermissionLevelsEnum.API_KEY_WRITE.value)
def deactivate_api_key(
    api_key_id: UUID,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> Response:
    try:
        api_key_repo = ApiKeyRepository(db_session)
        api_key_repo.deactivate_api_key(str(api_key_id))
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    finally:
        db_session.close()
