import copy
from typing import Annotated

import jinja2
import litellm
from arthur_common.models.common_schemas import PaginationParameters
from fastapi import APIRouter, Body, Depends, HTTPException, Path, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from dependencies import (
    get_db_session,
    get_validated_agentic_task,
    llm_get_all_filter_parameters,
    llm_get_versions_filter_parameters,
)
from repositories.agentic_prompts_repository import AgenticPromptRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.agentic_prompt_schemas import (
    AgenticPrompt,
)
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import Task, User
from schemas.request_schemas import (
    CompletionRequest,
    CreateAgenticPromptRequest,
    LLMGetAllFilterRequest,
    LLMGetVersionsFilterRequest,
    PromptCompletionRequest,
    SavedPromptRenderingRequest,
    UnsavedPromptRenderingRequest,
    UnsavedPromptVariablesRequest,
)
from schemas.response_schemas import (
    AgenticPromptRunResponse,
    AgenticPromptVersionListResponse,
    LLMGetAllMetadataListResponse,
    RenderedPromptResponse,
    UnsavedPromptVariablesListResponse,
)
from services.prompt.chat_completion_service import ChatCompletionService
from utils.users import permission_checker
from utils.utils import common_pagination_parameters

agentic_prompt_routes = APIRouter(
    prefix="/api/v1",
    route_class=GenaiEngineRoute,
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
        description="The version of the prompt to retrieve. Can be 'latest', a version number (e.g. '1', '2', etc.), an ISO datetime string (e.g. '2025-01-01T00:00:00'), or a tag.",
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
        agentic_prompt_service = AgenticPromptRepository(db_session)
        return await agentic_prompt_service.run_unsaved_prompt(unsaved_prompt)
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
    "/prompt_renders",
    summary="Render an unsaved prompt with variables",
    description="Render an unsaved prompt by replacing template variables with provided values. Accepts messages directly in the request body instead of loading from database.",
    response_model=RenderedPromptResponse,
    response_model_exclude_none=True,
    tags=["Prompts"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def render_unsaved_agentic_prompt(
    rendering_request: UnsavedPromptRenderingRequest,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> RenderedPromptResponse:
    """
    Render an unsaved agentic prompt with template variable substitution.

    Args:
        rendering_request: UnsavedPromptRenderingRequest containing messages and completion_request with variables
        current_user: User

    Returns:
        RenderedPromptResponse with rendered messages
    """
    try:
        # Extract completion_request and messages from the request
        completion_request = rendering_request.completion_request
        messages = rendering_request.messages

        # Get variable map from completion_request
        variable_map = (
            completion_request._variable_map if completion_request.variables else {}
        )

        # If strict mode, validate that all variables in messages are provided
        if completion_request.strict:
            chat_service = ChatCompletionService()
            missing_vars = chat_service.find_missing_variables_in_messages(
                variable_map,
                messages,
            )
            if missing_vars:
                raise ValueError(
                    f"Missing values for the following variables: {', '.join(sorted(missing_vars))}",
                )

        # Deep copy messages to avoid mutating the request
        rendered_messages = copy.deepcopy(messages)

        # Replace variables in messages
        chat_service = ChatCompletionService()
        rendered_messages = chat_service.replace_variables(
            variable_map,
            rendered_messages,
        )

        # Return a RenderedPromptResponse with rendered messages
        return RenderedPromptResponse(
            messages=rendered_messages,
        )
    except HTTPException:
        # propagate HTTP exceptions
        raise
    except jinja2.exceptions.TemplateSyntaxError as e:
        # Handle Jinja2 template syntax errors
        error_msg = f"Invalid Jinja2 template syntax in prompt messages: {str(e)}"
        raise HTTPException(status_code=400, detail=error_msg)
    except jinja2.exceptions.UndefinedError as e:
        # Handle missing variable errors
        error_msg = f"Template rendering error: {str(e)}"
        raise HTTPException(status_code=400, detail=error_msg)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@agentic_prompt_routes.post(
    "/prompt_variables",
    summary="Gets the list of variables needed from an unsaved prompt's messages",
    description="Gets the list of variables needed from an unsaved prompt's messages",
    response_model=UnsavedPromptVariablesListResponse,
    response_model_exclude_none=True,
    tags=["Prompts"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_unsaved_prompt_variables_list(
    unsaved_messages: UnsavedPromptVariablesRequest,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> UnsavedPromptVariablesListResponse:
    """
    Gets the list of variables needed from an unsaved prompt's messages.

    Args:
        unsaved_messages: UnsavedPromptVariablesRequest containing messages
        current_user: User

    Returns:
        UnsavedPromptVariablesListResponse - the list of variables needed to run an unsaved prompt
    """
    try:
        # Get the list of variables needed from the messages
        chat_service = ChatCompletionService()
        variables = chat_service.find_missing_variables_in_messages(
            variable_map={},
            messages=unsaved_messages.messages,
        )

        # Return the list of variables needed to run an unsaved prompt
        return UnsavedPromptVariablesListResponse(
            variables=list(variables),
        )
    except jinja2.exceptions.TemplateSyntaxError as e:
        # Handle Jinja2 template syntax errors
        error_msg = f"Invalid Jinja2 template syntax in prompt messages: {str(e)}"
        raise HTTPException(status_code=400, detail=error_msg)
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
        description="The version of the prompt to run. Can be 'latest', a version number (e.g. '1', '2', etc.), an ISO datetime string (e.g. '2025-01-01T00:00:00'), or a tag.",
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
        return await agentic_prompt_service.run_saved_prompt(
            task.id,
            prompt_name,
            prompt_version,
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
    "/tasks/{task_id}/prompts/{prompt_name}/versions/{prompt_version}/renders",
    summary="Render a specific version of an agentic prompt with variables",
    description="Render a specific version of an existing agentic prompt by replacing template variables with provided values. Returns the rendered messages.",
    response_model=RenderedPromptResponse,
    response_model_exclude_none=True,
    tags=["Prompts"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def render_saved_agentic_prompt(
    prompt_name: str = Path(
        ...,
        description="The name of the prompt to render.",
        title="Prompt Name",
    ),
    prompt_version: str = Path(
        ...,
        description="The version of the prompt to render. Can be 'latest', a version number (e.g. '1', '2', etc.), an ISO datetime string (e.g. '2025-01-01T00:00:00'), or a tag.",
        title="Prompt Version",
    ),
    rendering_request: SavedPromptRenderingRequest = SavedPromptRenderingRequest(),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
) -> RenderedPromptResponse:
    """
    Render an agentic prompt with template variable substitution.

    Args:
        prompt_name: str
        prompt_version: str
        rendering_request: SavedPromptRenderingRequest containing completion_request with variables for template substitution
        current_user: User
        task: Task

    Returns:
        RenderedPromptResponse with rendered messages
    """
    try:
        agentic_prompt_service = AgenticPromptRepository(db_session)
        rendered_prompt = agentic_prompt_service.render_saved_prompt(
            task.id,
            prompt_name,
            prompt_version,
            rendering_request.completion_request,
        )
        # Convert AgenticPrompt to RenderedPromptResponse
        return RenderedPromptResponse(
            messages=rendered_prompt.messages,
        )
    except HTTPException:
        # propagate HTTP exceptions
        raise
    except jinja2.exceptions.TemplateSyntaxError as e:
        # Handle Jinja2 template syntax errors
        error_msg = f"Invalid Jinja2 template syntax in prompt messages: {str(e)}"
        raise HTTPException(status_code=400, detail=error_msg)
    except jinja2.exceptions.UndefinedError as e:
        # Handle missing variable errors
        error_msg = f"Template rendering error: {str(e)}"
        raise HTTPException(status_code=400, detail=error_msg)
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
        return agentic_prompt_service.save_llm_item(task.id, prompt_name, prompt_config)
    except jinja2.exceptions.TemplateSyntaxError as e:
        # Handle Jinja2 template syntax errors with a helpful message
        error_msg = f"Invalid Jinja2 template syntax in prompt messages: {str(e)}"
        raise HTTPException(status_code=400, detail=error_msg)
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
        description="The version of the prompt to delete. Can be 'latest', a version number (e.g. '1', '2', etc.), an ISO datetime string (e.g. '2025-01-01T00:00:00'), or a tag.",
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


@agentic_prompt_routes.get(
    "/tasks/{task_id}/prompts/{prompt_name}/versions/tags/{tag}",
    summary="Get an agentic prompt by name and tag",
    description="Get an agentic prompt by name and tag",
    response_model=AgenticPrompt,
    response_model_exclude_none=True,
    tags=["Prompts"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_agentic_prompt_by_tag(
    prompt_name: str = Path(
        ...,
        description="The name of the prompt to retrieve.",
        title="Prompt Name",
    ),
    tag: str = Path(
        ...,
        description="The tag of the prompt to retrieve.",
        title="Tag",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
) -> AgenticPrompt:
    try:
        agentic_prompt_service = AgenticPromptRepository(db_session)
        return agentic_prompt_service.get_llm_item_by_tag(
            task.id,
            prompt_name,
            tag,
        )
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@agentic_prompt_routes.put(
    "/tasks/{task_id}/prompts/{prompt_name}/versions/{prompt_version}/tags",
    summary="Add a tag to an agentic prompt version",
    description="Add a tag to an agentic prompt version",
    response_model=AgenticPrompt,
    response_model_exclude_none=True,
    tags=["Prompts"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def add_tag_to_agentic_prompt_version(
    prompt_name: str = Path(
        ...,
        description="The name of the prompt to retrieve.",
        title="Prompt Name",
    ),
    prompt_version: str = Path(
        ...,
        description="The version of the prompt to retrieve. Can be 'latest', a version number (e.g. '1', '2', etc.), an ISO datetime string (e.g. '2025-01-01T00:00:00'), or a tag.",
        title="Prompt Version",
    ),
    tag: str = Body(..., embed=True, description="Tag to add to this prompt version"),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
) -> AgenticPrompt:
    try:
        agentic_prompt_service = AgenticPromptRepository(db_session)
        return agentic_prompt_service.add_tag_to_llm_item_version(
            task.id,
            prompt_name,
            prompt_version,
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


@agentic_prompt_routes.delete(
    "/tasks/{task_id}/prompts/{prompt_name}/versions/{prompt_version}/tags/{tag}",
    summary="Remove a tag from an agentic prompt version",
    description="Remove a tag from an agentic prompt version",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_204_NO_CONTENT: {"description": "Prompt version deleted."}},
    tags=["Prompts"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def delete_tag_from_agentic_prompt_version(
    prompt_name: str = Path(
        ...,
        description="The name of the prompt to retrieve.",
        title="Prompt Name",
    ),
    prompt_version: str = Path(
        ...,
        description="The version of the prompt to retrieve. Can be 'latest', a version number (e.g. '1', '2', etc.), an ISO datetime string (e.g. '2025-01-01T00:00:00'), or a tag.",
        title="Prompt Version",
    ),
    tag: str = Path(
        ...,
        description="The tag to remove from the prompt version.",
        title="Tag",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
) -> None:
    try:
        agentic_prompt_service = AgenticPromptRepository(db_session)
        agentic_prompt_service.delete_llm_item_tag_from_version(
            task.id,
            prompt_name,
            prompt_version,
            tag,
        )
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
