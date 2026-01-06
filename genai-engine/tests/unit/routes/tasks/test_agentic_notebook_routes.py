"""
Unit tests for agentic notebook routes.

This module tests the agentic notebook API endpoints:
- Creating an agentic notebook
- Getting agentic notebook details
- Listing agentic notebooks
- Updating agentic notebook metadata
- Getting/setting agentic notebook state
- Getting agentic notebook history
- Deleting agentic notebook
- Attaching notebook to experiment

All tests clean up test state after execution.
"""

import random
import time
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from litellm.types.utils import ModelResponse
from openinference.semconv.trace import SpanAttributes
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue
from opentelemetry.proto.trace.v1.trace_pb2 import Status

from schemas.agentic_experiment_schemas import (
    AgenticEvalRef,
    AgenticEvalVariableMapping,
    AgenticExperimentDetail,
    AgenticExperimentListResponse,
    AgenticExperimentOutputVariableSource,
    CreateAgenticExperimentRequest,
    GeneratedVariableSource,
    HttpHeader,
    HttpTemplate,
    RequestTimeParameterSource,
    TemplateVariableMapping,
    TransformVariableExperimentOutputSource,
)
from schemas.agentic_notebook_schemas import (
    AgenticNotebookDetail,
    AgenticNotebookListResponse,
    AgenticNotebookState,
    AgenticNotebookStateResponse,
    CreateAgenticNotebookRequest,
    SetAgenticNotebookStateRequest,
    UpdateAgenticNotebookRequest,
)
from schemas.base_experiment_schemas import (
    DatasetColumnSource,
    DatasetColumnVariableSource,
    DatasetRefInput,
    ExperimentStatus,
)
from schemas.common_schemas import (
    NewDatasetVersionRowColumnItemRequest,
    NewDatasetVersionRowRequest,
)
from schemas.request_schemas import (
    NewTraceTransformRequest,
    TraceTransformDefinition,
    TraceTransformVariableDefinition,
)
from tests.clients.base_test_client import GenaiEngineTestClientBase
from tests.routes.trace_api.conftest import (
    _create_base_trace_request,
    _create_span,
)
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
) -> AgenticExperimentDetail:
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
        AgenticExperimentDetail: The completed experiment details

    Raises:
        TimeoutError: If experiment doesn't complete within max_wait_time
        AssertionError: If experiment failed and allow_failure is False
    """
    start_time = time.time()
    last_status = None
    while time.time() - start_time < max_wait_time:
        status_code, experiment_data = client.get_agentic_experiment(experiment_id)
        assert status_code == 200, f"Failed to get experiment: {experiment_data}"

        experiment_detail = AgenticExperimentDetail.model_validate(experiment_data)
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
    status_code, experiment_data = client.get_agentic_experiment(experiment_id)
    if status_code == 200:
        experiment_detail = AgenticExperimentDetail.model_validate(experiment_data)
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


def create_mock_trace_with_session_id(
    client: GenaiEngineTestClientBase,
    task_id: str,
    session_id: str,
    trace_id: str = None,
) -> str:
    """
    Create a mock trace with the given session_id.

    Args:
        client: Test client instance
        task_id: Task ID for the trace
        session_id: Session ID to set on the trace
        trace_id: Optional trace ID (will be generated if not provided)

    Returns:
        str: The trace ID
    """
    if trace_id is None:
        trace_id = f"trace_{uuid4()}"

    # Create a trace request with the session_id
    trace_request, resource_span, scope_span = _create_base_trace_request(
        task_id=task_id,
    )

    # Create span with session_id
    # The transform will extract from the trace's raw_data structure
    # We need to use the OpenInference semantic convention for output.value
    span = _create_span(
        trace_id=trace_id.encode(),
        span_id=f"span_{uuid4()}".encode(),
        name="test_span",
        span_type="LLM",
        status=Status(code=Status.STATUS_CODE_OK),
        session_id=session_id,
    )

    # Add output value using OpenInference semantic convention
    # The transform looks for attributes.output.value.object.answer
    # We'll set output.value as a JSON string that contains the object with answer
    output_data = {
        "object": {
            "answer": "Machine learning is a subset of artificial intelligence.",
        },
    }
    output_attributes = [
        KeyValue(
            key=SpanAttributes.OUTPUT_VALUE,
            value=AnyValue(string_value=str(output_data).replace("'", '"')),
        ),
    ]
    span.attributes.extend(output_attributes)

    scope_span.spans.append(span)
    resource_span.scope_spans.append(scope_span)
    trace_request.resource_spans.append(resource_span)

    # Send the trace
    status_code, response_text = client.trace_api_receive_traces(
        trace_request.SerializeToString(),
    )
    assert status_code == 200, f"Failed to create trace: {response_text}"

    return trace_id


@pytest.mark.unit_tests
@patch("services.experiment_executor.db_session_context")
@patch("repositories.llm_evals_repository.supports_response_schema")
@patch("services.agentic_experiment_executor.requests.post")
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
@patch("services.agentic_experiment_executor.logger")
@patch("services.experiment_executor.logger")
def test_agentic_notebook_routes_happy_path(
    mock_experiment_logger,
    mock_agentic_logger,
    mock_completion,
    mock_completion_cost,
    mock_requests_post,
    mock_supports_response_schema,
    mock_db_session_context,
    client: GenaiEngineTestClientBase,
):
    """
    Test the complete agentic notebook workflow:
    1. Create an agentic notebook
    2. Get agentic notebook details
    3. List agentic notebooks
    4. Update notebook metadata
    5. Get/set notebook state
    6. Create an experiment from the notebook
    7. Get notebook history
    8. Attach notebook to existing experiment
    9. Delete notebook

    This test mocks:
    - HTTP requests to agent endpoints (using mock_requests_post)
    - LLM eval responses (using mock_completion and mock_completion_cost)
    - Database session context for background threads (using override_get_db_session)

    All response fields are validated to ensure they're set as expected.
    """

    # Mock db_session_context for background thread execution to use test database
    setup_db_session_context_mock(mock_db_session_context)

    # Setup: Create task
    task_name = f"agentic_notebook_task_{random.random()}"
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
    dataset_name = f"agentic_notebook_test_dataset_{random.random()}"
    status_code, dataset = client.create_dataset(
        name=dataset_name,
        task_id=task_id,
        description="Test dataset for agentic notebooks",
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

    # Setup: Create transform
    transform_name = f"test_transform_{random.random()}"
    transform_request = NewTraceTransformRequest(
        name=transform_name,
        description="Test transform for agentic notebooks",
        definition=TraceTransformDefinition(
            variables=[
                TraceTransformVariableDefinition(
                    variable_name="final_response",
                    span_name="test_span",
                    attribute_path="attributes.output.value.object.answer",
                    fallback="No answer found",
                ),
            ],
        ),
    )

    response = client.base_client.post(
        f"/api/v1/tasks/{task_id}/traces/transforms",
        json=transform_request.model_dump(mode="json"),
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200, f"Failed to create transform: {response.text}"
    transform_id = UUID(response.json()["id"])

    # Setup: Create LLM eval
    eval_name = "test_agentic_eval"
    eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Evaluate the agent response based on relevance and accuracy",
    }

    response = client.base_client.post(
        f"/api/v1/tasks/{task_id}/llm_evals/{eval_name}",
        json=eval_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200, f"Failed to create LLM eval: {response.text}"

    # Test 1: Create agentic notebook with initial state
    notebook_name = f"test_agentic_notebook_{random.random()}"

    # Build notebook state using Pydantic models
    notebook_state = AgenticNotebookState(
        http_template=HttpTemplate(
            endpoint_name="test_endpoint",
            endpoint_url="https://api.example.com/chat",
            headers=[
                HttpHeader(name="Content-Type", value="application/json"),
                HttpHeader(name="X-API-Key", value="{{api_key}}"),
            ],
            request_body={
                "message": "{{user_message}}",
                "session_id": "{{session_id}}",
            },
        ),
        template_variable_mapping=[
            TemplateVariableMapping(
                variable_name="user_message",
                source=DatasetColumnVariableSource(
                    type="dataset_column",
                    dataset_column=DatasetColumnSource(name="user_message"),
                ),
            ),
            TemplateVariableMapping(
                variable_name="session_id",
                source=GeneratedVariableSource(
                    type="generated",
                    generator_type="uuid",
                ),
            ),
        ],
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
        eval_list=[
            AgenticEvalRef(
                name=eval_name,
                version=1,
                transform_id=transform_id,
                variable_mapping=[
                    AgenticEvalVariableMapping(
                        variable_name="agent_response",
                        source=AgenticExperimentOutputVariableSource(
                            type="experiment_output",
                            experiment_output=TransformVariableExperimentOutputSource(
                                transform_variable_name="final_response",
                            ),
                        ),
                    ),
                ],
            ),
        ],
    )

    notebook_request = CreateAgenticNotebookRequest(
        name=notebook_name,
        description="Test agentic notebook",
        state=notebook_state,
    )

    status_code, notebook_detail = client.create_agentic_notebook(
        task_id=task_id,
        notebook_request=notebook_request.model_dump(mode="json"),
    )
    assert status_code == 201, f"Failed to create agentic notebook: {notebook_detail}"
    notebook_id = notebook_detail["id"]

    # Validate notebook detail response fields
    assert notebook_detail["name"] == notebook_name
    assert notebook_detail["description"] == "Test agentic notebook"
    assert notebook_detail["task_id"] == task_id
    assert "created_at" in notebook_detail
    assert "updated_at" in notebook_detail
    assert "state" in notebook_detail
    assert notebook_detail["state"]["http_template"] is not None
    assert notebook_detail["state"]["template_variable_mapping"] is not None
    assert len(notebook_detail["state"]["template_variable_mapping"]) == 2
    assert notebook_detail["state"]["dataset_ref"] is not None
    assert notebook_detail["state"]["dataset_ref"]["id"] == str(dataset_id)
    assert notebook_detail["state"]["eval_list"] is not None
    assert len(notebook_detail["state"]["eval_list"]) == 1
    assert notebook_detail["experiments"] == []  # No experiments yet

    # Test 2: Get agentic notebook details
    status_code, notebook_detail = client.get_agentic_notebook(notebook_id)
    assert status_code == 200, f"Failed to get agentic notebook: {notebook_detail}"

    notebook = AgenticNotebookDetail.model_validate(notebook_detail)
    assert notebook.id == notebook_id
    assert notebook.name == notebook_name
    assert notebook.description == "Test agentic notebook"
    assert notebook.task_id == task_id
    assert notebook.state.http_template is not None
    assert notebook.state.template_variable_mapping is not None
    assert len(notebook.state.template_variable_mapping) == 2
    assert notebook.state.dataset_ref is not None
    assert notebook.state.dataset_ref.id == dataset_id
    assert notebook.experiments == []  # No experiments yet

    # Test 3: List agentic notebooks
    status_code, notebooks_list_data = client.list_agentic_notebooks(
        task_id=task_id,
        page=0,
        page_size=10,
    )
    assert (
        status_code == 200
    ), f"Failed to list agentic notebooks: {notebooks_list_data}"

    notebooks_list = AgenticNotebookListResponse.model_validate(notebooks_list_data)
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
    assert our_notebook.description == "Test agentic notebook"
    assert our_notebook.run_count == 0  # No experiments run yet
    assert our_notebook.latest_run_id is None
    assert our_notebook.latest_run_status is None

    # Test 4: List notebooks with name filter
    status_code, filtered_list_data = client.list_agentic_notebooks(
        task_id=task_id,
        page=0,
        page_size=10,
        name=notebook_name,
    )
    assert (
        status_code == 200
    ), f"Failed to list filtered notebooks: {filtered_list_data}"
    filtered_list = AgenticNotebookListResponse.model_validate(filtered_list_data)
    assert filtered_list.total_count == 1
    assert len(filtered_list.data) == 1
    assert filtered_list.data[0].id == notebook_id

    # Test 5: Update notebook metadata
    update_request = UpdateAgenticNotebookRequest(
        name=f"{notebook_name}_updated",
        description="Updated description",
    )
    status_code, updated_notebook = client.update_agentic_notebook(
        notebook_id=notebook_id,
        update_request=update_request.model_dump(mode="json"),
    )
    assert status_code == 200, f"Failed to update notebook: {updated_notebook}"
    assert updated_notebook["name"] == f"{notebook_name}_updated"
    assert updated_notebook["description"] == "Updated description"
    # State should remain unchanged
    assert updated_notebook["state"]["http_template"] is not None

    # Test 6: Get notebook state
    status_code, state_data = client.get_agentic_notebook_state(notebook_id)
    assert status_code == 200, f"Failed to get notebook state: {state_data}"

    state = AgenticNotebookStateResponse.model_validate(state_data)
    assert state.http_template is not None
    assert state.template_variable_mapping is not None
    assert state.dataset_ref is not None
    assert state.eval_list is not None

    # Test 7: Set notebook state (update the state)
    new_state = AgenticNotebookState(
        http_template=HttpTemplate(
            endpoint_name="test_endpoint",
            endpoint_url="https://api.example.com/chat",
            headers=[
                HttpHeader(name="Content-Type", value="application/json"),
            ],
            request_body={
                "message": "{{user_message}}",
            },
        ),
        template_variable_mapping=[
            TemplateVariableMapping(
                variable_name="user_message",
                source=DatasetColumnVariableSource(
                    type="dataset_column",
                    dataset_column=DatasetColumnSource(name="user_message"),
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
            AgenticEvalRef(
                name=eval_name,
                version=1,
                transform_id=transform_id,
                variable_mapping=[
                    AgenticEvalVariableMapping(
                        variable_name="agent_response",
                        source=AgenticExperimentOutputVariableSource(
                            type="experiment_output",
                            experiment_output=TransformVariableExperimentOutputSource(
                                transform_variable_name="final_response",
                            ),
                        ),
                    ),
                ],
            ),
        ],
    )

    new_state_request = SetAgenticNotebookStateRequest(state=new_state)

    status_code, updated_notebook = client.set_agentic_notebook_state(
        notebook_id=notebook_id,
        state_request=new_state_request.model_dump(mode="json"),
    )
    assert status_code == 200, f"Failed to set notebook state: {updated_notebook}"
    # Verify state was updated
    assert updated_notebook["state"]["http_template"] is not None
    assert len(updated_notebook["state"]["template_variable_mapping"]) == 1
    # Verify dataset_row_filter was removed
    assert updated_notebook["state"].get("dataset_row_filter") is None

    # Test 8: Create an experiment from the notebook state
    # Mock HTTP request responses and create traces so the executor can complete
    def mock_post_response(*args, **kwargs):
        """Mock HTTP POST response from agent endpoint."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.ok = True
        mock_response.json.return_value = {
            "answer": "Machine learning is a subset of artificial intelligence.",
            "sources": ["source1", "source2"],
        }
        mock_response.text = '{"answer": "Machine learning is a subset of artificial intelligence.", "sources": ["source1", "source2"]}'
        mock_response.reason = "OK"
        return mock_response

    def mock_post_with_trace_creation(*args, **kwargs):
        """Mock HTTP POST response and create trace with session_id."""
        # Extract session_id from body (preferred) or headers
        body = kwargs.get("json", {})
        headers = kwargs.get("headers", {})
        session_id = (
            body.get("session_id")
            or headers.get("X-Session-Id")
            or headers.get("x-session-id")
        )

        if session_id:
            # Create trace with this session_id so the executor can find it
            # The executor should set session_id with AGENT_EXPERIMENT_SESSION_PREFIX
            # which will cause continuous evals to skip processing these traces
            create_mock_trace_with_session_id(
                client,
                task_id,
                session_id,
            )

        # Return the mocked response
        return mock_post_response(*args, **kwargs)

    # Configure the mock to return our response function with trace creation
    mock_requests_post.side_effect = mock_post_with_trace_creation
    # Ensure return_value is not set (side_effect takes precedence)
    mock_requests_post.return_value = None
    mock_supports_response_schema.return_value = True

    mock_response = MagicMock(spec=ModelResponse)
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": '{"reason": "The agent response is highly relevant and accurate.", "score": 1}',
    }
    mock_completion.return_value = mock_response
    mock_completion_cost.return_value = 0.002345

    # Mock loggers
    mock_agentic_logger.info = MagicMock()
    mock_agentic_logger.error = MagicMock()
    mock_agentic_logger.warning = MagicMock()
    mock_experiment_logger.info = MagicMock()
    mock_experiment_logger.error = MagicMock()
    mock_experiment_logger.warning = MagicMock()

    # Create experiment using the notebook state
    experiment_name = f"test_experiment_from_notebook_{random.random()}"
    experiment_request = CreateAgenticExperimentRequest(
        name=experiment_name,
        description="Experiment created from notebook",
        dataset_ref=DatasetRefInput(
            id=dataset_id,
            version=dataset_version_number,
        ),
        http_template=HttpTemplate(
            endpoint_name="test_endpoint",
            endpoint_url="https://api.example.com/chat",
            headers=[
                HttpHeader(name="Content-Type", value="application/json"),
            ],
            request_body={
                "message": "{{user_message}}",
            },
        ),
        template_variable_mapping=[
            TemplateVariableMapping(
                variable_name="user_message",
                source=DatasetColumnVariableSource(
                    type="dataset_column",
                    dataset_column=DatasetColumnSource(name="user_message"),
                ),
            ),
        ],
        eval_list=[
            AgenticEvalRef(
                name=eval_name,
                version=1,
                transform_id=transform_id,
                variable_mapping=[
                    AgenticEvalVariableMapping(
                        variable_name="agent_response",
                        source=AgenticExperimentOutputVariableSource(
                            type="experiment_output",
                            experiment_output=TransformVariableExperimentOutputSource(
                                transform_variable_name="final_response",
                            ),
                        ),
                    ),
                ],
            ),
        ],
    )

    status_code, experiment_summary = client.create_agentic_experiment(
        task_id=task_id,
        experiment_request=experiment_request.model_dump(mode="json"),
    )
    assert status_code == 200, f"Failed to create experiment: {experiment_summary}"
    experiment_id = experiment_summary["id"]

    # Attach notebook to the experiment
    status_code, attached_experiment = client.attach_notebook_to_agentic_experiment(
        experiment_id=experiment_id,
        notebook_id=notebook_id,
    )
    assert status_code == 200, f"Failed to attach notebook: {attached_experiment}"

    # Verify notebook_id is set by fetching experiment detail
    status_code, experiment_detail = client.get_agentic_experiment(experiment_id)
    assert status_code == 200, f"Failed to get experiment: {experiment_detail}"
    assert experiment_detail.get("notebook_id") == notebook_id

    # Wait for experiment to complete before proceeding to avoid interfering with other tests
    # This ensures all traces are processed and the experiment is in a final state
    wait_for_experiment_completion(client, experiment_id, allow_failure=True)

    # Test 9: Get notebook history (should include the experiment we just created)
    status_code, history_data = client.get_agentic_notebook_history(
        notebook_id=notebook_id,
        page=0,
        page_size=10,
    )
    assert status_code == 200, f"Failed to get notebook history: {history_data}"

    history = AgenticExperimentListResponse.model_validate(history_data)
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
    status_code, notebook_detail = client.get_agentic_notebook(notebook_id)
    assert status_code == 200, f"Failed to get notebook: {notebook_detail}"

    notebook = AgenticNotebookDetail.model_validate(notebook_detail)
    assert len(notebook.experiments) >= 1
    assert notebook.experiments[0].id == experiment_id

    # Test 11: Verify notebook summary shows run count
    status_code, notebooks_list_data = client.list_agentic_notebooks(
        task_id=task_id,
        page=0,
        page_size=10,
    )
    assert status_code == 200, f"Failed to list notebooks: {notebooks_list_data}"

    notebooks_list = AgenticNotebookListResponse.model_validate(notebooks_list_data)
    our_notebook = None
    for nb in notebooks_list.data:
        if nb.id == notebook_id:
            our_notebook = nb
            break

    assert our_notebook is not None
    assert our_notebook.run_count >= 1
    assert our_notebook.latest_run_id == experiment_id
    assert our_notebook.latest_run_status is not None

    # Cleanup: Delete experiment, notebook, dataset, transform, LLM eval, and task
    status_code = client.delete_agentic_experiment(experiment_id)
    assert status_code == 204, f"Failed to delete experiment: {status_code}"

    status_code = client.delete_agentic_notebook(notebook_id)
    assert status_code == 204, f"Failed to delete notebook: {status_code}"

    # Validate that deleted notebook cannot be fetched
    status_code, _ = client.get_agentic_notebook(notebook_id)
    assert (
        status_code == 404
    ), f"Expected 404 after deleting notebook, got {status_code}"

    status_code, _ = client.delete_llm_eval(task_id=task_id, llm_eval_name=eval_name)
    assert status_code in [200, 204], f"Failed to delete LLM eval: {status_code}"

    status_code, _ = client.delete_transform(transform_id)
    assert status_code == 204, f"Failed to delete transform: {status_code}"

    status_code = client.delete_dataset(dataset_id)
    assert status_code == 204, f"Failed to delete dataset: {status_code}"

    status_code = client.delete_task(task_id)
    assert status_code == 204, f"Failed to delete task: {status_code}"


@pytest.mark.unit_tests
def test_agentic_notebook_validation_errors(
    client: GenaiEngineTestClientBase,
):
    """
    Test that creating an agentic notebook with invalid resource references returns 400 errors.
    """
    # Setup: Create task
    task_name = f"agentic_notebook_validation_task_{random.random()}"
    status_code, task = client.create_task(task_name, is_agentic=True)
    assert status_code == 200, f"Failed to create task: {task}"
    task_id = task.id

    # Test 1: Create notebook with non-existent dataset
    notebook_state = AgenticNotebookState(
        dataset_ref=DatasetRefInput(
            id=uuid4(),  # Non-existent dataset ID
            version=1,
        ),
    )
    notebook_request = CreateAgenticNotebookRequest(
        name="test_invalid_dataset",
        state=notebook_state,
    )
    status_code, response = client.create_agentic_notebook(
        task_id=task_id,
        notebook_request=notebook_request.model_dump(mode="json"),
    )
    assert (
        status_code == 400
    ), f"Expected 400 for non-existent dataset, got {status_code}"
    assert response is not None, "Expected error response body"
    assert "not found" in response.get("detail", "").lower()

    # Test 2: Create notebook with non-existent transform
    # First create a valid dataset
    dataset_name = f"agentic_notebook_validation_dataset_{random.random()}"
    status_code, dataset = client.create_dataset(
        name=dataset_name,
        task_id=task_id,
        description="Test dataset for validation",
    )
    assert status_code == 200, f"Failed to create dataset: {dataset}"
    dataset_id = dataset.id

    status_code, dataset_version = client.create_dataset_version(
        dataset_id=dataset_id,
        rows_to_add=[],
    )
    assert status_code == 200, f"Failed to create dataset version: {dataset_version}"
    dataset_version_number = dataset_version.version_number

    # Create LLM eval
    eval_name = "test_agentic_eval_validation"
    eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Test eval",
    }

    response = client.base_client.post(
        f"/api/v1/tasks/{task_id}/llm_evals/{eval_name}",
        json=eval_data,
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 200, f"Failed to create LLM eval: {response.text}"

    notebook_state = AgenticNotebookState(
        dataset_ref=DatasetRefInput(
            id=dataset_id,
            version=dataset_version_number,
        ),
        eval_list=[
            AgenticEvalRef(
                name=eval_name,
                version=1,
                transform_id=uuid4(),  # Non-existent transform ID
                variable_mapping=[],
            ),
        ],
    )
    notebook_request = CreateAgenticNotebookRequest(
        name="test_invalid_transform",
        state=notebook_state,
    )
    status_code, response = client.create_agentic_notebook(
        task_id=task_id,
        notebook_request=notebook_request.model_dump(mode="json"),
    )
    assert (
        status_code == 400
    ), f"Expected 400 for non-existent transform, got {status_code}"
    assert response is not None, "Expected error response body"
    assert "not found" in response.get("detail", "").lower()

    # Test 3: Create notebook with non-existent eval
    notebook_state = AgenticNotebookState(
        dataset_ref=DatasetRefInput(
            id=dataset_id,
            version=dataset_version_number,
        ),
        eval_list=[
            AgenticEvalRef(
                name="non_existent_eval",
                version=1,
                transform_id=uuid4(),
                variable_mapping=[],
            ),
        ],
    )
    notebook_request = CreateAgenticNotebookRequest(
        name="test_invalid_eval",
        state=notebook_state,
    )
    status_code, response = client.create_agentic_notebook(
        task_id=task_id,
        notebook_request=notebook_request.model_dump(mode="json"),
    )
    assert status_code == 400, f"Expected 400 for non-existent eval, got {status_code}"
    assert response is not None, "Expected error response body"
    assert "not found" in response.get("detail", "").lower()

    # Test 4: Create notebook with request-time parameter (should return 400)
    notebook_state = AgenticNotebookState(
        dataset_ref=DatasetRefInput(
            id=dataset_id,
            version=dataset_version_number,
        ),
        template_variable_mapping=[
            TemplateVariableMapping(
                variable_name="api_key",
                source=RequestTimeParameterSource(
                    type="request_time_parameter",
                ),
            ),
        ],
    )
    notebook_request = CreateAgenticNotebookRequest(
        name="test_request_time_parameter",
        state=notebook_state,
    )
    status_code, response = client.create_agentic_notebook(
        task_id=task_id,
        notebook_request=notebook_request.model_dump(mode="json"),
    )
    assert (
        status_code == 400
    ), f"Expected 400 for request-time parameter, got {status_code}"
    assert response is not None, "Expected error response body"
    assert "request-time parameter" in response.get("detail", "").lower()
    assert "cannot be stored" in response.get("detail", "").lower()

    # Test 5: Set notebook state with request-time parameter (should return 400)
    # First create a valid notebook
    notebook_request = CreateAgenticNotebookRequest(
        name="test_no_state",
        description="Notebook without initial state",
    )
    status_code, notebook_detail = client.create_agentic_notebook(
        task_id=task_id,
        notebook_request=notebook_request.model_dump(mode="json"),
    )
    assert (
        status_code == 201
    ), f"Expected 201 for notebook without state, got {status_code}"
    notebook_id = notebook_detail["id"]

    # Try to set state with request-time parameter
    invalid_state = AgenticNotebookState(
        dataset_ref=DatasetRefInput(
            id=dataset_id,
            version=dataset_version_number,
        ),
        template_variable_mapping=[
            TemplateVariableMapping(
                variable_name="api_key",
                source=RequestTimeParameterSource(
                    type="request_time_parameter",
                ),
            ),
        ],
    )
    invalid_state_request = SetAgenticNotebookStateRequest(state=invalid_state)

    status_code, response = client.set_agentic_notebook_state(
        notebook_id=notebook_id,
        state_request=invalid_state_request.model_dump(mode="json"),
    )
    assert (
        status_code == 400
    ), f"Expected 400 for request-time parameter in set state, got {status_code}"
    assert response is not None, "Expected error response body"
    assert "request-time parameter" in response.get("detail", "").lower()
    assert "cannot be stored" in response.get("detail", "").lower()

    # Test 6: Create notebook with no state (should succeed)
    notebook_request = CreateAgenticNotebookRequest(
        name="test_no_state_valid",
        description="Notebook without initial state",
    )
    status_code, notebook_detail = client.create_agentic_notebook(
        task_id=task_id,
        notebook_request=notebook_request.model_dump(mode="json"),
    )
    assert (
        status_code == 201
    ), f"Expected 201 for notebook without state, got {status_code}"
    notebook_id_2 = notebook_detail["id"]

    # Cleanup
    status_code = client.delete_agentic_notebook(notebook_id)
    assert status_code == 204, f"Failed to delete notebook: {status_code}"

    status_code = client.delete_agentic_notebook(notebook_id_2)
    assert status_code == 204, f"Failed to delete notebook: {status_code}"

    status_code, _ = client.delete_llm_eval(task_id=task_id, llm_eval_name=eval_name)
    assert status_code in [200, 204], f"Failed to delete LLM eval: {status_code}"

    status_code = client.delete_dataset(dataset_id)
    assert status_code == 204, f"Failed to delete dataset: {status_code}"

    status_code = client.delete_task(task_id)
    assert status_code == 204, f"Failed to delete task: {status_code}"
