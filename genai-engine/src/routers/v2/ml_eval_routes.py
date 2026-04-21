"""Dedicated ML eval CRUD routes under /api/v2/tasks/{task_id}/ml_evals/.

These routes provide the same functionality as the unified /evals endpoints but
are scoped to ML eval types only and return ML-specific response shapes that the
frontend API client expects.
"""

from typing import Annotated

from arthur_common.models.common_schemas import PaginationParameters
from fastapi import APIRouter, Depends, Path, Response, status
from pydantic import AfterValidator
from sqlalchemy.orm import Session

from dependencies import (
    get_db_session,
    get_validated_task,
    llm_get_versions_filter_parameters,
)
from repositories.ml_evals_repository import MLEvalsRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import Task, User
from schemas.llm_eval_schemas import MLEval
from schemas.request_schemas import (
    CreateMLEvalRequest,
    LLMGetVersionsFilterRequest,
)
from schemas.response_schemas import MLEvalsVersionListResponse
from utils.url_encoding import decode_path_param
from utils.users import permission_checker
from utils.utils import common_pagination_parameters

ml_eval_routes = APIRouter(
    prefix="/api/v2",
    route_class=GenaiEngineRoute,
)


# ---------------------------------------------------------------------------
# GET /tasks/{task_id}/ml_evals — list all ML evals
# ---------------------------------------------------------------------------


@ml_eval_routes.get(
    "/tasks/{task_id}/ml_evals",
    summary="Get all ML evaluators",
    description="Return metadata for every ML evaluator associated with a task.",
    response_model_exclude_none=True,
    tags=["ML Evals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_all_ml_evals(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> dict:
    try:
        repo = MLEvalsRepository(db_session)
        result = repo.get_all_llm_item_metadata(task.id, pagination_parameters)
        return result.model_dump()
    except Exception as e:
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# POST /tasks/{task_id}/ml_evals/{eval_name} — create / version an ML eval
# ---------------------------------------------------------------------------


@ml_eval_routes.post(
    "/tasks/{task_id}/ml_evals/{eval_name}",
    summary="Save an ML eval",
    description="Save an ML eval. If an eval with the same name exists, a new version is created.",
    response_model=MLEval,
    response_model_exclude_none=True,
    tags=["ML Evals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def save_ml_eval(
    create_request: CreateMLEvalRequest,
    eval_name: Annotated[str, Path(), AfterValidator(decode_path_param)],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> MLEval:
    try:
        repo = MLEvalsRepository(db_session)
        return repo.save_ml_eval(task.id, eval_name, create_request)
    except ValueError as e:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# GET /tasks/{task_id}/ml_evals/{eval_name}/versions/{eval_version}
# ---------------------------------------------------------------------------


@ml_eval_routes.get(
    "/tasks/{task_id}/ml_evals/{eval_name}/versions/{eval_version}",
    summary="Get an ML eval by version",
    description="Get a specific version of an ML eval. Supports 'latest', version number, datetime, or tag.",
    response_model=MLEval,
    response_model_exclude_none=True,
    tags=["ML Evals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_ml_eval(
    eval_name: Annotated[str, Path(), AfterValidator(decode_path_param)],
    eval_version: str = Path(
        ...,
        description="Version: 'latest', a number, ISO datetime, or tag.",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> MLEval:
    try:
        repo = MLEvalsRepository(db_session)
        return repo.get_ml_eval(task.id, eval_name, eval_version)
    except ValueError as e:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 400,
            detail=str(e),
        )
    except Exception as e:
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# GET /tasks/{task_id}/ml_evals/{eval_name}/versions
# ---------------------------------------------------------------------------


@ml_eval_routes.get(
    "/tasks/{task_id}/ml_evals/{eval_name}/versions",
    summary="List versions of an ML eval",
    description="List all versions of an ML eval with optional filtering.",
    response_model=MLEvalsVersionListResponse,
    response_model_exclude_none=True,
    tags=["ML Evals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def list_ml_eval_versions(
    eval_name: Annotated[str, Path(), AfterValidator(decode_path_param)],
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    filter_request: Annotated[
        LLMGetVersionsFilterRequest,
        Depends(llm_get_versions_filter_parameters),
    ],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> MLEvalsVersionListResponse:
    try:
        repo = MLEvalsRepository(db_session)
        return repo.get_ml_eval_versions(
            task.id,
            eval_name,
            pagination_parameters,
            filter_request,
        )
    except ValueError as e:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# DELETE /tasks/{task_id}/ml_evals/{eval_name} — hard delete all versions
# ---------------------------------------------------------------------------


@ml_eval_routes.delete(
    "/tasks/{task_id}/ml_evals/{eval_name}",
    summary="Delete an ML eval",
    description="Hard-delete all versions of an ML eval.",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["ML Evals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def delete_ml_eval(
    eval_name: Annotated[str, Path(), AfterValidator(decode_path_param)],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> Response:
    try:
        repo = MLEvalsRepository(db_session)
        repo.delete_all_versions(task.id, eval_name)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404 if "not found" in str(e).lower() else 400,
            detail=str(e),
        )
    except Exception as e:
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# DELETE /tasks/{task_id}/ml_evals/{eval_name}/versions/{eval_version} — soft delete
# ---------------------------------------------------------------------------


@ml_eval_routes.delete(
    "/tasks/{task_id}/ml_evals/{eval_name}/versions/{eval_version}",
    summary="Soft-delete an ML eval version",
    description="Soft-delete a specific version of an ML eval.",
    response_model=MLEval,
    response_model_exclude_none=True,
    tags=["ML Evals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def delete_ml_eval_version(
    eval_name: Annotated[str, Path(), AfterValidator(decode_path_param)],
    eval_version: str = Path(..., description="Version to soft-delete."),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> MLEval:
    try:
        repo = MLEvalsRepository(db_session)
        return repo.delete_version(task.id, eval_name, eval_version)
    except ValueError as e:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404 if "no matching version" in str(e).lower() else 400,
            detail=str(e),
        )
    except Exception as e:
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail=str(e))
