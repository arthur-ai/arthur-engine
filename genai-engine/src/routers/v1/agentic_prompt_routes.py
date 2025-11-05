from datetime import datetime
from typing import Annotated, Optional, Union
from uuid import UUID

import litellm
from arthur_common.models.common_schemas import PaginationParameters
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
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
    CompletionRequest,
    PromptCompletionRequest,
)
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import ApplicationConfiguration, Task, User
from schemas.request_schemas import (
    PromptsGetAllFilterRequest,
    PromptsGetVersionsFilterRequest,
)
from schemas.response_schemas import (
    AgenticPromptMetadataListResponse,
    AgenticPromptRunResponse,
    AgenticPromptVersionListResponse,
)
from utils.users import permission_checker
from utils.utils import common_pagination_parameters

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


def prompts_get_all_filter_parameters(
    prompt_names: Optional[list[str]] = Query(
        None,
        description="Prompt names to filter on using partial matching. If provided, prompts matching any of these name patterns will be returned.",
    ),
    model_provider: Optional[str] = Query(
        None,
        description="Filter by model provider (e.g., 'openai', 'anthropic', 'azure').",
    ),
    model_name: Optional[str] = Query(
        None,
        description="Filter by model name (e.g., 'gpt-4', 'claude-3-5-sonnet').",
    ),
    created_after: Optional[str] = Query(
        None,
        description="Inclusive start date for prompt creation in ISO8601 string format. Use local time (not UTC).",
    ),
    created_before: Optional[str] = Query(
        None,
        description="Exclusive end date for prompt creation in ISO8601 string format. Use local time (not UTC).",
    ),
) -> PromptsGetAllFilterRequest:
    """Create a PromptsGetAllFilterRequest from query parameters."""
    return PromptsGetAllFilterRequest(
        prompt_names=prompt_names,
        model_provider=model_provider,
        model_name=model_name,
        created_after=datetime.fromisoformat(created_after) if created_after else None,
        created_before=(
            datetime.fromisoformat(created_before) if created_before else None
        ),
    )


def prompts_get_versions_filter_parameters(
    model_provider: Optional[str] = Query(
        None,
        description="Filter by model provider (e.g., 'openai', 'anthropic', 'azure').",
    ),
    model_name: Optional[str] = Query(
        None,
        description="Filter by model name (e.g., 'gpt-4', 'claude-3-5-sonnet').",
    ),
    created_after: Optional[str] = Query(
        None,
        description="Inclusive start date for prompt creation in ISO8601 string format. Use local time (not UTC).",
    ),
    created_before: Optional[str] = Query(
        None,
        description="Exclusive end date for prompt creation in ISO8601 string format. Use local time (not UTC).",
    ),
    exclude_deleted: bool = Query(
        False,
        description="Whether to exclude deleted prompt versions from the results. Default is False.",
    ),
    min_version: Optional[int] = Query(
        None,
        ge=1,
        description="Minimum version number to filter on (inclusive).",
    ),
    max_version: Optional[int] = Query(
        None,
        ge=1,
        description="Maximum version number to filter on (inclusive).",
    ),
) -> PromptsGetVersionsFilterRequest:
    """Create a PromptsGetVersionsFilterRequest from query parameters."""
    return PromptsGetVersionsFilterRequest(
        model_provider=model_provider,
        model_name=model_name,
        created_after=datetime.fromisoformat(created_after) if created_after else None,
        created_before=(
            datetime.fromisoformat(created_before) if created_before else None
        ),
        exclude_deleted=exclude_deleted,
        min_version=min_version,
        max_version=max_version,
    )


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
    "/tasks/{task_id}/prompts/{prompt_name}/versions/{prompt_version}",
    summary="Get an agentic prompt",
    description="Get an agentic prompt by name and version",
    response_model=AgenticPrompt,
    response_model_exclude_none=True,
    tags=["Prompts"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_agentic_prompt(
    prompt_name: str = Path(
        ...,
        description="The name of the prompt to retrieve.",
        title="Prompt Name",
    ),
    prompt_version: str = Path(
        ...,
        description="The version of the prompt to retrieve. Can be 'latest', a version number (e.g. '1', '2', etc.), or an ISO datetime string (e.g. '2025-01-01T00:00:00').",
        title="Prompt Version",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
):
    try:
        agentic_prompt_service = AgenticPromptRepository(db_session)
        prompt = agentic_prompt_service.get_prompt(
            task.id,
            prompt_name,
            prompt_version,
        )
        return prompt
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        elif "attempting to retrieve a deleted prompt" in str(e).lower():
            raise HTTPException(status_code=400, detail=error_message)
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@agentic_prompt_routes.get(
    "/tasks/{task_id}/prompts",
    summary="Get all agentic prompts",
    description="Get all agentic prompts for a given task with optional filtering.",
    response_model=AgenticPromptMetadataListResponse,
    response_model_exclude_none=True,
    tags=["Prompts"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_all_agentic_prompts(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    filter_request: Annotated[
        PromptsGetAllFilterRequest,
        Depends(prompts_get_all_filter_parameters),
    ],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
):
    try:
        agentic_prompt_service = AgenticPromptRepository(db_session)
        return agentic_prompt_service.get_all_prompt_metadata(
            task.id,
            pagination_parameters,
            filter_request,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@agentic_prompt_routes.get(
    "/tasks/{task_id}/prompts/{prompt_name}/versions",
    summary="List all versions of an agentic prompt",
    description="List all versions of an agentic prompt with optional filtering.",
    response_model=AgenticPromptVersionListResponse,
    response_model_exclude_none=True,
    tags=["Prompts"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_all_agentic_prompt_versions(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    filter_request: Annotated[
        PromptsGetVersionsFilterRequest,
        Depends(prompts_get_versions_filter_parameters),
    ],
    prompt_name: str = Path(
        ...,
        description="The name of the prompt to retrieve.",
        title="Prompt Name",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
):
    try:
        agentic_prompt_service = AgenticPromptRepository(db_session)
        return agentic_prompt_service.get_prompt_versions(
            task.id,
            prompt_name,
            pagination_parameters,
            filter_request,
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
    tags=["Prompts"],
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
    "/tasks/{task_id}/prompts/{prompt_name}/versions/{prompt_version}/completions",
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
    tags=["Prompts"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
async def run_saved_agentic_prompt(
    prompt_name: str = Path(
        ...,
        description="The name of the prompt to run.",
        title="Prompt Name",
    ),
    prompt_version: str = Path(
        ...,
        description="The version of the prompt to run. Can be 'latest', a version number (e.g. '1', '2', etc.), or an ISO datetime string (e.g. '2025-01-01T00:00:00').",
        title="Prompt Version",
    ),
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


@agentic_prompt_routes.post(
    "/tasks/{task_id}/prompts/{prompt_name}",
    summary="Save an agentic prompt",
    description="Save an agentic prompt to the database",
    response_model=AgenticPrompt,
    response_model_exclude_none=True,
    tags=["Prompts"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def save_agentic_prompt(
    prompt_config: AgenticPromptBaseConfig,
    prompt_name: str = Path(
        ...,
        description="The name of the prompt to save.",
        title="Prompt Name",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
):
    try:
        agentic_prompt_service = AgenticPromptRepository(db_session)
        full_prompt = AgenticPrompt(name=prompt_name, **prompt_config.model_dump())
        return agentic_prompt_service.save_prompt(task.id, full_prompt)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@agentic_prompt_routes.delete(
    "/tasks/{task_id}/prompts/{prompt_name}",
    summary="Delete an agentic prompt",
    description="Deletes an entire agentic prompt",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_204_NO_CONTENT: {"description": "Prompt deleted."}},
    tags=["Prompts"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def delete_agentic_prompt(
    prompt_name: str = Path(
        ...,
        description="The name of the prompt to delete.",
        title="Prompt Name",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
) -> Response:
    try:
        agentic_prompt_service = AgenticPromptRepository(db_session)
        agentic_prompt_service.delete_prompt(task.id, prompt_name)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@agentic_prompt_routes.delete(
    "/tasks/{task_id}/prompts/{prompt_name}/versions/{prompt_version}",
    summary="Delete an agentic prompt version",
    description="Deletes a specific version of an agentic prompt",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_204_NO_CONTENT: {"description": "Prompt version deleted."}},
    tags=["Prompts"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def delete_agentic_prompt_version(
    prompt_name: str = Path(
        ...,
        description="The name of the prompt to delete.",
        title="Prompt Name",
    ),
    prompt_version: str = Path(
        ...,
        description="The version of the prompt to delete. Can be 'latest', a version number (e.g. '1', '2', etc.), or an ISO datetime string (e.g. '2025-01-01T00:00:00').",
        title="Prompt Version",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
) -> Response:
    try:
        agentic_prompt_service = AgenticPromptRepository(db_session)
        agentic_prompt_service.soft_delete_prompt_version(
            task.id,
            prompt_name,
            prompt_version,
        )

        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
