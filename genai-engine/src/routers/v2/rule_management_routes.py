from typing import Annotated
from uuid import UUID

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import PaginationSortMethod
from arthur_common.models.request_schemas import SearchRulesRequest
from arthur_common.models.response_schemas import SearchRulesResponse
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from dependencies import get_application_config, get_db_session, get_org_scope
from repositories.rules_repository import RuleRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import ApplicationConfiguration, User
from utils.users import permission_checker
from utils.utils import common_pagination_parameters

rule_management_routes = APIRouter(
    prefix="/api/v2",
    route_class=GenaiEngineRoute,
)


@rule_management_routes.post(
    "/rules/search",
    description="Search rules.",
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
    org_scope: UUID | None = Depends(get_org_scope),
) -> SearchRulesResponse:
    rules_repo = RuleRepository(db_session)
    rules, count = rules_repo.query_rules(
        rule_ids=request.rule_ids,
        prompt_enabled=request.prompt_enabled,
        response_enabled=request.response_enabled,
        rule_scopes=request.rule_scopes,
        rule_types=request.rule_types,
        sort=pagination_parameters.sort or PaginationSortMethod.DESCENDING,
        page_size=pagination_parameters.page_size,
        page=pagination_parameters.page,
        org_scope=org_scope,
    )

    return SearchRulesResponse(
        count=count,
        rules=[r._to_response_model() for r in rules],
    )
