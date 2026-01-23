"""
Unit tests for agentic experiment routes.

This module tests the agentic experiment API endpoints:
- Creating and running an agentic experiment
- Getting agentic experiment details
- Getting experiment test cases
- Listing agentic experiments
- Deleting agentic experiments

All tests mock external dependencies (HTTP requests, traces, transforms, and LLM eval responses)
and clean up test state after execution.
"""

import json
import random
import time
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from arthur_common.models.task_eval_schemas import (
    TraceTransformDefinition,
    TraceTransformVariableDefinition,
)
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
    AgenticTestCase,
    AgenticTestCaseListResponse,
    CreateAgenticExperimentRequest,
    GeneratedVariableSource,
    HttpHeader,
    HttpTemplate,
    RequestTimeParameter,
    RequestTimeParameterSource,
    TemplateVariableMapping,
    TransformVariableExperimentOutputSource,
)
from schemas.base_experiment_schemas import (
    DatasetColumnSource,
    DatasetColumnVariableSource,
    DatasetRefInput,
    ExperimentStatus,
    TestCaseStatus,
)
from schemas.common_schemas import (
    NewDatasetVersionRowColumnItemRequest,
    NewDatasetVersionRowRequest,
)
from schemas.request_schemas import (
    NewTraceTransformRequest,
)
from services.agentic_experiment_executor import AgenticExperimentExecutor
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
@patch("services.experiment_executor.BaseExperimentExecutor.execute_experiment_async")
@patch("services.experiment_executor.db_session_context")
@patch("repositories.llm_evals_repository.supports_response_schema")
@patch("services.agentic_experiment_executor.requests.post")
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
@patch("services.agentic_experiment_executor.logger")
@patch("services.experiment_executor.logger")
def test_agentic_experiment_routes_happy_path(
    mock_experiment_logger,
    mock_agentic_logger,
    mock_completion,
    mock_completion_cost,
    mock_requests_post,
    mock_supports_response_schema,
    mock_db_session_context,
    mock_execute_async,
    client: GenaiEngineTestClientBase,
):
    """
    Test the complete agentic experiment workflow:
    1. Create an agentic experiment (happy path)
    2. Get agentic experiment details (polling until completion)
    3. Get experiment test cases
    4. List agentic experiments
    5. Delete agentic experiment

    This test mocks:
    - HTTP requests to agent endpoints (using mock_requests_post)
    - Trace creation (using create_mock_trace_with_session_id)
    - Transform execution (mocked via execute_transform)
    - LLM eval responses (using mock_completion and mock_completion_cost)
    - Database session context for background threads (using override_get_db_session)

    The request includes:
    - A request-time parameter variable (API key)
    - A UUID generator variable
    - A standard dataset column variable

    All response fields are validated to ensure they're set as expected.
    Request-time parameter mappings (structure) are persisted, but their values are not.
    Request-time parameter values are validated to never be persisted or returned.
    """

    # Mock db_session_context for background thread execution to use test database
    setup_db_session_context_mock(mock_db_session_context)

    def sync_execute(experiment_id, request_time_parameters=None):
        executor = AgenticExperimentExecutor()
        return executor._execute_experiment(experiment_id, request_time_parameters)

    mock_execute_async.side_effect = sync_execute

    # Setup: Create task
    task_name = f"agentic_experiment_task_{random.random()}"
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
    dataset_name = f"agentic_test_dataset_{random.random()}"
    status_code, dataset = client.create_dataset(
        name=dataset_name,
        task_id=task_id,
        description="Test dataset for agentic experiments",
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
    # The transform will extract from the trace span we create
    transform_name = f"test_transform_{random.random()}"
    transform_request = NewTraceTransformRequest(
        name=transform_name,
        description="Test transform for agentic experiments",
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

    # Mock HTTP request responses - set up before experiment creation
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

    # Configure the mock to return our response function
    mock_requests_post.side_effect = mock_post_response

    # Mock supports_response_schema to return True (required by run_llm_eval)
    mock_supports_response_schema.return_value = True

    # Mock LLM eval responses
    # ReasonedScore expects score to be an integer (0 or 1), not a float
    # The mock must be set up before the experiment is created so it's available in the background thread
    mock_response = MagicMock(spec=ModelResponse)
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": '{"reason": "The agent response is highly relevant and accurate.", "score": 1}',
    }
    # Ensure the mock is properly configured to return the response
    mock_completion.return_value = mock_response
    mock_completion_cost.return_value = 0.002345

    # Also ensure the mock doesn't raise exceptions
    mock_completion.side_effect = None

    # Mock loggers to prevent I/O errors on closed file handles in background threads
    # These loggers are used in background threads and may try to write after test cleanup
    mock_agentic_logger.info = MagicMock()
    mock_agentic_logger.error = MagicMock()
    mock_agentic_logger.warning = MagicMock()
    mock_experiment_logger.info = MagicMock()
    mock_experiment_logger.error = MagicMock()
    mock_experiment_logger.warning = MagicMock()

    # Track session IDs for trace creation
    created_session_ids = []
    # Track actual requests made to agent endpoint to validate request-time parameters are included
    actual_agent_requests = []

    def mock_post_with_trace_creation(*args, **kwargs):
        """Mock HTTP POST response and create trace with session_id."""
        # Extract session_id from headers (always sent in headers, not body)
        headers = kwargs.get("headers", {})
        session_id = headers.get("X-Session-Id") or headers.get("x-session-id")

        # Capture the actual request to validate request-time parameters are included
        # requests.post(url, headers=..., data=...) - first arg is URL
        request_url = args[0] if args else kwargs.get("url", "")
        body_data = kwargs.get("data", "")

        # Parse body for logging if it's JSON
        body_dict = {}
        try:
            if body_data:
                body_dict = (
                    json.loads(body_data) if isinstance(body_data, str) else body_data
                )
        except (json.JSONDecodeError, ValueError, TypeError):
            body_dict = {"raw": str(body_data)}

        actual_agent_requests.append(
            {
                "url": request_url,
                "headers": dict(headers) if headers else {},
                "body": (
                    body_dict
                    if isinstance(body_dict, dict)
                    else {"raw": str(body_data)}
                ),
            },
        )

        if not session_id:
            session_id = body_dict.get("thread_id")

        if session_id:
            created_session_ids.append(session_id)
            # Create trace with this session_id
            create_mock_trace_with_session_id(
                client,
                task_id,
                session_id,
            )

        # Return the mocked response
        return mock_post_response(*args, **kwargs)

    # Set the side_effect after defining the function
    mock_requests_post.side_effect = mock_post_with_trace_creation
    # Ensure return_value is not set (side_effect takes precedence)
    mock_requests_post.return_value = None

    # Test 1: Create agentic experiment with dataset row filter
    # Filter to only include rows where user_message contains "machine learning"
    # This should result in only 1 test case instead of 2
    experiment_name = f"test_agentic_experiment_{random.random()}"

    # Request-time parameter value (the value should never be persisted, but the mapping structure is)
    request_time_api_key = "secret-api-key-12345"

    experiment_request = CreateAgenticExperimentRequest(
        name=experiment_name,
        description="Test agentic experiment",
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
        http_template=HttpTemplate(
            endpoint_name="chat_endpoint",
            endpoint_url="https://example.com/api/chat",
            headers=[
                HttpHeader(
                    name="Authorization",
                    value="Bearer {{api_key}}",
                ),
                HttpHeader(
                    name="X-Request-ID",
                    value="{{request_id}}",
                ),
                HttpHeader(
                    name="X-Session-Id",
                    value="{{session_id}}",
                ),
            ],
            request_body='{"message": "{{user_message}}"}',
        ),
        template_variable_mapping=[
            TemplateVariableMapping(
                variable_name="api_key",
                source=RequestTimeParameterSource(
                    type="request_time_parameter",
                ),
            ),
            TemplateVariableMapping(
                variable_name="request_id",
                source=GeneratedVariableSource(
                    type="generated",
                    generator_type="uuid",
                ),
            ),
            TemplateVariableMapping(
                variable_name="session_id",
                source=GeneratedVariableSource(
                    type="generated",
                    generator_type="session_id",
                ),
            ),
            TemplateVariableMapping(
                variable_name="user_message",
                source=DatasetColumnVariableSource(
                    type="dataset_column",
                    dataset_column=DatasetColumnSource(
                        name="user_message",
                    ),
                ),
            ),
        ],
        request_time_parameters=[
            RequestTimeParameter(
                name="api_key",
                value=request_time_api_key,
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
                                type="transform_variable",
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
    assert (
        status_code == 200
    ), f"Failed to create agentic experiment: {experiment_summary}"
    experiment_id = experiment_summary["id"]

    # Validate experiment summary response fields
    assert experiment_summary["name"] == experiment_name
    assert experiment_summary["description"] == "Test agentic experiment"
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

    # Validate HTTP template structure
    # Validate HTTP template structure
    assert "http_template" in experiment_summary
    assert experiment_summary["http_template"]["endpoint_name"] == "chat_endpoint"
    assert (
        experiment_summary["http_template"]["endpoint_url"]
        == "https://example.com/api/chat"
    )
    assert len(experiment_summary["http_template"]["headers"]) == 3
    assert experiment_summary["http_template"]["headers"][0]["name"] == "Authorization"
    assert (
        experiment_summary["http_template"]["headers"][0]["value"]
        == "Bearer {{api_key}}"
    )
    assert experiment_summary["http_template"]["headers"][1]["name"] == "X-Request-ID"
    assert (
        experiment_summary["http_template"]["headers"][1]["value"] == "{{request_id}}"
    )
    assert (
        experiment_summary["http_template"]["request_body"]
        == '{"message": "{{user_message}}"}'
    )

    # Validate that request_time_parameters are NOT in the response
    assert "request_time_parameters" not in experiment_summary

    # Note: template_variable_mapping is NOT included in AgenticExperimentSummary
    # It's only available in AgenticExperimentDetail, which we'll validate below

    # Test 2: Get agentic experiment details (polling until completion)
    experiment_detail = wait_for_experiment_completion(client, experiment_id)

    # Validate experiment detail response fields
    assert experiment_detail.id == experiment_id
    assert experiment_detail.name == experiment_name
    assert experiment_detail.description == "Test agentic experiment"
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

    # Validate HTTP template with all expected values
    assert experiment_detail.http_template is not None
    assert experiment_detail.http_template.endpoint_name == "chat_endpoint"
    assert (
        experiment_detail.http_template.endpoint_url == "https://example.com/api/chat"
    )
    assert len(experiment_detail.http_template.headers) == 3
    assert experiment_detail.http_template.headers[0].name == "Authorization"
    assert experiment_detail.http_template.headers[0].value == "Bearer {{api_key}}"
    assert experiment_detail.http_template.headers[1].name == "X-Request-ID"
    assert experiment_detail.http_template.headers[1].value == "{{request_id}}"
    assert (
        experiment_detail.http_template.request_body
        == '{"message": "{{user_message}}"}'
    )

    # Validate template_variable_mapping - should include request-time parameter mappings
    # (the mapping structure is persisted, but not the values)
    assert experiment_detail.template_variable_mapping is not None
    assert (
        len(experiment_detail.template_variable_mapping) == 4
    )  # UUID generator, dataset column, and request-time parameter
    mapping_variable_names = [
        m.variable_name for m in experiment_detail.template_variable_mapping
    ]
    assert "request_id" in mapping_variable_names  # UUID generator
    assert "user_message" in mapping_variable_names  # Dataset column
    assert (
        "api_key" in mapping_variable_names
    )  # Request-time parameter mapping should be included

    # Verify the request-time parameter mapping structure
    api_key_mapping = None
    for mapping in experiment_detail.template_variable_mapping:
        if mapping.variable_name == "api_key":
            api_key_mapping = mapping
            break
    assert api_key_mapping is not None, "Request-time parameter mapping not found"
    assert api_key_mapping.source.type == "request_time_parameter"

    # Verify all mapping types are present
    mapping_types = {m.source.type for m in experiment_detail.template_variable_mapping}
    assert "generated" in mapping_types
    assert "dataset_column" in mapping_types
    assert "request_time_parameter" in mapping_types

    # Validate that request_time_parameters are NOT in the detail response
    # (they should not be stored or returned)
    assert not hasattr(
        experiment_detail,
        "request_time_parameters",
    ), "request_time_parameters should not be in AgenticExperimentDetail"

    # Validate summary results with expected values
    assert experiment_detail.summary_results is not None
    assert len(experiment_detail.summary_results.eval_summaries) == 1
    eval_summary = experiment_detail.summary_results.eval_summaries[0]
    assert eval_summary.eval_name == eval_name
    assert eval_summary.eval_version == "1"
    assert eval_summary.transform_id == transform_id
    assert eval_summary.eval_results is not None
    assert len(eval_summary.eval_results) == 1
    eval_result = eval_summary.eval_results[0]
    assert eval_result.eval_name == eval_name
    assert eval_result.eval_version == "1"
    # With dataset_row_filter, only 1 row should match
    assert eval_result.total_count == 1
    assert eval_result.pass_count == 1  # All should pass with our mock

    # Test 3: List agentic experiments for the task
    status_code, experiments_list_data = client.list_agentic_experiments(
        task_id=task_id,
        page=0,
        page_size=10,
    )
    assert (
        status_code == 200
    ), f"Failed to list agentic experiments: {experiments_list_data}"

    experiments_list = AgenticExperimentListResponse.model_validate(
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
    assert our_experiment.description == "Test agentic experiment"
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
    # Validate HTTP template structure
    assert our_experiment.http_template is not None
    assert our_experiment.http_template.endpoint_name == "chat_endpoint"
    assert our_experiment.http_template.endpoint_url == "https://example.com/api/chat"
    assert len(our_experiment.http_template.headers) == 3

    # Validate that request_time_parameters are NOT in the list response
    assert not hasattr(
        our_experiment,
        "request_time_parameters",
    ), "request_time_parameters should not be in AgenticExperimentSummary"

    # Test 4: Get experiment test cases
    status_code, test_cases_data = client.get_agentic_experiment_test_cases(
        experiment_id=experiment_id,
        page=0,
        page_size=10,
    )
    assert status_code == 200, f"Failed to get test cases: {test_cases_data}"

    test_cases_response = AgenticTestCaseListResponse.model_validate(test_cases_data)

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
    assert isinstance(test_case, AgenticTestCase)
    assert test_case.status == TestCaseStatus.COMPLETED
    # Validate dataset_row_id is a valid UUID string
    assert test_case.dataset_row_id is not None
    assert isinstance(test_case.dataset_row_id, str)
    assert len(test_case.dataset_row_id) > 0
    assert test_case.agentic_result is not None

    # Validate template_input_variables - should NOT include request-time parameters
    # Generated variables (like UUID) are added during execution and should be present after execution
    assert test_case.template_input_variables is not None
    variable_names = [var.variable_name for var in test_case.template_input_variables]

    # Request-time parameters should NEVER be in template_input_variables
    assert (
        "api_key" not in variable_names
    ), "Request-time parameter 'api_key' found in template_input_variables"

    # Dataset column should always be present
    assert (
        "user_message" in variable_names
    ), "Dataset column 'user_message' not found in template_input_variables"

    # Generated variables are added during execution and should be present after successful execution
    assert "request_id" in variable_names, (
        "Generated variable 'request_id' not found in template_input_variables after execution. "
        f"Found variables: {variable_names}"
    )

    # Should have exactly 3 variables: dataset column, generated UUID, and session_id
    assert len(test_case.template_input_variables) == 3, (
        f"Expected 3 variables (dataset column, generated UUID, and session_id), "
        f"but found {len(test_case.template_input_variables)}: {variable_names}"
    )

    # Validate the actual variable values
    user_message_var = None
    request_id_var = None
    for var in test_case.template_input_variables:
        if var.variable_name == "user_message":
            user_message_var = var
        elif var.variable_name == "request_id":
            request_id_var = var

    # Validate user_message variable
    assert user_message_var is not None, "user_message variable not found"
    assert user_message_var.value == "What is machine learning?"

    # Validate request_id variable (generated during execution)
    assert request_id_var is not None, "request_id variable not found"
    # Should be a valid UUID string
    assert isinstance(request_id_var.value, str)
    assert len(request_id_var.value) > 0
    # Verify it's a valid UUID format (contains hyphens and is 36 chars)
    assert (
        len(request_id_var.value) == 36
    ), f"Expected UUID format, got: {request_id_var.value}"
    assert request_id_var.value.count("-") == 4

    # Validate that the test case corresponds to the filtered row
    # The user_message text should match the filtered row's user_message
    assert test_case.agentic_result is not None
    # Validate request URL, headers, and body have expected structure
    assert test_case.agentic_result.request_url is not None
    assert isinstance(test_case.agentic_result.request_url, str)
    assert test_case.agentic_result.request_url == "https://example.com/api/chat"
    assert test_case.agentic_result.request_headers is not None
    assert isinstance(test_case.agentic_result.request_headers, dict)
    assert "Authorization" in test_case.agentic_result.request_headers
    assert "X-Request-ID" in test_case.agentic_result.request_headers
    # Validate Authorization header value (should not contain the actual API key)
    auth_header = test_case.agentic_result.request_headers["Authorization"]
    assert isinstance(auth_header, str)
    assert request_time_api_key not in auth_header
    # Validate X-Request-ID header value (should be a UUID string)
    request_id_header = test_case.agentic_result.request_headers["X-Request-ID"]
    assert isinstance(request_id_header, str)
    assert len(request_id_header) > 0
    assert test_case.agentic_result.request_body is not None
    assert isinstance(test_case.agentic_result.request_body, str)
    assert len(test_case.agentic_result.request_body) > 0
    # Parse the body as JSON to validate structure
    body_dict = json.loads(test_case.agentic_result.request_body)
    assert "message" in body_dict
    assert body_dict["message"] == "What is machine learning?"
    # Validate session_id is in the request headers (added by executor)
    assert "X-Session-Id" in test_case.agentic_result.request_headers
    assert isinstance(test_case.agentic_result.request_headers["X-Session-Id"], str)
    assert len(test_case.agentic_result.request_headers["X-Session-Id"]) > 0

    # Validate that request headers and body do NOT contain the request-time parameter value
    # (they should contain the placeholder or be rendered without the sensitive value)
    headers_str = str(test_case.agentic_result.request_headers)
    body_str = test_case.agentic_result.request_body  # Already a string
    assert (
        request_time_api_key not in headers_str
    ), "Request-time parameter value found in request_headers"
    assert (
        request_time_api_key not in body_str
    ), "Request-time parameter value found in request_body"

    # Validate that the ACTUAL HTTP request to the agent endpoint DOES include the request-time parameter
    # This is critical: request-time parameter VALUES should be included in the actual request,
    # even though the values are not stored in the DB or returned in API responses
    # (the mapping structure IS stored, but not the sensitive values)
    assert (
        len(actual_agent_requests) > 0
    ), "No actual HTTP requests were made to the agent endpoint"
    actual_request = actual_agent_requests[0]  # Get the first request
    assert (
        "Authorization" in actual_request["headers"]
    ), "Authorization header missing from actual request"
    actual_auth_header = actual_request["headers"]["Authorization"]
    assert isinstance(
        actual_auth_header,
        str,
    ), "Authorization header should be a string"
    # The actual request should contain the real API key value
    expected_auth_value = f"Bearer {request_time_api_key}"
    assert (
        actual_auth_header == expected_auth_value
    ), f"Actual request Authorization header should contain the API key. Expected '{expected_auth_value}', got '{actual_auth_header}'"

    # Validate agentic result output with expected values
    assert test_case.agentic_result.output is not None
    assert test_case.agentic_result.output.response_body is not None
    assert isinstance(test_case.agentic_result.output.response_body, dict)
    assert "answer" in test_case.agentic_result.output.response_body
    assert (
        test_case.agentic_result.output.response_body["answer"]
        == "Machine learning is a subset of artificial intelligence."
    )
    assert test_case.agentic_result.output.status_code == 200
    assert test_case.agentic_result.output.trace_id is not None
    assert isinstance(test_case.agentic_result.output.trace_id, str)
    assert len(test_case.agentic_result.output.trace_id) > 0

    # Validate eval executions
    # Note: eval results are stored separately, check that they exist
    # The actual eval results would be in the summary_results

    # Test 5: Create an experiment that will fail and verify it gets marked as failed
    # Reuse existing setup (task, dataset, transform, LLM eval)
    # Make the HTTP request fail by having the mock raise an exception
    failed_experiment_name = f"test_agentic_experiment_failed_{random.random()}"
    failed_experiment_request = CreateAgenticExperimentRequest(
        name=failed_experiment_name,
        description="Test agentic experiment that will fail",
        dataset_ref=DatasetRefInput(
            id=dataset_id,
            version=dataset_version_number,
        ),
        # No filter - use all rows
        dataset_row_filter=None,
        http_template=HttpTemplate(
            endpoint_name="chat_endpoint",
            endpoint_url="https://example.com/api/chat",
            headers=[
                HttpHeader(
                    name="Authorization",
                    value="Bearer {{api_key}}",
                ),
                HttpHeader(
                    name="X-Request-ID",
                    value="{{request_id}}",
                ),
            ],
            request_body='{"message": "{{user_message}}", "thread_id": "{{thread_id}}"}',
        ),
        template_variable_mapping=[
            TemplateVariableMapping(
                variable_name="api_key",
                source=RequestTimeParameterSource(
                    type="request_time_parameter",
                ),
            ),
            TemplateVariableMapping(
                variable_name="request_id",
                source=GeneratedVariableSource(
                    type="generated",
                    generator_type="uuid",
                ),
            ),
            TemplateVariableMapping(
                variable_name="user_message",
                source=DatasetColumnVariableSource(
                    type="dataset_column",
                    dataset_column=DatasetColumnSource(
                        name="user_message",
                    ),
                ),
            ),
            TemplateVariableMapping(
                variable_name="thread_id",
                source=GeneratedVariableSource(
                    type="generated",
                    generator_type="session_id",
                ),
            ),
        ],
        request_time_parameters=[
            RequestTimeParameter(
                name="api_key",
                value=request_time_api_key,
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
                                type="transform_variable",
                                transform_variable_name="final_response",
                            ),
                        ),
                    ),
                ],
            ),
        ],
    )

    # Mock HTTP request to fail by raising an exception
    def mock_post_failure(*args, **kwargs):
        """Mock HTTP POST that raises an exception."""
        raise Exception("HTTP request failed for testing")

    mock_requests_post.side_effect = mock_post_failure

    status_code, failed_experiment_summary = client.create_agentic_experiment(
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

    # Cleanup: Delete experiments, dataset, transform, LLM eval, and task
    status_code = client.delete_agentic_experiment(experiment_id)
    assert status_code == 204, f"Failed to delete agentic experiment: {status_code}"

    # Validate that deleted experiment cannot be fetched
    status_code, _ = client.get_agentic_experiment(experiment_id)
    assert (
        status_code == 404
    ), f"Expected 404 after deleting experiment, got {status_code}"

    # Validate that test cases for deleted experiment cannot be fetched
    status_code, _ = client.get_agentic_experiment_test_cases(experiment_id)
    assert (
        status_code == 404
    ), f"Expected 404 when fetching test cases for deleted experiment, got {status_code}"

    status_code = client.delete_agentic_experiment(failed_experiment_id)
    assert (
        status_code == 204
    ), f"Failed to delete failed agentic experiment: {status_code}"

    status_code, _ = client.delete_llm_eval(task_id=task_id, llm_eval_name=eval_name)
    assert status_code in [200, 204], f"Failed to delete LLM eval: {status_code}"

    # Delete transform
    status_code, _ = client.delete_transform(transform_id=str(transform_id))
    assert status_code in [200, 204], f"Failed to delete transform: {status_code}"

    status_code = client.delete_dataset(dataset_id)
    assert status_code == 204, f"Failed to delete dataset: {status_code}"

    status_code = client.delete_task(task_id)
    assert status_code == 204, f"Failed to delete task: {status_code}"


@pytest.mark.unit_tests
@patch("services.experiment_executor.BaseExperimentExecutor.execute_experiment_async")
@patch("services.experiment_executor.db_session_context")
@patch("repositories.llm_evals_repository.supports_response_schema")
@patch("services.agentic_experiment_executor.requests.post")
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
@patch("services.agentic_experiment_executor.logger")
@patch("services.experiment_executor.logger")
def test_agentic_experiment_session_id_generator(
    mock_experiment_logger,
    mock_agentic_logger,
    mock_completion,
    mock_completion_cost,
    mock_requests_post,
    mock_supports_response_schema,
    mock_db_session_context,
    mock_execute_async,
    client: GenaiEngineTestClientBase,
):
    """
    Test the validates that exactly one session_id generated template variable is present in the experiment,
    that it can be included in either the request body or request headers, and that the variable could be named anything.
    """

    # Mock db_session_context for background thread execution to use test database
    setup_db_session_context_mock(mock_db_session_context)

    def sync_execute(experiment_id, request_time_parameters=None):
        executor = AgenticExperimentExecutor()
        return executor._execute_experiment(experiment_id, request_time_parameters)

    mock_execute_async.side_effect = sync_execute

    # Setup: Create task
    task_name = f"agentic_experiment_task_{random.random()}"
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
    dataset_name = f"agentic_test_dataset_{random.random()}"
    status_code, dataset = client.create_dataset(
        name=dataset_name,
        task_id=task_id,
        description="Test dataset for agentic experiments",
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
    # The transform will extract from the trace span we create
    transform_name = f"test_transform_{random.random()}"
    transform_request = NewTraceTransformRequest(
        name=transform_name,
        description="Test transform for agentic experiments",
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

    # Mock HTTP request responses - set up before experiment creation
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

    # Configure the mock to return our response function
    mock_requests_post.side_effect = mock_post_response

    # Mock supports_response_schema to return True (required by run_llm_eval)
    mock_supports_response_schema.return_value = True

    # Mock LLM eval responses
    # ReasonedScore expects score to be an integer (0 or 1), not a float
    # The mock must be set up before the experiment is created so it's available in the background thread
    mock_response = MagicMock(spec=ModelResponse)
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": '{"reason": "The agent response is highly relevant and accurate.", "score": 1}',
    }
    # Ensure the mock is properly configured to return the response
    mock_completion.return_value = mock_response
    mock_completion_cost.return_value = 0.002345

    # Also ensure the mock doesn't raise exceptions
    mock_completion.side_effect = None

    # Mock loggers to prevent I/O errors on closed file handles in background threads
    # These loggers are used in background threads and may try to write after test cleanup
    mock_agentic_logger.info = MagicMock()
    mock_agentic_logger.error = MagicMock()
    mock_agentic_logger.warning = MagicMock()
    mock_experiment_logger.info = MagicMock()
    mock_experiment_logger.error = MagicMock()
    mock_experiment_logger.warning = MagicMock()

    # Track session IDs for trace creation
    created_session_ids = []
    # Track actual requests made to agent endpoint to validate request-time parameters are included
    actual_agent_requests = []

    def mock_post_with_trace_creation(*args, **kwargs):
        """Mock HTTP POST response and create trace with session_id."""
        # Extract session_id from headers (always sent in headers, not body)
        headers = kwargs.get("headers", {})
        session_id = None

        for value in headers.values():
            if value.startswith("arthur-exp"):
                session_id = value
                break

        # Capture the actual request to validate request-time parameters are included
        # requests.post(url, headers=..., data=...) - first arg is URL
        request_url = args[0] if args else kwargs.get("url", "")
        body_data = kwargs.get("data", "")

        # Parse body for logging if it's JSON
        body_dict = {}
        try:
            if body_data:
                body_dict = (
                    json.loads(body_data) if isinstance(body_data, str) else body_data
                )
        except (json.JSONDecodeError, ValueError, TypeError):
            body_dict = {"raw": str(body_data)}

        actual_agent_requests.append(
            {
                "url": request_url,
                "headers": dict(headers) if headers else {},
                "body": (
                    body_dict
                    if isinstance(body_dict, dict)
                    else {"raw": str(body_data)}
                ),
            },
        )

        if not session_id:
            for value in body_dict.values():
                if value.startswith("arthur-exp"):
                    session_id = value
                    break

        if session_id:
            created_session_ids.append(session_id)
            # Create trace with this session_id
            create_mock_trace_with_session_id(
                client,
                task_id,
                session_id,
            )

        # Return the mocked response
        return mock_post_response(*args, **kwargs)

    # Set the side_effect after defining the function
    mock_requests_post.side_effect = mock_post_with_trace_creation
    # Ensure return_value is not set (side_effect takes precedence)
    mock_requests_post.return_value = None

    # Test 1: Create agentic experiment with the session_id generator variable in the header
    experiment_name = f"test_agentic_experiment_{random.random()}"

    # Request-time parameter value (the value should never be persisted, but the mapping structure is)
    request_time_api_key = "secret-api-key-12345"

    experiment_request = CreateAgenticExperimentRequest(
        name=experiment_name,
        description="Test agentic experiment",
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
        http_template=HttpTemplate(
            endpoint_name="chat_endpoint",
            endpoint_url="https://example.com/api/chat",
            headers=[
                HttpHeader(
                    name="Authorization",
                    value="Bearer {{api_key}}",
                ),
                HttpHeader(
                    name="X-Request-ID",
                    value="{{request_id}}",
                ),
                HttpHeader(
                    name="random_session_id",
                    value="{{random_session_id}}",
                ),
            ],
            request_body='{"message": "{{user_message}}"}',
        ),
        template_variable_mapping=[
            TemplateVariableMapping(
                variable_name="api_key",
                source=RequestTimeParameterSource(
                    type="request_time_parameter",
                ),
            ),
            TemplateVariableMapping(
                variable_name="request_id",
                source=GeneratedVariableSource(
                    type="generated",
                    generator_type="uuid",
                ),
            ),
            TemplateVariableMapping(
                variable_name="random_session_id",
                source=GeneratedVariableSource(
                    type="generated",
                    generator_type="session_id",
                ),
            ),
            TemplateVariableMapping(
                variable_name="user_message",
                source=DatasetColumnVariableSource(
                    type="dataset_column",
                    dataset_column=DatasetColumnSource(
                        name="user_message",
                    ),
                ),
            ),
        ],
        request_time_parameters=[
            RequestTimeParameter(
                name="api_key",
                value=request_time_api_key,
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
                                type="transform_variable",
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
    assert (
        status_code == 200
    ), f"Failed to create agentic experiment: {experiment_summary}"
    experiment_id = experiment_summary["id"]

    # Validate experiment summary response fields
    assert experiment_summary["name"] == experiment_name
    assert experiment_summary["description"] == "Test agentic experiment"
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

    # Validate HTTP template structure
    # Validate HTTP template structure
    assert "http_template" in experiment_summary
    assert experiment_summary["http_template"]["endpoint_name"] == "chat_endpoint"
    assert (
        experiment_summary["http_template"]["endpoint_url"]
        == "https://example.com/api/chat"
    )
    assert len(experiment_summary["http_template"]["headers"]) == 3
    assert experiment_summary["http_template"]["headers"][0]["name"] == "Authorization"
    assert (
        experiment_summary["http_template"]["headers"][0]["value"]
        == "Bearer {{api_key}}"
    )
    assert experiment_summary["http_template"]["headers"][1]["name"] == "X-Request-ID"
    assert (
        experiment_summary["http_template"]["headers"][1]["value"] == "{{request_id}}"
    )
    assert (
        experiment_summary["http_template"]["request_body"]
        == '{"message": "{{user_message}}"}'
    )

    # Validate that request_time_parameters are NOT in the response
    assert "request_time_parameters" not in experiment_summary

    # Note: template_variable_mapping is NOT included in AgenticExperimentSummary
    # It's only available in AgenticExperimentDetail, which we'll validate below

    # Test 2: Get agentic experiment details (polling until completion)
    experiment_detail = wait_for_experiment_completion(client, experiment_id)

    # Validate experiment detail response fields
    assert experiment_detail.id == experiment_id
    assert experiment_detail.name == experiment_name
    assert experiment_detail.description == "Test agentic experiment"
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

    # Validate HTTP template with all expected values
    assert experiment_detail.http_template is not None
    assert experiment_detail.http_template.endpoint_name == "chat_endpoint"
    assert (
        experiment_detail.http_template.endpoint_url == "https://example.com/api/chat"
    )
    assert len(experiment_detail.http_template.headers) == 3
    assert experiment_detail.http_template.headers[0].name == "Authorization"
    assert experiment_detail.http_template.headers[0].value == "Bearer {{api_key}}"
    assert experiment_detail.http_template.headers[1].name == "X-Request-ID"
    assert experiment_detail.http_template.headers[1].value == "{{request_id}}"
    assert (
        experiment_detail.http_template.request_body
        == '{"message": "{{user_message}}"}'
    )

    # Validate template_variable_mapping - should include request-time parameter mappings
    # (the mapping structure is persisted, but not the values)
    assert experiment_detail.template_variable_mapping is not None
    assert (
        len(experiment_detail.template_variable_mapping) == 4
    )  # UUID generator, dataset column, and request-time parameter
    mapping_variable_names = [
        m.variable_name for m in experiment_detail.template_variable_mapping
    ]
    assert "request_id" in mapping_variable_names  # UUID generator
    assert "user_message" in mapping_variable_names  # Dataset column
    assert (
        "api_key" in mapping_variable_names
    )  # Request-time parameter mapping should be included

    # Verify the request-time parameter mapping structure
    api_key_mapping = None
    for mapping in experiment_detail.template_variable_mapping:
        if mapping.variable_name == "api_key":
            api_key_mapping = mapping
            break
    assert api_key_mapping is not None, "Request-time parameter mapping not found"
    assert api_key_mapping.source.type == "request_time_parameter"

    # Verify all mapping types are present
    mapping_types = {m.source.type for m in experiment_detail.template_variable_mapping}
    assert "generated" in mapping_types
    assert "dataset_column" in mapping_types
    assert "request_time_parameter" in mapping_types

    # Validate that request_time_parameters are NOT in the detail response
    # (they should not be stored or returned)
    assert not hasattr(
        experiment_detail,
        "request_time_parameters",
    ), "request_time_parameters should not be in AgenticExperimentDetail"

    # Validate summary results with expected values
    assert experiment_detail.summary_results is not None
    assert len(experiment_detail.summary_results.eval_summaries) == 1
    eval_summary = experiment_detail.summary_results.eval_summaries[0]
    assert eval_summary.eval_name == eval_name
    assert eval_summary.eval_version == "1"
    assert eval_summary.transform_id == transform_id
    assert eval_summary.eval_results is not None
    assert len(eval_summary.eval_results) == 1
    eval_result = eval_summary.eval_results[0]
    assert eval_result.eval_name == eval_name
    assert eval_result.eval_version == "1"
    # With dataset_row_filter, only 1 row should match
    assert eval_result.total_count == 1
    assert eval_result.pass_count == 1  # All should pass with our mock

    # Test 3: Test that the session_id variable included in the request body works properly
    experiment_request = CreateAgenticExperimentRequest(
        name=experiment_name,
        description="Test agentic experiment",
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
        http_template=HttpTemplate(
            endpoint_name="chat_endpoint",
            endpoint_url="https://example.com/api/chat",
            headers=[
                HttpHeader(
                    name="Authorization",
                    value="Bearer {{api_key}}",
                ),
                HttpHeader(
                    name="X-Request-ID",
                    value="{{request_id}}",
                ),
            ],
            request_body='{"message": "{{user_message}}", "body_session_id": "{{body_session_id}}"}',
        ),
        template_variable_mapping=[
            TemplateVariableMapping(
                variable_name="api_key",
                source=RequestTimeParameterSource(
                    type="request_time_parameter",
                ),
            ),
            TemplateVariableMapping(
                variable_name="request_id",
                source=GeneratedVariableSource(
                    type="generated",
                    generator_type="uuid",
                ),
            ),
            TemplateVariableMapping(
                variable_name="body_session_id",
                source=GeneratedVariableSource(
                    type="generated",
                    generator_type="session_id",
                ),
            ),
            TemplateVariableMapping(
                variable_name="user_message",
                source=DatasetColumnVariableSource(
                    type="dataset_column",
                    dataset_column=DatasetColumnSource(
                        name="user_message",
                    ),
                ),
            ),
        ],
        request_time_parameters=[
            RequestTimeParameter(
                name="api_key",
                value=request_time_api_key,
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
                                type="transform_variable",
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
    assert (
        status_code == 200
    ), f"Failed to create agentic experiment: {experiment_summary}"
    experiment_id = experiment_summary["id"]

    # Validate experiment summary response fields
    assert experiment_summary["name"] == experiment_name
    assert experiment_summary["description"] == "Test agentic experiment"
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

    # Validate HTTP template structure
    # Validate HTTP template structure
    assert "http_template" in experiment_summary
    assert experiment_summary["http_template"]["endpoint_name"] == "chat_endpoint"
    assert (
        experiment_summary["http_template"]["endpoint_url"]
        == "https://example.com/api/chat"
    )
    assert len(experiment_summary["http_template"]["headers"]) == 2
    assert experiment_summary["http_template"]["headers"][0]["name"] == "Authorization"
    assert (
        experiment_summary["http_template"]["headers"][0]["value"]
        == "Bearer {{api_key}}"
    )
    assert experiment_summary["http_template"]["headers"][1]["name"] == "X-Request-ID"
    assert (
        experiment_summary["http_template"]["headers"][1]["value"] == "{{request_id}}"
    )
    assert (
        experiment_summary["http_template"]["request_body"]
        == '{"message": "{{user_message}}", "body_session_id": "{{body_session_id}}"}',
    )

    # Validate that request_time_parameters are NOT in the response
    assert "request_time_parameters" not in experiment_summary

    # Note: template_variable_mapping is NOT included in AgenticExperimentSummary
    # It's only available in AgenticExperimentDetail, which we'll validate below

    # Test 4: Get agentic experiment details (polling until completion)
    experiment_detail = wait_for_experiment_completion(client, experiment_id)

    # Validate experiment detail response fields
    assert experiment_detail.id == experiment_id
    assert experiment_detail.name == experiment_name
    assert experiment_detail.description == "Test agentic experiment"
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

    # Validate HTTP template with all expected values
    assert experiment_detail.http_template is not None
    assert experiment_detail.http_template.endpoint_name == "chat_endpoint"
    assert (
        experiment_detail.http_template.endpoint_url == "https://example.com/api/chat"
    )
    assert len(experiment_detail.http_template.headers) == 2
    assert experiment_detail.http_template.headers[0].name == "Authorization"
    assert experiment_detail.http_template.headers[0].value == "Bearer {{api_key}}"
    assert experiment_detail.http_template.headers[1].name == "X-Request-ID"
    assert experiment_detail.http_template.headers[1].value == "{{request_id}}"
    assert (
        experiment_detail.http_template.request_body
        == '{"message": "{{user_message}}", "body_session_id": "{{body_session_id}}"}',
    )

    # Validate template_variable_mapping - should include request-time parameter mappings
    # (the mapping structure is persisted, but not the values)
    assert experiment_detail.template_variable_mapping is not None
    assert (
        len(experiment_detail.template_variable_mapping) == 4
    )  # UUID generator, dataset column, and request-time parameter
    mapping_variable_names = [
        m.variable_name for m in experiment_detail.template_variable_mapping
    ]
    assert "request_id" in mapping_variable_names  # UUID generator
    assert "user_message" in mapping_variable_names  # Dataset column
    assert (
        "api_key" in mapping_variable_names
    )  # Request-time parameter mapping should be included

    # Verify the request-time parameter mapping structure
    api_key_mapping = None
    for mapping in experiment_detail.template_variable_mapping:
        if mapping.variable_name == "api_key":
            api_key_mapping = mapping
            break
    assert api_key_mapping is not None, "Request-time parameter mapping not found"
    assert api_key_mapping.source.type == "request_time_parameter"

    # Verify all mapping types are present
    mapping_types = {m.source.type for m in experiment_detail.template_variable_mapping}
    assert "generated" in mapping_types
    assert "dataset_column" in mapping_types
    assert "request_time_parameter" in mapping_types

    # Validate that request_time_parameters are NOT in the detail response
    # (they should not be stored or returned)
    assert not hasattr(
        experiment_detail,
        "request_time_parameters",
    ), "request_time_parameters should not be in AgenticExperimentDetail"

    # Validate summary results with expected values
    assert experiment_detail.summary_results is not None
    assert len(experiment_detail.summary_results.eval_summaries) == 1
    eval_summary = experiment_detail.summary_results.eval_summaries[0]
    assert eval_summary.eval_name == eval_name
    assert eval_summary.eval_version == "1"
    assert eval_summary.transform_id == transform_id
    assert eval_summary.eval_results is not None
    assert len(eval_summary.eval_results) == 1
    eval_result = eval_summary.eval_results[0]
    assert eval_result.eval_name == eval_name
    assert eval_result.eval_version == "1"
    # With dataset_row_filter, only 1 row should match
    assert eval_result.total_count == 1
    assert eval_result.pass_count == 1  # All should pass with our mock

    # Test 5: Validate an error raises when creating two session_id template variables
    with pytest.raises(ValueError) as exc_info:
        experiment_request = CreateAgenticExperimentRequest(
            name=experiment_name,
            description="Test agentic experiment",
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
            http_template=HttpTemplate(
                endpoint_name="chat_endpoint",
                endpoint_url="https://example.com/api/chat",
                headers=[
                    HttpHeader(
                        name="Authorization",
                        value="Bearer {{api_key}}",
                    ),
                    HttpHeader(
                        name="X-Request-ID",
                        value="{{request_id}}",
                    ),
                ],
                request_body='{"message": "{{user_message}}", "body_session_id": "{{body_session_id}}"}',
            ),
            template_variable_mapping=[
                TemplateVariableMapping(
                    variable_name="api_key",
                    source=RequestTimeParameterSource(
                        type="request_time_parameter",
                    ),
                ),
                TemplateVariableMapping(
                    variable_name="request_id",
                    source=GeneratedVariableSource(
                        type="generated",
                        generator_type="session_id",
                    ),
                ),
                TemplateVariableMapping(
                    variable_name="body_session_id",
                    source=GeneratedVariableSource(
                        type="generated",
                        generator_type="session_id",
                    ),
                ),
                TemplateVariableMapping(
                    variable_name="user_message",
                    source=DatasetColumnVariableSource(
                        type="dataset_column",
                        dataset_column=DatasetColumnSource(
                            name="user_message",
                        ),
                    ),
                ),
            ],
            request_time_parameters=[
                RequestTimeParameter(
                    name="api_key",
                    value=request_time_api_key,
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
                                    type="transform_variable",
                                    transform_variable_name="final_response",
                                ),
                            ),
                        ),
                    ],
                ),
            ],
        )
    assert "Exactly one session_id is required per experiment" in str(exc_info.value)

    # Test 6: Validate an error raises when creating an experiment without a session_id template variable
    with pytest.raises(ValueError) as exc_info:
        experiment_request = CreateAgenticExperimentRequest(
            name=experiment_name,
            description="Test agentic experiment",
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
            http_template=HttpTemplate(
                endpoint_name="chat_endpoint",
                endpoint_url="https://example.com/api/chat",
                headers=[
                    HttpHeader(
                        name="Authorization",
                        value="Bearer {{api_key}}",
                    ),
                    HttpHeader(
                        name="X-Request-ID",
                        value="{{request_id}}",
                    ),
                ],
                request_body='{"message": "{{user_message}}", "body_session_id": "{{body_session_id}}"}',
            ),
            template_variable_mapping=[
                TemplateVariableMapping(
                    variable_name="api_key",
                    source=RequestTimeParameterSource(
                        type="request_time_parameter",
                    ),
                ),
                TemplateVariableMapping(
                    variable_name="request_id",
                    source=GeneratedVariableSource(
                        type="generated",
                        generator_type="uuid",
                    ),
                ),
                TemplateVariableMapping(
                    variable_name="body_session_id",
                    source=GeneratedVariableSource(
                        type="generated",
                        generator_type="uuid",
                    ),
                ),
                TemplateVariableMapping(
                    variable_name="user_message",
                    source=DatasetColumnVariableSource(
                        type="dataset_column",
                        dataset_column=DatasetColumnSource(
                            name="user_message",
                        ),
                    ),
                ),
            ],
            request_time_parameters=[
                RequestTimeParameter(
                    name="api_key",
                    value=request_time_api_key,
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
                                    type="transform_variable",
                                    transform_variable_name="final_response",
                                ),
                            ),
                        ),
                    ],
                ),
            ],
        )
    assert "A session_id variable is required to create an agentic experiment" in str(
        exc_info.value,
    )
