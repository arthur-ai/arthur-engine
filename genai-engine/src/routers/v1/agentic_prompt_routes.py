from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from dependencies import get_application_config, get_db_session
from repositories.agentic_prompts_repository import (
    AgenticPrompt,
    AgenticPromptRepository,
    AgenticPromptRunResponse,
    AgenticPrompts,
)
from repositories.metrics_repository import MetricRepository
from repositories.rules_repository import RuleRepository
from repositories.tasks_repository import TaskRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import ApplicationConfiguration, Task, User
from utils.users import permission_checker

agentic_prompt_routes = APIRouter(
    prefix="/v1",
    route_class=GenaiEngineRoute,
)


def get_task_repository(
    db_session: Session,
    application_config: ApplicationConfiguration,
) -> TaskRepository:
    return TaskRepository(
        db_session,
        RuleRepository(db_session),
        MetricRepository(db_session),
        application_config,
    )


def get_validated_agentic_task(
    task_id: UUID,
    db_session: Session = Depends(get_db_session),
    application_config: ApplicationConfiguration = Depends(get_application_config),
) -> Task:
    """Dependency that validates task exists and is agentic"""
    task_repo = get_task_repository(db_session, application_config)
    task = task_repo.get_task_by_id(str(task_id))

    if not task.is_agentic:
        raise HTTPException(status_code=400, detail="Task is not agentic")

    return task


@agentic_prompt_routes.get(
    "/{task_id}/agentic_prompt/get_prompt/{prompt_name}",
    summary="Get an agentic prompt",
    description="Get an agentic prompt",
    response_model=AgenticPrompt,
    response_model_exclude_none=True,
    tags=["AgenticPrompt"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_agentic_prompt(
    prompt_name: str,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
):
    try:
        agentic_prompt_service = AgenticPromptRepository(db_session)
        prompt = agentic_prompt_service.get_prompt(task.id, prompt_name)
        return prompt
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@agentic_prompt_routes.get(
    "/{task_id}/agentic_prompt/get_all_prompts",
    summary="Get all agentic prompts",
    description="Get all agentic prompts for a given task",
    response_model=AgenticPrompts,
    response_model_exclude_none=True,
    tags=["AgenticPrompt"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_all_agentic_prompts(
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
):
    try:
        agentic_prompt_service = AgenticPromptRepository(db_session)
        return agentic_prompt_service.get_all_prompts(task.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@agentic_prompt_routes.post(
    "/{task_id}/agentic_prompt/run_prompt",
    summary="Run an agentic prompt",
    description="Run an agentic prompt",
    response_model=AgenticPromptRunResponse,
    response_model_exclude_none=True,
    tags=["AgenticPrompt"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def run_agentic_prompt(
    prompt_body: Dict[str, Any] = Body(...),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
):
    try:
        agentic_prompt_service = AgenticPromptRepository(db_session)
        prompt = agentic_prompt_service.create_prompt(**prompt_body)
        return agentic_prompt_service.run_prompt(prompt)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@agentic_prompt_routes.post(
    "/{task_id}/agentic_prompt/run_prompt/{prompt_name}",
    summary="Run an existing agentic prompt",
    description="Run an existing agentic prompt",
    response_model=AgenticPromptRunResponse,
    response_model_exclude_none=True,
    tags=["AgenticPrompt"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def run_saved_agentic_prompt(
    prompt_name: str,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
):
    try:
        agentic_prompt_service = AgenticPromptRepository(db_session)
        return agentic_prompt_service.run_saved_prompt(task.id, prompt_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@agentic_prompt_routes.post(
    "/{task_id}/agentic_prompt/save_prompt",
    summary="Save an agentic prompt",
    description="Save an agentic prompt to the database",
    response_model=None,
    response_model_exclude_none=True,
    tags=["AgenticPrompt"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def save_agentic_prompt(
    prompt_body: Dict[str, Any] = Body(...),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
):
    try:
        agentic_prompt_service = AgenticPromptRepository(db_session)
        agentic_prompt_service.save_prompt(task.id, prompt_body)

        return {"message": "Prompt saved successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@agentic_prompt_routes.post(
    "/{task_id}/agentic_prompt/update_prompt",
    summary="Update an existing agentic prompt",
    description="Updates an existing agentic prompt",
    response_model=None,
    response_model_exclude_none=True,
    tags=["AgenticPrompt"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def update_agentic_prompt(
    prompt_body: Dict[str, Any] = Body(...),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
):
    try:
        agentic_prompt_service = AgenticPromptRepository(db_session)
        agentic_prompt_service.update_prompt(task.id, prompt_body)

        return {"message": "Prompt updated successfully"}
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@agentic_prompt_routes.delete(
    "/{task_id}/agentic_prompt/delete_prompt/{prompt_name}",
    summary="Delete an agentic prompt",
    description="Deletes an agentic prompt",
    response_model=None,
    response_model_exclude_none=True,
    tags=["AgenticPrompt"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def delete_agentic_prompt(
    prompt_name: str,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
):
    try:
        agentic_prompt_service = AgenticPromptRepository(db_session)
        agentic_prompt_service.delete_prompt(task.id, prompt_name)

        return {"message": "Prompt deleted successfully"}
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
