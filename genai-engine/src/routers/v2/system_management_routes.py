import json
from datetime import datetime

from arthur_common.models.enums import TokenUsageScope
from arthur_common.models.response_schemas import TokenUsageResponse
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import Response

from dependencies import get_application_config, get_db_session, logger
from repositories.configuration_repository import ConfigurationRepository
from repositories.metrics_repository import MetricRepository
from repositories.rules_repository import RuleRepository
from repositories.tasks_repository import TaskRepository
from repositories.usage_repository import UsageRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import ApplicationConfiguration, User
from schemas.request_schemas import ApplicationConfigurationUpdateRequest
from schemas.response_schemas import ApplicationConfigurationResponse
from utils.users import permission_checker
from utils.utils import public_endpoint

system_management_routes = APIRouter(
    prefix="/api/v2",
    route_class=GenaiEngineRoute,
)


@system_management_routes.get(
    "/usage/tokens",
    description="Get token usage.",
    response_model=list[TokenUsageResponse],
    tags=["Usage"],
)
@permission_checker(permissions=PermissionLevelsEnum.USAGE_READ.value)
def get_token_usage(
    start_time: datetime = Query(
        None,
        description="Inclusive start date in ISO8601 string format. Defaults to the beginning of the current day if not provided.",
    ),
    end_time: datetime = Query(
        None,
        description="Exclusive end date in ISO8601 string format. Defaults to the end of the current day if not provided.",
    ),
    group_by: list[TokenUsageScope] = Query(
        [TokenUsageScope.RULE_TYPE],
        description="Entities to group token counts on.",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    try:
        usage_repo = UsageRepository(db_session)
        return usage_repo.get_tokens_usage(
            start_time=start_time,
            end_time=end_time,
            group_by=group_by,
        )
    except:
        raise
    finally:
        db_session.close()


@system_management_routes.get(
    "/configuration",
    description="Get application configuration settings.",
    response_model=ApplicationConfigurationResponse,
    include_in_schema=False,
)
@permission_checker(permissions=PermissionLevelsEnum.APP_CONFIG_READ.value)
def get_configuration(
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    try:
        config_repo = ConfigurationRepository(db_session)
        config = config_repo.get_configurations()

        return config._to_response_model()
    except:
        raise
    finally:
        db_session.close()


@system_management_routes.post(
    "/configuration",
    description="Update application configuration settings.",
    response_model=ApplicationConfigurationResponse,
    include_in_schema=False,
)
@permission_checker(permissions=PermissionLevelsEnum.APP_CONFIG_WRITE.value)
def update_configuration(
    body: ApplicationConfigurationUpdateRequest,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    application_config: ApplicationConfiguration = Depends(get_application_config),
):
    try:
        if body.chat_task_id:
            tasks_repo = TaskRepository(
                db_session,
                RuleRepository(db_session),
                MetricRepository(db_session),
                application_config,
            )
            tasks_repo.get_db_task_by_id(body.chat_task_id)
        config_repo = ConfigurationRepository(db_session)

        new_config = config_repo.update_configurations(body)

        return new_config._to_response_model()
    except:
        raise
    finally:
        db_session.close()


@system_management_routes.post(
    "/csp_report",
    description="Receive CSP violation reports.",
    include_in_schema=False,
)
@public_endpoint
async def process_csp_report(request: Request):
    try:
        body = await request.body()
        csp_report = json.loads(body.decode("utf-8"))
        logger.debug("Content Security Policy violation report received.")
        logger.debug(csp_report)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        logger.error(f"Error processing Content Security Policy violation report: {e}")
        raise e
