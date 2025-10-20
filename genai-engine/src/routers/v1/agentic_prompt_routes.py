from typing import Union
from uuid import UUID

import litellm
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from clients.llm.llm_client import LLMClient
from dependencies import get_application_config, get_db_session
from repositories.agentic_prompts_repository import AgenticPromptRepository
from repositories.metrics_repository import MetricRepository
from repositories.model_provider_repository import ModelProviderRepository
from repositories.rules_repository import RuleRepository
from repositories.tasks_repository import TaskRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.agentic_prompt_schemas import (
    AgenticPrompt,
    AgenticPromptBaseConfig,
    AgenticPrompts,
    CompletionRequest,
    PromptCompletionRequest,
)
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import ApplicationConfiguration, Task, User
from schemas.response_schemas import AgenticPromptNames, AgenticPromptRunResponse
from utils.users import permission_checker

agentic_prompt_routes = APIRouter(
    prefix="/api/v1",
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


async def execute_prompt_completion(
    llm_client: LLMClient,
    prompt: AgenticPrompt,
    completion_request: PromptCompletionRequest,
) -> Union[AgenticPromptRunResponse, StreamingResponse]:
    """Helper to execute prompt completion with or without streaming"""
    if completion_request.stream is None or completion_request.stream == False:
        return prompt.run_chat_completion(llm_client, completion_request)

    return StreamingResponse(
        prompt.stream_chat_completion(llm_client, completion_request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@agentic_prompt_routes.get(
    "/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}",
    summary="Get an agentic prompt",
    description="Get an agentic prompt by name and version",
    response_model=AgenticPrompt,
    response_model_exclude_none=True,
    tags=["AgenticPrompt"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_agentic_prompt(
    prompt_name: str,
    prompt_version: str,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
    include_deleted: bool = Query(
        False,
        description="returns all unique prompt names including soft-deleted prompts",
    ),
):
    try:
        agentic_prompt_service = AgenticPromptRepository(db_session)
        prompt = agentic_prompt_service.get_prompt(
            task.id,
            prompt_name,
            prompt_version,
            include_deleted=include_deleted,
        )
        return prompt
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        elif "attempting to retrieve a deleted prompt" in str(e).lower():
            error_message = (
                str(e) + " Please set include_deleted=True to retrieve this prompt."
            )
            raise HTTPException(status_code=400, detail=error_message)
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@agentic_prompt_routes.get(
    "/{task_id}/agentic_prompts",
    summary="Get all agentic prompts",
    description="Get all agentic prompts for a given task. If include_deleted is true, this will return all existing and soft-deleted prompts.",
    response_model=AgenticPrompts,
    response_model_exclude_none=True,
    tags=["AgenticPrompt"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_all_agentic_prompts(
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
    include_deleted: bool = Query(
        False,
        description="returns all unique prompt names including soft-deleted prompts",
    ),
):
    try:
        agentic_prompt_service = AgenticPromptRepository(db_session)
        return agentic_prompt_service.get_all_prompts(
            task.id,
            include_deleted=include_deleted,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@agentic_prompt_routes.get(
    "/{task_id}/agentic_prompts/names",
    summary="Get all unique agentic prompt names",
    description="Get all unique agentic prompt names for a given task.",
    response_model=AgenticPromptNames,
    response_model_exclude_none=True,
    tags=["AgenticPrompt"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_unique_prompt_names(
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
):
    try:
        agentic_prompt_service = AgenticPromptRepository(db_session)
        return agentic_prompt_service.get_unique_prompt_names(task.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@agentic_prompt_routes.get(
    "/{task_id}/agentic_prompts/{prompt_name}/versions",
    summary="List all versions of an agentic prompt",
    description="List all versions of an agentic prompt",
    response_model=AgenticPrompts,
    response_model_exclude_none=True,
    tags=["AgenticPrompt"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_all_agentic_prompt_versions(
    prompt_name: str,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
    include_deleted: bool = Query(
        False,
        description="returns all unique prompt names including soft-deleted prompts",
    ),
):
    try:
        agentic_prompt_service = AgenticPromptRepository(db_session)
        return agentic_prompt_service.get_prompt_versions(
            task.id,
            prompt_name,
            include_deleted=include_deleted,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@agentic_prompt_routes.post(
    "/completions",
    summary="Run/Stream an unsaved agentic prompt",
    description="Runs or streams an unsaved agentic prompt",
    response_model=AgenticPromptRunResponse,
    response_model_exclude_none=True,
    responses={
        200: {
            "description": """An AgenticPromptRunResponse object for non-streaming requests or a StreamingResponse which has two events, a chunk event or a final_response event""",
            "content": {
                "text/event-stream": {
                    "schema": {
                        "type": "string",
                        "example": (
                            "# Chunk event\n"
                            "event: chunk\n"
                            "data: {\n"
                            '  "id": "string",\n'
                            '  "created": 1760636425,\n'
                            '  "model": "string",\n'
                            '  "object": "string",\n'
                            '  "system_fingerprint": "string",\n'
                            '  "choices": [\n'
                            "    {\n"
                            '      "finish_reason": null,\n'
                            '      "index": 0,\n'
                            '      "delta": {\n'
                            '        "provider_specific_fields": null,\n'
                            '        "refusal": null,\n'
                            '        "content": "string",\n'
                            '        "role": null,\n'
                            '        "function_call": null,\n'
                            '        "tool_calls": null,\n'
                            '        "audio": null\n'
                            "      },\n"
                            '      "logprobs": null\n'
                            "    }\n"
                            "  ],\n"
                            '  "provider_specific_fields": null\n'
                            "}\n\n"
                            "# Final response event\n"
                            "event: final_response\n"
                            "data: {\n"
                            '  "content": "string",\n'
                            '  "tool_calls": [\n'
                            '    "string"\n'
                            "  ],\n"
                            '  "cost": "string"\n'
                            "}\n\n"
                        ),
                    },
                },
            },
        },
    },
    tags=["AgenticPrompt"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
async def run_agentic_prompt(
    unsaved_prompt: CompletionRequest,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """
    Run and/or stream an unsaved agentic prompt.
    Note: For streaming, the response will be a StreamingResponse object.

    Args:
        unsaved_prompt: CompletionRequest
        current_user: User

    Returns:
        AgenticPromptRunResponse or StreamingResponse
    """
    try:
        repo = ModelProviderRepository(db_session)
        llm_client = repo.get_model_provider_client(
            provider=unsaved_prompt.model_provider,
        )
        prompt, completion_request = unsaved_prompt.to_prompt_and_request()
        return await execute_prompt_completion(
            llm_client,
            prompt,
            completion_request,
        )
    except HTTPException:
        # propagate HTTP exceptions
        raise
    except litellm.AuthenticationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@agentic_prompt_routes.post(
    "/task/{task_id}/prompt/{prompt_name}/versions/{prompt_version}/completions",
    summary="Run/Stream a specific version of an agentic prompt",
    description="Run or stream a specific version of an existing agentic prompt",
    response_model=AgenticPromptRunResponse,
    response_model_exclude_none=True,
    responses={
        200: {
            "description": """An AgenticPromptRunResponse object for non-streaming requests or a StreamingResponse which has two events, a chunk event or a final_response event""",
            "content": {
                "text/event-stream": {
                    "schema": {
                        "type": "string",
                        "example": (
                            "# Chunk event\n"
                            "event: chunk\n"
                            "data: {\n"
                            '  "id": "string",\n'
                            '  "created": 1760636425,\n'
                            '  "model": "string",\n'
                            '  "object": "string",\n'
                            '  "system_fingerprint": "string",\n'
                            '  "choices": [\n'
                            "    {\n"
                            '      "finish_reason": null,\n'
                            '      "index": 0,\n'
                            '      "delta": {\n'
                            '        "provider_specific_fields": null,\n'
                            '        "refusal": null,\n'
                            '        "content": "string",\n'
                            '        "role": null,\n'
                            '        "function_call": null,\n'
                            '        "tool_calls": null,\n'
                            '        "audio": null\n'
                            "      },\n"
                            '      "logprobs": null\n'
                            "    }\n"
                            "  ],\n"
                            '  "provider_specific_fields": null\n'
                            "}\n\n"
                            "# Final response event\n"
                            "event: final_response\n"
                            "data: {\n"
                            '  "content": "string",\n'
                            '  "tool_calls": [\n'
                            '    "string"\n'
                            "  ],\n"
                            '  "cost": "string"\n'
                            "}\n\n"
                        ),
                    },
                },
            },
        },
    },
    tags=["AgenticPrompt"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
async def run_saved_agentic_prompt(
    prompt_name: str,
    prompt_version: str,
    completion_request: PromptCompletionRequest = PromptCompletionRequest(),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
):
    """
    Run and/or stream an unsaved agentic prompt.
    Note: For streaming, the response will be a StreamingResponse object.

    Args:
        prompt_name: str
        prompt_version: str
        completion_request: PromptCompletionRequest
        current_user: User
        task: Task

    Returns:
        AgenticPromptRunResponse or StreamingResponse
    """
    try:
        agentic_prompt_service = AgenticPromptRepository(db_session)
        prompt = agentic_prompt_service.get_prompt(task.id, prompt_name, prompt_version)
        repo = ModelProviderRepository(db_session)
        llm_client = repo.get_model_provider_client(provider=prompt.model_provider)
        return await execute_prompt_completion(
            llm_client,
            prompt,
            completion_request,
        )
    except HTTPException:
        # propagate HTTP exceptions
        raise
    except litellm.AuthenticationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@agentic_prompt_routes.put(
    "/{task_id}/agentic_prompts/{prompt_name}",
    summary="Save an agentic prompt",
    description="Save an agentic prompt to the database",
    response_model=None,
    response_model_exclude_none=True,
    tags=["AgenticPrompt"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def save_agentic_prompt(
    prompt_name: str,
    prompt_config: AgenticPromptBaseConfig,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
):
    try:
        agentic_prompt_service = AgenticPromptRepository(db_session)
        full_prompt = AgenticPrompt(name=prompt_name, **prompt_config.model_dump())
        agentic_prompt_service.save_prompt(task.id, full_prompt)

        return {"message": "Prompt saved successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@agentic_prompt_routes.delete(
    "/{task_id}/agentic_prompts/{prompt_name}",
    summary="Delete an agentic prompt",
    description="Deletes an entire agentic prompt",
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

        return {"message": f"All versions of {prompt_name} deleted successfully"}
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@agentic_prompt_routes.delete(
    "/{task_id}/agentic_prompts/{prompt_name}/versions/{prompt_version}",
    summary="Delete an agentic prompt",
    description="Deletes a specific version of an agentic prompt",
    response_model=None,
    response_model_exclude_none=True,
    tags=["AgenticPrompt"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def delete_agentic_prompt_version(
    prompt_name: str,
    prompt_version: str,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
):
    try:
        agentic_prompt_service = AgenticPromptRepository(db_session)
        all_prompts_deleted = agentic_prompt_service.soft_delete_prompt(
            task.id,
            prompt_name,
            prompt_version,
        )

        if all_prompts_deleted:
            return {"message": "All prompt versions deleted successfully"}
        else:
            return {"message": "Prompt version deleted successfully"}
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
