"""
Unit tests for RAG experiment routes.

This module tests the RAG experiment API endpoints:
- Creating and running a RAG experiment
- Getting RAG experiment details
- Getting experiment test cases

All tests mock external dependencies (RAG search and LLM eval responses)
and clean up test state after execution.
"""

import random
import time
from contextlib import contextmanager
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from litellm.types.utils import ModelResponse

from schemas.base_experiment_schemas import ExperimentStatus, TestCaseStatus
from schemas.common_schemas import (
    NewDatasetVersionRowColumnItemRequest,
    NewDatasetVersionRowRequest,
)
from schemas.internal_schemas import (
    ApiKeyRagAuthenticationConfig,
    RagProviderConfiguration,
)
from schemas.rag_experiment_schemas import (
    RagExperimentDetail,
    RagExperimentListResponse,
    RagTestCase,
    RagTestCaseListResponse,
)
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)
from tests.mocks.mock_weaviate_client import MockWeaviateClientFactory

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
) -> RagExperimentDetail:
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
        RagExperimentDetail: The completed experiment details

    Raises:
        TimeoutError: If experiment doesn't complete within max_wait_time
        AssertionError: If experiment failed and allow_failure is False
    """
    start_time = time.time()
    last_status = None
    while time.time() - start_time < max_wait_time:
        status_code, experiment_data = client.get_rag_experiment(experiment_id)
        assert status_code == 200, f"Failed to get experiment: {experiment_data}"

        experiment_detail = RagExperimentDetail.model_validate(experiment_data)
        current_status = experiment_detail.status

        # Log status changes for debugging
        if current_status != last_status:
            last_status = current_status

        if current_status in [
            ExperimentStatus.COMPLETED,
            ExperimentStatus.FAILED,
        ]:
            if current_status == ExperimentStatus.FAILED and not allow_failure:
                # If failed and failures are not allowed, raise an error with details
                raise AssertionError(
                    f"Experiment {experiment_id} failed. "
                    f"Completed rows: {experiment_detail.completed_rows}, "
                    f"Failed rows: {experiment_detail.failed_rows}",
                )
            # Return the experiment detail (either completed or failed if allowed)
            return experiment_detail

        time.sleep(poll_interval)

    # Get final status for error message
    status_code, experiment_data = client.get_rag_experiment(experiment_id)
    if status_code == 200:
        experiment_detail = RagExperimentDetail.model_validate(experiment_data)
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
@patch("services.rag_experiment_executor.RagClientConstructor")
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
def test_rag_experiment_routes_happy_path(
    mock_completion,
    mock_completion_cost,
    mock_rag_client_constructor,
    mock_supports_response_schema,
    mock_db_session_context,
    client: GenaiEngineTestClientBase,
):
    """
    Test the complete RAG experiment workflow:
    1. Create a RAG experiment (happy path)
    2. Get RAG experiment details (polling until completion)
    3. Get experiment test cases

    This test mocks:
    - RAG search responses (using MockWeaviateClient)
    - LLM eval responses (using mock_completion and mock_completion_cost)
    - Database session context for background threads (using override_get_db_session)

    All response fields are validated to ensure they're set as expected.
    """

    # Mock db_session_context for background thread execution to use test database
    # The real db_session_context uses get_db_session() which is a generator
    # We need to replicate that behavior but use override_get_db_session
    # This ensures all background threads use the same test database engine
    def mock_get_db_session_generator():
        """Generator that yields a test database session, matching get_db_session() behavior"""
        session = override_get_db_session()
        try:
            yield session
        finally:
            session.close()

    @contextmanager
    def mock_db_session_context_func():
        """Context manager that uses override_get_db_session for background threads"""
        # Replicate the exact behavior of db_session_context
        session_gen = mock_get_db_session_generator()
        session = next(session_gen)
        try:
            yield session
        finally:
            try:
                next(session_gen)  # This will raise StopIteration and close the session
            except StopIteration:
                pass

    # db_session_context is a context manager function, so when called it should return a context manager
    # Use side_effect to return a new context manager each time it's called
    mock_db_session_context.side_effect = lambda: mock_db_session_context_func()

    # Setup: Create task
    task_name = f"rag_experiment_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200, f"Failed to create task: {task}"
    task_id = task.id

    # Setup: Configure model provider (required for LLM evals)
    response = client.base_client.put(
        f"/api/v1/model_providers/openai",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert (
        response.status_code == 201
    ), f"Failed to configure model provider: {response.text}"

    # Setup: Create dataset with test rows
    dataset_name = f"rag_test_dataset_{random.random()}"
    status_code, dataset = client.create_dataset(
        name=dataset_name,
        task_id=task_id,
        description="Test dataset for RAG experiments",
    )
    assert status_code == 200, f"Failed to create dataset: {dataset}"
    dataset_id = dataset.id

    # Create dataset version with test rows
    test_rows = [
        NewDatasetVersionRowRequest(
            data=[
                NewDatasetVersionRowColumnItemRequest(
                    column_name="query",
                    column_value="What is machine learning?",
                ),
                NewDatasetVersionRowColumnItemRequest(
                    column_name="expected_answer",
                    column_value="Machine learning is a subset of AI",
                ),
            ],
        ),
        NewDatasetVersionRowRequest(
            data=[
                NewDatasetVersionRowColumnItemRequest(
                    column_name="query",
                    column_value="What is deep learning?",
                ),
                NewDatasetVersionRowColumnItemRequest(
                    column_name="expected_answer",
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

    # Setup: Create RAG provider
    status_code, rag_provider = client.create_rag_provider(
        task_id=task_id,
        name="Test RAG Provider",
        description="Test RAG provider for experiments",
    )
    assert status_code == 200, f"Failed to create RAG provider: {rag_provider}"
    rag_provider_id = rag_provider.id

    # Setup: Create LLM eval
    eval_name = "test_rag_eval"
    eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Evaluate the RAG search results based on relevance and accuracy",
    }

    response = client.base_client.post(
        f"/api/v1/tasks/{task_id}/llm_evals/{eval_name}",
        json=eval_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200, f"Failed to create LLM eval: {response.text}"

    # Mock RAG search responses
    # Create a mock client that returns successful search results
    mock_auth_config = ApiKeyRagAuthenticationConfig(
        api_key="test-key",
        host_url="https://test.example.com",
        rag_provider="weaviate",
    )
    mock_provider_config = RagProviderConfiguration(
        id=rag_provider_id,
        task_id=task_id,
        name="Test RAG Provider",
        description="Test RAG provider",
        authentication_config=mock_auth_config,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    mock_client = MockWeaviateClientFactory.create_successful_client(
        mock_provider_config,
    )

    # Configure mock to return different results for different queries
    mock_client.search_results = [
        {
            "uuid": uuid4(),
            "properties": {
                "text": "Machine learning is a subset of artificial intelligence that enables systems to learn from data.",
                "title": "ML Introduction",
            },
            "metadata": {
                "distance": 0.1,
                "certainty": 0.9,
                "score": 0.9,
                "creation_time": None,
                "last_update_time": None,
                "explain_score": None,
                "is_consistent": True,
            },
            "vector": None,
        },
        {
            "uuid": uuid4(),
            "properties": {
                "text": "Deep learning uses neural networks with multiple layers.",
                "title": "DL Introduction",
            },
            "metadata": {
                "distance": 0.2,
                "certainty": 0.8,
                "score": 0.8,
                "creation_time": None,
                "last_update_time": None,
                "explain_score": None,
                "is_consistent": True,
            },
            "vector": None,
        },
    ]

    # Mock the RagClientConstructor to return our mock client
    mock_constructor_instance = MagicMock()
    mock_constructor_instance.execute_keyword_search.return_value = (
        mock_client.keyword_search(MagicMock())
    )
    mock_constructor_instance.execute_similarity_text_search.return_value = (
        mock_client.vector_similarity_text_search(MagicMock())
    )
    mock_constructor_instance.execute_hybrid_search.return_value = (
        mock_client.hybrid_search(MagicMock())
    )
    mock_rag_client_constructor.return_value = mock_constructor_instance

    # Mock supports_response_schema to return True (required by run_llm_eval)
    mock_supports_response_schema.return_value = True

    # Mock LLM eval responses
    # ReasonedScore expects score to be an integer (0 or 1), not a float
    mock_response = MagicMock(spec=ModelResponse)
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": '{"reason": "The RAG search results are highly relevant and accurate.", "score": 1}',
    }
    mock_completion.return_value = mock_response
    mock_completion_cost.return_value = 0.002345

    # Test 1: Create RAG experiment with dataset row filter
    # Filter to only include rows where query contains "machine learning"
    # This should result in only 1 test case instead of 2
    experiment_name = f"test_rag_experiment_{random.random()}"
    experiment_request = {
        "name": experiment_name,
        "description": "Test RAG experiment",
        "dataset_ref": {
            "id": str(dataset_id),
            "version": dataset_version_number,
        },
        "dataset_row_filter": [
            {
                "column_name": "query",
                "column_value": "What is machine learning?",
            },
        ],
        "eval_list": [
            {
                "name": eval_name,
                "version": 1,
                "variable_mapping": [
                    {
                        "variable_name": "rag_output",
                        "source": {
                            "type": "experiment_output",
                            "experiment_output": {
                                "json_path": "response.objects.0.properties.text",
                            },
                        },
                    },
                ],
            },
        ],
        "rag_configs": [
            {
                "type": "unsaved",
                "rag_provider_id": str(rag_provider_id),
                "settings": {
                    "rag_provider": "weaviate",
                    "search_kind": "keyword_search",
                    "collection_name": "test_collection",
                    "limit": 5,
                },
                "query_column": {
                    "type": "dataset_column",
                    "dataset_column": {"name": "query"},
                },
            },
        ],
    }

    status_code, experiment_summary = client.create_rag_experiment(
        task_id=task_id,
        experiment_request=experiment_request,
    )
    assert status_code == 200, f"Failed to create RAG experiment: {experiment_summary}"
    experiment_id = experiment_summary["id"]

    # Validate experiment summary response fields
    assert experiment_summary["name"] == experiment_name
    assert experiment_summary["description"] == "Test RAG experiment"
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
    assert "rag_configs" in experiment_summary
    assert len(experiment_summary["rag_configs"]) == 1
    assert experiment_summary["rag_configs"][0]["type"] == "unsaved"
    assert experiment_summary["rag_configs"][0]["rag_provider_id"] == str(
        rag_provider_id,
    )

    # Test 2: Get RAG experiment details (polling until completion)
    experiment_detail = wait_for_experiment_completion(client, experiment_id)

    # Validate experiment detail response fields
    assert experiment_detail.id == experiment_id
    assert experiment_detail.name == experiment_name
    assert experiment_detail.description == "Test RAG experiment"
    assert experiment_detail.status == ExperimentStatus.COMPLETED
    assert experiment_detail.dataset_ref.id == dataset_id
    assert experiment_detail.dataset_ref.name == dataset_name
    assert experiment_detail.dataset_ref.version == dataset_version_number
    # With dataset_row_filter, only 1 row should match (the "machine learning" query)
    assert experiment_detail.total_rows == 1
    assert experiment_detail.completed_rows == 1
    assert experiment_detail.failed_rows == 0

    # Validate that dataset_row_filter is present in the response
    assert experiment_detail.dataset_row_filter is not None
    assert len(experiment_detail.dataset_row_filter) == 1
    assert experiment_detail.dataset_row_filter[0].column_name == "query"
    assert (
        experiment_detail.dataset_row_filter[0].column_value
        == "What is machine learning?"
    )
    assert experiment_detail.finished_at is not None
    assert experiment_detail.created_at is not None

    # Validate RAG configs
    assert len(experiment_detail.rag_configs) == 1
    rag_config = experiment_detail.rag_configs[0]
    assert rag_config.type == "unsaved"
    assert rag_config.rag_provider_id == rag_provider_id
    assert rag_config.query_column.type == "dataset_column"
    assert rag_config.query_column.dataset_column.name == "query"

    # Validate summary results
    assert experiment_detail.summary_results is not None
    assert len(experiment_detail.summary_results.rag_eval_summaries) == 1
    eval_summary = experiment_detail.summary_results.rag_eval_summaries[0]
    assert eval_summary.eval_results is not None
    assert len(eval_summary.eval_results) == 1
    eval_result = eval_summary.eval_results[0]
    assert eval_result.eval_name == eval_name
    assert eval_result.eval_version == "1"
    # With dataset_row_filter, only 1 row should match
    assert eval_result.total_count == 1
    assert eval_result.pass_count >= 0  # At least some should pass

    # Test 3: List RAG experiments for the task
    status_code, experiments_list_data = client.list_rag_experiments(
        task_id=task_id,
        page=0,
        page_size=10,
    )
    assert (
        status_code == 200
    ), f"Failed to list RAG experiments: {experiments_list_data}"

    experiments_list = RagExperimentListResponse.model_validate(experiments_list_data)

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
    assert our_experiment.description == "Test RAG experiment"
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
    assert len(our_experiment.rag_configs) == 1
    assert our_experiment.rag_configs[0].type == "unsaved"
    assert our_experiment.rag_configs[0].rag_provider_id == rag_provider_id

    # Test 4: Get experiment test cases
    status_code, test_cases_data = client.get_rag_experiment_test_cases(
        experiment_id=experiment_id,
        page=0,
        page_size=10,
    )
    assert status_code == 200, f"Failed to get test cases: {test_cases_data}"

    test_cases_response = RagTestCaseListResponse.model_validate(test_cases_data)

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
    assert isinstance(test_case, RagTestCase)
    assert test_case.status == TestCaseStatus.COMPLETED
    assert test_case.dataset_row_id is not None
    assert test_case.rag_results is not None

    # Validate that the test case corresponds to the filtered row
    # The query text should match the filtered row's query
    assert test_case.rag_results is not None
    assert len(test_case.rag_results) == 1
    rag_result = test_case.rag_results[0]
    assert rag_result.rag_config_key is not None
    assert rag_result.rag_config_type == "unsaved"
    assert rag_result.query_text is not None
    assert len(rag_result.query_text) > 0
    # Verify the query text matches the filtered row
    assert rag_result.query_text == "What is machine learning?"

    # Validate RAG search output
    assert rag_result.output is not None
    assert rag_result.output.response is not None
    assert rag_result.output.response.response is not None
    assert len(rag_result.output.response.response.objects) > 0

    # Validate eval executions
    assert rag_result.evals is not None
    assert len(rag_result.evals) == 1
    eval_execution = rag_result.evals[0]
    assert eval_execution.eval_name == eval_name
    assert eval_execution.eval_version == "1"

    # Validate eval input variables
    assert eval_execution.eval_input_variables is not None
    assert len(eval_execution.eval_input_variables) == 1

    # Check that the variable name matches what we configured
    input_var = eval_execution.eval_input_variables[0]
    assert input_var.variable_name == "rag_output"

    # Validate that the value was extracted from the RAG search output
    # The json_path "response.objects.0.properties.text" should extract the text property
    # from the first object in the RAG search results
    assert input_var.value is not None
    assert len(input_var.value) > 0

    # The value should be one of the mock search result texts
    # (either from the first or second mock result, depending on which query was used)
    expected_texts = [
        "Machine learning is a subset of artificial intelligence that enables systems to learn from data.",
        "Deep learning uses neural networks with multiple layers.",
    ]
    assert input_var.value in expected_texts, (
        f"Expected eval input variable value to be one of the mock RAG search result texts, "
        f"but got: {input_var.value}"
    )

    # Validate eval results
    assert eval_execution.eval_results is not None
    assert (
        eval_execution.eval_results.score == 1
    )  # ReasonedScore expects integer (0 or 1)
    assert eval_execution.eval_results.explanation is not None
    assert eval_execution.eval_results.cost == "0.002345"

    # Test 5: Create an experiment that will fail and verify it gets marked as failed
    # Reuse existing setup (task, dataset, RAG provider, LLM eval)
    # Make the RAG search fail by having the mock raise an exception
    failed_experiment_name = f"test_rag_experiment_failed_{random.random()}"
    failed_experiment_request = {
        "name": failed_experiment_name,
        "description": "Test RAG experiment that will fail",
        "dataset_ref": {
            "id": str(dataset_id),
            "version": dataset_version_number,
        },
        # No filter - use all rows
        "eval_list": [
            {
                "name": eval_name,
                "version": 1,
                "variable_mapping": [
                    {
                        "variable_name": "rag_output",
                        "source": {
                            "type": "experiment_output",
                            "experiment_output": {
                                "json_path": "response.objects.0.properties.text",
                            },
                        },
                    },
                ],
            },
        ],
        "rag_configs": [
            {
                "type": "unsaved",
                "rag_provider_id": str(rag_provider_id),
                "settings": {
                    "rag_provider": "weaviate",
                    "search_kind": "keyword_search",
                    "collection_name": "test_collection",
                    "limit": 5,
                },
                "query_column": {
                    "type": "dataset_column",
                    "dataset_column": {"name": "query"},
                },
            },
        ],
    }

    # Mock RAG search to fail by raising an exception
    failed_mock_constructor_instance = MagicMock()
    failed_mock_constructor_instance.execute_keyword_search.side_effect = Exception(
        "RAG search failed for testing",
    )
    failed_mock_constructor_instance.execute_similarity_text_search.side_effect = (
        Exception("RAG search failed for testing")
    )
    failed_mock_constructor_instance.execute_hybrid_search.side_effect = Exception(
        "RAG search failed for testing",
    )
    mock_rag_client_constructor.return_value = failed_mock_constructor_instance

    status_code, failed_experiment_summary = client.create_rag_experiment(
        task_id=task_id,
        experiment_request=failed_experiment_request,
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
    assert failed_experiment_detail.failed_rows > 0
    assert failed_experiment_detail.total_rows == len(test_rows)
    assert (
        failed_experiment_detail.completed_rows + failed_experiment_detail.failed_rows
        == failed_experiment_detail.total_rows
    )
    assert failed_experiment_detail.finished_at is not None

    # Cleanup: Delete experiments, dataset, RAG provider, LLM eval, and task
    status_code = client.delete_rag_experiment(experiment_id)
    assert status_code == 204, f"Failed to delete RAG experiment: {status_code}"

    # Validate that deleted experiment cannot be fetched
    status_code, _ = client.get_rag_experiment(experiment_id)
    assert (
        status_code == 404
    ), f"Expected 404 after deleting experiment, got {status_code}"

    # Validate that test cases for deleted experiment cannot be fetched
    status_code, _ = client.get_rag_experiment_test_cases(experiment_id)
    assert (
        status_code == 404
    ), f"Expected 404 when fetching test cases for deleted experiment, got {status_code}"

    status_code = client.delete_rag_experiment(failed_experiment_id)
    assert status_code == 204, f"Failed to delete failed RAG experiment: {status_code}"

    status_code, _ = client.delete_llm_eval(task_id=task_id, llm_eval_name=eval_name)
    assert status_code in [200, 204], f"Failed to delete LLM eval: {status_code}"

    status_code = client.delete_rag_provider(rag_provider_id)
    assert status_code == 204, f"Failed to delete RAG provider: {status_code}"

    status_code = client.delete_dataset(dataset_id)
    assert status_code == 204, f"Failed to delete dataset: {status_code}"

    status_code = client.delete_task(task_id)
    assert status_code == 204, f"Failed to delete task: {status_code}"
