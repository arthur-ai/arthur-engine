from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import AfterValidator
from sqlalchemy.orm import Session

from dependencies import (
    get_db_session,
    get_validated_task,
    llm_get_all_filter_parameters,
)
from repositories.llm_evals_repository import LLMEvalsRepository
from repositories.ml_evals_repository import MLEvalsRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import Task, User
from schemas.request_schemas import LLMGetAllFilterRequest
from schemas.response_schemas import AllEvalsMetadataListResponse, EvalMetadataItem
from utils.users import permission_checker
from utils.utils import common_pagination_parameters
from arthur_common.models.common_schemas import PaginationParameters

eval_routes = APIRouter(
    prefix="/api/v2",
    route_class=GenaiEngineRoute,
)


@eval_routes.get(
    "/tasks/{task_id}/evals",
    summary="Get all evaluators",
    description=(
        "Return metadata for every evaluator associated with a task — "
        "both LLM and ML evals — in a single paginated list. "
        "The ``eval_type`` field on each item indicates the type "
        "(currently ``'llm'`` or ``'ml'``)."
    ),
    response_model=AllEvalsMetadataListResponse,
    response_model_exclude_none=True,
    tags=["Evals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_all_evals(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    filter_request: Annotated[
        LLMGetAllFilterRequest,
        Depends(llm_get_all_filter_parameters),
    ],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> AllEvalsMetadataListResponse:
    try:
        llm_repo = LLMEvalsRepository(db_session)
        ml_repo = MLEvalsRepository(db_session)

        llm_list = llm_repo.get_all_llm_item_metadata(task.id, pagination_parameters, filter_request)
        ml_list = ml_repo.get_all_metadata(task.id)

        items: list[EvalMetadataItem] = [
            EvalMetadataItem(
                eval_type="llm",
                name=item.name,
                versions=item.versions,
                tags=item.tags,
                created_at=item.created_at,
                latest_version_created_at=item.latest_version_created_at,
                deleted_versions=item.deleted_versions,
            )
            for item in llm_list.llm_metadata
        ] + [
            EvalMetadataItem(
                eval_type="ml",
                name=item.name,
                versions=item.versions,
                ml_eval_type=item.ml_eval_type,
                latest_version_created_at=item.latest_version_created_at,
            )
            for item in ml_list.ml_metadata
        ]

        return AllEvalsMetadataListResponse(evals=items, count=len(items))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
