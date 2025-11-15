from typing import Annotated
from uuid import uuid4

from arthur_common.models.common_schemas import PaginationParameters
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.orm import Session

from dependencies import get_db_session, get_validated_agentic_task
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import Task, User
from schemas.prompt_experiment_schemas import (
    CreateExperimentRequest,
    EvalExecution,
    EvalRef,
    EvalResult,
    EvalResults,
    ExperimentDetail,
    ExperimentListResponse,
    ExperimentStatus,
    ExperimentSummary,
    InputVariable,
    PromptEvalSummary,
    PromptOutput,
    PromptResult,
    SummaryResults,
    TestCase,
    TestCaseListResponse,
    TestCaseStatus,
)
from utils.users import permission_checker
from utils.utils import common_pagination_parameters

prompt_experiment_routes = APIRouter(
    prefix="/api/v1",
    route_class=GenaiEngineRoute,
)


# Mock data generators for the endpoints
def _generate_mock_experiment_summary(
    experiment_id: str,
    name: str,
    prompt_name: str,
) -> ExperimentSummary:
    """Generate mock experiment summary data"""
    return ExperimentSummary(
        id=experiment_id,
        name=name,
        created_at="2025-01-15T10:30:00Z",
        finished_at="2025-01-15T11:45:00Z",
        status=ExperimentStatus.COMPLETED,
        prompt_name=prompt_name,
        total_rows=100,
    )


def _generate_mock_experiment_detail(
    experiment_id: str,
    request: CreateExperimentRequest,
) -> ExperimentDetail:
    """Generate mock experiment detail data"""
    # Generate mock summary results
    prompt_eval_summaries = []
    for version in request.prompt_ref.version_list:
        eval_results = []
        for eval_ref in request.eval_list:
            eval_results.append(
                EvalResult(
                    eval_name=eval_ref.name,
                    eval_version=eval_ref.version,
                    pass_count=85,
                    total_count=100,
                )
            )

        prompt_eval_summaries.append(
            PromptEvalSummary(
                prompt_name=request.prompt_ref.name,
                prompt_version=version,
                eval_results=eval_results,
            )
        )

    summary_results = SummaryResults(prompt_eval_summaries=prompt_eval_summaries)

    return ExperimentDetail(
        id=experiment_id,
        name=request.name,
        created_at="2025-01-15T10:30:00Z",
        finished_at="2025-01-15T11:45:00Z",
        status=ExperimentStatus.COMPLETED,
        prompt_name=request.prompt_ref.name,
        dataset_ref=request.dataset_ref,
        prompt_ref=request.prompt_ref,
        eval_list=request.eval_list,
        summary_results=summary_results,
    )


def _generate_mock_test_cases(
    prompt_versions: list[str],
    eval_refs: list[EvalRef],
    num_cases: int = 10,
) -> list[TestCase]:
    """Generate mock test case data"""
    test_cases = []

    for i in range(num_cases):
        # Generate mock input variables
        input_variables = [
            InputVariable(variable_name="query", value=f"Sample query {i+1}"),
            InputVariable(variable_name="context", value=f"Sample context {i+1}"),
        ]

        # Generate mock prompt results for each version
        prompt_results = []
        for version in prompt_versions:
            # Generate mock evals
            evals = []
            for eval_ref in eval_refs:
                evals.append(
                    EvalExecution(
                        eval_name=eval_ref.name,
                        eval_version=eval_ref.version,
                        eval_input_variables=[
                            InputVariable(
                                variable_name="response",
                                value=f"Sample response {i+1}",
                            )
                        ],
                        eval_results=EvalResults(
                            score=0.85,
                            explanation="Response meets quality criteria",
                            cost=0.002,
                        ),
                    )
                )

            prompt_results.append(
                PromptResult(
                    name="test_prompt",
                    version=version,
                    rendered_input=f"Rendered prompt for test case {i+1}",
                    output=PromptOutput(
                        content=f"Generated response for test case {i+1}",
                        tool_calls=[],
                        cost="0.005",
                    ),
                    evals=evals,
                )
            )

        test_cases.append(
            TestCase(
                status=TestCaseStatus.COMPLETED,
                retries=0,
                dataset_row_id=f"row_{i+1}",
                prompt_input_variables=input_variables,
                prompt_results=prompt_results,
            )
        )

    return test_cases


@prompt_experiment_routes.get(
    "/tasks/{task_id}/prompt_experiments",
    summary="List prompt experiments",
    description="List all prompt experiments for a task with optional filtering and pagination",
    response_model=ExperimentListResponse,
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
        # Mock data - in production, this would query the database
        mock_experiments = [
            _generate_mock_experiment_summary(
                experiment_id=f"exp_{i}",
                name=f"Experiment {i}",
                prompt_name=f"prompt_v{i}",
            )
            for i in range(1, 6)
        ]

        page = pagination_parameters.page
        page_size = pagination_parameters.page_size

        total_count = len(mock_experiments)
        total_pages = (total_count + page_size - 1) // page_size

        start_idx = page * page_size
        end_idx = start_idx + page_size
        paginated_data = mock_experiments[start_idx:end_idx]

        return ExperimentListResponse(
            data=paginated_data,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            total_count=total_count,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@prompt_experiment_routes.post(
    "/tasks/{task_id}/prompt_experiments",
    summary="Create and run a prompt experiment",
    description="Create a new prompt experiment and initiate execution",
    response_model=ExperimentSummary,
    response_model_exclude_none=True,
    status_code=status.HTTP_200_OK,
    tags=["Prompt Experiments"],
)
@permission_checker(permissions=PermissionLevelsEnum.TASK_WRITE.value)
def create_prompt_experiment(
    experiment_request: CreateExperimentRequest,
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

        # Mock response - in production, this would create the experiment in the database
        # and kick off async execution
        return _generate_mock_experiment_summary(
            experiment_id=experiment_id,
            name=experiment_request.name,
            prompt_name=experiment_request.prompt_ref.name,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@prompt_experiment_routes.get(
    "/tasks/{task_id}/prompt_experiments/{experiment_id}",
    summary="Get prompt experiment details",
    description="Get detailed information about a specific prompt experiment including summary results",
    response_model=ExperimentDetail,
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
    task: Task = Depends(get_validated_agentic_task),
):
    """
    Get detailed information about a prompt experiment.

    Returns full experiment configuration and summary results across all test cases.
    """
    try:
        # Mock data - in production, this would query the database
        mock_request = CreateExperimentRequest(
            name="Sample Experiment",
            dataset_ref={"id": "dataset_123", "version": "v1"},
            prompt_ref={
                "name": "test_prompt",
                "version_list": ["v1", "v2"],
                "variable_mapping": [
                    {
                        "variable_name": "query",
                        "source": {
                            "type": "dataset_column",
                            "dataset_column": {"name": "user_query"},
                        },
                    }
                ],
            },
            eval_list=[
                {
                    "name": "relevance_eval",
                    "version": "v1",
                    "variable_mapping": [
                        {
                            "variable_name": "response",
                            "source": {
                                "type": "experiment_output",
                                "experiment_output": {"json_path": "$.content"},
                            },
                        }
                    ],
                }
            ],
        )

        return _generate_mock_experiment_detail(experiment_id, mock_request)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@prompt_experiment_routes.get(
    "/tasks/{task_id}/prompt_experiments/{experiment_id}/test_cases",
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
    task: Task = Depends(get_validated_agentic_task),
):
    """
    Get detailed test case results for an experiment.

    Returns paginated list of individual test cases with their inputs, outputs,
    and evaluation results.
    """
    try:
        # Mock data - in production, this would query the database
        mock_test_cases = _generate_mock_test_cases(
            prompt_versions=["v1", "v2"],
            eval_refs=[
                EvalRef(
                    name="relevance_eval",
                    version="v1",
                    variable_mapping=[
                        {
                            "variable_name": "response",
                            "source": {
                                "type": "experiment_output",
                                "experiment_output": {"json_path": "$.content"},
                            },
                        }
                    ],
                )
            ],
            num_cases=25,
        )

        page = pagination_parameters.page
        page_size = pagination_parameters.page_size

        total_count = len(mock_test_cases)
        total_pages = (total_count + page_size - 1) // page_size

        start_idx = page * page_size
        end_idx = start_idx + page_size
        paginated_data = mock_test_cases[start_idx:end_idx]

        return TestCaseListResponse(
            data=paginated_data,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            total_count=total_count,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@prompt_experiment_routes.delete(
    "/tasks/{task_id}/prompt_experiments/{experiment_id}",
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
    task: Task = Depends(get_validated_agentic_task),
) -> Response:
    """
    Delete a prompt experiment.

    This will remove the experiment and all associated test case results.
    This operation cannot be undone.
    """
    try:
        # Mock deletion - in production, this would delete from the database
        # For now, just return success
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
