from typing import Annotated

from arthur_common.models.task_eval_schemas import MLEval
from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import AfterValidator
from sqlalchemy.orm import Session

from dependencies import get_db_session, get_validated_task
from repositories.ml_evals_repository import MLEvalsRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import Task, User
from db_models.llm_eval_models import ML_EVAL_INPUT_VARIABLE
from schemas.request_schemas import CreateMLEvalRequest, RunMLEvalRequest
from schemas.response_schemas import (
    EvalRunResponse,
    MLEvalsVersionListResponse,
    MLGetAllMetadataListResponse,
)
from utils.url_encoding import decode_path_param
from utils.users import permission_checker

ml_eval_routes = APIRouter(
    prefix="/api/v2",
    route_class=GenaiEngineRoute,
)


@ml_eval_routes.post(
    "/tasks/{task_id}/ml_evals/{eval_name}",
    summary="Save an ML eval",
    description="Create a new version of an ML eval for a given task.",
    response_model=MLEval,
    response_model_exclude_none=True,
    tags=["MLEvals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def save_ml_eval(
    eval_config: CreateMLEvalRequest,
    eval_name: Annotated[str, Path(), AfterValidator(decode_path_param)],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> MLEval:
    try:
        repo = MLEvalsRepository(db_session)
        return repo.save_ml_eval(task.id, eval_name, eval_config)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@ml_eval_routes.get(
    "/tasks/{task_id}/ml_evals/{eval_name}/versions/{eval_version}",
    summary="Get an ML eval",
    description="Get a specific version of an ML eval by name and version.",
    response_model=MLEval,
    response_model_exclude_none=True,
    tags=["MLEvals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_ml_eval(
    eval_name: Annotated[str, Path(), AfterValidator(decode_path_param)],
    eval_version: str = Path(
        ...,
        description="The version of the ML eval to retrieve. Can be 'latest', a version number, or a tag.",
        title="ML Eval Version",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> MLEval:
    try:
        repo = MLEvalsRepository(db_session)
        return repo.get_ml_eval(task.id, eval_name, eval_version)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@ml_eval_routes.get(
    "/tasks/{task_id}/ml_evals/{eval_name}/versions",
    summary="List all versions of an ML eval",
    description="List all versions of an ML eval.",
    response_model=MLEvalsVersionListResponse,
    response_model_exclude_none=True,
    tags=["MLEvals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def list_ml_eval_versions(
    eval_name: Annotated[str, Path(), AfterValidator(decode_path_param)],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> MLEvalsVersionListResponse:
    try:
        repo = MLEvalsRepository(db_session)
        return repo.list_versions(task.id, eval_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@ml_eval_routes.get(
    "/tasks/{task_id}/ml_evals",
    summary="Get all ML evals",
    description="Get metadata for all ML evals associated with a task.",
    response_model=MLGetAllMetadataListResponse,
    response_model_exclude_none=True,
    tags=["MLEvals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_all_ml_evals(
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> MLGetAllMetadataListResponse:
    try:
        repo = MLEvalsRepository(db_session)
        return repo.get_all_metadata(task.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@ml_eval_routes.delete(
    "/tasks/{task_id}/ml_evals/{eval_name}",
    summary="Delete all versions of an ML eval",
    description="Hard-delete all versions of an ML eval by name.",
    status_code=204,
    tags=["MLEvals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def delete_ml_eval(
    eval_name: Annotated[str, Path(), AfterValidator(decode_path_param)],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> None:
    try:
        repo = MLEvalsRepository(db_session)
        repo.delete_all_versions(task.id, eval_name)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@ml_eval_routes.delete(
    "/tasks/{task_id}/ml_evals/{eval_name}/versions/{eval_version}",
    summary="Delete an ML eval version",
    description="Soft-delete a specific version of an ML eval.",
    response_model=MLEval,
    response_model_exclude_none=True,
    tags=["MLEvals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def delete_ml_eval_version(
    eval_name: Annotated[str, Path(), AfterValidator(decode_path_param)],
    eval_version: str = Path(
        ...,
        description="The version of the ML eval to delete. Can be 'latest' or a version number.",
        title="ML Eval Version",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> MLEval:
    try:
        repo = MLEvalsRepository(db_session)
        return repo.delete_version(task.id, eval_name, eval_version)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@ml_eval_routes.post(
    "/tasks/{task_id}/ml_evals/{eval_name}/versions/{eval_version}/run",
    summary="Run an ML eval",
    description="Run a saved ML eval with provided input text.",
    response_model=EvalRunResponse,
    response_model_exclude_none=True,
    tags=["MLEvals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def run_ml_eval(
    run_request: RunMLEvalRequest,
    eval_name: Annotated[str, Path(), AfterValidator(decode_path_param)],
    eval_version: str = Path(
        ...,
        description="The version of the ML eval to run. Can be 'latest' or a version number.",
        title="ML Eval Version",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> EvalRunResponse:
    """Run an ML eval with provided variables.

    Request body: {"text": "Hello, my name is John and my SSN is 123-45-6789"}
    """
    try:
        from repositories.ml_evals_repository import MLEvaluator

        evaluator = MLEvaluator(db_session)
        resolved_variables = {ML_EVAL_INPUT_VARIABLE: run_request.text}
        return evaluator.run(
            task_id=task.id,
            eval_name=eval_name,
            eval_version=eval_version,
            variable_mapping=[],
            resolved_variables=resolved_variables,
        )
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
