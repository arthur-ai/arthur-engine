from datetime import datetime
from typing import Annotated

from dependencies import get_db_session
from fastapi import APIRouter, Depends, HTTPException, Query
from repositories.inference_repository import InferenceRepository
from repositories.metrics_repository import MetricRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.common_schemas import PaginationParameters
from schemas.enums import PermissionLevelsEnum, RuleResultEnum, RuleType
from schemas.internal_schemas import Inference, User
from schemas.response_schemas import QueryInferencesResponse, ComputeMetricsResponse
from sqlalchemy.orm import Session
from utils import constants as constants
from utils.users import permission_checker
from utils.utils import common_pagination_parameters

query_routes = APIRouter(
    prefix="/api/v2",
    route_class=GenaiEngineRoute,
)


@query_routes.get(
    "/inferences/query",
    description="Paginated inference querying. See parameters for available filters. Includes inferences from archived tasks and rules.",
    tags=["Inferences"],
    response_model=QueryInferencesResponse,
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_READ.value)
def query_inferences(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    task_ids: list[str] = Query([], description="Task ID to filter on."),
    task_name: str = Query(None, description="Task name to filter on."),
    conversation_id: str = Query(None, description="Conversation ID to filter on."),
    inference_id: str = Query(None, description="Inference ID to filter on."),
    user_id: str = Query(
        None,
        description="User ID to filter on.",
    ),
    start_time: datetime = Query(
        None,
        description="Inclusive start date in ISO8601 string format.",
    ),
    end_time: datetime = Query(
        None,
        description="Exclusive end date in ISO8601 string format.",
    ),
    rule_types: list[RuleType] = Query(
        [],
        description="List of RuleType to query for. Any inference that ran any rule in the list will be returned. Defaults to all statuses. If used in conjunction with with rule_statuses, will return inferences with rules in the intersection of rule_types and rule_statuses.",
    ),
    rule_statuses: list[RuleResultEnum] = Query(
        [],
        description="List of RuleResultEnum to query for. Any inference with any rule status in the list will be returned. Defaults to all statuses. If used in conjunction with with rule_types, will return inferences with rules in the intersection of rule_statuses and rule_types.",
    ),
    prompt_statuses: list[RuleResultEnum] = Query(
        [],
        description="List of RuleResultEnum to query for at inference prompt stage level. Must be 'Pass' / 'Fail'. Defaults to both.",
    ),
    response_statuses: list[RuleResultEnum] = Query(
        [],
        description="List of RuleResultEnum to query for at inference response stage level. Must be 'Pass' / 'Fail'. Defaults to both. Inferences missing responses will not be affected by this filter.",
    ),
    include_count: bool = Query(
        True,
        description="Whether to include the total count of matching inferences. Set to False to improve query performance for large datasets. Count will be returned as -1 if set to False.",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    try:
        valid_stage_results = {RuleResultEnum.PASS, RuleResultEnum.FAIL}

        if prompt_statuses and not set(prompt_statuses).issubset(valid_stage_results):
            raise HTTPException(
                status_code=400,
                detail=constants.ERROR_INVALID_QUERY_PROMPT_STATUS,
            )
        if response_statuses and not set(response_statuses).issubset(
            valid_stage_results,
        ):
            raise HTTPException(
                status_code=400,
                detail=constants.ERROR_INVALID_QUERY_RESPONSE_STATUS,
            )

        inference_repo = InferenceRepository(db_session)
        if inference_id:
            try:
                results = [
                    Inference._from_database_model(
                        inference_repo.get_inference(inference_id=inference_id),
                    ),
                ]
            except HTTPException:
                results = []
            count = len(results)
        else:
            results, count = inference_repo.query_inferences(
                pagination_parameters.sort,
                pagination_parameters.page,
                task_ids=task_ids,
                task_name=task_name,
                conversation_id=conversation_id,
                page_size=pagination_parameters.page_size,
                start_time=start_time,
                end_time=end_time,
                rule_types=rule_types,
                rule_results=rule_statuses,
                prompt_statuses=prompt_statuses,
                response_statuses=response_statuses,
                user_id=user_id,
                include_count=include_count,
            )

        results_formatted = [i._to_response_model() for i in results]
        return QueryInferencesResponse(count=count, inferences=results_formatted)
    except:
        raise
    finally:
        db_session.close()

