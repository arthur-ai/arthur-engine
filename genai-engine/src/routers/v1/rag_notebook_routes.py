from typing import Annotated

from arthur_common.models.common_schemas import PaginationParameters
from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy.orm import Session

from dependencies import get_db_session, get_validated_task
from repositories.rag_notebook_repository import RagNotebookRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import Task, User
from schemas.rag_experiment_schemas import (
    RagExperimentListResponse,
)
from schemas.rag_notebook_schemas import (
    CreateRagNotebookRequest,
    RagNotebookDetail,
    RagNotebookListResponse,
    RagNotebookStateResponse,
    SetRagNotebookStateRequest,
    UpdateRagNotebookRequest,
)
from utils.users import permission_checker
from utils.utils import common_pagination_parameters

rag_notebook_routes = APIRouter(
    prefix="/api/v1",
    route_class=GenaiEngineRoute,
)


@rag_notebook_routes.post(
    "/tasks/{task_id}/rag_notebooks",
    summary="Create a RAG notebook",
    description="Create a new RAG notebook for organizing experiments within a task",
    response_model=RagNotebookDetail,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
    tags=["RAG Notebooks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def create_rag_notebook(
    notebook_request: CreateRagNotebookRequest,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> RagNotebookDetail:
    """
    Create a new RAG notebook for a task.

    RAG notebooks are draft experiment configurations that can be edited
    and executed multiple times to create experiment runs.
    """
    try:
        repo = RagNotebookRepository(db_session)
        notebook = repo.create_notebook(
            task_id=task.id,
            request=notebook_request,
        )
        return notebook
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@rag_notebook_routes.get(
    "/tasks/{task_id}/rag_notebooks",
    summary="List RAG notebooks",
    description="List all RAG notebooks for a task with pagination and optional name search",
    response_model=RagNotebookListResponse,
    response_model_exclude_none=True,
    tags=["RAG Notebooks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def list_rag_notebooks(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    name: str | None = None,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
) -> RagNotebookListResponse:
    """
    List all RAG notebooks for a given task.

    Returns paginated list of notebook summaries. Optionally filter by exact name match.
    """
    try:
        repo = RagNotebookRepository(db_session)
        response = repo.list_notebooks(
            task_id=task.id,
            pagination_params=pagination_parameters,
            name_filter=name,
        )
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@rag_notebook_routes.get(
    "/rag_notebooks/{notebook_id}",
    summary="Get RAG notebook details",
    description="Get detailed information about a RAG notebook including state and experiment history",
    response_model=RagNotebookDetail,
    response_model_exclude_none=True,
    tags=["RAG Notebooks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_rag_notebook(
    notebook_id: str = Path(..., description="RAG Notebook ID"),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> RagNotebookDetail:
    """
    Get detailed information about a RAG notebook.

    Includes the current state (draft configuration) and history
    of all experiments run from this notebook.
    """
    try:
        repo = RagNotebookRepository(db_session)
        notebook = repo.get_notebook(notebook_id)
        return notebook
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@rag_notebook_routes.put(
    "/rag_notebooks/{notebook_id}",
    summary="Update RAG notebook metadata",
    description="Update RAG notebook name or description (not the state)",
    response_model=RagNotebookDetail,
    response_model_exclude_none=True,
    tags=["RAG Notebooks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def update_rag_notebook(
    update_request: UpdateRagNotebookRequest,
    notebook_id: str = Path(..., description="RAG Notebook ID"),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> RagNotebookDetail:
    """
    Update RAG notebook metadata (name and/or description).

    To update the notebook state (RAG configs, dataset, etc.), use the
    set_rag_notebook_state endpoint instead.
    """
    try:
        repo = RagNotebookRepository(db_session)
        notebook = repo.update_notebook(notebook_id, update_request)
        return notebook
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@rag_notebook_routes.get(
    "/rag_notebooks/{notebook_id}/state",
    summary="Get RAG notebook state",
    description="Get the current state (draft configuration) of a RAG notebook",
    response_model=RagNotebookStateResponse,
    response_model_exclude_none=True,
    tags=["RAG Notebooks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_rag_notebook_state(
    notebook_id: str = Path(..., description="RAG Notebook ID"),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> RagNotebookStateResponse:
    """
    Get the current state of a RAG notebook.

    The state contains the draft experiment configuration including
    RAG configs, dataset, and evaluations.
    """
    try:
        repo = RagNotebookRepository(db_session)
        state = repo.get_notebook_state(notebook_id)
        return state
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@rag_notebook_routes.put(
    "/rag_notebooks/{notebook_id}/state",
    summary="Set RAG notebook state",
    description="Set the state (draft configuration) of a RAG notebook",
    response_model=RagNotebookDetail,
    response_model_exclude_none=True,
    tags=["RAG Notebooks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def set_rag_notebook_state(
    state_request: SetRagNotebookStateRequest,
    notebook_id: str = Path(..., description="RAG Notebook ID"),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> RagNotebookDetail:
    """
    Set the state of a RAG notebook.

    The state contains the draft experiment configuration including
    RAG configs, dataset, and evaluations. This completely
    replaces the current state.
    """
    try:
        repo = RagNotebookRepository(db_session)
        notebook = repo.set_notebook_state(notebook_id, state_request)
        return notebook
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@rag_notebook_routes.delete(
    "/rag_notebooks/{notebook_id}",
    summary="Delete RAG notebook",
    description="Delete a RAG notebook (experiments are kept)",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["RAG Notebooks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def delete_rag_notebook(
    notebook_id: str = Path(..., description="RAG Notebook ID"),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> Response:
    """
    Delete a RAG notebook.

    All experiments that were run from this notebook are preserved,
    but will no longer be linked to the notebook.
    """
    try:
        repo = RagNotebookRepository(db_session)
        repo.delete_notebook(notebook_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@rag_notebook_routes.get(
    "/rag_notebooks/{notebook_id}/history",
    summary="Get RAG notebook history",
    description="Get paginated list of experiments run from this RAG notebook",
    response_model=RagExperimentListResponse,
    response_model_exclude_none=True,
    tags=["RAG Notebooks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_rag_notebook_history(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    notebook_id: str = Path(..., description="RAG Notebook ID"),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> RagExperimentListResponse:
    """
    Get the history of experiments run from this RAG notebook.

    Returns a paginated list of experiment summaries for all experiments
    that were created by running this notebook.
    """
    try:
        repo = RagNotebookRepository(db_session)
        response = repo.get_notebook_history(
            notebook_id=notebook_id,
            pagination_params=pagination_parameters,
        )
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()
