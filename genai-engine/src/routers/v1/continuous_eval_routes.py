from typing import Annotated
from uuid import UUID

from arthur_common.models.common_schemas import PaginationParameters
from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from dependencies import (
    continuous_eval_list_filter_parameters,
    get_db_session,
    get_validated_agentic_task,
)
from repositories.continuous_evals_repository import ContinuousEvalsRepository
from repositories.llm_evals_repository import LLMEvalsRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import Task, User
from schemas.request_schemas import (
    ContinuousEvalCreateRequest,
    ContinuousEvalListFilterRequest,
    UpdateContinuousEvalRequest,
)
from schemas.response_schemas import ContinuousEvalResponse, ListContinuousEvalsResponse
from utils.users import permission_checker
from utils.utils import common_pagination_parameters

continuous_eval_routes = APIRouter(
    prefix="/api/v1",
    route_class=GenaiEngineRoute,
)


@continuous_eval_routes.get(
    "/continuous_evals/{eval_id}",
    summary="Get a continuous eval by id",
    description="Get a continuous eval by id",
    response_model=ContinuousEvalResponse,
    response_model_exclude_none=True,
    tags=["Continuous Evals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_continuous_eval_by_id(
    eval_id: UUID = Path(
        ...,
        description="The id of the continuous eval to retrieve.",
        title="Continuous Eval ID",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> ContinuousEvalResponse:
    try:
        continuous_eval_repo = ContinuousEvalsRepository(db_session)
        continuous_eval = continuous_eval_repo.get_continuous_eval_by_id(
            eval_id=eval_id,
        )
        return continuous_eval.to_response_model()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@continuous_eval_routes.get(
    "/tasks/{task_id}/continuous_evals",
    summary="Get all continuous evals for a specific task",
    description="Get all continuous evals for a specific task",
    response_model=ListContinuousEvalsResponse,
    response_model_exclude_none=True,
    tags=["Continuous Evals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def list_continuous_evals(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    filter_request: Annotated[
        ContinuousEvalListFilterRequest,
        Depends(continuous_eval_list_filter_parameters),
    ],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
) -> ListContinuousEvalsResponse:
    try:
        continuous_eval_repo = ContinuousEvalsRepository(db_session)
        continuous_evals = continuous_eval_repo.list_continuous_evals(
            task.id,
            pagination_parameters,
            filter_request,
        )
        return ListContinuousEvalsResponse(
            evals=[
                continuous_eval.to_response_model()
                for continuous_eval in continuous_evals
            ],
            count=len(continuous_evals),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@continuous_eval_routes.post(
    "/tasks/{task_id}/continuous_evals",
    summary="Create a continuous eval",
    description="Create a continuous eval",
    response_model=ContinuousEvalResponse,
    response_model_exclude_none=True,
    tags=["Continuous Evals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def create_continuous_eval(
    create_request: ContinuousEvalCreateRequest,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
) -> ContinuousEvalResponse:
    try:
        # Validate the llm eval exists and hasn't been deleted
        llm_eval_repo = LLMEvalsRepository(db_session)
        llm_eval_version = (
            str(create_request.llm_eval_version)
            if isinstance(create_request.llm_eval_version, int)
            else create_request.llm_eval_version
        )
        llm_eval = llm_eval_repo.get_llm_item(
            task.id,
            create_request.llm_eval_name,
            llm_eval_version,
        )

        if llm_eval.deleted_at is not None:
            raise HTTPException(
                status_code=400,
                detail=f"LLM Eval {llm_eval.name} (version {llm_eval.version}) has been deleted.",
            )

        # set the version to the integer version of the llm eval
        create_request.llm_eval_version = llm_eval.version

        continuous_eval_repo = ContinuousEvalsRepository(db_session)
        continuous_eval = continuous_eval_repo.create_continuous_eval(
            task.id,
            create_request,
        )
        return continuous_eval.to_response_model()
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@continuous_eval_routes.patch(
    "/continuous_evals/{eval_id}",
    summary="Update a continuous eval",
    description="Update a continuous eval",
    response_model=ContinuousEvalResponse,
    response_model_exclude_none=True,
    tags=["Continuous Evals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def update_continuous_eval(
    update_request: UpdateContinuousEvalRequest,
    eval_id: UUID = Path(
        ...,
        description="The id of the continuous eval to update.",
        title="Continuous Eval ID",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> ContinuousEvalResponse:
    try:
        continuous_eval_repo = ContinuousEvalsRepository(db_session)
        existing_eval = continuous_eval_repo.get_continuous_eval_by_id(eval_id)

        if update_request.llm_eval_version is not None:
            llm_eval_name = existing_eval.llm_eval_name
            if update_request.llm_eval_name is not None:
                llm_eval_name = update_request.llm_eval_name

            # Validate the llm eval exists and hasn't been deleted
            llm_eval_repo = LLMEvalsRepository(db_session)
            llm_eval_version = (
                str(update_request.llm_eval_version)
                if isinstance(update_request.llm_eval_version, int)
                else update_request.llm_eval_version
            )
            llm_eval = llm_eval_repo.get_llm_item(
                existing_eval.task_id,
                llm_eval_name,
                llm_eval_version,
            )

            if llm_eval.deleted_at is not None:
                raise HTTPException(
                    status_code=400,
                    detail=f"LLM Eval {llm_eval.name} (version {llm_eval.version}) has been deleted.",
                )

            # set the version to the integer version of the llm eval
            update_request.llm_eval_version = llm_eval.version

        continuous_eval = continuous_eval_repo.update_continuous_eval(
            eval_id,
            update_request,
        )
        return continuous_eval.to_response_model()
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@continuous_eval_routes.delete(
    "/continuous_evals/{eval_id}",
    summary="Delete a continuous eval",
    description="Delete a continuous eval",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_204_NO_CONTENT: {"description": "Continuous eval deleted."},
    },
    tags=["Continuous Evals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def delete_continuous_eval(
    eval_id: UUID = Path(
        ...,
        description="The id of the continuous eval to delete.",
        title="Continuous Eval ID",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> None:
    try:
        continuous_eval_repo = ContinuousEvalsRepository(db_session)
        continuous_eval_repo.delete_continuous_eval(eval_id)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
