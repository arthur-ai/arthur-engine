"""ML eval creation route under /api/v2/tasks/{task_id}/ml_evals/.

All read/delete operations are handled by the v1 /llm_evals/ endpoints which
serve all eval types via LLMEvalsRepository.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path
from pydantic import AfterValidator
from sqlalchemy.orm import Session

from dependencies import get_db_session, get_validated_task
from repositories.ml_evals_repository import MLEvalsRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import Task, User
from schemas.llm_eval_schemas import MLEval
from schemas.request_schemas import CreateMLEvalRequest
from utils.url_encoding import decode_path_param
from utils.users import permission_checker

ml_eval_routes = APIRouter(
    prefix="/api/v2",
    route_class=GenaiEngineRoute,
)


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
