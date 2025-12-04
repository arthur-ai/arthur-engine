from typing import Annotated

from arthur_common.models.common_schemas import PaginationParameters
from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy.orm import Session

from dependencies import get_db_session, get_validated_agentic_task
from repositories.notebook_repository import NotebookRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import Task, User
from schemas.notebook_schemas import (
    CreateNotebookRequest,
    NotebookDetail,
    NotebookListResponse,
    NotebookState,
    SetNotebookStateRequest,
    UpdateNotebookRequest,
)
from schemas.prompt_experiment_schemas import (
    PromptExperimentListResponse,
)
from utils.users import permission_checker
from utils.utils import common_pagination_parameters

notebook_routes = APIRouter(
    prefix="/api/v1",
    route_class=GenaiEngineRoute,
)


@notebook_routes.post(
    "/tasks/{task_id}/notebooks",
    summary="Create a notebook",
    description="Create a new notebook for organizing experiments within a task",
    response_model=NotebookDetail,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
    tags=["Notebooks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def create_notebook(
    notebook_request: CreateNotebookRequest,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
):
    """
    Create a new notebook for a task.

    Notebooks are draft experiment configurations that can be edited
    and executed multiple times to create experiment runs.
    """
    try:
        repo = NotebookRepository(db_session)
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


@notebook_routes.get(
    "/tasks/{task_id}/notebooks",
    summary="List notebooks",
    description="List all notebooks for a task with pagination and optional name search",
    response_model=NotebookListResponse,
    response_model_exclude_none=True,
    tags=["Notebooks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def list_notebooks(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    name: str | None = None,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
):
    """
    List all notebooks for a given task.

    Returns paginated list of notebook summaries. Optionally filter by exact name match.
    """
    try:
        repo = NotebookRepository(db_session)
        response = repo.list_notebooks(
            task_id=task.id,
            pagination_params=pagination_parameters,
            name_filter=name,
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@notebook_routes.get(
    "/notebooks/{notebook_id}",
    summary="Get notebook details",
    description="Get detailed information about a notebook including state and experiment history",
    response_model=NotebookDetail,
    response_model_exclude_none=True,
    tags=["Notebooks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_notebook(
    notebook_id: str = Path(..., description="Notebook ID"),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """
    Get detailed information about a notebook.

    Includes the current state (draft configuration) and history
    of all experiments run from this notebook.
    """
    try:
        repo = NotebookRepository(db_session)
        notebook = repo.get_notebook(notebook_id)
        return notebook
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@notebook_routes.put(
    "/notebooks/{notebook_id}",
    summary="Update notebook metadata",
    description="Update notebook name or description (not the state)",
    response_model=NotebookDetail,
    response_model_exclude_none=True,
    tags=["Notebooks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def update_notebook(
    update_request: UpdateNotebookRequest,
    notebook_id: str = Path(..., description="Notebook ID"),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """
    Update notebook metadata (name and/or description).

    To update the notebook state (prompts, dataset, etc.), use the
    set_notebook_state endpoint instead.
    """
    try:
        repo = NotebookRepository(db_session)
        notebook = repo.update_notebook(notebook_id, update_request)
        return notebook
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@notebook_routes.get(
    "/notebooks/{notebook_id}/state",
    summary="Get notebook state",
    description="Get the current state (draft configuration) of a notebook",
    response_model=NotebookState,
    response_model_exclude_none=True,
    tags=["Notebooks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_notebook_state(
    notebook_id: str = Path(..., description="Notebook ID"),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """
    Get the current state of a notebook.

    The state contains the draft experiment configuration including
    prompts, dataset, variables, and evaluations.
    """
    try:
        repo = NotebookRepository(db_session)
        state = repo.get_notebook_state(notebook_id)
        return state
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@notebook_routes.put(
    "/notebooks/{notebook_id}/state",
    summary="Set notebook state",
    description="Set the state (draft configuration) of a notebook",
    response_model=NotebookDetail,
    response_model_exclude_none=True,
    tags=["Notebooks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def set_notebook_state(
    state_request: SetNotebookStateRequest,
    notebook_id: str = Path(..., description="Notebook ID"),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """
    Set the state of a notebook.

    The state contains the draft experiment configuration including
    prompts, dataset, variables, and evaluations. This completely
    replaces the current state.
    """
    try:
        repo = NotebookRepository(db_session)
        notebook = repo.set_notebook_state(notebook_id, state_request)
        return notebook
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@notebook_routes.delete(
    "/notebooks/{notebook_id}",
    summary="Delete notebook",
    description="Delete a notebook (experiments are kept)",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Notebooks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def delete_notebook(
    notebook_id: str = Path(..., description="Notebook ID"),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> Response:
    """
    Delete a notebook.

    All experiments that were run from this notebook are preserved,
    but will no longer be linked to the notebook.
    """
    try:
        repo = NotebookRepository(db_session)
        repo.delete_notebook(notebook_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@notebook_routes.get(
    "/notebooks/{notebook_id}/history",
    summary="Get notebook history",
    description="Get paginated list of experiments run from this notebook",
    response_model=PromptExperimentListResponse,
    response_model_exclude_none=True,
    tags=["Notebooks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_notebook_history(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    notebook_id: str = Path(..., description="Notebook ID"),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """
    Get the history of experiments run from this notebook.

    Returns a paginated list of experiment summaries for all experiments
    that were created by running this notebook.
    """
    try:
        repo = NotebookRepository(db_session)
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
