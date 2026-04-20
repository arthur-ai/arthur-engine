"""v1 LLM eval routes — thin aliases over the v2 eval handlers.

All logic lives in routers.v2.eval_routes; these endpoints preserve the v1
URL shape (/llm_evals/…) and response types (LLMEval, LLMEvalsVersionListResponse)
expected by existing clients.
"""

from typing import Annotated

import jinja2
from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.task_eval_schemas import LLMEval
from fastapi import APIRouter, Body, Depends, HTTPException, Path, Response, status
from pydantic import AfterValidator
from sqlalchemy.orm import Session

from dependencies import (
    get_db_session,
    get_validated_task,
    llm_get_all_filter_parameters,
    llm_get_versions_filter_parameters,
)
from repositories.llm_evals_repository import LLMEvalsRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import Task, User
from schemas.request_schemas import (
    BaseCompletionRequest,
    CreateEvalRequest,
    LLMGetAllFilterRequest,
    LLMGetVersionsFilterRequest,
)
from schemas.response_schemas import (
    LLMEvalRunResponse,
    LLMEvalsVersionListResponse,
    LLMGetAllMetadataListResponse,
)
from utils.url_encoding import decode_path_param
from utils.users import permission_checker
from utils.utils import common_pagination_parameters

llm_eval_routes = APIRouter(
    prefix="/api/v1",
    route_class=GenaiEngineRoute,
)


def _repo(db_session: Session) -> LLMEvalsRepository:
    return LLMEvalsRepository(db_session)


@llm_eval_routes.get(
    "/tasks/{task_id}/llm_evals/{eval_name}/versions/{eval_version}",
    summary="Get an llm eval",
    description="Get an llm eval by name and version",
    response_model=LLMEval,
    response_model_exclude_none=True,
    tags=["LLMEvals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_llm_eval(
    eval_name: Annotated[str, Path(), AfterValidator(decode_path_param)],
    eval_version: str = Path(
        ...,
        description="'latest', version number, ISO datetime, or tag.",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> LLMEval:
    try:
        return _repo(db_session).get_llm_item(task.id, eval_name, eval_version)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@llm_eval_routes.get(
    "/tasks/{task_id}/llm_evals/{eval_name}/versions",
    summary="List all versions of an llm eval",
    description="List all versions of an llm eval with optional filtering.",
    response_model=LLMEvalsVersionListResponse,
    response_model_exclude_none=True,
    tags=["LLMEvals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_all_llm_eval_versions(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    filter_request: Annotated[
        LLMGetVersionsFilterRequest,
        Depends(llm_get_versions_filter_parameters),
    ],
    eval_name: Annotated[str, Path(), AfterValidator(decode_path_param)],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> LLMEvalsVersionListResponse:
    try:
        result = _repo(db_session).get_llm_item_versions(
            task.id,
            eval_name,
            pagination_parameters,
            filter_request,
        )
        assert isinstance(result, LLMEvalsVersionListResponse)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@llm_eval_routes.get(
    "/tasks/{task_id}/llm_evals",
    summary="Get all llm evals",
    description="Get all llm evals for a given task with optional filtering.",
    response_model=LLMGetAllMetadataListResponse,
    response_model_exclude_none=True,
    tags=["LLMEvals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_all_llm_evals(
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
) -> LLMGetAllMetadataListResponse:
    try:
        return _repo(db_session).get_all_llm_item_metadata(
            task.id,
            pagination_parameters,
            filter_request,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@llm_eval_routes.post(
    "/tasks/{task_id}/llm_evals/{eval_name}/versions/{eval_version}/completions",
    summary="Run a saved llm eval",
    response_model=LLMEvalRunResponse,
    response_model_exclude_none=True,
    tags=["LLMEvals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def run_saved_llm_eval(
    completion_request: BaseCompletionRequest,
    eval_name: Annotated[str, Path(), AfterValidator(decode_path_param)],
    eval_version: str = Path(...),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> LLMEvalRunResponse:
    try:
        return _repo(db_session).run_llm_eval(
            task.id,
            eval_name,
            eval_version,
            completion_request,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@llm_eval_routes.post(
    "/tasks/{task_id}/llm_evals/{eval_name}",
    summary="Save an llm eval",
    description="Save an llm eval to the database",
    response_model=LLMEval,
    response_model_exclude_none=True,
    tags=["LLMEvals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def save_llm_eval(
    eval_config: CreateEvalRequest,
    eval_name: Annotated[str, Path(), AfterValidator(decode_path_param)],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> LLMEval:
    try:
        return _repo(db_session).save_llm_item(task.id, eval_name, eval_config)
    except jinja2.exceptions.TemplateSyntaxError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Jinja2 template syntax in evaluator messages: {e}",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@llm_eval_routes.delete(
    "/tasks/{task_id}/llm_evals/{eval_name}",
    summary="Delete an llm eval",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_204_NO_CONTENT: {"description": "LLM eval deleted."}},
    tags=["LLMEvals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def delete_llm_eval(
    eval_name: Annotated[str, Path(), AfterValidator(decode_path_param)],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> Response:
    try:
        _repo(db_session).delete_llm_item(task.id, eval_name)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@llm_eval_routes.delete(
    "/tasks/{task_id}/llm_evals/{eval_name}/versions/{eval_version}",
    summary="Delete an llm eval version",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_204_NO_CONTENT: {"description": "LLM eval version deleted."},
    },
    tags=["LLMEvals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def soft_delete_llm_eval_version(
    eval_name: Annotated[str, Path(), AfterValidator(decode_path_param)],
    eval_version: str = Path(...),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> Response:
    try:
        _repo(db_session).soft_delete_llm_item_version(task.id, eval_name, eval_version)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        if "no matching version" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@llm_eval_routes.get(
    "/tasks/{task_id}/llm_evals/{eval_name}/versions/tags/{tag}",
    summary="Get an llm eval by name and tag",
    response_model=LLMEval,
    response_model_exclude_none=True,
    tags=["LLMEvals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_llm_eval_by_tag(
    eval_name: Annotated[str, Path(), AfterValidator(decode_path_param)],
    tag: Annotated[str, Path(), AfterValidator(decode_path_param)],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> LLMEval:
    try:
        result = _repo(db_session).get_llm_item_by_tag(task.id, eval_name, tag)
        assert isinstance(result, LLMEval)
        return result
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        elif "deleted version" in str(e).lower():
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@llm_eval_routes.put(
    "/tasks/{task_id}/llm_evals/{eval_name}/versions/{eval_version}/tags",
    summary="Add a tag to an llm eval version",
    response_model=LLMEval,
    response_model_exclude_none=True,
    tags=["LLMEvals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def add_tag_to_llm_eval_version(
    eval_name: Annotated[str, Path(), AfterValidator(decode_path_param)],
    eval_version: str = Path(...),
    tag: str = Body(..., embed=True, description="Tag to add to this llm eval version"),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> LLMEval:
    try:
        repo = _repo(db_session)
        repo.add_tag_to_llm_item_version(task.id, eval_name, eval_version, tag)
        return repo.get_llm_item(task.id, eval_name, eval_version)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        elif "deleted version" in str(e).lower():
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@llm_eval_routes.delete(
    "/tasks/{task_id}/llm_evals/{eval_name}/versions/{eval_version}/tags/{tag}",
    summary="Remove a tag from an llm eval version",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_204_NO_CONTENT: {"description": "Tag removed."}},
    tags=["LLMEvals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def delete_tag_from_llm_eval_version(
    eval_name: Annotated[str, Path(), AfterValidator(decode_path_param)],
    eval_version: Annotated[str, Path()],
    tag: Annotated[str, Path(), AfterValidator(decode_path_param)],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> None:
    try:
        _repo(db_session).delete_llm_item_tag_from_version(
            task.id,
            eval_name,
            eval_version,
            tag,
        )
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
