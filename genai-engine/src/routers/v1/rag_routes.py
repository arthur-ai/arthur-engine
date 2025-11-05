from typing import Annotated, Optional
from uuid import UUID

from arthur_common.models.common_schemas import PaginationParameters
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session
from starlette.responses import Response
from starlette.status import HTTP_204_NO_CONTENT

from clients.rag_providers.rag_client_constructor import RagClientConstructor
from dependencies import get_application_config, get_db_session
from repositories.metrics_repository import MetricRepository
from repositories.rag_providers_repository import RagProvidersRepository
from repositories.rules_repository import RuleRepository
from repositories.tasks_repository import TaskRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import (
    PermissionLevelsEnum,
    RagAPIKeyAuthenticationProviderEnum,
    RagProviderAuthenticationMethodEnum,
)
from schemas.internal_schemas import (
    ApplicationConfiguration,
    RagProviderConfiguration,
    RagProviderTestConfiguration,
    RagSearchSettingConfiguration,
    RagSearchSettingConfigurationVersion,
    User,
)
from schemas.request_schemas import (
    RagHybridSearchSettingRequest,
    RagKeywordSearchSettingRequest,
    RagProviderConfigurationRequest,
    RagProviderConfigurationUpdateRequest,
    RagProviderTestConfigurationRequest,
    RagSearchSettingConfigurationRequest,
    RagSearchSettingConfigurationUpdateRequest,
    RagSearchSettingNewVersionRequest,
    RagVectorSimilarityTextSearchSettingRequest,
)
from schemas.response_schemas import (
    ConnectionCheckResult,
    RagProviderConfigurationResponse,
    RagProviderQueryResponse,
    RagSearchSettingConfigurationResponse,
    RagSearchSettingConfigurationVersionResponse,
    SearchRagProviderCollectionsResponse,
    SearchRagProviderConfigurationsResponse,
    SearchRagSearchSettingConfigurationsResponse,
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
    application_config: ApplicationConfiguration = Depends(get_application_config),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> RagProviderConfigurationResponse:
    # validate task exists - get function will raise a 404 if it doesn't exist
    task_repo = TaskRepository(
        db_session,
        RuleRepository(db_session),
        MetricRepository(db_session),
        application_config,
    )
    task_repo.get_task_by_id(task_id)

    # create config
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


@rag_routes.get(
    "/rag_providers/{provider_id}/collections",
    description="Lists all available vector database collections.",
    response_model=SearchRagProviderCollectionsResponse,
    tags=[rag_router_tag],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def list_rag_provider_collections(
    provider_id: UUID = Path(
        description="ID of RAG provider configuration to use for authentication with the vector store.",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> SearchRagProviderCollectionsResponse:
    try:
        rag_providers_repo = RagProvidersRepository(db_session)
        rag_provider_config = rag_providers_repo.get_rag_provider_configuration(
            provider_id,
        )
        rag_client_constructor = RagClientConstructor(rag_provider_config)
        return rag_client_constructor.list_collections()
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
    request: RagProviderTestConfigurationRequest,
    task_id: str = Path(
        description="ID of the task to test the new provider connection for. Should be formatted as a UUID.",
    ),
    db_session: Session = Depends(get_db_session),
    application_config: ApplicationConfiguration = Depends(get_application_config),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> ConnectionCheckResult:
    try:
        # validate task exists - get function will raise a 404 if it doesn't exist
        task_repo = TaskRepository(
            db_session,
            RuleRepository(db_session),
            MetricRepository(db_session),
            application_config,
        )
        task_repo.get_task_by_id(task_id)

        # execute connection test
        rag_provider_config = RagProviderTestConfiguration._from_request_model(
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


@rag_routes.post(
    "/rag_providers/{provider_id}/hybrid_search",
    description="Execute a RAG provider hybrid (keyword and vector similarity) search.",
    response_model=RagProviderQueryResponse,
    tags=[rag_router_tag],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def execute_hybrid_search(
    request: RagHybridSearchSettingRequest,
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
        return rag_client_constructor.execute_hybrid_search(request)
    finally:
        db_session.close()


@rag_routes.post(
    "/tasks/{task_id}/rag_search_settings",
    description="Create a new RAG search settings configuration.",
    response_model=RagSearchSettingConfigurationResponse,
    tags=[rag_router_tag],
    operation_id="create_rag_search_settings",
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def create_rag_search_settings(
    request: RagSearchSettingConfigurationRequest,
    task_id: str = Path(
        description="ID of the task to create the search settings configuration under.",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    application_config: ApplicationConfiguration = Depends(get_application_config),
) -> RagSearchSettingConfigurationResponse:
    try:
        # validate task exists - get function will raise a 404 if it doesn't exist
        task_repo = TaskRepository(
            db_session,
            RuleRepository(db_session),
            MetricRepository(db_session),
            application_config,
        )
        task_repo.get_task_by_id(task_id)

        # validate rag_provider_id exists
        rag_providers_repo = RagProvidersRepository(db_session)
        rag_providers_repo.get_rag_provider_configuration(request.rag_provider_id)

        # create new settings config
        rag_providers_repo = RagProvidersRepository(db_session)
        setting_config = RagSearchSettingConfiguration._from_request_model(
            request,
            task_id,
        )
        rag_providers_repo.create_rag_setting_configuration(setting_config)
        return setting_config.to_response_model()
    finally:
        db_session.close()


@rag_routes.get(
    "/rag_search_settings/{setting_configuration_id}",
    description="Get a single RAG setting configuration.",
    response_model=RagSearchSettingConfigurationResponse,
    tags=[rag_router_tag],
    operation_id="get_rag_search_setting",
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_rag_search_setting(
    setting_configuration_id: UUID = Path(
        description="ID of RAG search setting configuration.",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> RagSearchSettingConfigurationResponse:
    try:
        rag_providers_repo = RagProvidersRepository(db_session)
        config = rag_providers_repo.get_rag_setting_configuration(
            setting_configuration_id,
        )
        return config.to_response_model()
    finally:
        db_session.close()


@rag_routes.delete(
    "/rag_search_settings/{setting_configuration_id}",
    description="Delete a RAG search setting configuration.",
    tags=[rag_router_tag],
    status_code=HTTP_204_NO_CONTENT,
    operation_id="delete_rag_search_setting",
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def delete_rag_search_setting(
    setting_configuration_id: UUID = Path(
        description="ID of RAG setting configuration.",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> Response:
    try:
        rag_providers_repo = RagProvidersRepository(db_session)
        rag_providers_repo.delete_rag_setting_configuration(setting_configuration_id)
        return Response(status_code=HTTP_204_NO_CONTENT)
    finally:
        db_session.close()


@rag_routes.patch(
    "/rag_search_settings/{setting_configuration_id}",
    description="Update a single RAG search setting configuration.",
    response_model=RagSearchSettingConfigurationResponse,
    tags=[rag_router_tag],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def update_rag_search_settings(
    request: RagSearchSettingConfigurationUpdateRequest,
    setting_configuration_id: UUID = Path(
        description="ID of the RAG setting configuration to update.",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> RagSearchSettingConfigurationResponse:
    try:
        rag_providers_repo = RagProvidersRepository(db_session)
        rag_providers_repo.update_rag_provider_setting_configuration(
            setting_configuration_id,
            request,
        )
        config = rag_providers_repo.get_rag_setting_configuration(
            setting_configuration_id,
        )
        return config.to_response_model()
    finally:
        db_session.close()


@rag_routes.get(
    "/tasks/{task_id}/rag_search_settings",
    description="Get list of RAG search setting configurations for the task.",
    response_model=SearchRagSearchSettingConfigurationsResponse,
    tags=[rag_router_tag],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_task_rag_search_settings(
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
        description="Rag search setting configuration name substring to search for.",
    ),
    rag_provider_ids: Optional[list[UUID]] = Query(
        default=None,
        description="List of rag provider configuration IDs to filter for.",
    ),
) -> SearchRagSearchSettingConfigurationsResponse:
    try:
        rag_providers_repo = RagProvidersRepository(db_session)
        configs, total_count = (
            rag_providers_repo.get_rag_search_setting_configurations_by_task(
                str(task_id),
                pagination_parameters,
                config_name=config_name,
                rag_provider_ids=rag_provider_ids,
            )
        )

        return SearchRagSearchSettingConfigurationsResponse(
            count=total_count,
            rag_provider_setting_configurations=[
                config.to_response_model() for config in configs
            ],
        )
    finally:
        db_session.close()


@rag_routes.post(
    "/rag_search_settings/{setting_configuration_id}/versions",
    description="Create a new version for an existing RAG search settings configuration.",
    response_model=RagSearchSettingConfigurationVersionResponse,
    tags=[rag_router_tag],
    operation_id="create_rag_search_settings_version",
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def create_rag_search_settings_version(
    request: RagSearchSettingNewVersionRequest,
    setting_configuration_id: UUID = Path(
        description="ID of the RAG settings configuration to create the new version for.",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> RagSearchSettingConfigurationVersionResponse:
    try:
        # get parent settings config
        rag_providers_repo = RagProvidersRepository(db_session)
        settings_config = rag_providers_repo.get_rag_setting_configuration(
            setting_configuration_id,
        )

        # create new settings version
        rag_providers_repo = RagProvidersRepository(db_session)
        setting_config = RagSearchSettingConfigurationVersion._from_request_model(
            request,
            setting_configuration_id,
            settings_config.latest_version_number + 1,
        )
        rag_providers_repo.create_rag_setting_configuration_version(setting_config)

        return setting_config.to_response_model()
    finally:
        db_session.close()


@rag_routes.get(
    "/rag_search_settings/{setting_configuration_id}/versions/{version_number}",
    description="Get a single RAG setting configuration version.",
    response_model=RagSearchSettingConfigurationVersionResponse,
    tags=[rag_router_tag],
    operation_id="get_rag_search_setting_version",
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_rag_search_setting_version(
    setting_configuration_id: UUID = Path(
        description="ID of RAG search setting configuration.",
    ),
    version_number: int = Path(description="Version number of the version to fetch."),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> RagSearchSettingConfigurationVersionResponse:
    try:
        rag_providers_repo = RagProvidersRepository(db_session)
        config = rag_providers_repo.get_rag_setting_configuration_version(
            setting_configuration_id,
            version_number,
        )
        return config.to_response_model()
    finally:
        db_session.close()


@rag_routes.delete(
    "/rag_search_settings/{setting_configuration_id}/versions/{version_number}",
    description="Soft delete a RAG search setting configuration version.",
    tags=[rag_router_tag],
    status_code=HTTP_204_NO_CONTENT,
    operation_id="delete_rag_search_setting_version",
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def delete_rag_search_setting_version(
    setting_configuration_id: UUID = Path(
        description="ID of RAG search setting configuration.",
    ),
    version_number: int = Path(description="Version number of the version to delete."),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> Response:
    try:
        rag_providers_repo = RagProvidersRepository(db_session)
        rag_providers_repo.soft_delete_rag_setting_configuration_version(
            setting_configuration_id,
            version_number,
        )
        return Response(status_code=HTTP_204_NO_CONTENT)
    finally:
        db_session.close()
