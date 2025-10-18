import logging

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from starlette.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT

from dependencies import get_db_session
from repositories.model_provider_repository import ModelProviderRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum, ModelProvider
from schemas.internal_schemas import User
from schemas.request_schemas import PutModelProviderCredentials
from schemas.response_schemas import ModelProviderResponse
from utils.users import permission_checker

logger = logging.getLogger(__name__)

model_provider_routes = APIRouter(
    prefix="/api/v1",
    route_class=GenaiEngineRoute,
)


@model_provider_routes.put(
    "/model_providers/{provider}",
    summary="Set the configuration for a model provider.",
    description="Set the configuration for a model provider",
    status_code=HTTP_201_CREATED,
    responses={
        HTTP_201_CREATED: {"model": None},
    },
    tags=["Model Providers"],
)
@permission_checker(permissions=PermissionLevelsEnum.MODEL_PROVIDER_WRITE.value)
def set_model_provider(
    provider: ModelProvider,
    provider_credentials: PutModelProviderCredentials,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> Response:
    """Set the configuration for a model provider"""
    try:
        repo = ModelProviderRepository(db_session)
        repo.set_model_provider_credentials(
            provider=provider,
            api_key=provider_credentials.api_key,
        )
        return Response(status_code=HTTP_201_CREATED)
    finally:
        db_session.close()


@model_provider_routes.delete(
    "/model_providers/{provider}",
    summary="Disables the configuration for a model provider.",
    description="Disables the configuration for a model provider",
    tags=["Model Providers"],
    status_code=HTTP_204_NO_CONTENT,
    responses={HTTP_204_NO_CONTENT: {"description": "Provider deleted."}},
)
@permission_checker(permissions=PermissionLevelsEnum.MODEL_PROVIDER_WRITE.value)
def set_model_provider(
    provider: ModelProvider,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> Response:
    """Set the configuration for a model provider"""
    try:
        repo = ModelProviderRepository(db_session)
        repo.delete_model_provider_credentials(
            provider=provider,
        )
        return Response(status_code=HTTP_204_NO_CONTENT)
    finally:
        db_session.close()


@model_provider_routes.get(
    "/model_providers",
    summary="List the model providers..",
    description="Shows all model providers and if they're enabled.",
    tags=["Model Providers"],
    response_model=list[ModelProviderResponse],
)
@permission_checker(permissions=PermissionLevelsEnum.MODEL_PROVIDER_WRITE.value)
def get_model_providers(
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """Set the configuration for a model provider"""
    try:
        repo = ModelProviderRepository(db_session)
        return repo.list_model_providers()
    finally:
        db_session.close()
