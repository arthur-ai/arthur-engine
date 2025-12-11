from typing import Annotated, Optional
from uuid import UUID, uuid4

from arthur_common.models.common_schemas import PaginationParameters
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session

from dependencies import get_db_session, get_validated_agentic_task
from repositories.rag_experiment_repository import RagExperimentRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import Task, User
from schemas.rag_experiment_schemas import (
    CreateRagExperimentRequest,
    RagConfigResultListResponse,
    RagExperimentDetail,
    RagExperimentListResponse,
    RagExperimentSummary,
    RagTestCaseListResponse,
)
from services.rag_experiment_executor import RagExperimentExecutor
from utils.users import permission_checker
from utils.utils import common_pagination_parameters

rag_experiment_routes = APIRouter(
    prefix="/api/v1",
    route_class=GenaiEngineRoute,
)


@rag_experiment_routes.get(
    "/tasks/{task_id}/rag_experiments",
    summary="List RAG experiments",
    description="List all RAG experiments for a task with optional filtering and pagination",
    response_model=RagExperimentListResponse,
    response_model_exclude_none=True,
    tags=["RAG Experiments"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def list_rag_experiments(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    search: Optional[str] = Query(
        None,
        description="Search text to filter experiments by name or description",
    ),
    dataset_id: Optional[UUID] = Query(
        None,
        description="Filter experiments by dataset ID",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
):
    """
    List all RAG experiments for a given task.

    Returns paginated list of experiment summaries.
    Optionally filter by search text matching experiment name or description.
    Optionally filter by dataset ID.
    """
    try:
        repo = RagExperimentRepository(db_session)
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

        return RagExperimentListResponse(
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


@rag_experiment_routes.post(
    "/tasks/{task_id}/rag_experiments",
    summary="Create and run a RAG experiment",
    description="Create a new RAG experiment and initiate execution",
    response_model=RagExperimentSummary,
    response_model_exclude_none=True,
    status_code=status.HTTP_200_OK,
    tags=["RAG Experiments"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def create_rag_experiment(
    experiment_request: CreateRagExperimentRequest,
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    task: Task = Depends(get_validated_agentic_task),
):
    """
    Create a new RAG experiment and start execution.

    The experiment will test the specified RAG configurations
    against the dataset using the configured evaluations.
    """
    try:
        # Validate at least one RAG config is provided
        if (
            not experiment_request.rag_configs
            or len(experiment_request.rag_configs) == 0
        ):
            raise HTTPException(
                status_code=400,
                detail="At least one RAG configuration is required",
            )

        # Check for duplicate RAG configs
        rag_config_keys_seen = set()
        for config in experiment_request.rag_configs:
            if config.type == "saved":
                key = f"saved:{config.setting_configuration_id}:{config.version}"
            else:  # unsaved
                # For unsaved configs, we check for identical settings/provider combinations
                # using the unsaved_id UUID
                key = f"unsaved:{config.unsaved_id}"

            if key in rag_config_keys_seen:
                raise HTTPException(
                    status_code=400,
                    detail=f"Duplicate RAG configuration detected: {key}",
                )
            rag_config_keys_seen.add(key)

        # Generate a unique experiment ID
        experiment_id = str(uuid4())

        repo = RagExperimentRepository(db_session)
        experiment = repo.create_experiment(
            task_id=task.id,
            experiment_id=experiment_id,
            request=experiment_request,
        )

        # Kick off async execution of the experiment
        executor = RagExperimentExecutor()
        executor.execute_experiment_async(experiment_id)

        return experiment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@rag_experiment_routes.get(
    "/rag_experiments/{experiment_id}",
    summary="Get RAG experiment details",
    description="Get detailed information about a specific RAG experiment including summary results",
    response_model=RagExperimentDetail,
    response_model_exclude_none=True,
    tags=["RAG Experiments"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_rag_experiment(
    experiment_id: str = Path(
        ...,
        description="The ID of the experiment to retrieve",
        title="Experiment ID",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
):
    """
    Get detailed information about a RAG experiment.

    Returns full experiment configuration and summary results across all test cases.
    """
    try:
        repo = RagExperimentRepository(db_session)
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


@rag_experiment_routes.get(
    "/rag_experiments/{experiment_id}/test_cases",
    summary="Get experiment test cases",
    description="Get paginated list of test case results for a RAG experiment",
    response_model=RagTestCaseListResponse,
    response_model_exclude_none=True,
    tags=["RAG Experiments"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_rag_experiment_test_cases(
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
    Get detailed test case results for a RAG experiment.

    Returns paginated list of individual test cases with their inputs, RAG search outputs,
    and evaluation results.
    """
    try:
        repo = RagExperimentRepository(db_session)
        test_cases, total_count = repo.get_test_cases(
            experiment_id=experiment_id,
            pagination_parameters=pagination_parameters,
        )

        page = pagination_parameters.page
        page_size = pagination_parameters.page_size
        total_pages = (
            (total_count + page_size - 1) // page_size if total_count > 0 else 0
        )

        return RagTestCaseListResponse(
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


@rag_experiment_routes.get(
    "/rag_experiments/{experiment_id}/rag_configs/{rag_config_key}/results",
    summary="Get RAG config results",
    description="Get paginated list of results for a specific RAG configuration within an experiment (supports both saved and unsaved configs)",
    response_model=RagConfigResultListResponse,
    response_model_exclude_none=True,
    tags=["RAG Experiments"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_READ.value)
def get_rag_config_results(
    pagination_parameters: Annotated[
        PaginationParameters,
        Depends(common_pagination_parameters),
    ],
    experiment_id: str = Path(
        ...,
        description="The ID of the experiment",
        title="Experiment ID",
    ),
    rag_config_key: str = Path(
        ...,
        description="The RAG config key (format: 'saved:setting_config_id:version' or 'unsaved:uuid'). URL-encode colons as %3A",
        title="RAG Config Key",
    ),
    db_session: Session = Depends(get_db_session),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> RagConfigResultListResponse:
    """
    Get detailed results for a specific RAG configuration within an experiment.

    Returns paginated list of results showing inputs, query text, RAG search outputs,
    and evaluation results for the specified RAG configuration across all test cases.

    The rag_config_key parameter should be:
    - For saved configs: 'saved:setting_config_id:version' (e.g., 'saved:123e4567-e89b-12d3-a456-426614174000:1')
    - For unsaved configs: 'unsaved:uuid' (e.g., 'unsaved:123e4567-e89b-12d3-a456-426614174000')

    Note: Colons in the rag_config_key should be URL-encoded as %3A in the URL path.
    """
    try:
        repo = RagExperimentRepository(db_session)
        results, total_count = repo.get_rag_config_results(
            experiment_id=experiment_id,
            rag_config_key=rag_config_key,
            pagination_parameters=pagination_parameters,
        )

        page = pagination_parameters.page
        page_size = pagination_parameters.page_size
        total_pages = (
            (total_count + page_size - 1) // page_size if total_count > 0 else 0
        )

        return RagConfigResultListResponse(
            data=results,
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
