from typing import Annotated, Optional
from uuid import UUID

from arthur_common.models.common_schemas import PaginationParameters
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session
from starlette.responses import Response
from starlette.status import HTTP_204_NO_CONTENT

from clients.rag_providers.rag_client_constructor import RagClientConstructor
from dependencies import get_db_session
from repositories.rag_providers_repository import RagProvidersRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import (
    PermissionLevelsEnum,
    RagAPIKeyAuthenticationProviderEnum,
    RagProviderAuthenticationMethodEnum,
)
from schemas.internal_schemas import RagProviderConfiguration, User
from schemas.request_schemas import (
    RagKeywordSearchSettingRequest,
    RagProviderConfigurationRequest,
    RagProviderConfigurationUpdateRequest,
    RagVectorSimilarityTextSearchSettingRequest,
)
from schemas.response_schemas import (
    ConnectionCheckResult,
    RagProviderConfigurationResponse,
    RagProviderQueryResponse,
    SearchRagProviderConfigurationsResponse,
)
from utils.users import permission_checker
from utils.utils import common_pagination_parameters

rag_routes = APIRouter(
    prefix="/api/v1",
    route_class=GenaiEngineRoute,
)
rag_router_tag = "RAG Providers"

###################################
###### RAG Management Routes ######
###################################


@rag_routes.post(
    "/tasks/{task_id}/rag_providers",
    description="Register a new RAG provider connection configuration.",
    response_model=RagProviderConfigurationResponse,
    tags=[rag_router_tag],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def create_rag_provider(
    request: RagProviderConfigurationRequest,
    task_id: str = Path(
        description="ID of the task to register a new provider connection for. Should be formatted as a UUID.",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> RagProviderConfigurationResponse:
    try:
        rag_providers_repo = RagProvidersRepository(db_session)
        rag_provider_config = RagProviderConfiguration._from_request_model(
            task_id,
            request,
        )
        rag_providers_repo.create_rag_provider_configuration(rag_provider_config)
        return rag_provider_config.to_response_model()
    finally:
        db_session.close()


@rag_routes.get(
    "/tasks/{task_id}/rag_providers",
    description="Get list of RAG provider connection configurations for the task.",
    response_model=SearchRagProviderConfigurationsResponse,
    tags=[rag_router_tag],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_rag_providers(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    task_id: UUID = Path(
        description="ID of the task to fetch the provider connections for.",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    config_name: Optional[str] = Query(
        default=None,
        description="RAG Provider configuration name substring to search for.",
    ),
    authentication_method: Optional[RagProviderAuthenticationMethodEnum] = Query(
        default=None,
        description="RAG Provider authentication method to filter by.",
    ),
    rag_provider_name: Optional[RagAPIKeyAuthenticationProviderEnum] = Query(
        default=None,
        description="RAG provider name to filter by.",
    ),
) -> SearchRagProviderConfigurationsResponse:
    try:
        rag_providers_repo = RagProvidersRepository(db_session)
        configs, total_count = (
            rag_providers_repo.get_rag_provider_configurations_by_task(
                str(task_id),
                pagination_parameters,
                config_name=config_name,
                authentication_method=authentication_method,
                rag_provider_name=rag_provider_name,
            )
        )

        return SearchRagProviderConfigurationsResponse(
            count=total_count,
            rag_provider_configurations=[
                config.to_response_model() for config in configs
            ],
        )
    finally:
        db_session.close()


@rag_routes.get(
    "/rag_providers/{provider_id}",
    description="Get a single RAG provider connection configuration.",
    response_model=RagProviderConfigurationResponse,
    tags=[rag_router_tag],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_rag_provider(
    provider_id: UUID = Path(description="ID of RAG provider configuration."),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> RagProviderConfigurationResponse:
    try:
        rag_providers_repo = RagProvidersRepository(db_session)
        config = rag_providers_repo.get_rag_provider_configuration(provider_id)
        return config.to_response_model()
    finally:
        db_session.close()


@rag_routes.patch(
    "/rag_providers/{provider_id}",
    description="Update a single RAG provider connection configuration.",
    response_model=RagProviderConfigurationResponse,
    tags=[rag_router_tag],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def update_rag_provider(
    request: RagProviderConfigurationUpdateRequest,
    provider_id: UUID = Path(
        description="ID of the RAG provider to update the connection configuration for.",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> RagProviderConfigurationResponse:
    try:
        rag_providers_repo = RagProvidersRepository(db_session)
        rag_providers_repo.update_rag_provider_configuration(provider_id, request)
        config = rag_providers_repo.get_rag_provider_configuration(provider_id)
        return config.to_response_model()
    finally:
        db_session.close()


@rag_routes.delete(
    "/rag_providers/{provider_id}",
    description="Delete a RAG provider connection configuration.",
    tags=[rag_router_tag],
    status_code=HTTP_204_NO_CONTENT,
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def delete_rag_provider(
    provider_id: UUID = Path(
        description="ID of the RAG provider configuration to delete.",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> Response:
    try:
        rag_providers_repo = RagProvidersRepository(db_session)
        rag_providers_repo.delete_rag_provider_configuration(provider_id)
        return Response(status_code=HTTP_204_NO_CONTENT)
    finally:
        db_session.close()


@rag_routes.post(
    "/tasks/{task_id}/rag_providers/test_connection",
    description="Test a new RAG provider connection configuration.",
    response_model=ConnectionCheckResult,
    tags=[rag_router_tag],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def test_rag_provider_connection(
    request: RagProviderConfigurationRequest,
    task_id: str = Path(
        description="ID of the task to test the new provider connection for. Should be formatted as a UUID.",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> ConnectionCheckResult:
    try:
        rag_provider_config = RagProviderConfiguration._from_request_model(
            task_id,
            request,
        )
        rag_client_constructor = RagClientConstructor(rag_provider_config)
        return rag_client_constructor.execute_test_connection()
    finally:
        db_session.close()


@rag_routes.post(
    "/rag_providers/{provider_id}/similarity_text_search",
    description="Execute a RAG Provider Similarity Text Search.",
    response_model=RagProviderQueryResponse,
    tags=[rag_router_tag],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def execute_similarity_text_search(
    request: RagVectorSimilarityTextSearchSettingRequest,
    provider_id: UUID = Path(
        description="ID of the RAG provider configuration to use for the vector database connection.",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> RagProviderQueryResponse:
    try:
        rag_providers_repo = RagProvidersRepository(db_session)
        rag_provider_config = rag_providers_repo.get_rag_provider_configuration(
            provider_id,
        )
        rag_client_constructor = RagClientConstructor(rag_provider_config)
        return rag_client_constructor.execute_similarity_text_search(request)
    finally:
        db_session.close()


@rag_routes.post(
    "/rag_providers/{provider_id}/keyword_search",
    description="Execute a RAG Provider Keyword (BM25/Sparse Vector) Search.",
    response_model=RagProviderQueryResponse,
    tags=[rag_router_tag],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def execute_keyword_search(
    request: RagKeywordSearchSettingRequest,
    provider_id: UUID = Path(
        description="ID of the RAG provider configuration to use for the vector database connection.",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> RagProviderQueryResponse:
    try:
        rag_providers_repo = RagProvidersRepository(db_session)
        rag_provider_config = rag_providers_repo.get_rag_provider_configuration(
            provider_id,
        )
        rag_client_constructor = RagClientConstructor(rag_provider_config)
        return rag_client_constructor.execute_keyword_search(request)
    finally:
        db_session.close()
