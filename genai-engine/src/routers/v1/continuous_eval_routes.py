from datetime import datetime, timedelta
from typing import Annotated, Optional
from uuid import UUID

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.response_schemas import ListAgenticAnnotationsResponse
from arthur_common.models.task_eval_schemas import (
    ContinuousEvalResponse,
    ContinuousEvalVariableMappingResponse,
    ListContinuousEvalsResponse,
)
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import AfterValidator
from sqlalchemy.orm import Session

from dependencies import (
    get_db_session,
    get_validated_task,
)
from repositories.continuous_evals_repository import ContinuousEvalsRepository
from repositories.llm_evals_repository import LLMEvalsRepository
from repositories.trace_transform_repository import TraceTransformRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import Task, User
from schemas.request_schemas import (
    ContinuousEvalCreateRequest,
    ContinuousEvalListFilterRequest,
    ContinuousEvalRunResultsListFilterRequest,
    UpdateContinuousEvalRequest,
)
from schemas.response_schemas import (
    AgenticAnnotationAnalyticsResponse,
    ContinuousEvalRerunResponse,
)
from utils.url_encoding import decode_path_param
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
        Depends(ContinuousEvalListFilterRequest.from_query_parameters),
    ],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
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


@continuous_eval_routes.get(
    "/tasks/{task_id}/continuous_evals/results",
    summary="Get all continuous eval run results for a specific task",
    description="Get all continuous eval run results for a specific task",
    response_model=ListAgenticAnnotationsResponse,
    response_model_exclude_none=True,
    tags=["Continuous Evals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def list_continuous_eval_run_results(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    filter_request: Annotated[
        ContinuousEvalRunResultsListFilterRequest,
        Depends(ContinuousEvalRunResultsListFilterRequest.from_query_parameters),
    ],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> ListAgenticAnnotationsResponse:
    try:
        continuous_eval_repo = ContinuousEvalsRepository(db_session)
        agentic_annotations = continuous_eval_repo.list_continuous_eval_run_results(
            task.id,
            pagination_parameters,
            filter_request,
        )
        return ListAgenticAnnotationsResponse(
            annotations=[
                annotation.to_response_model() for annotation in agentic_annotations
            ],
            count=len(agentic_annotations),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@continuous_eval_routes.get(
    "/tasks/{task_id}/continuous_evals/transforms/{transform_id}/llm_evals/{eval_name}/versions/{eval_version}/variables",
    summary="Get all variables and mappings for a continuous eval",
    description="Get all variables and mappings for a continuous eval",
    response_model=ContinuousEvalVariableMappingResponse,
    response_model_exclude_none=True,
    tags=["Continuous Evals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_continuous_eval_variables_and_mappings(
    transform_id: Annotated[
        UUID,
        Path(
            description="The id of the transform to get the continuous eval variables and mappings for.",
            title="Transform ID",
        ),
    ],
    eval_name: Annotated[str, Path(), AfterValidator(decode_path_param)],
    eval_version: Annotated[
        str,
        Path(
            description="The version of the llm eval to get the continuous eval variables and mappings for.",
            title="LLM Eval Version",
        ),
    ],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> ContinuousEvalVariableMappingResponse:
    try:
        # Validate the llm eval exists and hasn't been deleted
        llm_eval_repo = LLMEvalsRepository(db_session)
        llm_eval = llm_eval_repo.get_llm_item(
            task.id,
            eval_name,
            eval_version,
        )
        if llm_eval.deleted_at is not None:
            raise HTTPException(
                status_code=400,
                detail=f"LLM Eval {llm_eval.name} (version {llm_eval.version}) has been deleted.",
            )

        # Validate the transform exists and hasn't been deleted
        transform_repo = TraceTransformRepository(db_session)
        transform = transform_repo.get_transform_by_id(transform_id)
        if not transform:
            raise HTTPException(
                status_code=404,
                detail=f"Transform {transform_id} not found.",
            )

        eval_vars = set(llm_eval.variables)
        transform_vars = {v.variable_name for v in transform.definition.variables}
        matching_vars = list(eval_vars & transform_vars)

        return ContinuousEvalVariableMappingResponse(
            matching_variables=matching_vars,
            transform_variables=list(transform_vars),
            eval_variables=list(eval_vars),
        )

    except HTTPException:
        raise
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
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
    task: Task = Depends(get_validated_task),
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

        # Validate the transform variable mapping
        transform_repo = TraceTransformRepository(db_session)
        transform = transform_repo.get_transform_by_id(create_request.transform_id)
        if not transform:
            raise HTTPException(
                status_code=404,
                detail=f"Transform {create_request.transform_id} not found.",
            )

        continuous_eval_repo = ContinuousEvalsRepository(db_session)

        continuous_eval_repo.validate_transform_variable_mapping(
            transform,
            llm_eval,
            create_request.transform_variable_mapping,
        )

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
        llm_eval_repo = LLMEvalsRepository(db_session)
        transform_repo = TraceTransformRepository(db_session)

        existing_eval = continuous_eval_repo.get_continuous_eval_by_id(eval_id)
        llm_eval = None
        llm_eval_version: str | int | None = None

        if update_request.llm_eval_version is not None:
            llm_eval_name = existing_eval.llm_eval_name
            if update_request.llm_eval_name is not None:
                llm_eval_name = update_request.llm_eval_name

            # Validate the llm eval exists and hasn't been deleted
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

        # Validate the transform variable mapping
        if update_request.transform_variable_mapping is not None:
            transform_id = (
                update_request.transform_id
                if update_request.transform_id is not None
                else existing_eval.transform_id
            )
            transform = transform_repo.get_transform_by_id(transform_id)
            if not transform:
                raise HTTPException(
                    status_code=404,
                    detail=f"Transform {transform_id} not found.",
                )

            if llm_eval is None:
                llm_eval_name = (
                    update_request.llm_eval_name
                    if update_request.llm_eval_name is not None
                    else existing_eval.llm_eval_name
                )
                llm_eval_version = (
                    update_request.llm_eval_version
                    if update_request.llm_eval_version is not None
                    else existing_eval.llm_eval_version
                )
                llm_eval = llm_eval_repo.get_llm_item(
                    existing_eval.task_id,
                    llm_eval_name,
                    str(llm_eval_version),
                )
                if llm_eval.deleted_at is not None:
                    raise HTTPException(
                        status_code=400,
                        detail=f"LLM Eval {llm_eval.name} (version {llm_eval.version}) has been deleted.",
                    )

            continuous_eval_repo.validate_transform_variable_mapping(
                transform,
                llm_eval,
                update_request.transform_variable_mapping,
            )

        # Update the continuous eval
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


@continuous_eval_routes.post(
    "/continuous_evals/results/{run_id}/rerun",
    summary="Rerun a failed continuous eval",
    description="Rerun a failed continuous eval",
    response_model=ContinuousEvalRerunResponse,
    response_model_exclude_none=True,
    tags=["Continuous Evals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def rerun_continuous_eval(
    run_id: UUID = Path(
        ...,
        description="The id of the continuous eval run to rerun.",
        title="Run ID",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> ContinuousEvalRerunResponse:
    try:
        continuous_eval_repo = ContinuousEvalsRepository(db_session)
        return continuous_eval_repo.rerun_continuous_eval_by_annotation_id(run_id)
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


@continuous_eval_routes.get(
    "/tasks/{task_id}/continuous_evals/analytics/daily",
    summary="Get daily aggregated analytics for agentic annotations",
    description="Returns daily counts of passed/failed/error/skipped annotations and total cost per day",
    response_model=AgenticAnnotationAnalyticsResponse,
    response_model_exclude_none=True,
    tags=["Continuous Evals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_daily_annotation_analytics(
    start_time: Annotated[
        Optional[datetime],
        Query(description="Start time (inclusive). Defaults to 30 days ago."),
    ] = None,
    end_time: Annotated[
        Optional[datetime],
        Query(description="End time (exclusive). Defaults to now."),
    ] = None,
    db_session: Session = Depends(get_db_session),
    current_user: User = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> AgenticAnnotationAnalyticsResponse:
    try:
        # Set defaults: last 30 days if not provided
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(days=30)

        # Validate time range
        if start_time >= end_time:
            raise HTTPException(
                status_code=400,
                detail="start_time must be before end_time",
            )

        # Get analytics from repository (already returns response models)
        continuous_eval_repo = ContinuousEvalsRepository(db_session)
        stats = continuous_eval_repo.get_daily_annotation_analytics(
            task.id,
            start_time,
            end_time,
        )

        return AgenticAnnotationAnalyticsResponse(
            stats=stats,
            count=len(stats),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
