import logging
from uuid import UUID

from auth.ApiKeyValidator.APIKeyvalidatorCreator import APIKeyValidatorCreator
from auth.ApiKeyValidator.enums import APIKeyValidatorType
from auth.multi_validator import MultiMethodValidator
from config.config import Config
from dependencies import get_db_session
from fastapi import APIRouter, Depends
from repositories.api_key_repository import ApiKeyRepository
from routers.route_handler import GenaiEngineRoute
from arthur_common.models.enums import APIKeysRolesEnum
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import User
from arthur_common.models.request_schemas import NewApiKeyRequest
from arthur_common.models.response_schemas import ApiKeyResponse
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import Response
from utils.users import permission_checker

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
    description=f"Generates a new API key. Up to {Config.max_api_key_limit()} active keys can exist at the same time by default. Contact your system administrator if you need more. Allowed roles are: {', '.join(role.value for role in APIKeysRolesEnum)}.",
    response_model_exclude_none=True,
)
@permission_checker(permissions=PermissionLevelsEnum.API_KEY_WRITE.value)
def create_api_key(
    new_api_key: NewApiKeyRequest,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    try:
        api_key_repo = ApiKeyRepository(db_session)
        api_key = api_key_repo.create_api_key(
            description=new_api_key.description,
            roles=new_api_key.roles,
        )
        return api_key._to_response_model(
            message="The provided key is only available for display now. "
            "It is your responsibility to store it safely after creation. GenAI Engine "
            "will not be able to retrieve the key for you after this creation request. "
            "If you reach the maximum limit or lose old keys, you can deactivate an old "
            "key using its ID and create new keys.",
        )
    except Exception as e:
        raise e
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
):
    try:
        api_key_repo = ApiKeyRepository(db_session)
        api_key = api_key_repo.get_api_key_by_id(str(api_key_id))
        return api_key._to_response_model()
    except:
        raise
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
):
    try:
        api_key_repo = ApiKeyRepository(db_session)
        active_api_keys = api_key_repo.get_all_active_api_keys()
        return [api_key._to_response_model() for api_key in active_api_keys]
    except:
        raise
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
):
    try:
        api_key_repo = ApiKeyRepository(db_session)
        api_key_repo.deactivate_api_key(str(api_key_id))
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except:
        raise
    finally:
        db_session.close()
