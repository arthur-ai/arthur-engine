from typing import Annotated
from uuid import UUID

from clients.telemetry.telemetry_client import (
    TelemetryEventTypes,
    send_telemetry_event,
    send_telemetry_event_for_default_rule_create_completed,
)
from dependencies import get_application_config, get_db_session
from fastapi import APIRouter, Body, Depends
from opentelemetry import trace
from repositories.rules_repository import RuleRepository
from repositories.tasks_repository import TaskRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.common_schemas import PaginationParameters
from schemas.enums import PermissionLevelsEnum, RuleScope, RuleType
from schemas.internal_schemas import ApplicationConfiguration, Rule, User
from schemas.request_schemas import NewRuleRequest, SearchRulesRequest
from schemas.response_schemas import RuleResponse, SearchRulesResponse
from sqlalchemy.orm import Session
from starlette import status
from starlette.responses import Response
from utils.users import permission_checker
from utils.utils import common_pagination_parameters

rule_management_routes = APIRouter(
    prefix="/api/v2",
    route_class=GenaiEngineRoute,
)

tracer = trace.get_tracer(__name__)


@rule_management_routes.post(
    "/default_rules",
    description="Create a default rule. Default rules are applied universally across existing tasks, "
    "subsequently created new tasks, and any non-task related requests. Once a rule is created, "
    "it is immutable. Available rules are {}. Note: The rules are cached by the validation endpoints for 60 seconds.".format(
        ", ".join(
            [f"'{rule.value}'" for rule in RuleType],
        ),
    ),
    response_model=RuleResponse,
    response_model_exclude_none=True,
    tags=["Rules"],
)
@permission_checker(permissions=PermissionLevelsEnum.DEFAULT_RULES_WRITE.value)
@tracer.start_as_current_span("route_v2_create_default_rule")
def create_default_rule(
    request: NewRuleRequest = Body(
        None,
        openapi_examples=NewRuleRequest.model_config["json_schema_extra"],
    ),
    db_session: Session = Depends(get_db_session),
    application_config: ApplicationConfiguration = Depends(get_application_config),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    try:
        send_telemetry_event(TelemetryEventTypes.DEFAULT_RULE_CREATE_INITIATED)
        rules_repo = RuleRepository(db_session)
        tasks_repo = TaskRepository(db_session, rules_repo, application_config)
        rule = Rule._from_request_model(request, scope=RuleScope.DEFAULT)
        rule = rules_repo.create_rule(rule)
        tasks_repo.update_all_tasks_add_default_rule(rule)
        send_telemetry_event_for_default_rule_create_completed(rule.type)
        return rule._to_response_model()
    except:
        raise
    finally:
        db_session.close()


@rule_management_routes.get(
    "/default_rules",
    description="Get default rules.",
    response_model=list[RuleResponse],
    response_model_exclude_none=True,
    tags=["Rules"],
)
@permission_checker(permissions=PermissionLevelsEnum.DEFAULT_RULES_READ.value)
def get_default_rules(
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    try:
        rules_repo = RuleRepository(db_session)
        rules, _ = rules_repo.query_rules(rule_scopes=[RuleScope.DEFAULT])

        return [rule._to_response_model() for rule in rules]
    except:
        raise
    finally:
        db_session.close()


@rule_management_routes.delete(
    "/default_rules/{rule_id}",
    description="Archive existing default rule.",
    tags=["Rules"],
)
@permission_checker(permissions=PermissionLevelsEnum.DEFAULT_RULES_WRITE.value)
def archive_default_rule(
    rule_id: UUID,
    db_session: Session = Depends(get_db_session),
    application_config: ApplicationConfiguration = Depends(get_application_config),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    try:
        rules_repo = RuleRepository(db_session)
        task_repo = TaskRepository(db_session, rules_repo, application_config)
        rules_repo.archive_rule(rule_id=str(rule_id))
        task_repo.update_all_tasks_remove_default_rule(str(rule_id))

        return Response(status_code=status.HTTP_200_OK)
    except:
        raise
    finally:
        db_session.close()


@rule_management_routes.post(
    "/rules/search",
    description="Search default and/or task rules.",
    response_model=SearchRulesResponse,
    response_model_exclude_none=True,
    tags=["Rules"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def search_rules(
    request: SearchRulesRequest,
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    db_session: Session = Depends(get_db_session),
    application_config: ApplicationConfiguration = Depends(get_application_config),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    try:
        rules_repo = RuleRepository(db_session)
        rules, count = rules_repo.query_rules(
            rule_ids=request.rule_ids,
            prompt_enabled=request.prompt_enabled,
            response_enabled=request.response_enabled,
            rule_scopes=request.rule_scopes,
            rule_types=request.rule_types,
            sort=pagination_parameters.sort,
            page_size=pagination_parameters.page_size,
            page=pagination_parameters.page,
        )

        return SearchRulesResponse(
            count=count,
            rules=[r._to_response_model() for r in rules],
        )
    except:
        raise
    finally:
        db_session.close()
