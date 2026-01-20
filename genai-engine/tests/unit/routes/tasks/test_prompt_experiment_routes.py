"""
Unit tests for prompt experiment routes.

This module tests the prompt experiment API endpoints:
- Creating and running a prompt experiment
- Getting prompt experiment details
- Getting experiment test cases
- Listing prompt experiments
- Deleting prompt experiments

All tests mock external dependencies (LLM completion and LLM eval responses)
and clean up test state after execution.
"""

import random
import time
from unittest.mock import MagicMock, patch

import pytest
from litellm.types.utils import ModelResponse

from schemas.base_experiment_schemas import (
    DatasetColumnSource,
    DatasetColumnVariableSource,
    DatasetRefInput,
    EvalRef,
    ExperimentStatus,
    TestCaseStatus,
)
from schemas.common_schemas import (
    NewDatasetVersionRowColumnItemRequest,
    NewDatasetVersionRowRequest,
)
from schemas.prompt_experiment_schemas import (
    CreatePromptExperimentRequest,
    PromptExperimentDetail,
    PromptExperimentListResponse,
    PromptVariableMapping,
    SavedPromptConfig,
    TestCase,
    TestCaseListResponse,
    UnsavedPromptConfig,
)
from tests.clients.base_test_client import GenaiEngineTestClientBase
from tests.unit.routes.conftest import setup_db_session_context_mock

# Maximum time to wait for experiment completion (in seconds)
MAX_WAIT_TIME = 30
# Polling interval (in seconds)
POLL_INTERVAL = 0.5


def wait_for_experiment_completion(
    client: GenaiEngineTestClientBase,
    experiment_id: str,
    max_wait_time: float = MAX_WAIT_TIME,
    poll_interval: float = POLL_INTERVAL,
    allow_failure: bool = False,
) -> PromptExperimentDetail:
    """
    Poll the experiment details endpoint until the experiment completes.

    Args:
        client: Test client instance
        experiment_id: ID of the experiment to poll
        max_wait_time: Maximum time to wait (in seconds)
        poll_interval: Time between polls (in seconds)
        allow_failure: If True, return the experiment detail even if it failed.
                       If False (default), raise AssertionError if experiment failed.

    Returns:
        PromptExperimentDetail: The completed experiment details

    Raises:
        TimeoutError: If experiment doesn't complete within max_wait_time
        AssertionError: If experiment failed and allow_failure is False
    """
    start_time = time.time()
    last_status = None
    while time.time() - start_time < max_wait_time:
        status_code, experiment_data = client.get_prompt_experiment(experiment_id)
        assert status_code == 200, f"Failed to get experiment: {experiment_data}"

        experiment_detail = PromptExperimentDetail.model_validate(experiment_data)
        current_status = experiment_detail.status

        # Log status changes for debugging
        if current_status != last_status:
            last_status = current_status

        if current_status in [
            ExperimentStatus.COMPLETED,
            ExperimentStatus.FAILED,
        ]:
            if current_status == ExperimentStatus.FAILED and not allow_failure:
                raise AssertionError(
                    f"Experiment {experiment_id} failed. "
                    f"Completed rows: {experiment_detail.completed_rows}, "
                    f"Failed rows: {experiment_detail.failed_rows}",
                )
            # Return the experiment detail (either completed or failed if allowed)
            return experiment_detail

        time.sleep(poll_interval)

    # Get final status for error message
    status_code, experiment_data = client.get_prompt_experiment(experiment_id)
    if status_code == 200:
        experiment_detail = PromptExperimentDetail.model_validate(experiment_data)
        raise TimeoutError(
            f"Experiment {experiment_id} did not complete within {max_wait_time} seconds. "
            f"Final status: {experiment_detail.status}, "
            f"Completed rows: {experiment_detail.completed_rows}/{experiment_detail.total_rows}, "
            f"Failed rows: {experiment_detail.failed_rows}",
        )
    else:
        raise TimeoutError(
            f"Experiment {experiment_id} did not complete within {max_wait_time} seconds. "
            f"Could not get final status: {experiment_data}",
        )


@pytest.mark.unit_tests
@patch("services.experiment_executor.db_session_context")
@patch("repositories.llm_evals_repository.supports_response_schema")
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
@patch("services.prompt_experiment_executor.logger")
@patch("services.experiment_executor.logger")
def test_prompt_experiment_routes_happy_path(
    mock_experiment_logger,
    mock_prompt_logger,
    mock_completion,
    mock_completion_cost,
    mock_supports_response_schema,
    mock_db_session_context,
    client: GenaiEngineTestClientBase,
):
    """
    Test the complete prompt experiment workflow:
    1. Create a prompt experiment (happy path)
    2. Get prompt experiment details (polling until completion)
    3. Get experiment test cases
    4. List prompt experiments
    5. Delete prompt experiment

    This test mocks:
    - LLM completion responses (using mock_completion and mock_completion_cost)
    - LLM eval responses (using mock_completion and mock_completion_cost)
    - Database session context for background threads (using override_get_db_session)

    All response fields are validated to ensure they're set as expected.
    """

    # Mock db_session_context for background thread execution to use test database
    setup_db_session_context_mock(mock_db_session_context)

    # Setup: Create task
    task_name = f"prompt_experiment_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200, f"Failed to create task: {task}"
    task_id = task.id

    # Setup: Configure model provider (required for LLM evals and prompts)
    response = client.base_client.put(
        f"/api/v1/model_providers/openai",
        data={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert (
        response.status_code == 201
    ), f"Failed to configure model provider: {response.text}"

    # Setup: Create dataset with test rows
    dataset_name = f"prompt_test_dataset_{random.random()}"
    status_code, dataset = client.create_dataset(
        name=dataset_name,
        task_id=task_id,
        description="Test dataset for prompt experiments",
    )
    assert status_code == 200, f"Failed to create dataset: {dataset}"
    dataset_id = dataset.id

    # Create dataset version with test rows
    test_rows = [
        NewDatasetVersionRowRequest(
            data=[
                NewDatasetVersionRowColumnItemRequest(
                    column_name="user_message",
                    column_value="What is machine learning?",
                ),
                NewDatasetVersionRowColumnItemRequest(
                    column_name="expected_response",
                    column_value="Machine learning is a subset of AI",
                ),
            ],
        ),
        NewDatasetVersionRowRequest(
            data=[
                NewDatasetVersionRowColumnItemRequest(
                    column_name="user_message",
                    column_value="What is deep learning?",
                ),
                NewDatasetVersionRowColumnItemRequest(
                    column_name="expected_response",
                    column_value="Deep learning uses neural networks",
                ),
            ],
        ),
    ]

    status_code, dataset_version = client.create_dataset_version(
        dataset_id=dataset_id,
        rows_to_add=test_rows,
    )
    assert status_code == 200, f"Failed to create dataset version: {dataset_version}"
    dataset_version_number = dataset_version.version_number

    # Setup: Create saved prompt
    prompt_name = f"test_prompt_{random.random()}"
    prompt_data = {
        "name": prompt_name,
        "messages": [
            {
                "role": "user",
                "content": "Answer the following question: {{user_message}}",
            },
        ],
        "model_name": "gpt-4o",
        "model_provider": "openai",
    }

    response = client.base_client.post(
        f"/api/v1/tasks/{task_id}/prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200, f"Failed to create prompt: {response.text}"
    prompt_version = 1

    # Setup: Create LLM eval
    eval_name = "test_prompt_eval"
    eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Evaluate the prompt response based on relevance and accuracy",
    }

    response = client.base_client.post(
        f"/api/v1/tasks/{task_id}/llm_evals/{eval_name}",
        json=eval_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200, f"Failed to create LLM eval: {response.text}"

    # Mock supports_response_schema to return True (required by run_llm_eval)
    mock_supports_response_schema.return_value = True

    mock_prompt_response = MagicMock(spec=ModelResponse)
    mock_prompt_response.choices = [MagicMock()]
    mock_prompt_message = MagicMock()
    mock_prompt_message.content = (
        "Machine learning is a subset of artificial intelligence."
    )
    mock_prompt_message.tool_calls = None
    mock_prompt_response.choices[0].message = mock_prompt_message
    mock_prompt_response.usage = MagicMock()
    mock_prompt_response.usage.total_tokens = 100

    mock_eval_response = MagicMock(spec=ModelResponse)
    mock_eval_response.choices = [MagicMock()]
    mock_eval_message = MagicMock()
    mock_eval_message.content = (
        '{"reason": "The prompt response is highly relevant and accurate.", "score": 1}'
    )

    def message_get(key, default=None):
        if key == "content":
            return mock_eval_message.content
        return default

    mock_eval_message.get = message_get
    mock_eval_message.tool_calls = None
    mock_eval_response.choices[0].message = mock_eval_message
    mock_eval_response.usage = MagicMock()
    mock_eval_response.usage.total_tokens = 50

    call_count = [0]

    def mock_completion_side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_prompt_response
        else:
            return mock_eval_response

    mock_completion.side_effect = mock_completion_side_effect
    mock_completion_cost.return_value = 0.002345

    mock_prompt_logger.info = MagicMock()
    mock_prompt_logger.error = MagicMock()
    mock_prompt_logger.warning = MagicMock()
    mock_experiment_logger.info = MagicMock()
    mock_experiment_logger.error = MagicMock()
    mock_experiment_logger.warning = MagicMock()

    # Test 1: Create prompt experiment with dataset row filter
    # Filter to only include rows where user_message contains "machine learning"
    # This should result in only 1 test case instead of 2
    experiment_name = f"test_prompt_experiment_{random.random()}"

    experiment_request = CreatePromptExperimentRequest(
        name=experiment_name,
        description="Test prompt experiment",
        dataset_ref=DatasetRefInput(
            id=dataset_id,
            version=dataset_version_number,
        ),
        dataset_row_filter=[
            NewDatasetVersionRowColumnItemRequest(
                column_name="user_message",
                column_value="What is machine learning?",
            ),
        ],
        prompt_configs=[
            SavedPromptConfig(
                type="saved",
                name=prompt_name,
                version=prompt_version,
            ),
        ],
        prompt_variable_mapping=[
            PromptVariableMapping(
                variable_name="user_message",
                source=DatasetColumnVariableSource(
                    type="dataset_column",
                    dataset_column=DatasetColumnSource(
                        name="user_message",
                    ),
                ),
            ),
        ],
        eval_list=[
            EvalRef(
                name=eval_name,
                version=1,
                variable_mapping=[],
            ),
        ],
    )

    status_code, experiment_summary = client.create_prompt_experiment(
        task_id=task_id,
        experiment_request=experiment_request.model_dump(mode="json"),
    )
    assert (
        status_code == 200
    ), f"Failed to create prompt experiment: {experiment_summary}"
    experiment_id = experiment_summary["id"]

    # Validate experiment summary response fields
    assert experiment_summary["name"] == experiment_name
    assert experiment_summary["description"] == "Test prompt experiment"
    assert experiment_summary["status"] == ExperimentStatus.QUEUED
    assert experiment_summary["dataset_id"] == str(dataset_id)
    assert experiment_summary["dataset_name"] == dataset_name
    assert experiment_summary["dataset_version"] == dataset_version_number
    # With dataset_row_filter, only 1 row should match (the "machine learning" query)
    assert experiment_summary["total_rows"] == 1
    assert experiment_summary["completed_rows"] == 0
    assert experiment_summary["failed_rows"] == 0
    assert "created_at" in experiment_summary
    # finished_at may be excluded from response if None due to response_model_exclude_none=True
    assert experiment_summary.get("finished_at") is None
    assert "prompt_configs" in experiment_summary
    assert len(experiment_summary["prompt_configs"]) == 1
    assert experiment_summary["prompt_configs"][0]["type"] == "saved"
    assert experiment_summary["prompt_configs"][0]["name"] == prompt_name
    assert experiment_summary["prompt_configs"][0]["version"] == prompt_version

    # Test 2: Get prompt experiment details (polling until completion)
    experiment_detail = wait_for_experiment_completion(client, experiment_id)

    # Validate experiment detail response fields
    assert experiment_detail.id == experiment_id
    assert experiment_detail.name == experiment_name
    assert experiment_detail.description == "Test prompt experiment"
    assert experiment_detail.status == ExperimentStatus.COMPLETED
    assert experiment_detail.dataset_ref.id == dataset_id
    assert experiment_detail.dataset_ref.name == dataset_name
    assert experiment_detail.dataset_ref.version == dataset_version_number
    # With dataset_row_filter, only 1 row should match (the "machine learning" query)
    assert experiment_detail.total_rows == 1
    assert experiment_detail.completed_rows == 1
    assert experiment_detail.failed_rows == 0

    # Validate that dataset_row_filter is present in the response with expected values
    assert experiment_detail.dataset_row_filter is not None
    assert len(experiment_detail.dataset_row_filter) == 1
    assert experiment_detail.dataset_row_filter[0].column_name == "user_message"
    assert (
        experiment_detail.dataset_row_filter[0].column_value
        == "What is machine learning?"
    )
    assert experiment_detail.finished_at is not None
    assert experiment_detail.created_at is not None

    # Validate prompt configs
    assert len(experiment_detail.prompt_configs) == 1
    prompt_config = experiment_detail.prompt_configs[0]
    assert prompt_config.type == "saved"
    assert prompt_config.name == prompt_name
    assert prompt_config.version == prompt_version

    # Validate prompt variable mapping
    assert experiment_detail.prompt_variable_mapping is not None
    assert len(experiment_detail.prompt_variable_mapping) == 1
    mapping = experiment_detail.prompt_variable_mapping[0]
    assert mapping.variable_name == "user_message"
    assert mapping.source.type == "dataset_column"
    assert mapping.source.dataset_column.name == "user_message"

    # Validate summary results
    assert experiment_detail.summary_results is not None
    assert len(experiment_detail.summary_results.prompt_eval_summaries) == 1
    prompt_eval_summary = experiment_detail.summary_results.prompt_eval_summaries[0]
    assert prompt_eval_summary.prompt_key is not None
    assert prompt_eval_summary.prompt_type == "saved"
    assert prompt_eval_summary.prompt_name == prompt_name
    assert prompt_eval_summary.prompt_version == str(prompt_version)
    assert prompt_eval_summary.eval_results is not None
    assert len(prompt_eval_summary.eval_results) == 1
    eval_result = prompt_eval_summary.eval_results[0]
    assert eval_result.eval_name == eval_name
    assert eval_result.eval_version == "1"
    # With dataset_row_filter, only 1 row should match
    assert eval_result.total_count == 1
    assert eval_result.pass_count == 1  # All should pass with our mock

    # Test 3: List prompt experiments for the task
    status_code, experiments_list_data = client.list_prompt_experiments(
        task_id=task_id,
        page=0,
        page_size=10,
    )
    assert (
        status_code == 200
    ), f"Failed to list prompt experiments: {experiments_list_data}"

    experiments_list = PromptExperimentListResponse.model_validate(
        experiments_list_data,
    )

    # Validate list response fields
    assert experiments_list.page == 0
    assert experiments_list.page_size == 10
    assert (
        experiments_list.total_count >= 1
    )  # At least our experiment should be in the list
    assert experiments_list.total_pages >= 1
    assert len(experiments_list.data) >= 1

    # Find our experiment in the list
    our_experiment = None
    for exp in experiments_list.data:
        if exp.id == experiment_id:
            our_experiment = exp
            break

    assert our_experiment is not None, f"Experiment {experiment_id} not found in list"

    # Validate our experiment in the list
    assert our_experiment.name == experiment_name
    assert our_experiment.description == "Test prompt experiment"
    assert our_experiment.status == ExperimentStatus.COMPLETED
    assert our_experiment.dataset_id == dataset_id
    assert our_experiment.dataset_name == dataset_name
    assert our_experiment.dataset_version == dataset_version_number
    # With dataset_row_filter, only 1 row should match
    assert our_experiment.total_rows == 1
    assert our_experiment.completed_rows == 1
    assert our_experiment.failed_rows == 0
    assert our_experiment.finished_at is not None
    assert our_experiment.created_at is not None
    assert len(our_experiment.prompt_configs) == 1
    assert our_experiment.prompt_configs[0].type == "saved"
    assert our_experiment.prompt_configs[0].name == prompt_name
    assert our_experiment.prompt_configs[0].version == prompt_version

    # Test 4: Get experiment test cases
    status_code, test_cases_data = client.get_prompt_experiment_test_cases(
        experiment_id=experiment_id,
        page=0,
        page_size=10,
    )
    assert status_code == 200, f"Failed to get test cases: {test_cases_data}"

    test_cases_response = TestCaseListResponse.model_validate(test_cases_data)

    # Validate test cases response fields
    # With dataset_row_filter, only 1 row should match
    assert test_cases_response.page == 0
    assert test_cases_response.page_size == 10
    assert test_cases_response.total_count == 1
    assert test_cases_response.total_pages == 1
    assert len(test_cases_response.data) == 1

    # Validate each test case
    # With dataset_row_filter, we should only have 1 test case
    assert len(test_cases_response.data) == 1
    test_case = test_cases_response.data[0]
    assert isinstance(test_case, TestCase)
    assert test_case.status == TestCaseStatus.COMPLETED
    # Validate dataset_row_id is a valid UUID string
    assert test_case.dataset_row_id is not None
    assert isinstance(test_case.dataset_row_id, str)
    assert len(test_case.dataset_row_id) > 0

    # Validate prompt_input_variables
    assert test_case.prompt_input_variables is not None
    assert len(test_case.prompt_input_variables) == 1
    input_var = test_case.prompt_input_variables[0]
    assert input_var.variable_name == "user_message"
    assert input_var.value == "What is machine learning?"

    # Validate prompt results
    assert test_case.prompt_results is not None
    assert len(test_case.prompt_results) == 1
    prompt_result = test_case.prompt_results[0]
    assert prompt_result.prompt_key == f"saved:{prompt_name}:{prompt_version}"
    assert prompt_result.prompt_type == "saved"
    assert prompt_result.name == prompt_name
    assert prompt_result.version == str(prompt_version)
    assert prompt_result.rendered_prompt is not None
    assert len(prompt_result.rendered_prompt) > 0
    assert prompt_result.output is not None
    assert prompt_result.output.content is not None
    assert len(prompt_result.output.content) > 0
    assert prompt_result.output.cost is not None

    # Validate eval executions
    assert prompt_result.evals is not None
    assert len(prompt_result.evals) == 1
    eval_execution = prompt_result.evals[0]
    assert eval_execution.eval_name == eval_name
    assert eval_execution.eval_version == "1"
    assert eval_execution.eval_results is not None
    assert eval_execution.eval_results.score == 1  # ReasonedScore expects integer
    assert eval_execution.eval_results.explanation is not None
    assert eval_execution.eval_results.cost == "0.002345"

    # Test 5: Create an experiment that will fail and verify it gets marked as failed
    # Reuse existing setup (task, dataset, prompt, LLM eval)
    # Make the LLM completion fail by having the mock raise an exception
    failed_experiment_name = f"test_prompt_experiment_failed_{random.random()}"
    failed_experiment_request = CreatePromptExperimentRequest(
        name=failed_experiment_name,
        description="Test prompt experiment that will fail",
        dataset_ref=DatasetRefInput(
            id=dataset_id,
            version=dataset_version_number,
        ),
        # No filter - use all rows
        dataset_row_filter=None,
        prompt_configs=[
            SavedPromptConfig(
                type="saved",
                name=prompt_name,
                version=prompt_version,
            ),
        ],
        prompt_variable_mapping=[
            PromptVariableMapping(
                variable_name="user_message",
                source=DatasetColumnVariableSource(
                    type="dataset_column",
                    dataset_column=DatasetColumnSource(
                        name="user_message",
                    ),
                ),
            ),
        ],
        eval_list=[
            EvalRef(
                name=eval_name,
                version=1,
                variable_mapping=[],
            ),
        ],
    )

    # Mock LLM completion to fail by raising an exception
    def mock_completion_failure(*args, **kwargs):
        """Mock LLM completion that raises an exception."""
        raise Exception("LLM completion failed for testing")

    mock_completion.side_effect = mock_completion_failure

    status_code, failed_experiment_summary = client.create_prompt_experiment(
        task_id=task_id,
        experiment_request=failed_experiment_request.model_dump(mode="json"),
    )
    assert (
        status_code == 200
    ), f"Failed to create failed experiment: {failed_experiment_summary}"
    failed_experiment_id = failed_experiment_summary["id"]

    # Wait for the experiment to complete (should fail)
    # Pass allow_failure=True since we expect this experiment to fail
    failed_experiment_detail = wait_for_experiment_completion(
        client,
        failed_experiment_id,
        allow_failure=True,
    )

    # Validate that the experiment is marked as failed
    assert failed_experiment_detail.status == ExperimentStatus.FAILED
    assert failed_experiment_detail.failed_rows == len(
        test_rows,
    )  # All rows should fail
    assert failed_experiment_detail.total_rows == len(test_rows)
    assert failed_experiment_detail.completed_rows == 0  # No rows completed
    assert (
        failed_experiment_detail.completed_rows + failed_experiment_detail.failed_rows
        == failed_experiment_detail.total_rows
    )
    assert failed_experiment_detail.finished_at is not None

    # Cleanup: Delete experiments, dataset, prompt, LLM eval, and task
    status_code = client.delete_prompt_experiment(experiment_id)
    assert status_code == 204, f"Failed to delete prompt experiment: {status_code}"

    # Validate that deleted experiment cannot be fetched
    status_code, _ = client.get_prompt_experiment(experiment_id)
    assert (
        status_code == 404
    ), f"Expected 404 after deleting experiment, got {status_code}"

    # Validate that test cases for deleted experiment cannot be fetched
    status_code, _ = client.get_prompt_experiment_test_cases(experiment_id)
    assert (
        status_code == 404
    ), f"Expected 404 when fetching test cases for deleted experiment, got {status_code}"

    status_code = client.delete_prompt_experiment(failed_experiment_id)
    assert (
        status_code == 204
    ), f"Failed to delete failed prompt experiment: {status_code}"

    status_code, _ = client.delete_llm_eval(task_id=task_id, llm_eval_name=eval_name)
    assert status_code in [200, 204], f"Failed to delete LLM eval: {status_code}"

    # Delete prompt
    response = client.base_client.delete(
        f"/api/v1/tasks/{task_id}/prompts/{prompt_name}/versions/{prompt_version}",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code in [
        200,
        204,
    ], f"Failed to delete prompt: {response.text}"

    status_code = client.delete_dataset(dataset_id)
    assert status_code == 204, f"Failed to delete dataset: {status_code}"

    status_code = client.delete_task(task_id)
    assert status_code == 204, f"Failed to delete task: {status_code}"


@pytest.mark.unit_tests
@patch("services.experiment_executor.db_session_context")
@patch("repositories.llm_evals_repository.supports_response_schema")
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
@patch("services.prompt_experiment_executor.logger")
@patch("services.experiment_executor.logger")
@patch("repositories.prompt_experiment_repository.logger")
def test_prompt_experiment_none_value_conversion(
    mock_repo_logger,
    mock_experiment_logger,
    mock_prompt_logger,
    mock_completion,
    mock_completion_cost,
    mock_supports_response_schema,
    mock_db_session_context,
    client: GenaiEngineTestClientBase,
):
    """
    Test that None values in dataset columns are converted to empty strings.

    This test verifies the scenario where dataset rows
    with None values in columns are properly handled by converting None to ""
    when creating test cases. This ensures the InputVariable.value field is
    always a string, not None.
    """
    # Mock db_session_context for background thread execution to use test database
    setup_db_session_context_mock(mock_db_session_context)

    # Setup: Create task
    task_name = f"prompt_experiment_none_test_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200, f"Failed to create task: {task}"
    task_id = task.id

    # Setup: Configure model provider
    response = client.base_client.put(
        f"/api/v1/model_providers/openai",
        data={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert (
        response.status_code == 201
    ), f"Failed to configure model provider: {response.text}"

    # Setup: Create dataset with a row that has None value in a column
    dataset_name = f"prompt_none_test_dataset_{random.random()}"
    status_code, dataset = client.create_dataset(
        name=dataset_name,
        task_id=task_id,
        description="Test dataset with None values",
    )
    assert status_code == 200, f"Failed to create dataset: {dataset}"
    dataset_id = dataset.id

    # Create dataset version with two rows:
    # 1. One row that includes expected_response (so the column exists in the schema)
    # 2. One row that omits expected_response (so that row will have None for that column)
    test_rows = [
        NewDatasetVersionRowRequest(
            data=[
                NewDatasetVersionRowColumnItemRequest(
                    column_name="user_message",
                    column_value="What is machine learning?",
                ),
                NewDatasetVersionRowColumnItemRequest(
                    column_name="expected_response",
                    column_value="AI is artificial intelligence",
                ),
            ],
        ),
        NewDatasetVersionRowRequest(
            data=[
                NewDatasetVersionRowColumnItemRequest(
                    column_name="user_message",
                    column_value="What is AI?",
                ),
            ],
        ),
    ]

    status_code, dataset_version = client.create_dataset_version(
        dataset_id=dataset_id,
        rows_to_add=test_rows,
    )
    assert status_code == 200, f"Failed to create dataset version: {dataset_version}"
    dataset_version_number = dataset_version.version_number

    # Setup: Create saved prompt
    prompt_name = f"test_prompt_none_{random.random()}"
    prompt_data = {
        "name": prompt_name,
        "messages": [
            {
                "role": "user",
                "content": "Answer: {{user_message}}. Expected: {{expected_response}}",
            },
        ],
        "model_name": "gpt-4o",
        "model_provider": "openai",
    }

    response = client.base_client.post(
        f"/api/v1/tasks/{task_id}/prompts/{prompt_name}",
        json=prompt_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200, f"Failed to create prompt: {response.text}"
    prompt_version = 1

    # Setup: Create LLM eval
    eval_name = "test_prompt_eval_none"
    eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Evaluate the prompt response",
    }

    response = client.base_client.post(
        f"/api/v1/tasks/{task_id}/llm_evals/{eval_name}",
        json=eval_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200, f"Failed to create LLM eval: {response.text}"

    # Mock supports_response_schema
    mock_supports_response_schema.return_value = True

    mock_prompt_response = MagicMock(spec=ModelResponse)
    mock_prompt_response.choices = [MagicMock()]
    mock_message = MagicMock()
    mock_message.content = "AI is artificial intelligence."
    mock_message.tool_calls = None
    mock_prompt_response.choices[0].message = mock_message
    mock_prompt_response.usage = MagicMock()
    mock_prompt_response.usage.total_tokens = 100

    mock_eval_response = MagicMock(spec=ModelResponse)
    mock_eval_response.choices = [MagicMock()]
    mock_eval_message = MagicMock()
    mock_eval_message.content = '{"reason": "Good response.", "score": 1}'

    def message_get(key, default=None):
        if key == "content":
            return mock_eval_message.content
        return default

    mock_eval_message.get = message_get
    mock_eval_message.tool_calls = None
    mock_eval_response.choices[0].message = mock_eval_message
    mock_eval_response.usage = MagicMock()
    mock_eval_response.usage.total_tokens = 50

    call_count = [0]

    def mock_completion_side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_prompt_response
        else:
            return mock_eval_response

    mock_completion.side_effect = mock_completion_side_effect
    mock_completion_cost.return_value = 0.002345

    mock_repo_logger.warning = MagicMock()
    mock_prompt_logger.info = MagicMock()
    mock_prompt_logger.error = MagicMock()
    mock_prompt_logger.warning = MagicMock()
    mock_experiment_logger.info = MagicMock()
    mock_experiment_logger.error = MagicMock()
    mock_experiment_logger.warning = MagicMock()

    # Create experiment with variable mapping that includes expected_response
    # Filter to only the row that omits expected_response (which will have None)
    experiment_name = f"test_prompt_experiment_none_{random.random()}"

    experiment_request = CreatePromptExperimentRequest(
        name=experiment_name,
        description="Test prompt experiment with None values",
        dataset_ref=DatasetRefInput(
            id=dataset_id,
            version=dataset_version_number,
        ),
        dataset_row_filter=[
            NewDatasetVersionRowColumnItemRequest(
                column_name="user_message",
                column_value="What is AI?",
            ),
        ],
        prompt_configs=[
            SavedPromptConfig(
                type="saved",
                name=prompt_name,
                version=prompt_version,
            ),
        ],
        prompt_variable_mapping=[
            PromptVariableMapping(
                variable_name="user_message",
                source=DatasetColumnVariableSource(
                    type="dataset_column",
                    dataset_column=DatasetColumnSource(
                        name="user_message",
                    ),
                ),
            ),
            PromptVariableMapping(
                variable_name="expected_response",
                source=DatasetColumnVariableSource(
                    type="dataset_column",
                    dataset_column=DatasetColumnSource(
                        name="expected_response",
                    ),
                ),
            ),
        ],
        eval_list=[
            EvalRef(
                name=eval_name,
                version=1,
                variable_mapping=[],
            ),
        ],
    )

    status_code, experiment_summary = client.create_prompt_experiment(
        task_id=task_id,
        experiment_request=experiment_request.model_dump(mode="json"),
    )
    assert (
        status_code == 200
    ), f"Failed to create prompt experiment: {experiment_summary}"
    experiment_id = experiment_summary["id"]

    # Wait for experiment to complete
    experiment_detail = wait_for_experiment_completion(client, experiment_id)

    # Verify that the experiment completed successfully
    assert experiment_detail.status == ExperimentStatus.COMPLETED
    assert experiment_detail.completed_rows == 1

    # Get test cases and verify that None values were converted to empty strings
    status_code, test_cases_data = client.get_prompt_experiment_test_cases(
        experiment_id=experiment_id,
        page=0,
        page_size=10,
    )
    assert status_code == 200, f"Failed to get test cases: {test_cases_data}"

    test_cases_response = TestCaseListResponse.model_validate(test_cases_data)
    assert len(test_cases_response.data) == 1

    test_case = test_cases_response.data[0]

    # Verify that all input variables have string values (not None)
    assert test_case.prompt_input_variables is not None
    assert len(test_case.prompt_input_variables) == 2

    for var in test_case.prompt_input_variables:
        assert isinstance(
            var.value,
            str,
        ), f"Expected InputVariable.value to be a string, but got {type(var.value)}: {var.value}"
        # Verify the expected_response variable has empty string value
        if var.variable_name == "expected_response":
            # The value should be an empty string (either from the dataset or converted from None)
            assert (
                var.value == ""
            ), f"Expected expected_response value to be empty string, but got: {var.value}"
        elif var.variable_name == "user_message":
            assert var.value == "What is AI?"

    # Cleanup
    status_code = client.delete_prompt_experiment(experiment_id)
    assert status_code == 204, f"Failed to delete prompt experiment: {status_code}"

    status_code, _ = client.delete_llm_eval(task_id=task_id, llm_eval_name=eval_name)
    assert status_code in [200, 204], f"Failed to delete LLM eval: {status_code}"

    response = client.base_client.delete(
        f"/api/v1/tasks/{task_id}/prompts/{prompt_name}/versions/{prompt_version}",
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code in [
        200,
        204,
    ], f"Failed to delete prompt: {response.text}"

    status_code = client.delete_dataset(dataset_id)
    assert status_code == 204, f"Failed to delete dataset: {status_code}"

    status_code = client.delete_task(task_id)
    assert status_code == 204, f"Failed to delete task: {status_code}"


@pytest.mark.unit_tests
@patch("services.experiment_executor.db_session_context")
@patch("repositories.llm_evals_repository.supports_response_schema")
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
@patch("services.prompt_experiment_executor.logger")
@patch("services.experiment_executor.logger")
def test_prompt_experiment_unsaved_prompt(
    mock_experiment_logger,
    mock_prompt_logger,
    mock_completion,
    mock_completion_cost,
    mock_supports_response_schema,
    mock_db_session_context,
    client: GenaiEngineTestClientBase,
):
    """
    Test prompt experiment with unsaved prompt configuration.

    This test verifies that unsaved prompts work correctly in experiments.
    """
    # Mock db_session_context for background thread execution to use test database
    setup_db_session_context_mock(mock_db_session_context)

    # Setup: Create task
    task_name = f"prompt_experiment_unsaved_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200, f"Failed to create task: {task}"
    task_id = task.id

    # Setup: Configure model provider
    response = client.base_client.put(
        f"/api/v1/model_providers/openai",
        data={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert (
        response.status_code == 201
    ), f"Failed to configure model provider: {response.text}"

    # Setup: Create dataset
    dataset_name = f"prompt_unsaved_test_dataset_{random.random()}"
    status_code, dataset = client.create_dataset(
        name=dataset_name,
        task_id=task_id,
        description="Test dataset for unsaved prompt experiments",
    )
    assert status_code == 200, f"Failed to create dataset: {dataset}"
    dataset_id = dataset.id

    test_rows = [
        NewDatasetVersionRowRequest(
            data=[
                NewDatasetVersionRowColumnItemRequest(
                    column_name="question",
                    column_value="What is Python?",
                ),
            ],
        ),
    ]

    status_code, dataset_version = client.create_dataset_version(
        dataset_id=dataset_id,
        rows_to_add=test_rows,
    )
    assert status_code == 200, f"Failed to create dataset version: {dataset_version}"
    dataset_version_number = dataset_version.version_number

    # Setup: Create LLM eval
    eval_name = "test_prompt_eval_unsaved"
    eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Evaluate the prompt response",
    }

    response = client.base_client.post(
        f"/api/v1/tasks/{task_id}/llm_evals/{eval_name}",
        json=eval_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200, f"Failed to create LLM eval: {response.text}"

    # Mock supports_response_schema
    mock_supports_response_schema.return_value = True

    mock_prompt_response = MagicMock(spec=ModelResponse)
    mock_prompt_response.choices = [MagicMock()]
    mock_message = MagicMock()
    mock_message.content = "Python is a programming language."
    mock_message.tool_calls = None
    mock_prompt_response.choices[0].message = mock_message
    mock_prompt_response.usage = MagicMock()
    mock_prompt_response.usage.total_tokens = 100

    mock_eval_response = MagicMock(spec=ModelResponse)
    mock_eval_response.choices = [MagicMock()]
    mock_eval_message = MagicMock()
    mock_eval_message.content = '{"reason": "Good response.", "score": 1}'

    def message_get(key, default=None):
        if key == "content":
            return mock_eval_message.content
        return default

    mock_eval_message.get = message_get
    mock_eval_message.tool_calls = None
    mock_eval_response.choices[0].message = mock_eval_message
    mock_eval_response.usage = MagicMock()
    mock_eval_response.usage.total_tokens = 50

    call_count = [0]

    def mock_completion_side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return mock_prompt_response
        else:
            return mock_eval_response

    mock_completion.side_effect = mock_completion_side_effect
    mock_completion_cost.return_value = 0.002345

    mock_prompt_logger.info = MagicMock()
    mock_prompt_logger.error = MagicMock()
    mock_prompt_logger.warning = MagicMock()
    mock_experiment_logger.info = MagicMock()
    mock_experiment_logger.error = MagicMock()
    mock_experiment_logger.warning = MagicMock()

    # Create experiment with unsaved prompt
    experiment_name = f"test_prompt_experiment_unsaved_{random.random()}"

    experiment_request = CreatePromptExperimentRequest(
        name=experiment_name,
        description="Test prompt experiment with unsaved prompt",
        dataset_ref=DatasetRefInput(
            id=dataset_id,
            version=dataset_version_number,
        ),
        dataset_row_filter=None,
        prompt_configs=[
            UnsavedPromptConfig(
                type="unsaved",
                messages=[
                    {
                        "role": "user",
                        "content": "Answer: {{question}}",
                    },
                ],
                model_name="gpt-4o",
                model_provider="openai",
            ),
        ],
        prompt_variable_mapping=[
            PromptVariableMapping(
                variable_name="question",
                source=DatasetColumnVariableSource(
                    type="dataset_column",
                    dataset_column=DatasetColumnSource(
                        name="question",
                    ),
                ),
            ),
        ],
        eval_list=[
            EvalRef(
                name=eval_name,
                version=1,
                variable_mapping=[],
            ),
        ],
    )

    status_code, experiment_summary = client.create_prompt_experiment(
        task_id=task_id,
        experiment_request=experiment_request.model_dump(mode="json"),
    )
    assert (
        status_code == 200
    ), f"Failed to create prompt experiment: {experiment_summary}"
    experiment_id = experiment_summary["id"]

    # Validate that unsaved prompt config is in the response
    assert "prompt_configs" in experiment_summary
    assert len(experiment_summary["prompt_configs"]) == 1
    assert experiment_summary["prompt_configs"][0]["type"] == "unsaved"
    assert "auto_name" in experiment_summary["prompt_configs"][0]

    # Wait for experiment to complete
    experiment_detail = wait_for_experiment_completion(client, experiment_id)

    # Verify completion
    assert experiment_detail.status == ExperimentStatus.COMPLETED
    assert experiment_detail.completed_rows == 1

    # Verify unsaved prompt in detail
    assert len(experiment_detail.prompt_configs) == 1
    prompt_config = experiment_detail.prompt_configs[0]
    assert prompt_config.type == "unsaved"
    assert prompt_config.auto_name is not None

    # Get test cases and verify unsaved prompt results
    status_code, test_cases_data = client.get_prompt_experiment_test_cases(
        experiment_id=experiment_id,
        page=0,
        page_size=10,
    )
    assert status_code == 200, f"Failed to get test cases: {test_cases_data}"

    test_cases_response = TestCaseListResponse.model_validate(test_cases_data)
    assert len(test_cases_response.data) == 1

    test_case = test_cases_response.data[0]
    assert len(test_case.prompt_results) == 1
    prompt_result = test_case.prompt_results[0]
    assert prompt_result.prompt_type == "unsaved"
    assert prompt_result.prompt_key.startswith("unsaved:")
    assert prompt_result.name is None  # Unsaved prompts don't have names
    assert prompt_result.version is None  # Unsaved prompts don't have versions

    # Cleanup
    status_code = client.delete_prompt_experiment(experiment_id)
    assert status_code == 204, f"Failed to delete prompt experiment: {status_code}"

    status_code, _ = client.delete_llm_eval(task_id=task_id, llm_eval_name=eval_name)
    assert status_code in [200, 204], f"Failed to delete LLM eval: {status_code}"

    status_code = client.delete_dataset(dataset_id)
    assert status_code == 204, f"Failed to delete dataset: {status_code}"

    status_code = client.delete_task(task_id)
    assert status_code == 204, f"Failed to delete task: {status_code}"
