from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy.orm import Session

from dependencies import get_db_session, get_validated_agentic_task
from repositories.llm_evals_repository import LLMEvalsRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import Task, User
from schemas.llm_eval_schemas import LLMEval
from schemas.request_schemas import CreateEvalRequest
from utils.users import permission_checker

llm_eval_routes = APIRouter(
    prefix="/api/v1",
    route_class=GenaiEngineRoute,
)


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
        return llm_eval_service.save_eval(task.id, eval_name, eval_config)
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
        llm_eval_service.delete_eval(task.id, eval_name)
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
        llm_eval_service.soft_delete_eval_version(
            task.id,
            eval_name,
            eval_version,
        )

        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
