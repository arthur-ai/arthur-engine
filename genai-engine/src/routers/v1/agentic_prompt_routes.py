from typing import Annotated, Union

import litellm
from arthur_common.models.common_schemas import PaginationParameters
from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from clients.llm.llm_client import LLMClient
from dependencies import (
    get_db_session,
    get_validated_agentic_task,
    llm_get_all_filter_parameters,
    llm_get_versions_filter_parameters,
)
from repositories.agentic_prompts_repository import AgenticPromptRepository
from repositories.model_provider_repository import ModelProviderRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.agentic_prompt_schemas import (
    AgenticPrompt,
    CompletionRequest,
    PromptCompletionRequest,
)
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import Task, User
from schemas.request_schemas import (
    CreateAgenticPromptRequest,
    LLMGetAllFilterRequest,
    LLMGetVersionsFilterRequest,
)
from schemas.response_schemas import (
    AgenticPromptRunResponse,
    AgenticPromptVersionListResponse,
    LLMGetAllMetadataListResponse,
)
from utils.users import permission_checker
from utils.utils import common_pagination_parameters

agentic_prompt_routes = APIRouter(
    prefix="/api/v1",
    route_class=GenaiEngineRoute,
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
) -> AgenticPrompt:
    try:
        agentic_prompt_service = AgenticPromptRepository(db_session)
        prompt = agentic_prompt_service.get_llm_item(
            task.id,
            prompt_name,
            prompt_version,
        )
        return prompt
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@agentic_prompt_routes.get(
    "/tasks/{task_id}/prompts",
    summary="Get all agentic prompts",
    description="Get all agentic prompts for a given task with optional filtering.",
    response_model=LLMGetAllMetadataListResponse,
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
        LLMGetAllFilterRequest,
        Depends(llm_get_all_filter_parameters),
    ],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
) -> LLMGetAllMetadataListResponse:
    try:
        agentic_prompt_service = AgenticPromptRepository(db_session)
        return agentic_prompt_service.get_all_llm_item_metadata(
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
        LLMGetVersionsFilterRequest,
        Depends(llm_get_versions_filter_parameters),
    ],
    prompt_name: str = Path(
        ...,
        description="The name of the prompt to retrieve.",
        title="Prompt Name",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
) -> AgenticPromptVersionListResponse:
    try:
        agentic_prompt_service = AgenticPromptRepository(db_session)
        return agentic_prompt_service.get_llm_item_versions(
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
) -> AgenticPromptRunResponse | StreamingResponse:
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
) -> AgenticPromptRunResponse | StreamingResponse:
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
        prompt = agentic_prompt_service.get_llm_item(
            task.id,
            prompt_name,
            prompt_version,
        )
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
    prompt_config: CreateAgenticPromptRequest,
    prompt_name: str = Path(
        ...,
        description="The name of the prompt to save.",
        title="Prompt Name",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
) -> AgenticPrompt:
    try:
        agentic_prompt_service = AgenticPromptRepository(db_session)
        full_prompt = AgenticPrompt(name=prompt_name, **prompt_config.model_dump())
        return agentic_prompt_service.save_llm_item(task.id, full_prompt)
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
        agentic_prompt_service.delete_llm_item(task.id, prompt_name)
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
        agentic_prompt_service.soft_delete_llm_item_version(
            task.id,
            prompt_name,
            prompt_version,
        )

        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        if "no matching version" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
