from typing import Annotated

import jinja2
from arthur_common.models.common_schemas import PaginationParameters
from fastapi import APIRouter, Body, Depends, HTTPException, Path, Response, status
from sqlalchemy.orm import Session

from dependencies import (
    get_db_session,
    get_validated_agentic_task,
    llm_get_all_filter_parameters,
    llm_get_versions_filter_parameters,
)
from repositories.llm_evals_repository import LLMEvalsRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import Task, User
from schemas.llm_eval_schemas import LLMEval
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
from utils.users import permission_checker
from utils.utils import common_pagination_parameters

llm_eval_routes = APIRouter(
    prefix="/api/v1",
    route_class=GenaiEngineRoute,
)


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
    eval_name: str = Path(
        ...,
        description="The name of the llm eval to retrieve.",
        title="LLM Eval Name",
    ),
    eval_version: str = Path(
        ...,
        description="The version of the llm eval to retrieve. Can be 'latest', a version number (e.g. '1', '2', etc.), or an ISO datetime string (e.g. '2025-01-01T00:00:00').",
        title="LLM Eval Version",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
):
    try:
        llm_eval_service = LLMEvalsRepository(db_session)
        llm_eval = llm_eval_service.get_llm_item(
            task.id,
            eval_name,
            eval_version,
        )
        return llm_eval
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
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
    eval_name: str = Path(
        ...,
        description="The name of the llm eval to retrieve.",
        title="LLM Eval Name",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
):
    try:

        llm_eval_service = LLMEvalsRepository(db_session)
        return llm_eval_service.get_llm_item_versions(
            task.id,
            eval_name,
            pagination_parameters,
            filter_request,
        )
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
    task: Task = Depends(get_validated_agentic_task),
):
    try:
        llm_eval_service = LLMEvalsRepository(db_session)
        return llm_eval_service.get_all_llm_item_metadata(
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
    description="Run a saved llm eval",
    response_model=LLMEvalRunResponse,
    response_model_exclude_none=True,
    tags=["LLMEvals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def run_saved_llm_eval(
    completion_request: BaseCompletionRequest,
    eval_name: str = Path(
        ...,
        description="The name of the llm eval to run.",
        title="LLM Eval Name",
    ),
    eval_version: str = Path(
        ...,
        description="The version of the llm eval to run. Can be 'latest', a version number (e.g. '1', '2', etc.), or an ISO datetime string (e.g. '2025-01-01T00:00:00').",
        title="LLM Eval Version",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
):
    try:
        llm_eval_service = LLMEvalsRepository(db_session)
        return llm_eval_service.run_llm_eval(
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
    eval_name: str = Path(
        ...,
        description="The name of the llm eval to save.",
        title="LLM Eval Name",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
):
    try:
        llm_eval_service = LLMEvalsRepository(db_session)
        return llm_eval_service.save_llm_item(task.id, eval_name, eval_config)
    except jinja2.exceptions.TemplateSyntaxError as e:
        # Handle Jinja2 template syntax errors with a helpful message
        error_msg = f"Invalid Jinja2 template syntax in evaluator messages: {str(e)}"
        raise HTTPException(status_code=400, detail=error_msg)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@llm_eval_routes.delete(
    "/tasks/{task_id}/llm_evals/{eval_name}",
    summary="Delete an llm eval",
    description="Deletes an entire llm eval",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_204_NO_CONTENT: {"description": "LLM eval deleted."}},
    tags=["LLMEvals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def delete_llm_eval(
    eval_name: str = Path(
        ...,
        description="The name of the llm eval to delete.",
        title="LLM Eval Name",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
) -> Response:
    try:
        llm_eval_service = LLMEvalsRepository(db_session)
        llm_eval_service.delete_llm_item(task.id, eval_name)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@llm_eval_routes.delete(
    "/tasks/{task_id}/llm_evals/{eval_name}/versions/{eval_version}",
    summary="Delete an llm eval version",
    description="Deletes a specific version of an llm eval",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_204_NO_CONTENT: {"description": "LLM eval version deleted."},
    },
    tags=["LLMEvals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def soft_delete_llm_eval_version(
    eval_name: str = Path(
        ...,
        description="The name of the llm eval to delete.",
        title="LLM Eval Name",
    ),
    eval_version: str = Path(
        ...,
        description="The version of the llm eval to delete. Can be 'latest', a version number (e.g. '1', '2', etc.), or an ISO datetime string (e.g. '2025-01-01T00:00:00').",
        title="LLM Eval Version",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
) -> Response:
    try:
        llm_eval_service = LLMEvalsRepository(db_session)
        llm_eval_service.soft_delete_llm_item_version(
            task.id,
            eval_name,
            eval_version,
        )

        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        if "no matching version" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@llm_eval_routes.get(
    "/tasks/{task_id}/llm_evals/{eval_name}/versions/tags/{tag}",
    summary="Get an llm eval by name and tag",
    description="Get an llm eval by name and tag",
    response_model=LLMEval,
    response_model_exclude_none=True,
    tags=["LLMEvals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_llm_eval_by_tag(
    eval_name: str = Path(
        ...,
        description="The name of the llm eval to retrieve.",
        title="LLM Eval Name",
    ),
    tag: str = Path(
        ...,
        description="The tag of the llm eval to retrieve.",
        title="Tag",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
) -> LLMEval:
    try:
        llm_eval_service = LLMEvalsRepository(db_session)
        return llm_eval_service.get_llm_item_by_tag(
            task.id,
            eval_name,
            tag,
        )
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        elif "deleted version" in str(e).lower():
            raise HTTPException(status_code=409, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@llm_eval_routes.put(
    "/tasks/{task_id}/llm_evals/{eval_name}/versions/{eval_version}/tags",
    summary="Add a tag to an llm eval version",
    description="Add a tag to an llm eval version",
    response_model=LLMEval,
    response_model_exclude_none=True,
    tags=["LLMEvals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def add_tag_to_llm_eval_version(
    eval_name: str = Path(
        ...,
        description="The name of the llm eval to retrieve.",
        title="LLM Eval Name",
    ),
    eval_version: str = Path(
        ...,
        description="The version of the llm eval to retrieve. Can be 'latest', a version number (e.g. '1', '2', etc.), or an ISO datetime string (e.g. '2025-01-01T00:00:00').",
        title="LLM Eval Version",
    ),
    tag: str = Body(..., embed=True, description="Tag to add to this llm eval version"),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
) -> LLMEval:
    try:
        llm_eval_service = LLMEvalsRepository(db_session)
        return llm_eval_service.add_tag_to_llm_item_version(
            task.id,
            eval_name,
            eval_version,
            tag,
        )
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        elif "deleted version" in str(e).lower():
            raise HTTPException(status_code=409, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@llm_eval_routes.delete(
    "/tasks/{task_id}/llm_evals/{eval_name}/versions/{eval_version}/tags/{tag}",
    summary="Remove a tag from an llm eval version",
    description="Remove a tag from an llm eval version",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_204_NO_CONTENT: {"description": "LLM eval version deleted."},
    },
    tags=["LLMEvals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def delete_tag_from_llm_eval_version(
    eval_name: str = Path(
        ...,
        description="The name of the llm eval to retrieve.",
        title="LLM Eval Name",
    ),
    eval_version: str = Path(
        ...,
        description="The version of the llm eval to retrieve. Can be 'latest', a version number (e.g. '1', '2', etc.), or an ISO datetime string (e.g. '2025-01-01T00:00:00').",
        title="LLM Eval Version",
    ),
    tag: str = Path(
        ...,
        description="The tag to remove from the llm eval version.",
        title="Tag",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
) -> None:
    try:
        llm_eval_service = LLMEvalsRepository(db_session)
        llm_eval_service.delete_llm_item_tag_from_version(
            task.id,
            eval_name,
            eval_version,
            tag,
        )
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
