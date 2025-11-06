from typing import Annotated, Optional
from uuid import UUID

from arthur_common.models.common_schemas import PaginationParameters
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session
from starlette.responses import Response
from starlette.status import HTTP_204_NO_CONTENT

from dependencies import get_application_config, get_db_session
from repositories.metrics_repository import MetricRepository
from repositories.rag_providers_repository import RagProvidersRepository
from repositories.rules_repository import RuleRepository
from repositories.tasks_repository import TaskRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import (
    PermissionLevelsEnum,
)
from schemas.internal_schemas import (
    ApplicationConfiguration,
    RagSearchSettingConfiguration,
    RagSearchSettingConfigurationVersion,
    User,
)
from schemas.request_schemas import (
    RagSearchSettingConfigurationNewVersionRequest,
    RagSearchSettingConfigurationRequest,
    RagSearchSettingConfigurationUpdateRequest,
)
from schemas.response_schemas import (
    ListRagSearchSettingConfigurationsResponse,
    RagSearchSettingConfigurationResponse,
    RagSearchSettingConfigurationVersionResponse,
)
from utils.users import permission_checker
from utils.utils import common_pagination_parameters

rag_setting_routes = APIRouter(
    prefix="/api/v1",
    route_class=GenaiEngineRoute,
)
rag_settings_router_tag = "RAG Settings"

############################################
###### RAG Settings Management Routes ######
############################################


@rag_setting_routes.post(
    "/tasks/{task_id}/rag_search_settings",
    description="Create a new RAG search settings configuration.",
    response_model=RagSearchSettingConfigurationResponse,
    tags=[rag_settings_router_tag],
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


@rag_setting_routes.get(
    "/rag_search_settings/{setting_configuration_id}",
    description="Get a single RAG setting configuration.",
    response_model=RagSearchSettingConfigurationResponse,
    tags=[rag_settings_router_tag],
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


@rag_setting_routes.delete(
    "/rag_search_settings/{setting_configuration_id}",
    description="Delete a RAG search setting configuration.",
    tags=[rag_settings_router_tag],
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


@rag_setting_routes.patch(
    "/rag_search_settings/{setting_configuration_id}",
    description="Update a single RAG search setting configuration.",
    response_model=RagSearchSettingConfigurationResponse,
    tags=[rag_settings_router_tag],
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


@rag_setting_routes.get(
    "/tasks/{task_id}/rag_search_settings",
    description="Get list of RAG search setting configurations for the task.",
    response_model=ListRagSearchSettingConfigurationsResponse,
    tags=[rag_settings_router_tag],
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
) -> ListRagSearchSettingConfigurationsResponse:
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

        return ListRagSearchSettingConfigurationsResponse(
            count=total_count,
            rag_provider_setting_configurations=[
                config.to_response_model() for config in configs
            ],
        )
    finally:
        db_session.close()


@rag_setting_routes.post(
    "/rag_search_settings/{setting_configuration_id}/versions",
    description="Create a new version for an existing RAG search settings configuration.",
    response_model=RagSearchSettingConfigurationVersionResponse,
    tags=[rag_settings_router_tag],
    operation_id="create_rag_search_settings_version",
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def create_rag_search_settings_version(
    request: RagSearchSettingConfigurationNewVersionRequest,
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


@rag_setting_routes.get(
    "/rag_search_settings/{setting_configuration_id}/versions/{version_number}",
    description="Get a single RAG setting configuration version.",
    response_model=RagSearchSettingConfigurationVersionResponse,
    tags=[rag_settings_router_tag],
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


@rag_setting_routes.delete(
    "/rag_search_settings/{setting_configuration_id}/versions/{version_number}",
    description="Soft delete a RAG search setting configuration version.",
    tags=[rag_settings_router_tag],
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
