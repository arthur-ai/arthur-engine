from typing import Annotated, Optional
from uuid import UUID, uuid4

from arthur_common.models.common_schemas import PaginationParameters
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.orm import Session

from dependencies import get_db_session, get_validated_task
from repositories.agentic_experiment_repository import AgenticExperimentRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.agentic_experiment_schemas import (
    AgenticExperimentDetail,
    AgenticExperimentListResponse,
    AgenticExperimentSummary,
    AgenticTestCaseListResponse,
    CreateAgenticExperimentRequest,
)
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import Task, User
from services.agentic_experiment_executor import AgenticExperimentExecutor
from utils.users import permission_checker
from utils.utils import common_pagination_parameters

agentic_experiment_routes = APIRouter(
    prefix="/api/v1",
    route_class=GenaiEngineRoute,
)


@agentic_experiment_routes.get(
    "/tasks/{task_id}/agentic_experiments",
    summary="List agentic experiments",
    description="List all agentic experiments for a task with optional filtering and pagination",
    response_model=AgenticExperimentListResponse,
    response_model_exclude_none=True,
    tags=["Agentic Experiments"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def list_agentic_experiments(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    search: Optional[str] = None,
    dataset_id: Optional[UUID] = None,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
):
    """
    List all agentic experiments for a given task.

    Returns paginated list of experiment summaries.
    Optionally filter by search text matching experiment name or description.
    Optionally filter by dataset ID.
    """
    try:
        repo = AgenticExperimentRepository(db_session)
        experiments, total_count = repo.list_experiments(
            task_id=task.id,
            pagination_parameters=pagination_parameters,
            search=search,
            dataset_id=dataset_id,
        )

        page = pagination_parameters.page
        page_size = pagination_parameters.page_size
        total_pages = (
            (total_count + page_size - 1) // page_size if total_count > 0 else 0
        )

        return AgenticExperimentListResponse(
            data=experiments,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            total_count=total_count,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@agentic_experiment_routes.post(
    "/tasks/{task_id}/agentic_experiments",
    summary="Create and run an agentic experiment",
    description="Create a new agentic experiment and initiate execution",
    response_model=AgenticExperimentSummary,
    response_model_exclude_none=True,
    status_code=status.HTTP_200_OK,
    tags=["Agentic Experiments"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def create_agentic_experiment(
    experiment_request: CreateAgenticExperimentRequest,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_task),
):
    """
    Create a new agentic experiment and start execution.

    The experiment will test the specified HTTP template configuration
    against the dataset using the configured evaluations with transforms.
    """
    try:
        # Validate at least one eval is provided
        if not experiment_request.eval_list or len(experiment_request.eval_list) == 0:
            raise HTTPException(
                status_code=400,
                detail="At least one evaluation configuration is required",
            )

        # Generate a unique experiment ID
        experiment_id = str(uuid4())

        repo = AgenticExperimentRepository(db_session)
        experiment = repo.create_experiment(
            task_id=task.id,
            experiment_id=experiment_id,
            request=experiment_request,
        )

        # Kick off async execution of the experiment
        # Pass request-time parameters directly to the thread (not stored in DB for security considerations)
        executor = AgenticExperimentExecutor()
        executor.execute_experiment_async(
            experiment_id,
            request_time_parameters=experiment_request.request_time_parameters,
        )

        return experiment
    except HTTPException:
        raise
    except ValueError as e:
        # Convert any remaining ValueErrors to HTTP 400
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@agentic_experiment_routes.get(
    "/agentic_experiments/{experiment_id}",
    summary="Get agentic experiment details",
    description="Get detailed information about a specific agentic experiment including summary results",
    response_model=AgenticExperimentDetail,
    response_model_exclude_none=True,
    tags=["Agentic Experiments"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_agentic_experiment(
    experiment_id: str = Path(
        ...,
        description="The ID of the experiment to retrieve",
        title="Experiment ID",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """
    Get detailed information about an agentic experiment.

    Returns full experiment configuration and summary results across all test cases.
    """
    try:
        repo = AgenticExperimentRepository(db_session)
        return repo.get_experiment(experiment_id)
    except HTTPException:
        raise
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@agentic_experiment_routes.get(
    "/agentic_experiments/{experiment_id}/test_cases",
    summary="Get experiment test cases",
    description="Get paginated list of test case results for an agentic experiment",
    response_model=AgenticTestCaseListResponse,
    response_model_exclude_none=True,
    tags=["Agentic Experiments"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_agentic_experiment_test_cases(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    experiment_id: str = Path(
        ...,
        description="The ID of the experiment",
        title="Experiment ID",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """
    Get detailed test case results for an agentic experiment.

    Returns paginated list of individual test cases with their inputs, agent outputs,
    and evaluation results.
    """
    try:
        repo = AgenticExperimentRepository(db_session)
        test_cases, total_count = repo.get_test_cases(
            experiment_id=experiment_id,
            pagination_parameters=pagination_parameters,
        )

        page = pagination_parameters.page
        page_size = pagination_parameters.page_size
        total_pages = (
            (total_count + page_size - 1) // page_size if total_count > 0 else 0
        )

        return AgenticTestCaseListResponse(
            data=test_cases,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            total_count=total_count,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@agentic_experiment_routes.delete(
    "/agentic_experiments/{experiment_id}",
    summary="Delete agentic experiment",
    description="Delete an agentic experiment and all its associated data",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_204_NO_CONTENT: {"description": "Experiment deleted successfully."},
    },
    tags=["Agentic Experiments"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def delete_agentic_experiment(
    experiment_id: str = Path(
        ...,
        description="The ID of the experiment to delete",
        title="Experiment ID",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> Response:
    """
    Delete an agentic experiment.

    This will remove the experiment and all associated test case results.
    This operation cannot be undone.
    """
    try:
        repo = AgenticExperimentRepository(db_session)
        repo.delete_experiment(experiment_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@agentic_experiment_routes.patch(
    "/agentic_experiments/{experiment_id}/notebook",
    summary="Attach notebook to agentic experiment",
    description="Attach an agentic notebook to an existing experiment",
    response_model=AgenticExperimentSummary,
    response_model_exclude_none=True,
    tags=["Agentic Experiments"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def attach_notebook_to_agentic_experiment(
    experiment_id: str = Path(..., description="ID of the experiment"),
    notebook_id: str = Query(..., description="ID of the notebook to attach"),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> AgenticExperimentSummary:
    """Attach an agentic notebook to an existing experiment."""
    try:
        repo = AgenticExperimentRepository(db_session)
        return repo.attach_notebook_to_experiment(experiment_id, notebook_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()
