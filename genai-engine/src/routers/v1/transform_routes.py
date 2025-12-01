from typing import Annotated
from uuid import UUID

from arthur_common.models.common_schemas import PaginationParameters
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from starlette.responses import Response
from starlette.status import HTTP_204_NO_CONTENT

from dependencies import (
    get_db_session,
    get_validated_agentic_task,
    transform_list_filter_parameters,
)
from repositories.trace_transform_repository import TraceTransformRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import Task, User
from schemas.request_schemas import (
    NewTraceTransformRequest,
    TraceTransformUpdateRequest,
    TransformListFilterRequest,
)
from schemas.response_schemas import ListTraceTransformsResponse, TraceTransformResponse
from utils.users import permission_checker
from utils.utils import common_pagination_parameters

transform_routes = APIRouter(
    prefix="/api/v1",
    route_class=GenaiEngineRoute,
)


@transform_routes.get(
    "/tasks/{task_id}/transforms",
    description="List all transforms for a task.",
    response_model=ListTraceTransformsResponse,
    tags=["Transforms"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def list_transforms_for_task(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    filter_request: Annotated[
        TransformListFilterRequest,
        Depends(transform_list_filter_parameters),
    ],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
) -> ListTraceTransformsResponse:
    try:
        trace_transform_repo = TraceTransformRepository(db_session)
        transforms = trace_transform_repo.list_transforms(
            task.id,
            pagination_parameters,
            filter_request,
        )
        return ListTraceTransformsResponse(
            transforms=[transform.to_response_model() for transform in transforms],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@transform_routes.get(
    "/tasks/{task_id}/transforms/{transform_id}",
    description="Get a specific transform.",
    response_model=TraceTransformResponse,
    tags=["Transforms"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_transform(
    transform_id: UUID = Path(description="ID of the transform to fetch."),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
) -> TraceTransformResponse:
    try:
        trace_transform_repo = TraceTransformRepository(db_session)
        trace_transform = trace_transform_repo.get_transform_by_id(
            task.id,
            transform_id,
        )
        return trace_transform.to_response_model()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@transform_routes.post(
    "/tasks/{task_id}/transforms",
    description="Create a new transform for a task.",
    response_model=TraceTransformResponse,
    tags=["Transforms"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def create_transform_for_task(
    request: NewTraceTransformRequest,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
) -> TraceTransformResponse:
    try:
        trace_transform_repo = TraceTransformRepository(db_session)
        trace_transform = trace_transform_repo.create_transform(task.id, request)
        return trace_transform.to_response_model()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@transform_routes.patch(
    "/tasks/{task_id}/transforms/{transform_id}",
    description="Update a transform.",
    response_model=TraceTransformResponse,
    tags=["Transforms"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def update_transform(
    request: TraceTransformUpdateRequest,
    transform_id: UUID = Path(description="ID of the transform to update."),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
) -> TraceTransformResponse:
    try:
        trace_transform_repo = TraceTransformRepository(db_session)
        trace_transform = trace_transform_repo.update_transform(
            task.id,
            transform_id,
            request,
        )
        return trace_transform.to_response_model()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@transform_routes.delete(
    "/tasks/{task_id}/transforms/{transform_id}",
    description="Delete a transform.",
    tags=["Transforms"],
    status_code=HTTP_204_NO_CONTENT,
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def delete_transform(
    transform_id: UUID = Path(description="ID of the transform to delete."),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
) -> Response:
    try:
        trace_transform_repo = TraceTransformRepository(db_session)
        trace_transform_repo.delete_transform(task.id, transform_id)
        return Response(status_code=HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
