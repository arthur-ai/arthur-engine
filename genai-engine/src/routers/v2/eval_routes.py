from typing import Annotated, Any, Union

import jinja2
from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.llm_model_providers import ModelProvider
from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    Path,
    Query,
    Response,
    status,
)
from pydantic import AfterValidator
from sqlalchemy.orm import Session

from dependencies import (
    get_db_session,
    get_validated_task,
    llm_get_all_filter_parameters,
    llm_get_versions_filter_parameters,
)
from repositories.llm_evals_repository import LLMEvalsRepository
from repositories.ml_evals_repository import (  # MLEvalsRepository used for dispatch by eval_type
    ML_EVAL_TYPES,
    MLEvalsRepository,
)
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import Task, User
from schemas.request_schemas import (
    BaseCompletionRequest,
    CreateAnyEvalRequest,
    CreateEvalRequest,
    CreateMLEvalRequest,
    LLMGetAllFilterRequest,
    LLMGetVersionsFilterRequest,
)
from schemas.response_schemas import (
    AllEvalsMetadataListResponse,
    EvalMetadataItem,
    EvalResponse,
    EvalRunResponse,
    EvalVersionItem,
    EvalVersionsListResponse,
)
from utils.url_encoding import decode_path_param
from utils.users import permission_checker
from utils.utils import common_pagination_parameters

eval_routes = APIRouter(
    prefix="/api/v2",
    route_class=GenaiEngineRoute,
)

# ---------------------------------------------------------------------------
# Helpers — repo dispatch by eval_type
# ---------------------------------------------------------------------------


def _get_repo(
    eval_type: str,
    db_session: Session,
) -> Union[MLEvalsRepository, LLMEvalsRepository]:
    """Return the right repository for the given eval_type."""
    if eval_type in ML_EVAL_TYPES:
        return MLEvalsRepository(db_session)
    return LLMEvalsRepository(db_session)


def _to_eval_response(obj: Any) -> EvalResponse:
    """Convert a LLMEval or MLEval domain object into a unified EvalResponse."""
    return EvalResponse(
        name=obj.name,
        eval_type=getattr(obj, "eval_type", "llm_as_a_judge"),
        version=obj.version,
        variables=obj.variables,
        tags=obj.tags if obj.tags else [],
        config=obj.config if obj.config else None,
        created_at=obj.created_at,
        deleted_at=obj.deleted_at,
        model_name=getattr(obj, "model_name", None),
        model_provider=(
            str(getattr(obj, "model_provider", None))
            if getattr(obj, "model_provider", None)
            else None
        ),
        instructions=getattr(obj, "instructions", None),
    )


# ---------------------------------------------------------------------------
# GET /tasks/{task_id}/evals  — list all evals (LLM + ML)
# ---------------------------------------------------------------------------


@eval_routes.get(
    "/tasks/{task_id}/evals",
    summary="Get all evaluators",
    description="Return metadata for every evaluator (LLM and ML) associated with a task.",
    response_model=AllEvalsMetadataListResponse,
    response_model_exclude_none=True,
    tags=["Evals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_all_evals(
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
) -> AllEvalsMetadataListResponse:
    try:
        # LLMEvalsRepository now returns all eval types (llm_as_a_judge + ML types)
        # so a single query is sufficient.
        repo = LLMEvalsRepository(db_session)
        all_list = repo.get_all_llm_item_metadata(
            task.id,
            pagination_parameters,
            filter_request,
        )

        items: list[EvalMetadataItem] = []
        for item in all_list.llm_metadata:
            is_ml = item.eval_type != "llm_as_a_judge"
            items.append(
                EvalMetadataItem(
                    eval_type="ml" if is_ml else "llm_as_a_judge",
                    ml_eval_type=item.eval_type if is_ml else None,
                    name=item.name,
                    versions=item.versions,
                    tags=item.tags,
                    created_at=item.created_at,
                    latest_version_created_at=item.latest_version_created_at,
                    deleted_versions=item.deleted_versions,
                ),
            )

        return AllEvalsMetadataListResponse(evals=items, count=all_list.count)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# POST /tasks/{task_id}/evals/{eval_name}  — create / version an eval
# ---------------------------------------------------------------------------


@eval_routes.post(
    "/tasks/{task_id}/evals/{eval_name}",
    summary="Save an eval",
    description=(
        "Save an eval (LLM-as-a-judge or ML type). "
        "If an eval with the same name exists, a new version is created."
    ),
    response_model=EvalResponse,
    response_model_exclude_none=True,
    tags=["Evals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def save_eval(
    eval_config: CreateAnyEvalRequest,
    eval_name: Annotated[str, Path(), AfterValidator(decode_path_param)],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> EvalResponse:
    try:
        result: Any
        if eval_config.eval_type == "llm_as_a_judge":
            llm_repo = LLMEvalsRepository(db_session)
            create_req = CreateEvalRequest(
                model_name=eval_config.model_name or "",
                model_provider=ModelProvider(eval_config.model_provider),
                instructions=eval_config.instructions or "",
                config=eval_config.config,
            )
            result = llm_repo.save_llm_item(task.id, eval_name, create_req)
        else:
            ml_repo = MLEvalsRepository(db_session)
            ml_create_req = CreateMLEvalRequest(
                eval_type=eval_config.eval_type,
                config=eval_config.config,
            )
            result = ml_repo.save_ml_eval(task.id, eval_name, ml_create_req)
        return _to_eval_response(result)
    except jinja2.exceptions.TemplateSyntaxError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Jinja2 template syntax in eval instructions: {e}",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# GET /tasks/{task_id}/evals/{eval_name}/versions/{eval_version}
# ---------------------------------------------------------------------------


@eval_routes.get(
    "/tasks/{task_id}/evals/{eval_name}/versions/{eval_version}",
    summary="Get an eval by version",
    description="Get a specific version of an eval. Supports 'latest', version number, datetime, or tag.",
    response_model=EvalResponse,
    response_model_exclude_none=True,
    tags=["Evals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_eval(
    eval_name: Annotated[str, Path(), AfterValidator(decode_path_param)],
    eval_version: str = Path(
        ...,
        description="Version: 'latest', a number, ISO datetime, or tag.",
    ),
    eval_type: str = Query(
        default="llm_as_a_judge",
        description="Eval type discriminator",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> EvalResponse:
    try:
        repo = _get_repo(eval_type, db_session)
        result = repo.get_llm_item(task.id, eval_name, eval_version)
        return _to_eval_response(result)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# GET /tasks/{task_id}/evals/{eval_name}/versions/tags/{tag}
# ---------------------------------------------------------------------------


@eval_routes.get(
    "/tasks/{task_id}/evals/{eval_name}/versions/tags/{tag}",
    summary="Get an eval by tag",
    description="Get a specific version of an eval by tag.",
    response_model=EvalResponse,
    response_model_exclude_none=True,
    tags=["Evals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_eval_by_tag(
    eval_name: Annotated[str, Path(), AfterValidator(decode_path_param)],
    tag: Annotated[str, Path(), AfterValidator(decode_path_param)],
    eval_type: str = Query(
        default="llm_as_a_judge",
        description="Eval type discriminator",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> EvalResponse:
    try:
        repo = _get_repo(eval_type, db_session)
        result = repo.get_llm_item_by_tag(task.id, eval_name, tag)
        return _to_eval_response(result)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# GET /tasks/{task_id}/evals/{eval_name}/versions
# ---------------------------------------------------------------------------


@eval_routes.get(
    "/tasks/{task_id}/evals/{eval_name}/versions",
    summary="List versions of an eval",
    description="List all versions of an eval with optional filtering.",
    response_model=EvalVersionsListResponse,
    response_model_exclude_none=True,
    tags=["Evals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_eval_versions(
    eval_name: Annotated[str, Path(), AfterValidator(decode_path_param)],
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    filter_request: Annotated[
        LLMGetVersionsFilterRequest,
        Depends(llm_get_versions_filter_parameters),
    ],
    eval_type: str = Query(
        default="llm_as_a_judge",
        description="Eval type discriminator",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> EvalVersionsListResponse:
    try:
        repo = _get_repo(eval_type, db_session)
        raw: Any = repo.get_llm_item_versions(
            task.id,
            eval_name,
            pagination_parameters,
            filter_request,
        )

        versions = []
        for v in raw.versions:
            versions.append(
                EvalVersionItem(
                    version=v.version,
                    eval_type=getattr(v, "eval_type", eval_type),
                    created_at=v.created_at,
                    deleted_at=v.deleted_at,
                    tags=v.tags if v.tags else [],
                    model_name=getattr(v, "model_name", None),
                    model_provider=(
                        str(getattr(v, "model_provider", None))
                        if getattr(v, "model_provider", None)
                        else None
                    ),
                ),
            )
        return EvalVersionsListResponse(versions=versions, count=raw.count)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# DELETE /tasks/{task_id}/evals/{eval_name}  — hard delete all versions
# ---------------------------------------------------------------------------


@eval_routes.delete(
    "/tasks/{task_id}/evals/{eval_name}",
    summary="Delete an eval",
    description="Hard-delete all versions of an eval.",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Evals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def delete_eval(
    eval_name: Annotated[str, Path(), AfterValidator(decode_path_param)],
    eval_type: str = Query(
        default="llm_as_a_judge",
        description="Eval type discriminator",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> Response:
    try:
        repo = _get_repo(eval_type, db_session)
        repo.delete_llm_item(task.id, eval_name)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# DELETE /tasks/{task_id}/evals/{eval_name}/versions/{eval_version}  — soft delete
# ---------------------------------------------------------------------------


@eval_routes.delete(
    "/tasks/{task_id}/evals/{eval_name}/versions/{eval_version}",
    summary="Soft-delete an eval version",
    description="Soft-delete a specific version of an eval.",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Evals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def soft_delete_eval_version(
    eval_name: Annotated[str, Path(), AfterValidator(decode_path_param)],
    eval_version: str = Path(
        ...,
        description="Version: 'latest', a number, ISO datetime, or tag.",
    ),
    eval_type: str = Query(
        default="llm_as_a_judge",
        description="Eval type discriminator",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> Response:
    try:
        repo = _get_repo(eval_type, db_session)
        repo.soft_delete_llm_item_version(task.id, eval_name, eval_version)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        if "no matching version" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# PUT /tasks/{task_id}/evals/{eval_name}/versions/{eval_version}/tags
# ---------------------------------------------------------------------------


@eval_routes.put(
    "/tasks/{task_id}/evals/{eval_name}/versions/{eval_version}/tags",
    summary="Add a tag to an eval version",
    response_model=EvalResponse,
    response_model_exclude_none=True,
    tags=["Evals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def add_eval_tag(
    eval_name: Annotated[str, Path(), AfterValidator(decode_path_param)],
    eval_version: str = Path(...),
    eval_type: str = Query(
        default="llm_as_a_judge",
        description="Eval type discriminator",
    ),
    tag: str = Body(..., embed=True, description="Tag to add"),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> EvalResponse:
    try:
        repo = _get_repo(eval_type, db_session)
        repo.add_tag_to_llm_item_version(task.id, eval_name, eval_version, tag)
        result = repo.get_llm_item(task.id, eval_name, eval_version)
        return _to_eval_response(result)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# DELETE /tasks/{task_id}/evals/{eval_name}/versions/{eval_version}/tags/{tag}
# ---------------------------------------------------------------------------


@eval_routes.delete(
    "/tasks/{task_id}/evals/{eval_name}/versions/{eval_version}/tags/{tag}",
    summary="Remove a tag from an eval version",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Evals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def delete_eval_tag(
    eval_name: Annotated[str, Path(), AfterValidator(decode_path_param)],
    eval_version: Annotated[str, Path()],
    tag: Annotated[str, Path(), AfterValidator(decode_path_param)],
    eval_type: str = Query(
        default="llm_as_a_judge",
        description="Eval type discriminator",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> None:
    try:
        repo = _get_repo(eval_type, db_session)
        repo.delete_llm_item_tag_from_version(task.id, eval_name, eval_version, tag)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# POST /tasks/{task_id}/evals/{eval_name}/versions/{eval_version}/completions
# ---------------------------------------------------------------------------


@eval_routes.post(
    "/tasks/{task_id}/evals/{eval_name}/versions/{eval_version}/completions",
    summary="Run a saved eval",
    description="Execute a saved LLM-as-a-judge eval and return a scored result.",
    response_model=EvalRunResponse,
    response_model_exclude_none=True,
    tags=["Evals"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def run_eval(
    completion_request: BaseCompletionRequest,
    eval_name: Annotated[str, Path(), AfterValidator(decode_path_param)],
    eval_version: str = Path(...),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> EvalRunResponse:
    """Run endpoint is only supported for llm_as_a_judge evals (which produce a structured score).
    ML evals are executed automatically by the continuous eval queue."""
    try:
        repo = LLMEvalsRepository(db_session)
        return repo.run_llm_eval(task.id, eval_name, eval_version, completion_request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
