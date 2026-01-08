from typing import Annotated

from arthur_common.models.common_schemas import PaginationParameters
from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy.orm import Session

from dependencies import get_db_session, get_validated_task
from repositories.agentic_notebook_repository import AgenticNotebookRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.agentic_experiment_schemas import (
    AgenticExperimentListResponse,
)
from schemas.agentic_notebook_schemas import (
    AgenticNotebookDetail,
    AgenticNotebookListResponse,
    AgenticNotebookStateResponse,
    CreateAgenticNotebookRequest,
    SetAgenticNotebookStateRequest,
    UpdateAgenticNotebookRequest,
)
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import Task, User
from utils.users import permission_checker
from utils.utils import common_pagination_parameters

agentic_notebook_routes = APIRouter(
    prefix="/api/v1",
    route_class=GenaiEngineRoute,
)


@agentic_notebook_routes.post(
    "/tasks/{task_id}/agentic_notebooks",
    summary="Create an agentic notebook",
    description="Create a new agentic notebook for organizing experiments within a task",
    response_model=AgenticNotebookDetail,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
    tags=["Agentic Notebooks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def create_agentic_notebook(
    notebook_request: CreateAgenticNotebookRequest,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
):
    """
    Create a new agentic notebook for a task.

    Agentic notebooks are draft experiment configurations that can be edited
    and executed multiple times to create experiment runs.
    """
    try:
        repo = AgenticNotebookRepository(db_session)
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


@agentic_notebook_routes.get(
    "/tasks/{task_id}/agentic_notebooks",
    summary="List agentic notebooks",
    description="List all agentic notebooks for a task with pagination and optional name search",
    response_model=AgenticNotebookListResponse,
    response_model_exclude_none=True,
    tags=["Agentic Notebooks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def list_agentic_notebooks(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    name: str | None = None,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
):
    """
    List all agentic notebooks for a given task.

    Returns paginated list of notebook summaries. Optionally filter by exact name match.
    """
    try:
        repo = AgenticNotebookRepository(db_session)
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


@agentic_notebook_routes.get(
    "/agentic_notebooks/{notebook_id}",
    summary="Get agentic notebook details",
    description="Get detailed information about an agentic notebook including state and experiment history",
    response_model=AgenticNotebookDetail,
    response_model_exclude_none=True,
    tags=["Agentic Notebooks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_agentic_notebook(
    notebook_id: str = Path(..., description="Agentic Notebook ID"),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """
    Get detailed information about an agentic notebook.

    Includes the current state (draft configuration) and history
    of all experiments run from this notebook.
    """
    try:
        repo = AgenticNotebookRepository(db_session)
        notebook = repo.get_notebook(notebook_id)
        return notebook
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@agentic_notebook_routes.put(
    "/agentic_notebooks/{notebook_id}",
    summary="Update agentic notebook metadata",
    description="Update agentic notebook name or description (not the state)",
    response_model=AgenticNotebookDetail,
    response_model_exclude_none=True,
    tags=["Agentic Notebooks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def update_agentic_notebook(
    update_request: UpdateAgenticNotebookRequest,
    notebook_id: str = Path(..., description="Agentic Notebook ID"),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """
    Update agentic notebook metadata (name and/or description).

    To update the notebook state (HTTP template, dataset, etc.), use the
    set_agentic_notebook_state endpoint instead.
    """
    try:
        repo = AgenticNotebookRepository(db_session)
        notebook = repo.update_notebook(notebook_id, update_request)
        return notebook
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@agentic_notebook_routes.get(
    "/agentic_notebooks/{notebook_id}/state",
    summary="Get agentic notebook state",
    description="Get the current state (draft configuration) of an agentic notebook",
    response_model=AgenticNotebookStateResponse,
    response_model_exclude_none=True,
    tags=["Agentic Notebooks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_agentic_notebook_state(
    notebook_id: str = Path(..., description="Agentic Notebook ID"),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """
    Get the current state of an agentic notebook.

    The state contains the draft experiment configuration including
    HTTP template, dataset, and evaluations.
    """
    try:
        repo = AgenticNotebookRepository(db_session)
        state = repo.get_notebook_state(notebook_id)
        return state
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@agentic_notebook_routes.put(
    "/agentic_notebooks/{notebook_id}/state",
    summary="Set agentic notebook state",
    description="Set the state (draft configuration) of an agentic notebook",
    response_model=AgenticNotebookDetail,
    response_model_exclude_none=True,
    tags=["Agentic Notebooks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def set_agentic_notebook_state(
    state_request: SetAgenticNotebookStateRequest,
    notebook_id: str = Path(..., description="Agentic Notebook ID"),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """
    Set the state of an agentic notebook.

    The state contains the draft experiment configuration including
    HTTP template, dataset, and evaluations. This completely
    replaces the current state.
    """
    try:
        repo = AgenticNotebookRepository(db_session)
        notebook = repo.set_notebook_state(notebook_id, state_request)
        return notebook
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@agentic_notebook_routes.delete(
    "/agentic_notebooks/{notebook_id}",
    summary="Delete agentic notebook",
    description="Delete an agentic notebook (experiments are kept)",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Agentic Notebooks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def delete_agentic_notebook(
    notebook_id: str = Path(..., description="Agentic Notebook ID"),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> Response:
    """
    Delete an agentic notebook.

    All experiments that were run from this notebook are preserved,
    but will no longer be linked to the notebook.
    """
    try:
        repo = AgenticNotebookRepository(db_session)
        repo.delete_notebook(notebook_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@agentic_notebook_routes.get(
    "/agentic_notebooks/{notebook_id}/history",
    summary="Get agentic notebook history",
    description="Get paginated list of experiments run from this agentic notebook",
    response_model=AgenticExperimentListResponse,
    response_model_exclude_none=True,
    tags=["Agentic Notebooks"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_agentic_notebook_history(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    notebook_id: str = Path(..., description="Agentic Notebook ID"),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """
    Get the history of experiments run from this agentic notebook.

    Returns a paginated list of experiment summaries for all experiments
    that were created by running this notebook.
    """
    try:
        repo = AgenticNotebookRepository(db_session)
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
