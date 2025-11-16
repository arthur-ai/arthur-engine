from typing import Annotated
from uuid import uuid4

from arthur_common.models.common_schemas import PaginationParameters
from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy.orm import Session

from dependencies import get_db_session, get_validated_agentic_task
from repositories.prompt_experiment_repository import PromptExperimentRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import Task, User
from schemas.prompt_experiment_schemas import (
    CreatePromptExperimentRequest,
    PromptExperimentDetail,
    PromptExperimentListResponse,
    PromptExperimentSummary,
    TestCaseListResponse,
)
from services.experiment_executor import ExperimentExecutor
from utils.users import permission_checker
from utils.utils import common_pagination_parameters

prompt_experiment_routes = APIRouter(
    prefix="/api/v1",
    route_class=GenaiEngineRoute,
)


@prompt_experiment_routes.get(
    "/tasks/{task_id}/prompt_experiments",
    summary="List prompt experiments",
    description="List all prompt experiments for a task with optional filtering and pagination",
    response_model=PromptExperimentListResponse,
    response_model_exclude_none=True,
    tags=["Prompt Experiments"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def list_prompt_experiments(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
):
    """
    List all prompt experiments for a given task.

    Returns paginated list of experiment summaries.
    """
    try:
        repo = PromptExperimentRepository(db_session)
        experiments, total_count = repo.list_experiments(
            task_id=task.id,
            pagination_params=pagination_parameters,
        )

        page = pagination_parameters.page
        page_size = pagination_parameters.page_size
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0

        return PromptExperimentListResponse(
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


@prompt_experiment_routes.post(
    "/tasks/{task_id}/prompt_experiments",
    summary="Create and run a prompt experiment",
    description="Create a new prompt experiment and initiate execution",
    response_model=PromptExperimentSummary,
    response_model_exclude_none=True,
    status_code=status.HTTP_200_OK,
    tags=["Prompt Experiments"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def create_prompt_experiment(
    experiment_request: CreatePromptExperimentRequest,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
):
    """
    Create a new prompt experiment and start execution.

    The experiment will test the specified prompt versions against the dataset
    using the configured evaluations.
    """
    try:
        # Generate a unique experiment ID
        experiment_id = str(uuid4())

        repo = PromptExperimentRepository(db_session)
        experiment = repo.create_experiment(
            task_id=task.id,
            experiment_id=experiment_id,
            request=experiment_request,
        )

        # Kick off async execution of the experiment
        executor = ExperimentExecutor()
        executor.execute_experiment_async(experiment_id)

        return experiment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@prompt_experiment_routes.get(
    "/prompt_experiments/{experiment_id}",
    summary="Get prompt experiment details",
    description="Get detailed information about a specific prompt experiment including summary results",
    response_model=PromptExperimentDetail,
    response_model_exclude_none=True,
    tags=["Prompt Experiments"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_prompt_experiment(
    experiment_id: str = Path(
        ...,
        description="The ID of the experiment to retrieve",
        title="Experiment ID",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """
    Get detailed information about a prompt experiment.

    Returns full experiment configuration and summary results across all test cases.
    """
    try:
        repo = PromptExperimentRepository(db_session)
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


@prompt_experiment_routes.get(
    "/prompt_experiments/{experiment_id}/test_cases",
    summary="Get experiment test cases",
    description="Get paginated list of test case results for a prompt experiment",
    response_model=TestCaseListResponse,
    response_model_exclude_none=True,
    tags=["Prompt Experiments"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_experiment_test_cases(
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
    Get detailed test case results for an experiment.

    Returns paginated list of individual test cases with their inputs, outputs,
    and evaluation results.
    """
    try:
        repo = PromptExperimentRepository(db_session)
        test_cases, total_count = repo.get_test_cases(
            experiment_id=experiment_id,
            pagination_params=pagination_parameters,
        )

        page = pagination_parameters.page
        page_size = pagination_parameters.page_size
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0

        return TestCaseListResponse(
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


@prompt_experiment_routes.delete(
    "/prompt_experiments/{experiment_id}",
    summary="Delete prompt experiment",
    description="Delete a prompt experiment and all its associated data",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_204_NO_CONTENT: {"description": "Experiment deleted successfully."}
    },
    tags=["Prompt Experiments"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def delete_prompt_experiment(
    experiment_id: str = Path(
        ...,
        description="The ID of the experiment to delete",
        title="Experiment ID",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> Response:
    """
    Delete a prompt experiment.

    This will remove the experiment and all associated test case results.
    This operation cannot be undone.
    """
    try:
        repo = PromptExperimentRepository(db_session)
        repo.delete_experiment(experiment_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
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
