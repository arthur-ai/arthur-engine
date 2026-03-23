"""
Unit tests for RAG notebook routes.

This module tests the RAG notebook API endpoints:
- Creating a RAG notebook
- Getting RAG notebook details
- Listing RAG notebooks
- Updating RAG notebook metadata
- Getting/setting RAG notebook state
- Getting RAG notebook history
- Deleting RAG notebook
- Attaching notebook to experiment

All tests clean up test state after execution.
"""

import random
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from litellm.types.utils import ModelResponse

from schemas.base_experiment_schemas import (
    DatasetColumnSource,
    DatasetColumnVariableSource,
    DatasetRefInput,
    EvalRef,
    EvalVariableMapping,
    ExperimentOutputSource,
    ExperimentOutputVariableSource,
)
from schemas.common_schemas import (
    NewDatasetVersionRowColumnItemRequest,
    NewDatasetVersionRowRequest,
)
from schemas.internal_schemas import (
    ApiKeyRagAuthenticationConfig,
    RagProviderConfiguration,
)
from schemas.rag_experiment_schemas import (
    CreateRagExperimentRequest,
    RagExperimentListResponse,
    UnsavedRagConfig,
)
from schemas.rag_notebook_schemas import (
    CreateRagNotebookRequest,
    RagNotebookDetail,
    RagNotebookListResponse,
    RagNotebookState,
    RagNotebookStateResponse,
    SetRagNotebookStateRequest,
    UpdateRagNotebookRequest,
)
from schemas.request_schemas import (
    CreateEvalRequest,
    WeaviateKeywordSearchSettingsConfigurationRequest,
)
from services.rag_experiment_executor import RagExperimentExecutor
from tests.clients.base_test_client import GenaiEngineTestClientBase
from tests.mocks.mock_weaviate_client import MockWeaviateClientFactory
from tests.unit.routes.conftest import setup_db_session_context_mock


@pytest.mark.unit_tests
@patch("services.experiment_executor.BaseExperimentExecutor.execute_experiment_async")
@patch("services.experiment_executor.db_session_context")
@patch("repositories.llm_evals_repository.supports_response_schema")
@patch("services.rag_experiment_executor.RagClientConstructor")
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
def test_rag_notebook_routes_happy_path(
    mock_completion,
    mock_completion_cost,
    mock_rag_client_constructor,
    mock_supports_response_schema,
    mock_db_session_context,
    mock_execute_async,
    client: GenaiEngineTestClientBase,
):
    """
    Test the complete RAG notebook workflow:
    1. Create a RAG notebook
    2. Get RAG notebook details
    3. List RAG notebooks
    4. Update notebook metadata
    5. Get/set notebook state
    6. Create an experiment from the notebook
    7. Get notebook history
    8. Attach notebook to existing experiment
    9. Delete notebook

    This test mocks:
    - RAG search responses (using MockWeaviateClient)
    - LLM eval responses (using mock_completion and mock_completion_cost)
    - Database session context for background threads (using override_get_db_session)

    All response fields are validated to ensure they're set as expected.
    """

    # Mock db_session_context for background thread execution to use test database
    setup_db_session_context_mock(mock_db_session_context)

    def sync_execute(experiment_id, request_time_parameters=None):
        executor = RagExperimentExecutor()
        return executor._execute_experiment(experiment_id, request_time_parameters)

    mock_execute_async.side_effect = sync_execute

    # Setup: Create task
    task_name = f"rag_notebook_task_{random.random()}"
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
    dataset_name = f"rag_notebook_test_dataset_{random.random()}"
    status_code, dataset = client.create_dataset(
        name=dataset_name,
        task_id=task_id,
        description="Test dataset for RAG notebooks",
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
        description="Test RAG provider for notebooks",
    )
    assert status_code == 200, f"Failed to create RAG provider: {rag_provider}"
    rag_provider_id = rag_provider.id

    # Setup: Create LLM eval
    eval_name = "test_rag_eval"
    eval_data = CreateEvalRequest(
        model_name="gpt-4o",
        model_provider="openai",
        instructions="Evaluate the RAG search results based on relevance and accuracy",
    )

    response = client.base_client.post(
        f"/api/v1/tasks/{task_id}/llm_evals/{eval_name}",
        json=eval_data.model_dump(mode="json"),
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200, f"Failed to create LLM eval: {response.text}"

    # Test 1: Create RAG notebook with initial state
    notebook_name = f"test_rag_notebook_{random.random()}"

    # Build notebook state using Pydantic models
    notebook_state = RagNotebookState(
        rag_configs=[
            UnsavedRagConfig(
                rag_provider_id=rag_provider_id,
                settings=WeaviateKeywordSearchSettingsConfigurationRequest(
                    collection_name="test_collection",
                    limit=5,
                ),
                query_column=DatasetColumnVariableSource(
                    type="dataset_column",
                    dataset_column=DatasetColumnSource(name="query"),
                ),
            ),
        ],
        dataset_ref=DatasetRefInput(
            id=dataset_id,
            version=dataset_version_number,
        ),
        dataset_row_filter=[
            NewDatasetVersionRowColumnItemRequest(
                column_name="query",
                column_value="What is machine learning?",
            ),
        ],
        eval_list=[
            EvalRef(
                name=eval_name,
                version=1,
                variable_mapping=[
                    EvalVariableMapping(
                        variable_name="rag_output",
                        source=ExperimentOutputVariableSource(
                            type="experiment_output",
                            experiment_output=ExperimentOutputSource(
                                json_path="response.objects.0.properties.text",
                            ),
                        ),
                    ),
                ],
            ),
        ],
    )

    notebook_request = CreateRagNotebookRequest(
        name=notebook_name,
        description="Test RAG notebook",
        state=notebook_state,
    )

    status_code, notebook_detail = client.create_rag_notebook(
        task_id=task_id,
        notebook_request=notebook_request.model_dump(mode="json"),
    )
    assert status_code == 201, f"Failed to create RAG notebook: {notebook_detail}"
    notebook_id = notebook_detail["id"]

    # Validate notebook detail response fields
    assert notebook_detail["name"] == notebook_name
    assert notebook_detail["description"] == "Test RAG notebook"
    assert notebook_detail["task_id"] == task_id
    assert "created_at" in notebook_detail
    assert "updated_at" in notebook_detail
    assert "state" in notebook_detail
    assert notebook_detail["state"]["rag_configs"] is not None
    assert len(notebook_detail["state"]["rag_configs"]) == 1
    assert notebook_detail["state"]["dataset_ref"] is not None
    assert notebook_detail["state"]["dataset_ref"]["id"] == str(dataset_id)
    assert notebook_detail["state"]["eval_list"] is not None
    assert len(notebook_detail["state"]["eval_list"]) == 1
    assert notebook_detail["experiments"] == []  # No experiments yet

    # Test 2: Get RAG notebook details
    status_code, notebook_detail = client.get_rag_notebook(notebook_id)
    assert status_code == 200, f"Failed to get RAG notebook: {notebook_detail}"

    notebook = RagNotebookDetail.model_validate(notebook_detail)
    assert notebook.id == notebook_id
    assert notebook.name == notebook_name
    assert notebook.description == "Test RAG notebook"
    assert notebook.task_id == task_id
    assert notebook.state.rag_configs is not None
    assert len(notebook.state.rag_configs) == 1
    assert notebook.state.dataset_ref is not None
    assert notebook.state.dataset_ref.id == dataset_id
    assert notebook.experiments == []  # No experiments yet

    # Test 3: List RAG notebooks
    status_code, notebooks_list_data = client.list_rag_notebooks(
        task_id=task_id,
        page=0,
        page_size=10,
    )
    assert status_code == 200, f"Failed to list RAG notebooks: {notebooks_list_data}"

    notebooks_list = RagNotebookListResponse.model_validate(notebooks_list_data)
    assert notebooks_list.page == 0
    assert notebooks_list.page_size == 10
    assert notebooks_list.total_count >= 1
    assert notebooks_list.total_pages >= 1
    assert len(notebooks_list.data) >= 1

    # Find our notebook in the list
    our_notebook = None
    for nb in notebooks_list.data:
        if nb.id == notebook_id:
            our_notebook = nb
            break

    assert our_notebook is not None, f"Notebook {notebook_id} not found in list"
    assert our_notebook.name == notebook_name
    assert our_notebook.description == "Test RAG notebook"
    assert our_notebook.run_count == 0  # No experiments run yet
    assert our_notebook.latest_run_id is None
    assert our_notebook.latest_run_status is None

    # Test 4: List notebooks with name filter
    status_code, filtered_list_data = client.list_rag_notebooks(
        task_id=task_id,
        page=0,
        page_size=10,
        name=notebook_name,
    )
    assert (
        status_code == 200
    ), f"Failed to list filtered notebooks: {filtered_list_data}"
    filtered_list = RagNotebookListResponse.model_validate(filtered_list_data)
    assert filtered_list.total_count == 1
    assert len(filtered_list.data) == 1
    assert filtered_list.data[0].id == notebook_id

    # Test 5: Update notebook metadata
    update_request = UpdateRagNotebookRequest(
        name=f"{notebook_name}_updated",
        description="Updated description",
    )
    status_code, updated_notebook = client.update_rag_notebook(
        notebook_id=notebook_id,
        update_request=update_request.model_dump(mode="json"),
    )
    assert status_code == 200, f"Failed to update notebook: {updated_notebook}"
    assert updated_notebook["name"] == f"{notebook_name}_updated"
    assert updated_notebook["description"] == "Updated description"
    # State should remain unchanged
    assert updated_notebook["state"]["rag_configs"] is not None

    # Test 6: Get notebook state
    status_code, state_data = client.get_rag_notebook_state(notebook_id)
    assert status_code == 200, f"Failed to get notebook state: {state_data}"

    state = RagNotebookStateResponse.model_validate(state_data)
    assert state.rag_configs is not None
    assert len(state.rag_configs) == 1
    assert state.dataset_ref is not None
    assert state.eval_list is not None

    # Test 7: Set notebook state (update the state)
    new_state = RagNotebookState(
        rag_configs=[
            UnsavedRagConfig(
                rag_provider_id=rag_provider_id,
                settings=WeaviateKeywordSearchSettingsConfigurationRequest(
                    collection_name="test_collection",
                    limit=10,  # Changed limit
                ),
                query_column=DatasetColumnVariableSource(
                    type="dataset_column",
                    dataset_column=DatasetColumnSource(name="query"),
                ),
            ),
        ],
        dataset_ref=DatasetRefInput(
            id=dataset_id,
            version=dataset_version_number,
        ),
        # Remove dataset_row_filter (set to None)
        dataset_row_filter=None,
        eval_list=[
            EvalRef(
                name=eval_name,
                version=1,
                variable_mapping=[
                    EvalVariableMapping(
                        variable_name="rag_output",
                        source=ExperimentOutputVariableSource(
                            type="experiment_output",
                            experiment_output=ExperimentOutputSource(
                                json_path="response.objects.0.properties.text",
                            ),
                        ),
                    ),
                ],
            ),
        ],
    )

    new_state_request = SetRagNotebookStateRequest(state=new_state)

    status_code, updated_notebook = client.set_rag_notebook_state(
        notebook_id=notebook_id,
        state_request=new_state_request.model_dump(mode="json"),
    )
    assert status_code == 200, f"Failed to set notebook state: {updated_notebook}"
    # Verify state was updated
    assert updated_notebook["state"]["rag_configs"] is not None
    assert len(updated_notebook["state"]["rag_configs"]) == 1
    # Verify dataset_row_filter was removed
    assert updated_notebook["state"].get("dataset_row_filter") is None

    # Test 8: Create an experiment from the notebook state
    # First, mock RAG search responses
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

    mock_client.search_results = [
        {
            "uuid": uuid4(),
            "properties": {
                "text": "Machine learning is a subset of artificial intelligence.",
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
    ]

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
    mock_supports_response_schema.return_value = True

    mock_response = MagicMock(spec=ModelResponse)
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": '{"reason": "The RAG search results are relevant.", "score": 1}',
    }
    mock_completion.return_value = mock_response
    mock_completion_cost.return_value = 0.002345

    # Create experiment using the notebook state
    experiment_name = f"test_experiment_from_notebook_{random.random()}"
    experiment_request = CreateRagExperimentRequest(
        name=experiment_name,
        description="Experiment created from notebook",
        dataset_ref=DatasetRefInput(
            id=dataset_id,
            version=dataset_version_number,
        ),
        rag_configs=[
            UnsavedRagConfig(
                rag_provider_id=rag_provider_id,
                settings=WeaviateKeywordSearchSettingsConfigurationRequest(
                    collection_name="test_collection",
                    limit=10,
                ),
                query_column=DatasetColumnVariableSource(
                    type="dataset_column",
                    dataset_column=DatasetColumnSource(name="query"),
                ),
            ),
        ],
        eval_list=[
            EvalRef(
                name=eval_name,
                version=1,
                variable_mapping=[
                    EvalVariableMapping(
                        variable_name="rag_output",
                        source=ExperimentOutputVariableSource(
                            type="experiment_output",
                            experiment_output=ExperimentOutputSource(
                                json_path="response.objects.0.properties.text",
                            ),
                        ),
                    ),
                ],
            ),
        ],
    )

    status_code, experiment_summary = client.create_rag_experiment(
        task_id=task_id,
        experiment_request=experiment_request.model_dump(mode="json"),
    )
    assert status_code == 200, f"Failed to create experiment: {experiment_summary}"
    experiment_id = experiment_summary["id"]

    # Attach notebook to the experiment
    status_code, attached_experiment = client.attach_notebook_to_rag_experiment(
        experiment_id=experiment_id,
        notebook_id=notebook_id,
    )
    assert status_code == 200, f"Failed to attach notebook: {attached_experiment}"

    # Verify notebook_id is set by fetching experiment detail
    status_code, experiment_detail = client.get_rag_experiment(experiment_id)
    assert status_code == 200, f"Failed to get experiment: {experiment_detail}"
    assert experiment_detail.get("notebook_id") == notebook_id

    # Test 9: Get notebook history (should include the experiment we just created)
    status_code, history_data = client.get_rag_notebook_history(
        notebook_id=notebook_id,
        page=0,
        page_size=10,
    )
    assert status_code == 200, f"Failed to get notebook history: {history_data}"

    history = RagExperimentListResponse.model_validate(history_data)
    assert history.total_count >= 1
    assert len(history.data) >= 1

    # Find our experiment in the history
    our_experiment = None
    for exp in history.data:
        if exp.id == experiment_id:
            our_experiment = exp
            break

    assert (
        our_experiment is not None
    ), f"Experiment {experiment_id} not found in history"
    assert our_experiment.name == experiment_name

    # Test 10: Verify notebook details now show the experiment
    status_code, notebook_detail = client.get_rag_notebook(notebook_id)
    assert status_code == 200, f"Failed to get notebook: {notebook_detail}"

    notebook = RagNotebookDetail.model_validate(notebook_detail)
    assert len(notebook.experiments) >= 1
    assert notebook.experiments[0].id == experiment_id

    # Test 11: Verify notebook summary shows run count
    status_code, notebooks_list_data = client.list_rag_notebooks(
        task_id=task_id,
        page=0,
        page_size=10,
    )
    assert status_code == 200, f"Failed to list notebooks: {notebooks_list_data}"

    notebooks_list = RagNotebookListResponse.model_validate(notebooks_list_data)
    our_notebook = None
    for nb in notebooks_list.data:
        if nb.id == notebook_id:
            our_notebook = nb
            break

    assert our_notebook is not None
    assert our_notebook.run_count >= 1
    assert our_notebook.latest_run_id == experiment_id
    assert our_notebook.latest_run_status is not None

    # Cleanup: Delete experiment, notebook, dataset, RAG provider, LLM eval, and task
    status_code = client.delete_rag_experiment(experiment_id)
    assert status_code == 204, f"Failed to delete experiment: {status_code}"

    status_code = client.delete_rag_notebook(notebook_id)
    assert status_code == 204, f"Failed to delete notebook: {status_code}"

    # Validate that deleted notebook cannot be fetched
    status_code, _ = client.get_rag_notebook(notebook_id)
    assert (
        status_code == 404
    ), f"Expected 404 after deleting notebook, got {status_code}"

    status_code, _ = client.delete_llm_eval(task_id=task_id, llm_eval_name=eval_name)
    assert status_code in [200, 204], f"Failed to delete LLM eval: {status_code}"

    status_code = client.delete_rag_provider(rag_provider_id)
    assert status_code == 204, f"Failed to delete RAG provider: {status_code}"

    status_code = client.delete_dataset(dataset_id)
    assert status_code == 204, f"Failed to delete dataset: {status_code}"

    status_code = client.delete_task(task_id)
    assert status_code == 204, f"Failed to delete task: {status_code}"


@pytest.mark.unit_tests
def test_rag_notebook_validation_errors(
    client: GenaiEngineTestClientBase,
):
    """
    Test that creating a RAG notebook with invalid resource references returns 400 errors.
    """
    # Setup: Create task
    task_name = f"rag_notebook_validation_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200, f"Failed to create task: {task}"
    task_id = task.id

    # Test 1: Create notebook with non-existent dataset
    notebook_state = RagNotebookState(
        dataset_ref=DatasetRefInput(
            id=uuid4(),  # Non-existent dataset ID
            version=1,
        ),
    )
    notebook_request = CreateRagNotebookRequest(
        name="test_invalid_dataset",
        state=notebook_state,
    )
    status_code, response = client.create_rag_notebook(
        task_id=task_id,
        notebook_request=notebook_request.model_dump(mode="json"),
    )
    assert (
        status_code == 400
    ), f"Expected 400 for non-existent dataset, got {status_code}"
    assert "not found" in response.get("detail", "").lower()

    # Test 2: Create notebook with non-existent RAG provider
    notebook_state = RagNotebookState(
        rag_configs=[
            UnsavedRagConfig(
                rag_provider_id=uuid4(),  # Non-existent RAG provider ID
                settings=WeaviateKeywordSearchSettingsConfigurationRequest(
                    collection_name="test_collection",
                    limit=5,
                ),
                query_column=DatasetColumnVariableSource(
                    type="dataset_column",
                    dataset_column=DatasetColumnSource(name="query"),
                ),
            ),
        ],
    )
    notebook_request = CreateRagNotebookRequest(
        name="test_invalid_rag_provider",
        state=notebook_state,
    )
    status_code, response = client.create_rag_notebook(
        task_id=task_id,
        notebook_request=notebook_request.model_dump(mode="json"),
    )
    assert (
        status_code == 400
    ), f"Expected 400 for non-existent RAG provider, got {status_code}"
    assert "not found" in response.get("detail", "").lower()

    # Test 3: Create notebook with non-existent eval
    notebook_state = RagNotebookState(
        eval_list=[
            EvalRef(
                name="non_existent_eval",
                version=1,
                variable_mapping=[],
            ),
        ],
    )
    notebook_request = CreateRagNotebookRequest(
        name="test_invalid_eval",
        state=notebook_state,
    )
    status_code, response = client.create_rag_notebook(
        task_id=task_id,
        notebook_request=notebook_request.model_dump(mode="json"),
    )
    assert status_code == 400, f"Expected 400 for non-existent eval, got {status_code}"
    assert "not found" in response.get("detail", "").lower()

    # Test 4: Create notebook with no state (should succeed)
    notebook_request = CreateRagNotebookRequest(
        name="test_no_state",
        description="Notebook without initial state",
    )
    status_code, notebook_detail = client.create_rag_notebook(
        task_id=task_id,
        notebook_request=notebook_request.model_dump(mode="json"),
    )
    assert (
        status_code == 201
    ), f"Expected 201 for notebook without state, got {status_code}"
    notebook_id = notebook_detail["id"]

    # Cleanup
    status_code = client.delete_rag_notebook(notebook_id)
    assert status_code == 204, f"Failed to delete notebook: {status_code}"

    status_code = client.delete_task(task_id)
    assert status_code == 204, f"Failed to delete task: {status_code}"
