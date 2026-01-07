import uuid
from datetime import datetime
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest
from arthur_common.models.enums import AgenticAnnotationType, ContinuousEvalRunStatus
from litellm.types.utils import ModelResponse

from db_models.agentic_annotation_models import DatabaseAgenticAnnotation
from db_models.llm_eval_models import DatabaseContinuousEval
from db_models.task_models import DatabaseTask
from db_models.telemetry_models import DatabaseSpan, DatabaseTraceMetadata
from repositories.continuous_evals_repository import ContinuousEvalsRepository
from schemas.internal_schemas import Span as InternalSpan
from services.continuous_eval import (
    ContinuousEvalJob,
    get_continuous_eval_queue_service,
    initialize_continuous_eval_queue_service,
    shutdown_continuous_eval_queue_service,
)
from services.trace.span_normalization_service import SpanNormalizationService
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)


def mock_get_db_session_generator():
    """Generator function that yields the test database session."""
    yield override_get_db_session()


def create_mock_annotation(
    trace_id: str,
    annotation_type: AgenticAnnotationType,
    annotation_score: Optional[int] = None,
    continuous_eval_id: Optional[str] = None,
    run_status: Optional[ContinuousEvalRunStatus] = None,
    created_at: Optional[datetime] = None,
    updated_at: Optional[datetime] = None,
) -> tuple[int, DatabaseAgenticAnnotation]:
    db_session = override_get_db_session()
    db_annotation = DatabaseAgenticAnnotation(
        id=uuid.uuid4(),
        annotation_type=annotation_type.value,
        trace_id=trace_id,
        annotation_score=annotation_score,
        continuous_eval_id=continuous_eval_id,
        run_status=run_status.value if run_status else None,
        created_at=datetime.now() if created_at is None else created_at,
        updated_at=datetime.now() if updated_at is None else updated_at,
    )
    db_session.add(db_annotation)
    db_session.commit()
    db_session.refresh(db_annotation)
    return db_annotation


def delete_mock_annotation(annotation_id: uuid.UUID) -> None:
    db_session = override_get_db_session()
    db_annotation = (
        db_session.query(DatabaseAgenticAnnotation)
        .filter(DatabaseAgenticAnnotation.id == annotation_id)
        .first()
    )
    if not db_annotation:
        return
    db_session.delete(db_annotation)
    db_session.commit()


def cleanup_model_provider(client: GenaiEngineTestClientBase) -> None:
    """Clean up the OpenAI model provider configured during tests."""
    client.base_client.delete(
        "/api/v1/model_providers/openai",
        headers=client.authorized_user_api_key_headers,
    )


def setup_test_data():
    """Setup test data including task, trace, and spans."""
    db_session = override_get_db_session()
    span_normalizer = SpanNormalizationService()

    task_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())

    # Create task
    task = DatabaseTask(
        id=task_id,
        name="Test Task for Transform Execution",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        is_agentic=True,
    )
    db_session.add(task)
    db_session.commit()

    # Create spans with nested attributes
    base_time = datetime.now()

    # Span 1: RAG retrieval span with sqlQuery
    span1_raw_data = span_normalizer.normalize_span_to_nested_dict(
        {
            "kind": "SPAN_KIND_INTERNAL",
            "name": "rag-retrieval-savedQueries",
            "spanId": f"span1_{uuid.uuid4()}",
            "traceId": trace_id,
            "attributes": {
                "openinference.span.kind": "RETRIEVER",
                "input.value.sqlQuery": "SELECT * FROM users WHERE id = 1",
                "input.value.context": "User query context",
                "output.value.results": [
                    {"id": 1, "name": "John"},
                    {"id": 2, "name": "Jane"},
                ],
            },
        },
    )
    span1_raw_data["arthur_span_version"] = "arthur_span_v1"

    span1 = InternalSpan(
        id=str(uuid.uuid4()),
        trace_id=trace_id,
        span_id=span1_raw_data["spanId"],
        task_id=task_id,
        parent_span_id=None,
        span_kind="RETRIEVER",
        start_time=base_time,
        end_time=base_time,
        session_id=None,
        user_id=None,
        raw_data=span1_raw_data,
        created_at=base_time,
        updated_at=base_time,
    )

    # Span 2: LLM span with token costs
    span2_raw_data = span_normalizer.normalize_span_to_nested_dict(
        {
            "kind": "SPAN_KIND_INTERNAL",
            "name": "llm_call",
            "spanId": f"span2_{uuid.uuid4()}",
            "traceId": trace_id,
            "attributes": {
                "openinference.span.kind": "LLM",
                "llm.model_name": "gpt-4",
                "llm.token_cost": 0.05,
                "llm.token_count.prompt": 100,
                "llm.token_count.completion": 50,
            },
        },
    )
    span2_raw_data["arthur_span_version"] = "arthur_span_v1"

    span2 = InternalSpan(
        id=str(uuid.uuid4()),
        trace_id=trace_id,
        span_id=span2_raw_data["spanId"],
        task_id=task_id,
        parent_span_id=None,
        span_kind="LLM",
        start_time=base_time,
        end_time=base_time,
        session_id=None,
        user_id=None,
        raw_data=span2_raw_data,
        created_at=base_time,
        updated_at=base_time,
    )

    # Span 3: Span with nested child
    span3_raw_data = span_normalizer.normalize_span_to_nested_dict(
        {
            "kind": "SPAN_KIND_INTERNAL",
            "name": "agent_span",
            "spanId": f"span3_{uuid.uuid4()}",
            "traceId": trace_id,
            "attributes": {
                "openinference.span.kind": "AGENT",
                "agent.name": "test_agent",
            },
        },
    )
    span3_raw_data["arthur_span_version"] = "arthur_span_v1"

    span3 = InternalSpan(
        id=str(uuid.uuid4()),
        trace_id=trace_id,
        span_id=span3_raw_data["spanId"],
        task_id=task_id,
        parent_span_id=span1_raw_data["spanId"],  # Child of span1
        span_kind="AGENT",
        start_time=base_time,
        end_time=base_time,
        session_id=None,
        user_id=None,
        raw_data=span3_raw_data,
        created_at=base_time,
        updated_at=base_time,
    )

    # Create database spans
    spans = [span1, span2, span3]
    database_spans = []
    for span in spans:
        db_span = DatabaseSpan(
            id=span.id,
            trace_id=span.trace_id,
            span_id=span.span_id,
            parent_span_id=span.parent_span_id,
            span_name=span.raw_data.get("name"),
            span_kind=span.span_kind,
            start_time=span.start_time,
            end_time=span.end_time,
            task_id=span.task_id,
            session_id=span.session_id,
            user_id=span.user_id,
            status_code="Ok",
            raw_data=span.raw_data,
            created_at=span.created_at,
            updated_at=span.updated_at,
        )
        database_spans.append(db_span)

    db_session.add_all(database_spans)
    db_session.commit()

    # Create trace metadata
    trace_metadata = DatabaseTraceMetadata(
        task_id=task_id,
        trace_id=trace_id,
        session_id=None,
        user_id=None,
        span_count=len(spans),
        start_time=base_time,
        end_time=base_time,
        created_at=base_time,
        updated_at=base_time,
        input_content="test input",
        output_content="test output",
    )
    db_session.add(trace_metadata)
    db_session.commit()

    return {
        "task_id": task_id,
        "trace_id": trace_id,
        "spans": spans,
        "db_session": db_session,
    }


def cleanup_test_data(test_data):
    db_session = override_get_db_session()
    trace_id = test_data["trace_id"]
    task_id = test_data["task_id"]

    # Cleanup
    db_session.query(DatabaseSpan).filter(DatabaseSpan.trace_id == trace_id).delete()
    db_session.query(DatabaseTraceMetadata).filter(
        DatabaseTraceMetadata.trace_id == trace_id,
    ).delete()
    db_session.query(DatabaseTask).filter(DatabaseTask.id == task_id).delete()
    db_session.commit()


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
@patch(
    "services.continuous_eval.continuous_eval_queue_service.get_db_session",
    side_effect=mock_get_db_session_generator,
)
def test_continuous_eval_execution(
    mock_get_db_session,
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    """Test continuous eval execution."""
    test_data = setup_test_data()

    # Mock LLM response to return score of 1
    mock_response = MagicMock(spec=ModelResponse)
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": '{"reason": "The model name is correct.", "score": 1}',
    }
    mock_completion.return_value = mock_response
    mock_completion_cost.return_value = 0.002345

    # Initialize with 1 second delay for faster test execution
    initialize_continuous_eval_queue_service(num_workers=2, override_execution_delay=0)
    continuous_eval_queue_service = get_continuous_eval_queue_service()

    status_code, agentic_task = client.create_task(
        name="test_continuous_eval_execution",
        is_agentic=True,
    )
    assert status_code == 200

    # Configure model provider
    response = client.base_client.put(
        "/api/v1/model_providers/openai",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201

    llm_eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Test instructions {{model_name}}",
    }
    status_code, llm_eval = client.save_llm_eval(
        task_id=agentic_task.id,
        llm_eval_name="test_llm_eval",
        llm_eval_data=llm_eval_data,
    )
    assert status_code == 200

    transform_definition = {
        "variables": [
            {
                "variable_name": "model_name",
                "span_name": "rag-retrieval-savedQueries",
                "attribute_path": "attributes.input.value.context",
            },
        ],
    }
    status_code, transform = client.create_transform(
        task_id=agentic_task.id,
        name="test_transform",
        description="Test transform description",
        definition=transform_definition,
    )
    assert status_code == 200

    status_code, continuous_eval = client.save_continuous_eval(
        task_id=agentic_task.id,
        continuous_eval_data={
            "name": "test_continuous_eval",
            "description": "Test continuous eval description",
            "llm_eval_name": "test_llm_eval",
            "llm_eval_version": 1,
            "transform_id": str(transform.id),
            "transform_variable_mapping": [
                {
                    "transform_variable": "model_name",
                    "eval_variable": "model_name",
                },
            ],
        },
    )
    assert status_code == 200

    annotation = create_mock_annotation(
        trace_id=test_data["trace_id"],
        annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL,
        continuous_eval_id=continuous_eval.id,
        run_status=ContinuousEvalRunStatus.PENDING,
    )

    job = ContinuousEvalJob(
        annotation_id=annotation.id,
        trace_id=test_data["trace_id"],
        continuous_eval_id=continuous_eval.id,
        task_id=agentic_task.id,
        delay_seconds=0,
    )
    continuous_eval_queue_service._execute_job(job)

    status_code, received_annotation = client.get_annotation_by_id(annotation.id)
    assert status_code == 200
    assert received_annotation.run_status == ContinuousEvalRunStatus.PASSED.value

    delete_mock_annotation(annotation.id)

    status_code = client.delete_task(agentic_task.id)
    assert status_code == 204

    shutdown_continuous_eval_queue_service()
    cleanup_model_provider(client)
    cleanup_test_data(test_data)


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
@patch(
    "services.continuous_eval.continuous_eval_queue_service.get_db_session",
    side_effect=mock_get_db_session_generator,
)
def test_continuous_eval_execution_response_fail(
    mock_get_db_session,
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    """Test continuous eval execution."""
    test_data = setup_test_data()

    # Mock LLM response to return score of 1
    mock_response = MagicMock(spec=ModelResponse)
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": '{"reason": "The model name is correct.", "score": 0}',
    }
    mock_completion.return_value = mock_response
    mock_completion_cost.return_value = 0.002345

    # Initialize with 1 second delay for faster test execution
    initialize_continuous_eval_queue_service(num_workers=2, override_execution_delay=0)
    continuous_eval_queue_service = get_continuous_eval_queue_service()

    status_code, agentic_task = client.create_task(
        name="test_continuous_eval_execution_response_fail",
        is_agentic=True,
    )
    assert status_code == 200

    # Configure model provider
    response = client.base_client.put(
        "/api/v1/model_providers/openai",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201

    llm_eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Test instructions {{model_name}}",
    }
    status_code, llm_eval = client.save_llm_eval(
        task_id=agentic_task.id,
        llm_eval_name="test_llm_eval",
        llm_eval_data=llm_eval_data,
    )
    assert status_code == 200

    transform_definition = {
        "variables": [
            {
                "variable_name": "model_name",
                "span_name": "rag-retrieval-savedQueries",
                "attribute_path": "attributes.input.value.context",
            },
        ],
    }
    status_code, transform = client.create_transform(
        task_id=agentic_task.id,
        name="test_transform",
        description="Test transform description",
        definition=transform_definition,
    )
    assert status_code == 200

    status_code, continuous_eval = client.save_continuous_eval(
        task_id=agentic_task.id,
        continuous_eval_data={
            "name": "test_continuous_eval",
            "description": "Test continuous eval description",
            "llm_eval_name": "test_llm_eval",
            "llm_eval_version": 1,
            "transform_id": str(transform.id),
            "transform_variable_mapping": [
                {
                    "transform_variable": "model_name",
                    "eval_variable": "model_name",
                },
            ],
        },
    )
    assert status_code == 200

    annotation = create_mock_annotation(
        trace_id=test_data["trace_id"],
        annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL,
        continuous_eval_id=continuous_eval.id,
        run_status=ContinuousEvalRunStatus.PENDING,
    )

    job = ContinuousEvalJob(
        annotation_id=annotation.id,
        trace_id=test_data["trace_id"],
        continuous_eval_id=continuous_eval.id,
        task_id=agentic_task.id,
        delay_seconds=0,
    )
    continuous_eval_queue_service._execute_job(job)

    status_code, received_annotation = client.get_annotation_by_id(annotation.id)
    assert status_code == 200
    assert received_annotation.run_status == ContinuousEvalRunStatus.FAILED.value

    delete_mock_annotation(annotation.id)

    status_code = client.delete_task(agentic_task.id)
    assert status_code == 204

    shutdown_continuous_eval_queue_service()
    cleanup_model_provider(client)
    cleanup_test_data(test_data)


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
@patch(
    "services.continuous_eval.continuous_eval_queue_service.get_db_session",
    side_effect=mock_get_db_session_generator,
)
def test_continuous_eval_execution_annotation_eval_errors(
    mock_get_db_session,
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    """Test continuous eval execution."""
    test_data = setup_test_data()
    # Mock LLM response to return score of 1
    mock_response = MagicMock(spec=ModelResponse)
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": '{"reason": "The model name is correct.", "score": 0}',
    }
    mock_completion.return_value = mock_response
    mock_completion_cost.return_value = 0.002345

    # Initialize the queue service
    initialize_continuous_eval_queue_service(num_workers=2)
    continuous_eval_queue_service = get_continuous_eval_queue_service()

    status_code, agentic_task = client.create_task(
        name="test_continuous_eval_execution_annotation_eval_errors",
        is_agentic=True,
    )
    assert status_code == 200

    # Configure model provider
    response = client.base_client.put(
        "/api/v1/model_providers/openai",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201

    llm_eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Test instructions {{model_name}}",
    }
    status_code, llm_eval = client.save_llm_eval(
        task_id=agentic_task.id,
        llm_eval_name="test_llm_eval",
        llm_eval_data=llm_eval_data,
    )
    assert status_code == 200

    transform_definition = {
        "variables": [
            {
                "variable_name": "model_name",
                "span_name": "rag-retrieval-savedQueries",
                "attribute_path": "attributes.input.value.context",
            },
        ],
    }
    status_code, transform = client.create_transform(
        task_id=agentic_task.id,
        name="test_transform",
        description="Test transform description",
        definition=transform_definition,
    )
    assert status_code == 200

    transform_definition = {
        "variables": [
            {
                "variable_name": "model_name",
                "span_name": "rag-retrieval-savedQueries",
                "attribute_path": "fake_path",
            },
        ],
    }
    status_code, incorrect_transform = client.create_transform(
        task_id=agentic_task.id,
        name="incorrect_transform",
        description="Test transform description",
        definition=transform_definition,
    )
    assert status_code == 200

    status_code, continuous_eval = client.save_continuous_eval(
        task_id=agentic_task.id,
        continuous_eval_data={
            "name": "test_continuous_eval",
            "description": "Test continuous eval description",
            "llm_eval_name": "test_llm_eval",
            "llm_eval_version": 1,
            "transform_id": str(transform.id),
            "transform_variable_mapping": [
                {
                    "transform_variable": "model_name",
                    "eval_variable": "model_name",
                },
            ],
        },
    )
    assert status_code == 200

    # test executing a job for a non-existent annotation
    fake_annotation_id = uuid.uuid4()
    job = ContinuousEvalJob(
        annotation_id=fake_annotation_id,
        trace_id=test_data["trace_id"],
        continuous_eval_id=continuous_eval.id,
        task_id=agentic_task.id,
        delay_seconds=0,
    )

    with pytest.raises(ValueError, match=f"Annotation {fake_annotation_id} not found"):
        continuous_eval_queue_service._execute_job(job)

    # create a mock annotation that's not a continuous eval
    annotation = create_mock_annotation(
        trace_id=test_data["trace_id"],
        annotation_type=AgenticAnnotationType.HUMAN,
        annotation_score=1,
    )

    # test executing a job for a non-continuous eval annotation
    job = ContinuousEvalJob(
        annotation_id=annotation.id,
        trace_id=test_data["trace_id"],
        continuous_eval_id=continuous_eval.id,
        task_id=agentic_task.id,
        delay_seconds=0,
    )

    with pytest.raises(
        ValueError,
        match=f"Annotation {annotation.id} is not a continuous eval",
    ):
        continuous_eval_queue_service._execute_job(job)

    status_code, received_annotation = client.get_annotation_by_id(annotation.id)
    assert status_code == 200
    assert received_annotation.run_status == ContinuousEvalRunStatus.ERROR.value

    delete_mock_annotation(annotation.id)

    # test non-matching trace ID
    annotation = create_mock_annotation(
        trace_id="api_trace_456",
        annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL,
        continuous_eval_id=continuous_eval.id,
        annotation_score=1,
        run_status=ContinuousEvalRunStatus.PENDING,
    )

    job = ContinuousEvalJob(
        annotation_id=annotation.id,
        trace_id=test_data["trace_id"],
        continuous_eval_id=continuous_eval.id,
        task_id=agentic_task.id,
        delay_seconds=0,
    )

    with pytest.raises(
        ValueError,
        match=f"Annotation's trace ID does not match the job's trace ID",
    ):
        continuous_eval_queue_service._execute_job(job)

    status_code, received_annotation = client.get_annotation_by_id(annotation.id)
    assert status_code == 200
    assert received_annotation.run_status == ContinuousEvalRunStatus.ERROR.value

    delete_mock_annotation(annotation.id)

    # test non-matching continuous eval ID
    annotation = create_mock_annotation(
        trace_id=test_data["trace_id"],
        annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL,
        continuous_eval_id=uuid.uuid4(),
        annotation_score=1,
        run_status=ContinuousEvalRunStatus.PENDING,
    )

    job = ContinuousEvalJob(
        annotation_id=annotation.id,
        trace_id=test_data["trace_id"],
        continuous_eval_id=uuid.uuid4(),
        task_id=agentic_task.id,
        delay_seconds=0,
    )

    with pytest.raises(
        ValueError,
        match=f"Annotation's continuous eval ID does not match the job's continuous eval ID",
    ):
        continuous_eval_queue_service._execute_job(job)

    status_code, received_annotation = client.get_annotation_by_id(annotation.id)
    assert status_code == 200
    assert received_annotation.run_status == ContinuousEvalRunStatus.ERROR.value

    delete_mock_annotation(annotation.id)

    # test executing a job for a non-pending annotation
    annotation = create_mock_annotation(
        trace_id=test_data["trace_id"],
        annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL,
        continuous_eval_id=continuous_eval.id,
        annotation_score=1,
        run_status=ContinuousEvalRunStatus.RUNNING,
    )

    job = ContinuousEvalJob(
        annotation_id=annotation.id,
        trace_id=test_data["trace_id"],
        continuous_eval_id=continuous_eval.id,
        task_id=agentic_task.id,
        delay_seconds=0,
    )

    with pytest.raises(
        ValueError,
        match=f"Annotation {annotation.id} is running or has already finished executing",
    ):
        continuous_eval_queue_service._execute_job(job)

    status_code, received_annotation = client.get_annotation_by_id(annotation.id)
    assert status_code == 200
    assert received_annotation.run_status == ContinuousEvalRunStatus.ERROR.value

    delete_mock_annotation(annotation.id)

    # create a real mock annotation
    fake_continuous_eval_id = uuid.uuid4()
    annotation = create_mock_annotation(
        trace_id=test_data["trace_id"],
        annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL,
        continuous_eval_id=fake_continuous_eval_id,
        run_status=ContinuousEvalRunStatus.PENDING,
    )

    # test executing for a non-existent continuous eval
    job = ContinuousEvalJob(
        annotation_id=annotation.id,
        trace_id=test_data["trace_id"],
        continuous_eval_id=fake_continuous_eval_id,
        task_id=agentic_task.id,
        delay_seconds=0,
    )
    with pytest.raises(
        ValueError,
        match=f"Continuous eval {fake_continuous_eval_id} not found",
    ):
        continuous_eval_queue_service._execute_job(job)

    status_code, received_annotation = client.get_annotation_by_id(annotation.id)
    assert status_code == 200
    assert received_annotation.run_status == ContinuousEvalRunStatus.ERROR.value

    delete_mock_annotation(annotation.id)

    # create a real mock annotation
    fake_trace_id = "fake_trace_id"
    annotation = create_mock_annotation(
        trace_id=fake_trace_id,
        annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL,
        continuous_eval_id=continuous_eval.id,
        run_status=ContinuousEvalRunStatus.PENDING,
    )

    # test executing for a non-existent trace
    job = ContinuousEvalJob(
        annotation_id=annotation.id,
        trace_id=fake_trace_id,
        continuous_eval_id=continuous_eval.id,
        task_id=agentic_task.id,
        delay_seconds=0,
    )
    with pytest.raises(ValueError, match=f"Trace {fake_trace_id} not found"):
        continuous_eval_queue_service._execute_job(job)
    status_code, received_annotation = client.get_annotation_by_id(annotation.id)
    assert status_code == 200
    assert received_annotation.run_status == ContinuousEvalRunStatus.ERROR.value

    delete_mock_annotation(annotation.id)

    status_code, bad_continuous_eval = client.save_continuous_eval(
        task_id=agentic_task.id,
        continuous_eval_data={
            "name": "test_continuous_eval2",
            "description": "Test continuous eval description2",
            "llm_eval_name": "test_llm_eval",
            "llm_eval_version": 1,
            "transform_id": str(incorrect_transform.id),
            "transform_variable_mapping": [
                {
                    "transform_variable": "model_name",
                    "eval_variable": "model_name",
                },
            ],
        },
    )
    assert status_code == 200

    status_code = client.delete_task(agentic_task.id)
    assert status_code == 204

    shutdown_continuous_eval_queue_service()
    cleanup_model_provider(client)
    cleanup_test_data(test_data)


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
@patch(
    "services.continuous_eval.continuous_eval_queue_service.get_db_session",
    side_effect=mock_get_db_session_generator,
)
def test_continuous_eval_execution_transform_errors(
    mock_get_db_session,
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    test_data = setup_test_data()

    # Mock LLM response to return score of 1
    mock_response = MagicMock(spec=ModelResponse)
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": '{"reason": "The model name is correct.", "score": 0}',
    }
    mock_completion.return_value = mock_response
    mock_completion_cost.return_value = 0.002345

    # Initialize with 1 second delay for faster test execution
    initialize_continuous_eval_queue_service(num_workers=2)
    continuous_eval_queue_service = get_continuous_eval_queue_service()

    status_code, agentic_task = client.create_task(
        name="test_continuous_eval_execution_transform_errors",
        is_agentic=True,
    )
    assert status_code == 200

    # Configure model provider
    response = client.base_client.put(
        "/api/v1/model_providers/openai",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201

    llm_eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Test instructions {{model_name}}",
    }
    status_code, llm_eval = client.save_llm_eval(
        task_id=agentic_task.id,
        llm_eval_name="test_llm_eval",
        llm_eval_data=llm_eval_data,
    )
    assert status_code == 200

    transform_definition = {
        "variables": [
            {
                "variable_name": "model_name",
                "span_name": "api_test_span",
                "attribute_path": "attributes.llm.model_name",
            },
        ],
    }
    status_code, transform = client.create_transform(
        task_id=agentic_task.id,
        name="test_transform",
        description="Test transform description",
        definition=transform_definition,
    )
    assert status_code == 200

    transform_definition = {
        "variables": [
            {
                "variable_name": "model_name",
                "span_name": "api_test_span",
                "attribute_path": "fake_path",
            },
        ],
    }
    status_code, incorrect_transform = client.create_transform(
        task_id=agentic_task.id,
        name="incorrect_transform",
        description="Test transform description",
        definition=transform_definition,
    )
    assert status_code == 200

    status_code, continuous_eval = client.save_continuous_eval(
        task_id=agentic_task.id,
        continuous_eval_data={
            "name": "test_continuous_eval",
            "description": "Test continuous eval description",
            "llm_eval_name": "test_llm_eval",
            "llm_eval_version": 1,
            "transform_id": str(transform.id),
            "transform_variable_mapping": [
                {
                    "transform_variable": "model_name",
                    "eval_variable": "model_name",
                },
            ],
        },
    )
    assert status_code == 200

    status_code, bad_continuous_eval = client.save_continuous_eval(
        task_id=agentic_task.id,
        continuous_eval_data={
            "name": "test_continuous_eval",
            "description": "Test continuous eval description",
            "llm_eval_name": "test_llm_eval",
            "llm_eval_version": 1,
            "transform_id": str(incorrect_transform.id),
            "transform_variable_mapping": [
                {
                    "transform_variable": "model_name",
                    "eval_variable": "model_name",
                },
            ],
        },
    )
    assert status_code == 200

    # create a real mock annotation
    annotation = create_mock_annotation(
        trace_id=test_data["trace_id"],
        annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL,
        continuous_eval_id=bad_continuous_eval.id,
        run_status=ContinuousEvalRunStatus.PENDING,
    )

    # test executing for a non-existent trace variables
    job = ContinuousEvalJob(
        annotation_id=annotation.id,
        trace_id=test_data["trace_id"],
        continuous_eval_id=bad_continuous_eval.id,
        task_id=test_data["task_id"],
        delay_seconds=0,
    )
    continuous_eval_queue_service._execute_job(job)
    status_code, received_annotation = client.get_annotation_by_id(annotation.id)
    assert status_code == 200
    assert received_annotation.run_status == ContinuousEvalRunStatus.SKIPPED.value
    assert (
        received_annotation.annotation_description
        == f"Could not extract variables: model_name using transform {incorrect_transform.id} on trace {test_data['trace_id']}"
    )

    delete_mock_annotation(annotation.id)

    # test executing for a non-existent transform
    # create a continuous eval with a non-existent transform
    fake_transform_id = uuid.uuid4()
    db_session = test_data["db_session"]
    db_cont_eval = DatabaseContinuousEval(
        id=uuid.uuid4(),
        name="test_continuous_eval",
        description="Test continuous eval description",
        task_id=agentic_task.id,
        llm_eval_name="test_llm_eval",
        llm_eval_version=1,
        transform_id=fake_transform_id,
    )
    db_session.add(db_cont_eval)
    db_session.commit()
    db_session.refresh(db_cont_eval)
    db_session.close()

    annotation = create_mock_annotation(
        trace_id=test_data["trace_id"],
        annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL,
        continuous_eval_id=db_cont_eval.id,
        run_status=ContinuousEvalRunStatus.PENDING,
    )

    job = ContinuousEvalJob(
        annotation_id=annotation.id,
        trace_id=test_data["trace_id"],
        continuous_eval_id=db_cont_eval.id,
        task_id=agentic_task.id,
        delay_seconds=0,
    )
    with pytest.raises(ValueError, match=f"Transform {fake_transform_id} not found"):
        continuous_eval_queue_service._execute_job(job)
    status_code, received_annotation = client.get_annotation_by_id(annotation.id)
    assert status_code == 200
    assert received_annotation.run_status == ContinuousEvalRunStatus.ERROR.value

    delete_mock_annotation(annotation.id)

    status_code = client.delete_task(agentic_task.id)
    assert status_code == 204

    shutdown_continuous_eval_queue_service()
    cleanup_model_provider(client)
    cleanup_test_data(test_data)


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
@patch(
    "services.continuous_eval.continuous_eval_queue_service.get_db_session",
    side_effect=mock_get_db_session_generator,
)
def test_continuous_eval_execution_more_transform_vars_than_eval_vars(
    mock_get_db_session,
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    """Test continuous eval execution when the transform has more variables than the eval still succeeds."""
    test_data = setup_test_data()

    # Mock LLM response to return score of 1
    mock_response = MagicMock(spec=ModelResponse)
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": '{"reason": "The model name is correct.", "score": 1}',
    }
    mock_completion.return_value = mock_response
    mock_completion_cost.return_value = 0.002345

    # Initialize with 1 second delay for faster test execution
    initialize_continuous_eval_queue_service(num_workers=2, override_execution_delay=0)
    continuous_eval_queue_service = get_continuous_eval_queue_service()

    status_code, agentic_task = client.create_task(
        name="test_continuous_eval_execution",
        is_agentic=True,
    )
    assert status_code == 200

    # Configure model provider
    response = client.base_client.put(
        "/api/v1/model_providers/openai",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201

    llm_eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Test instructions {{model_name}}",
    }
    status_code, llm_eval = client.save_llm_eval(
        task_id=agentic_task.id,
        llm_eval_name="test_llm_eval",
        llm_eval_data=llm_eval_data,
    )
    assert status_code == 200

    transform_definition = {
        "variables": [
            {
                "variable_name": "model_name",
                "span_name": "rag-retrieval-savedQueries",
                "attribute_path": "attributes.input.value.context",
            },
            {
                "variable_name": "model_version",
                "span_name": "rag-retrieval-savedQueries",
                "attribute_path": "attributes.input.value.sqlQuery",
            },
        ],
    }
    status_code, transform = client.create_transform(
        task_id=agentic_task.id,
        name="test_transform",
        description="Test transform description",
        definition=transform_definition,
    )
    assert status_code == 200

    status_code, continuous_eval = client.save_continuous_eval(
        task_id=agentic_task.id,
        continuous_eval_data={
            "name": "test_continuous_eval",
            "description": "Test continuous eval description",
            "llm_eval_name": "test_llm_eval",
            "llm_eval_version": 1,
            "transform_id": str(transform.id),
            "transform_variable_mapping": [
                {
                    "transform_variable": "model_name",
                    "eval_variable": "model_name",
                },
            ],
        },
    )
    assert status_code == 200

    annotation = create_mock_annotation(
        trace_id=test_data["trace_id"],
        annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL,
        continuous_eval_id=continuous_eval.id,
        run_status=ContinuousEvalRunStatus.PENDING,
    )

    job = ContinuousEvalJob(
        annotation_id=annotation.id,
        trace_id=test_data["trace_id"],
        continuous_eval_id=continuous_eval.id,
        task_id=agentic_task.id,
        delay_seconds=0,
    )
    continuous_eval_queue_service._execute_job(job)

    status_code, received_annotation = client.get_annotation_by_id(annotation.id)
    assert status_code == 200
    assert received_annotation.run_status == ContinuousEvalRunStatus.PASSED.value
    assert len(received_annotation.input_variables) == 1
    assert received_annotation.input_variables[0].name == "model_name"

    delete_mock_annotation(annotation.id)

    status_code = client.delete_task(agentic_task.id)
    assert status_code == 204

    shutdown_continuous_eval_queue_service()
    cleanup_model_provider(client)
    cleanup_test_data(test_data)


@pytest.mark.unit_tests
@patch("clients.llm.llm_client.completion_cost")
@patch("clients.llm.llm_client.litellm.completion")
@patch(
    "services.continuous_eval.continuous_eval_queue_service.get_db_session",
    side_effect=mock_get_db_session_generator,
)
def test_continuous_eval_execution_less_transform_vars_than_eval_vars(
    mock_get_db_session,
    mock_completion,
    mock_completion_cost,
    client: GenaiEngineTestClientBase,
):
    """Test continuous eval execution when the transform has less variables than the eval skips the eval execution"""
    test_data = setup_test_data()

    # Mock LLM response to return score of 1
    mock_response = MagicMock(spec=ModelResponse)
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = {
        "content": '{"reason": "The model name is correct.", "score": 1}',
    }
    mock_completion.return_value = mock_response
    mock_completion_cost.return_value = 0.002345

    # Initialize with 1 second delay for faster test execution
    initialize_continuous_eval_queue_service(num_workers=2, override_execution_delay=0)
    continuous_eval_queue_service = get_continuous_eval_queue_service()

    status_code, agentic_task = client.create_task(
        name="test_continuous_eval_execution",
        is_agentic=True,
    )
    assert status_code == 200

    # Configure model provider
    response = client.base_client.put(
        "/api/v1/model_providers/openai",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201

    llm_eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Test instructions {{model_name}} {{model_version}}",
    }
    status_code, llm_eval = client.save_llm_eval(
        task_id=agentic_task.id,
        llm_eval_name="test_llm_eval",
        llm_eval_data=llm_eval_data,
    )
    assert status_code == 200

    transform_definition = {
        "variables": [
            {
                "variable_name": "model_name",
                "span_name": "rag-retrieval-savedQueries",
                "attribute_path": "attributes.input.value.context",
            },
            # keep the below to bypass the pydantic model validator
            {
                "variable_name": "model_version",
                "span_name": "rag-retrieval-savedQueries",
                "attribute_path": "attributes.input.value.sqlQuery",
            },
        ],
    }
    status_code, transform = client.create_transform(
        task_id=agentic_task.id,
        name="test_transform",
        description="Test transform description",
        definition=transform_definition,
    )
    assert status_code == 200

    status_code, continuous_eval = client.save_continuous_eval(
        task_id=agentic_task.id,
        continuous_eval_data={
            "name": "test_continuous_eval",
            "description": "Test continuous eval description",
            "llm_eval_name": "test_llm_eval",
            "llm_eval_version": 1,
            "transform_id": str(transform.id),
            "transform_variable_mapping": [
                {
                    "transform_variable": "model_name",
                    "eval_variable": "model_name",
                },
                {
                    "transform_variable": "model_version",
                    "eval_variable": "model_version",
                },
            ],
        },
    )
    assert status_code == 200
    
    # Also verify saving a continuous eval without all eval variables mapped returns a 400 error
    status_code, bad_ce = client.save_continuous_eval(
        task_id=agentic_task.id,
        continuous_eval_data={
            "name": "test_continuous_eval",
            "description": "Test continuous eval description",
            "llm_eval_name": "test_llm_eval",
            "llm_eval_version": 1,
            "transform_id": str(transform.id),
            "transform_variable_mapping": [
                {
                    "transform_variable": "model_name",
                    "eval_variable": "model_name",
                },
            ],
        },
    )
    assert status_code == 400
    
    # remove the model_version variable from the transform
    transform_definition = {
        "variables": [
            {
                "variable_name": "model_name",
                "span_name": "rag-retrieval-savedQueries",
                "attribute_path": "attributes.input.value.context",
            },
        ],
    }
    status_code, transform = client.update_transform(
        transform_id=transform.id,
        definition=transform_definition,
    )
    assert status_code == 200

    annotation = create_mock_annotation(
        trace_id=test_data["trace_id"],
        annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL,
        continuous_eval_id=continuous_eval.id,
        run_status=ContinuousEvalRunStatus.PENDING,
    )

    job = ContinuousEvalJob(
        annotation_id=annotation.id,
        trace_id=test_data["trace_id"],
        continuous_eval_id=continuous_eval.id,
        task_id=agentic_task.id,
        delay_seconds=0,
    )
    continuous_eval_queue_service._execute_job(job)

    status_code, received_annotation = client.get_annotation_by_id(annotation.id)
    assert status_code == 200
    assert received_annotation.run_status == ContinuousEvalRunStatus.SKIPPED.value

    delete_mock_annotation(annotation.id)

    status_code = client.delete_task(agentic_task.id)
    assert status_code == 204

    shutdown_continuous_eval_queue_service()
    cleanup_model_provider(client)
    cleanup_test_data(test_data)


@pytest.mark.unit_tests
@patch(
    "repositories.continuous_evals_repository.get_continuous_eval_queue_service",
)
def test_only_enabled_continuous_evals_are_enqueued(
    mock_get_queue_service,
    client: GenaiEngineTestClientBase,
):
    """Test that only enabled continuous evals are enqueued when processing root spans."""
    test_data = setup_test_data()

    # Setup mock queue service to track enqueued jobs
    mock_queue_service = MagicMock()
    mock_get_queue_service.return_value = mock_queue_service

    status_code, agentic_task = client.create_task(
        name="test_only_enabled_continuous_evals_are_enqueued",
        is_agentic=True,
    )
    assert status_code == 200

    # Configure model provider
    response = client.base_client.put(
        "/api/v1/model_providers/openai",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201

    llm_eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Test instructions {{model_name}}",
    }
    status_code, llm_eval = client.save_llm_eval(
        task_id=agentic_task.id,
        llm_eval_name="test_llm_eval",
        llm_eval_data=llm_eval_data,
    )
    assert status_code == 200

    transform_definition = {
        "variables": [
            {
                "variable_name": "model_name",
                "span_name": "rag-retrieval-savedQueries",
                "attribute_path": "attributes.input.value.context",
            },
        ],
    }
    status_code, transform = client.create_transform(
        task_id=agentic_task.id,
        name="test_transform",
        description="Test transform description",
        definition=transform_definition,
    )
    assert status_code == 200

    # Create enabled continuous eval
    status_code, enabled_continuous_eval = client.save_continuous_eval(
        task_id=agentic_task.id,
        continuous_eval_data={
            "name": "enabled_continuous_eval",
            "description": "This eval is enabled",
            "llm_eval_name": "test_llm_eval",
            "llm_eval_version": 1,
            "transform_id": str(transform.id),
            "transform_variable_mapping": [
                {
                    "transform_variable": "model_name",
                    "eval_variable": "model_name",
                },
            ],
            "enabled": True,
        },
    )
    assert status_code == 200

    # Create disabled continuous eval
    status_code, disabled_continuous_eval = client.save_continuous_eval(
        task_id=agentic_task.id,
        continuous_eval_data={
            "name": "disabled_continuous_eval",
            "description": "This eval is disabled",
            "llm_eval_name": "test_llm_eval",
            "llm_eval_version": 1,
            "transform_id": str(transform.id),
            "transform_variable_mapping": [
                {
                    "transform_variable": "model_name",
                    "eval_variable": "model_name",
                },
            ],
            "enabled": False,
        },
    )
    assert status_code == 200

    # Update the test data spans to use the correct task_id
    db_session = override_get_db_session()
    db_session.query(DatabaseSpan).filter(
        DatabaseSpan.trace_id == test_data["trace_id"]
    ).update({"task_id": agentic_task.id})
    db_session.commit()

    # Get the root spans
    root_spans = (
        db_session.query(DatabaseSpan)
        .filter(DatabaseSpan.trace_id == test_data["trace_id"])
        .filter(DatabaseSpan.parent_span_id == None)
        .all()
    )

    # Call enqueue_continuous_evals_for_root_spans
    repo = ContinuousEvalsRepository(db_session)
    repo.enqueue_continuous_evals_for_root_spans(root_spans, delay_seconds=0)

    # Verify that only one job was enqueued (for the enabled continuous eval)
    assert mock_queue_service.enqueue.call_count == 1

    # Verify the enqueued job is for the enabled continuous eval
    enqueued_job = mock_queue_service.enqueue.call_args[0][0]
    assert enqueued_job.continuous_eval_id == enabled_continuous_eval.id
    assert enqueued_job.trace_id == test_data["trace_id"]
    assert enqueued_job.task_id == agentic_task.id

    # Verify annotation was created only for enabled continuous eval
    annotations = (
        db_session.query(DatabaseAgenticAnnotation)
        .filter(DatabaseAgenticAnnotation.trace_id == test_data["trace_id"])
        .all()
    )
    assert len(annotations) == 1
    assert annotations[0].continuous_eval_id == enabled_continuous_eval.id

    # Cleanup
    status_code = client.delete_task(agentic_task.id)
    assert status_code == 204

    cleanup_model_provider(client)
    cleanup_test_data(test_data)
