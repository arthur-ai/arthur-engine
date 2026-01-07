import uuid
from datetime import datetime
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest
from arthur_common.models.enums import AgenticAnnotationType, ContinuousEvalRunStatus

from db_models.agentic_annotation_models import DatabaseAgenticAnnotation
from db_models.task_models import DatabaseTask
from db_models.telemetry_models import DatabaseSpan, DatabaseTraceMetadata
from schemas.internal_schemas import Span as InternalSpan
from schemas.internal_schemas import TraceTransform
from schemas.llm_eval_schemas import LLMEval
from services.continuous_eval.continuous_eval_queue_service import (
    ContinuousEvalQueueService,
)
from services.trace.span_normalization_service import SpanNormalizationService
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)


def create_test_transform(
    client: GenaiEngineTestClientBase,
    task_id: str,
) -> tuple[int, TraceTransform]:
    transform_definition = {
        "variables": [
            {
                "variable_name": "test_variable",
                "span_name": "test_span",
                "attribute_path": "test_attribute",
            },
        ],
    }
    return client.create_transform(
        task_id=task_id,
        name="test_transform",
        description="Test transform description",
        definition=transform_definition,
    )


def create_test_llm_eval(
    client: GenaiEngineTestClientBase,
    task_id: str,
    llm_eval_name: str = "test_llm_eval",
) -> tuple[int, LLMEval]:
    llm_eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Test instructions {{test_variable}}",
    }
    return client.save_llm_eval(
        task_id=task_id,
        llm_eval_name=llm_eval_name,
        llm_eval_data=llm_eval_data,
    )


def create_mock_annotation(
    trace_id: str,
    annotation_type: AgenticAnnotationType,
    annotation_score: Optional[int] = None,
    continuous_eval_id: Optional[str] = None,
    run_status: Optional[ContinuousEvalRunStatus] = None,
) -> tuple[int, DatabaseAgenticAnnotation]:
    db_session = override_get_db_session()
    db_annotation = DatabaseAgenticAnnotation(
        id=uuid.uuid4(),
        annotation_type=annotation_type.value,
        trace_id=trace_id,
        annotation_score=annotation_score,
        continuous_eval_id=continuous_eval_id,
        run_status=run_status.value if run_status else None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
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
def test_create_continuous_eval_success(client: GenaiEngineTestClientBase):
    """Test creating a continuous eval successfully."""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_create_continuous_eval_success",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Save an llm eval
        status_code, llm_eval = create_test_llm_eval(client, agentic_task.id)
        assert status_code == 200

        # Create a transform
        status_code, transform = create_test_transform(client, agentic_task.id)
        assert status_code == 200

        # Create a continuous eval
        status_code, continuous_eval = client.save_continuous_eval(
            task_id=agentic_task.id,
            continuous_eval_data={
                "name": "test_continuous_eval",
                "description": "Test continuous eval description",
                "llm_eval_name": llm_eval.name,
                "llm_eval_version": llm_eval.version,
                "transform_id": str(transform.id),
                "transform_variable_mapping": [
                    {
                        "transform_variable": "test_variable",
                        "eval_variable": "test_variable",
                    },
                ],
            },
        )
        assert status_code == 200
        assert continuous_eval.id is not None
        assert continuous_eval.name == "test_continuous_eval"
        assert continuous_eval.description == "Test continuous eval description"
        assert continuous_eval.task_id == agentic_task.id
        assert continuous_eval.llm_eval_name == llm_eval.name
        assert continuous_eval.llm_eval_version == llm_eval.version
        assert continuous_eval.transform_id == transform.id
        assert continuous_eval.created_at is not None
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_create_continuous_eval_allows_duplicates(client: GenaiEngineTestClientBase):
    """Test creating a continuous eval allows duplicates."""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_create_continuous_eval_allows_duplicates",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Save an llm eval
        status_code, llm_eval = create_test_llm_eval(client, agentic_task.id)
        assert status_code == 200

        # Create a transform
        status_code, transform = create_test_transform(client, agentic_task.id)
        assert status_code == 200

        # Create a continuous eval
        status_code, continuous_eval1 = client.save_continuous_eval(
            task_id=agentic_task.id,
            continuous_eval_data={
                "name": "test_continuous_eval",
                "description": "Test continuous eval description",
                "llm_eval_name": llm_eval.name,
                "llm_eval_version": llm_eval.version,
                "transform_id": str(transform.id),
                "transform_variable_mapping": [
                    {
                        "transform_variable": "test_variable",
                        "eval_variable": "test_variable",
                    },
                ],
            },
        )
        assert status_code == 200

        # Create a duplicate continuous eval
        status_code, continuous_eval2 = client.save_continuous_eval(
            task_id=agentic_task.id,
            continuous_eval_data={
                "name": "test_continuous_eval",
                "description": "Test continuous eval description",
                "llm_eval_name": llm_eval.name,
                "llm_eval_version": llm_eval.version,
                "transform_id": str(transform.id),
                "transform_variable_mapping": [
                    {
                        "transform_variable": "test_variable",
                        "eval_variable": "test_variable",
                    },
                ],
            },
        )
        assert status_code == 200

        status_code, retrieved_evals = client.list_continuous_evals(
            task_id=agentic_task.id,
            search_url="sort=asc",
        )
        assert status_code == 200
        assert len(retrieved_evals.evals) == 2

        # verify the ids are different
        assert retrieved_evals.evals[0].id != retrieved_evals.evals[1].id

        # check the first continuous eval
        assert retrieved_evals.evals[0].id == continuous_eval1.id
        assert retrieved_evals.evals[0].name == "test_continuous_eval"
        assert (
            retrieved_evals.evals[0].description == "Test continuous eval description"
        )
        assert retrieved_evals.evals[0].task_id == agentic_task.id
        assert retrieved_evals.evals[0].llm_eval_name == llm_eval.name
        assert retrieved_evals.evals[0].llm_eval_version == llm_eval.version
        assert retrieved_evals.evals[0].transform_id == transform.id
        assert retrieved_evals.evals[0].created_at is not None

        # check the duplicate has the same parameters
        assert retrieved_evals.evals[1].id == continuous_eval2.id
        assert retrieved_evals.evals[1].name == "test_continuous_eval"
        assert (
            retrieved_evals.evals[1].description == "Test continuous eval description"
        )
        assert retrieved_evals.evals[1].task_id == agentic_task.id
        assert retrieved_evals.evals[1].llm_eval_name == llm_eval.name
        assert retrieved_evals.evals[1].llm_eval_version == llm_eval.version
        assert retrieved_evals.evals[1].transform_id == transform.id
        assert retrieved_evals.evals[1].created_at is not None
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_create_continuous_eval_failures(client: GenaiEngineTestClientBase):
    """Test creating a continuous eval failures."""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_create_continuous_eval_failures",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Save an llm eval
        status_code, llm_eval = create_test_llm_eval(client, agentic_task.id)
        assert status_code == 200

        # Create a transform
        status_code, transform = create_test_transform(client, agentic_task.id)
        assert status_code == 200

        # Create a continuous eval for a non-existent task
        fake_task_id = str(uuid.uuid4())
        status_code, error = client.save_continuous_eval(
            task_id=fake_task_id,
            continuous_eval_data={
                "name": "test_continuous_eval",
                "description": "Test continuous eval description",
                "llm_eval_name": llm_eval.name,
                "llm_eval_version": llm_eval.version,
                "transform_id": str(transform.id),
                "transform_variable_mapping": [
                    {
                        "transform_variable": "test_variable",
                        "eval_variable": "test_variable",
                    },
                ],
            },
        )
        assert status_code == 404
        assert error is not None
        assert f"task {fake_task_id} not found" in error.get("detail", "").lower()

        # Create a continuous eval for a non-existent llm eval
        status_code, error = client.save_continuous_eval(
            task_id=agentic_task.id,
            continuous_eval_data={
                "name": "test_continuous_eval",
                "description": "Test continuous eval description",
                "llm_eval_name": "fake_llm_eval_name",
                "llm_eval_version": "latest",
                "transform_id": str(transform.id),
                "transform_variable_mapping": [
                    {
                        "transform_variable": "test_variable",
                        "eval_variable": "test_variable",
                    },
                ],
            },
        )
        assert status_code == 404
        assert error is not None
        assert (
            f"'fake_llm_eval_name' (version 'latest') not found for task '{agentic_task.id}'"
            in error.get("detail", "").lower()
        )
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_update_continuous_eval_success(client: GenaiEngineTestClientBase):
    """Test creating a continuous eval successfully."""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_create_continuous_eval_success",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Save an llm eval
        status_code, llm_eval = create_test_llm_eval(client, agentic_task.id)
        assert status_code == 200

        # Create a transform
        status_code, transform = create_test_transform(client, agentic_task.id)
        assert status_code == 200

        # Create a continuous eval
        status_code, continuous_eval = client.save_continuous_eval(
            task_id=agentic_task.id,
            continuous_eval_data={
                "name": "test_continuous_eval",
                "description": "Test continuous eval description",
                "llm_eval_name": llm_eval.name,
                "llm_eval_version": llm_eval.version,
                "transform_id": str(transform.id),
                "transform_variable_mapping": [
                    {
                        "transform_variable": "test_variable",
                        "eval_variable": "test_variable",
                    },
                ],
            },
        )
        assert status_code == 200

        # Update the continuous eval
        status_code, updated_continuous_eval = client.update_continuous_eval(
            continuous_eval_id=continuous_eval.id,
            continuous_eval_data={
                "name": "test_continuous_eval_updated",
                "description": "Test continuous eval description updated",
            },
        )
        assert status_code == 200
        assert updated_continuous_eval.id == continuous_eval.id
        assert updated_continuous_eval.name == "test_continuous_eval_updated"
        assert (
            updated_continuous_eval.description
            == "Test continuous eval description updated"
        )
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_update_continuous_eval_failures(client: GenaiEngineTestClientBase):
    """Test updating a continuous eval failures."""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_create_continuous_eval_success",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Save an llm eval
        status_code, llm_eval = create_test_llm_eval(client, agentic_task.id)
        assert status_code == 200

        # Create a transform
        status_code, transform = create_test_transform(client, agentic_task.id)
        assert status_code == 200

        # Update the continuous eval for non-existent continuous eval
        fake_eval_id = str(uuid.uuid4())
        status_code, error = client.update_continuous_eval(
            continuous_eval_id=fake_eval_id,
            continuous_eval_data={
                "name": "test_continuous_eval_updated",
                "description": "Test continuous eval description updated",
            },
        )
        assert status_code == 404
        assert error is not None
        assert (
            f"continuous eval {fake_eval_id} not found"
            in error.get("detail", "").lower()
        )

        # Create a continuous eval
        status_code, continuous_eval = client.save_continuous_eval(
            task_id=agentic_task.id,
            continuous_eval_data={
                "name": "test_continuous_eval",
                "description": "Test continuous eval description",
                "llm_eval_name": llm_eval.name,
                "llm_eval_version": llm_eval.version,
                "transform_id": str(transform.id),
                "transform_variable_mapping": [
                    {
                        "transform_variable": "test_variable",
                        "eval_variable": "test_variable",
                    },
                ],
            },
        )
        assert status_code == 200

        # Update the continuous eval name without version should raise an error
        status_code, error = client.update_continuous_eval(
            continuous_eval_id=continuous_eval.id,
            continuous_eval_data={
                "name": "test_continuous_eval_updated",
                "description": "Test continuous eval description updated",
                "llm_eval_name": llm_eval.name,
            },
        )
        assert status_code == 400
        assert error is not None
        assert (
            f"must specify which version of the llm eval this continuous eval should be associated with"
            in error.get("detail", "").lower()
        )
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_get_continuous_eval_by_id_success(client: GenaiEngineTestClientBase):
    """Test getting a continuous eval by id successfully."""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_get_continuous_eval_by_id_success",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Save an llm eval
        status_code, llm_eval = create_test_llm_eval(client, agentic_task.id)
        assert status_code == 200

        # Create a transform
        status_code, transform = create_test_transform(client, agentic_task.id)
        assert status_code == 200

        # Create a continuous eval
        status_code, continuous_eval = client.save_continuous_eval(
            task_id=agentic_task.id,
            continuous_eval_data={
                "name": "test_continuous_eval",
                "description": "Test continuous eval description",
                "llm_eval_name": llm_eval.name,
                "llm_eval_version": llm_eval.version,
                "transform_id": str(transform.id),
                "transform_variable_mapping": [
                    {
                        "transform_variable": "test_variable",
                        "eval_variable": "test_variable",
                    },
                ],
            },
        )
        assert status_code == 200

        status_code, retrieved_continuous_eval = client.get_continuous_eval_by_id(
            continuous_eval_id=continuous_eval.id,
        )
        assert status_code == 200
        assert retrieved_continuous_eval.id == continuous_eval.id
        assert retrieved_continuous_eval.task_id == agentic_task.id
        assert retrieved_continuous_eval.llm_eval_name == llm_eval.name
        assert retrieved_continuous_eval.llm_eval_version == llm_eval.version
        assert retrieved_continuous_eval.transform_id == transform.id
        assert retrieved_continuous_eval.created_at is not None
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_get_continuous_eval_by_id_for_non_existent_eval(
    client: GenaiEngineTestClientBase,
):
    """Test getting a continuous eval by id for a non-existent eval."""
    fake_eval_id = str(uuid.uuid4())
    status_code, error = client.get_continuous_eval_by_id(
        continuous_eval_id=fake_eval_id,
    )
    assert status_code == 404
    assert error is not None
    assert (
        f"continuous eval {fake_eval_id} not found" in error.get("detail", "").lower()
    )


@pytest.mark.unit_tests
def test_list_continuous_evals_success(client: GenaiEngineTestClientBase):
    """Test listing continuous evals successfully."""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_list_continuous_evals_success",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Save an llm eval
        status_code, llm_eval = create_test_llm_eval(client, agentic_task.id)
        assert status_code == 200

        # Create transforms
        transforms = {}
        for i in range(3):
            status_code, transform = create_test_transform(client, agentic_task.id)
            assert status_code == 200
            transforms[transform.id] = transform

        # Add the transforms to the llm eval
        continuous_evals = []
        for transform in transforms.values():
            status_code, continuous_eval = client.save_continuous_eval(
                task_id=agentic_task.id,
                continuous_eval_data={
                    "name": "test_continuous_eval",
                    "description": "Test continuous eval description",
                    "llm_eval_name": llm_eval.name,
                    "llm_eval_version": llm_eval.version,
                    "transform_id": str(transform.id),
                    "transform_variable_mapping": [
                        {
                            "transform_variable": "test_variable",
                            "eval_variable": "test_variable",
                        },
                    ],
                },
            )
            assert status_code == 200
            continuous_evals.append(continuous_eval)

        # Sort the transforms by created_at in descending order since that's what pagination defaults to
        continuous_evals = sorted(
            continuous_evals,
            key=lambda x: x.created_at,
            reverse=True,
        )
        sorted_continuous_evals = []
        for continuous_eval in continuous_evals:
            sorted_continuous_evals.append(transforms[continuous_eval.transform_id])

        # List the continuous evals
        status_code, received_continuous_evals = client.list_continuous_evals(
            task_id=agentic_task.id,
        )
        assert status_code == 200
        assert len(received_continuous_evals.evals) == len(transforms)
        assert received_continuous_evals.count == len(transforms)

        for i in range(len(transforms)):
            assert received_continuous_evals.evals[i].id == continuous_evals[i].id
            assert received_continuous_evals.evals[i].task_id == agentic_task.id
            assert received_continuous_evals.evals[i].llm_eval_name == llm_eval.name
            assert (
                received_continuous_evals.evals[i].llm_eval_version == llm_eval.version
            )
            assert (
                received_continuous_evals.evals[i].transform_id
                == sorted_continuous_evals[i].id
            )
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_list_continuous_evals_pagination(client: GenaiEngineTestClientBase):
    """Test listing continuous evals with pagination"""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_list_continuous_evals_pagination",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Save an llm eval
        status_code, llm_eval = create_test_llm_eval(client, agentic_task.id)
        assert status_code == 200

        # Create transforms
        transforms = {}
        for i in range(10):
            status_code, transform = create_test_transform(client, agentic_task.id)
            assert status_code == 200
            transforms[transform.id] = transform

        # Save the continuous evals
        continuous_evals = []
        for transform in transforms.values():
            status_code, continuous_eval = client.save_continuous_eval(
                task_id=agentic_task.id,
                continuous_eval_data={
                    "name": "test_continuous_eval",
                    "description": "Test continuous eval description",
                    "llm_eval_name": llm_eval.name,
                    "llm_eval_version": llm_eval.version,
                    "transform_id": str(transform.id),
                    "transform_variable_mapping": [
                        {
                            "transform_variable": "test_variable",
                            "eval_variable": "test_variable",
                        },
                    ],
                },
            )
            assert status_code == 200
            continuous_evals.append(continuous_eval)

        # Test sort ascending
        continuous_evals = sorted(continuous_evals, key=lambda x: x.created_at)
        status_code, received_continuous_evals = client.list_continuous_evals(
            task_id=agentic_task.id,
            search_url="sort=asc",
        )
        assert status_code == 200
        assert len(received_continuous_evals.evals) == len(transforms)
        assert received_continuous_evals.count == len(transforms)

        for i in range(len(transforms)):
            assert received_continuous_evals.evals[i].id == continuous_evals[i].id
            assert (
                received_continuous_evals.evals[i].task_id
                == continuous_evals[i].task_id
            )
            assert (
                received_continuous_evals.evals[i].llm_eval_name
                == continuous_evals[i].llm_eval_name
            )
            assert (
                received_continuous_evals.evals[i].llm_eval_version
                == continuous_evals[i].llm_eval_version
            )
            assert (
                received_continuous_evals.evals[i].transform_id
                == continuous_evals[i].transform_id
            )

        # Test page size = 5
        status_code, received_continuous_evals = client.list_continuous_evals(
            task_id=agentic_task.id,
            search_url="sort=asc&page=0&page_size=5",
        )
        assert status_code == 200
        assert len(received_continuous_evals.evals) == len(transforms) // 2
        assert received_continuous_evals.count == len(transforms) // 2
        for i in range(len(received_continuous_evals.evals) // 2):
            assert received_continuous_evals.evals[i].id == continuous_evals[i].id
            assert (
                received_continuous_evals.evals[i].task_id
                == continuous_evals[i].task_id
            )
            assert (
                received_continuous_evals.evals[i].llm_eval_name
                == continuous_evals[i].llm_eval_name
            )
            assert (
                received_continuous_evals.evals[i].llm_eval_version
                == continuous_evals[i].llm_eval_version
            )
            assert (
                received_continuous_evals.evals[i].transform_id
                == continuous_evals[i].transform_id
            )

        # Test page size = 5 and page = 2 (over the number of items)
        status_code, received_continuous_evals = client.list_continuous_evals(
            task_id=agentic_task.id,
            search_url="sort=asc&page=2&page_size=5",
        )
        assert status_code == 200
        assert len(received_continuous_evals.evals) == 0
        assert received_continuous_evals.count == 0
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_list_continuous_evals_filtering(client: GenaiEngineTestClientBase):
    """Test listing continuous evals with filtering"""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_list_continuous_evals_filtering",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Save an llm eval
        llm_evals = []
        for i in range(2):
            status_code, llm_eval = create_test_llm_eval(
                client,
                agentic_task.id,
                f"test_llm_eval_{i}",
            )
            assert status_code == 200
            llm_evals.append(llm_eval)

        # Create transforms
        transforms = []
        for i in range(4):
            status_code, transform = create_test_transform(client, agentic_task.id)
            assert status_code == 200
            transforms.append(transform)

        # Save the continuous evals
        continuous_evals = []
        for i in range(4):
            status_code, continuous_eval = client.save_continuous_eval(
                task_id=agentic_task.id,
                continuous_eval_data={
                    "name": f"test_continuous_eval_{i % 2}",
                    "description": "Test continuous eval description",
                    "llm_eval_name": llm_evals[i % 2].name,
                    "llm_eval_version": llm_evals[i % 2].version,
                    "transform_id": str(transforms[i].id),
                    "transform_variable_mapping": [
                        {
                            "transform_variable": "test_variable",
                            "eval_variable": "test_variable",
                        },
                    ],
                },
            )
            assert status_code == 200
            continuous_evals.append(continuous_eval)

        # Test filtering by name
        status_code, received_continuous_evals = client.list_continuous_evals(
            task_id=agentic_task.id,
            search_url="name=test_continuous_eval_0",
        )
        assert status_code == 200
        assert len(received_continuous_evals.evals) == len(transforms) // 2
        assert received_continuous_evals.count == len(transforms) // 2

        # Test filtering by llm eval name
        status_code, received_continuous_evals = client.list_continuous_evals(
            task_id=agentic_task.id,
            search_url="llm_eval_name=test_llm_eval_0",
        )
        assert status_code == 200
        assert len(received_continuous_evals.evals) == len(transforms) // 2
        assert received_continuous_evals.count == len(transforms) // 2

        continuous_evals = sorted(continuous_evals, key=lambda x: x.created_at)

        # Test filtering by created after
        status_code, received_continuous_evals = client.list_continuous_evals(
            task_id=agentic_task.id,
            search_url=f"created_after={continuous_evals[-1].created_at.isoformat()}",
        )
        assert status_code == 200
        assert len(received_continuous_evals.evals) == 1
        assert received_continuous_evals.count == 1

        # Test filtering by created before
        status_code, received_continuous_evals = client.list_continuous_evals(
            task_id=agentic_task.id,
            search_url=f"created_before={continuous_evals[-1].created_at.isoformat()}",
        )
        assert status_code == 200
        assert len(received_continuous_evals.evals) == 3
        assert received_continuous_evals.count == 3
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_delete_continuous_eval_success(client: GenaiEngineTestClientBase):
    """Test deleting a continuous eval successfully."""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_delete_continuous_eval_success",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Save an llm eval
        status_code, llm_eval = create_test_llm_eval(client, agentic_task.id)
        assert status_code == 200

        # Create a transform
        status_code, transform = create_test_transform(client, agentic_task.id)
        assert status_code == 200

        # Save the continuous eval
        status_code, continuous_eval = client.save_continuous_eval(
            task_id=agentic_task.id,
            continuous_eval_data={
                "name": "test_continuous_eval",
                "description": "Test continuous eval description",
                "llm_eval_name": llm_eval.name,
                "llm_eval_version": llm_eval.version,
                "transform_id": str(transform.id),
                "transform_variable_mapping": [
                    {
                        "transform_variable": "test_variable",
                        "eval_variable": "test_variable",
                    },
                ],
            },
        )
        assert status_code == 200

        # Get the transform from the llm eval
        status_code, retrieved_continuous_eval = client.get_continuous_eval_by_id(
            continuous_eval_id=continuous_eval.id,
        )
        assert status_code == 200
        assert retrieved_continuous_eval.transform_id == transform.id

        # Delete the continuous eval
        status_code, _ = client.delete_continuous_eval(
            continuous_eval_id=continuous_eval.id,
        )
        assert status_code == 204

        # Verify the transform was removed
        status_code, error = client.get_continuous_eval_by_id(
            continuous_eval_id=continuous_eval.id,
        )
        assert status_code == 404
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_delete_continuous_eval_failures(client: GenaiEngineTestClientBase):
    """Test deleting a continuous eval failures."""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_delete_continuous_eval_failures",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Save an llm eval
        status_code, llm_eval = create_test_llm_eval(client, agentic_task.id)
        assert status_code == 200

        # Create a transform
        status_code, transform = create_test_transform(client, agentic_task.id)
        assert status_code == 200

        # Remove a transform from a non-existent task
        fake_continuous_eval_id = str(uuid.uuid4())
        status_code, error = client.delete_continuous_eval(
            continuous_eval_id=fake_continuous_eval_id,
        )
        assert status_code == 404
        assert error is not None
        assert (
            f"continuous eval {fake_continuous_eval_id} not found"
            in error.get("detail", "").lower()
        )
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_list_continuous_eval_run_results_pagination(client: GenaiEngineTestClientBase):
    """Test listing continuous eval run results with pagination"""

    test_data = setup_test_data()
    task_id = test_data["task_id"]
    trace_id = test_data["trace_id"]

    # Save an llm eval
    status_code, llm_eval = create_test_llm_eval(client, task_id)
    assert status_code == 200

    # Create transforms
    status_code, transform = create_test_transform(client, task_id)
    assert status_code == 200

    # Save a continuous eval
    status_code, continuous_eval = client.save_continuous_eval(
        task_id=task_id,
        continuous_eval_data={
            "name": "test_continuous_eval",
            "description": "Test continuous eval description",
            "llm_eval_name": llm_eval.name,
            "llm_eval_version": llm_eval.version,
            "transform_id": str(transform.id),
            "transform_variable_mapping": [
                {
                    "transform_variable": "test_variable",
                    "eval_variable": "test_variable",
                },
            ],
        },
    )

    # create mock annotations
    annotation_1 = create_mock_annotation(
        trace_id=trace_id,
        annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL,
        continuous_eval_id=continuous_eval.id,
        run_status=ContinuousEvalRunStatus.PASSED,
    )
    annotation_2 = create_mock_annotation(
        trace_id=trace_id,
        annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL,
        continuous_eval_id=continuous_eval.id,
        run_status=ContinuousEvalRunStatus.FAILED,
    )
    annotation_3 = create_mock_annotation(
        trace_id=trace_id,
        annotation_type=AgenticAnnotationType.HUMAN,
        annotation_score=1,
    )
    annotations = [annotation_1, annotation_2, annotation_3]

    try:
        continuous_eval_annotations = [annotation_1, annotation_2]

        # Test sort ascending
        continuous_eval_annotations = sorted(
            continuous_eval_annotations,
            key=lambda x: x.created_at,
        )
        status_code, received_run_results = client.list_continuous_eval_run_results(
            task_id=task_id,
            search_url="sort=asc",
        )
        assert status_code == 200
        assert len(received_run_results.annotations) == len(continuous_eval_annotations)
        assert received_run_results.count == len(continuous_eval_annotations)

        for i in range(len(received_run_results.annotations)):
            assert received_run_results.annotations[i].id == str(
                continuous_eval_annotations[i].id,
            )
            assert received_run_results.annotations[i].trace_id == str(
                continuous_eval_annotations[i].trace_id,
            )
            assert received_run_results.annotations[i].continuous_eval_id == str(
                continuous_eval_annotations[i].continuous_eval_id,
            )
            assert (
                received_run_results.annotations[i].run_status
                == continuous_eval_annotations[i].run_status
            )
            assert (
                received_run_results.annotations[i].annotation_type
                == continuous_eval_annotations[i].annotation_type
            )

        # Test page size = 1
        status_code, received_run_results = client.list_continuous_eval_run_results(
            task_id=task_id,
            search_url="sort=asc&page=0&page_size=1",
        )
        assert status_code == 200
        assert (
            len(received_run_results.annotations)
            == len(continuous_eval_annotations) // 2
        )
        assert received_run_results.count == len(continuous_eval_annotations) // 2
        for i in range(len(received_run_results.annotations) // 2):
            assert received_run_results.annotations[i].id == str(
                continuous_eval_annotations[i].id,
            )
            assert received_run_results.annotations[i].trace_id == str(
                continuous_eval_annotations[i].trace_id,
            )
            assert received_run_results.annotations[i].continuous_eval_id == str(
                continuous_eval_annotations[i].continuous_eval_id,
            )
            assert (
                received_run_results.annotations[i].run_status
                == continuous_eval_annotations[i].run_status
            )
            assert (
                received_run_results.annotations[i].annotation_type
                == continuous_eval_annotations[i].annotation_type
            )

        # Test page size = 1 and page = 2 (over the number of items)
        status_code, received_run_results = client.list_continuous_eval_run_results(
            task_id=task_id,
            search_url="sort=asc&page=2&page_size=1",
        )
        assert status_code == 200
        assert len(received_run_results.annotations) == 0
        assert received_run_results.count == 0
    finally:
        client.delete_transform(transform.id)
        client.delete_llm_eval(task_id, llm_eval.name)
        client.delete_continuous_eval(continuous_eval.id)
        for annotation in annotations:
            delete_mock_annotation(annotation.id)
        cleanup_test_data(test_data)


@pytest.mark.unit_tests
def test_list_continuous_eval_run_results_filtering(client: GenaiEngineTestClientBase):
    """Test listing continuous evals with filtering"""

    test_data = setup_test_data()
    task_id = test_data["task_id"]
    trace_id = test_data["trace_id"]

    # Save an llm eval
    status_code, llm_eval = create_test_llm_eval(client, task_id)
    assert status_code == 200

    # Create transforms
    status_code, transform = create_test_transform(client, task_id)
    assert status_code == 200

    # Save a continuous eval
    status_code, continuous_eval = client.save_continuous_eval(
        task_id=task_id,
        continuous_eval_data={
            "name": "test_continuous_eval",
            "description": "Test continuous eval description",
            "llm_eval_name": llm_eval.name,
            "llm_eval_version": llm_eval.version,
            "transform_id": str(transform.id),
            "transform_variable_mapping": [
                {
                    "transform_variable": "test_variable",
                    "eval_variable": "test_variable",
                },
            ],
        },
    )

    # Save a second continuous eval
    status_code, continuous_eval_2 = client.save_continuous_eval(
        task_id=task_id,
        continuous_eval_data={
            "name": "test_continuous_eval_2",
            "description": "Test continuous eval description",
            "llm_eval_name": llm_eval.name,
            "llm_eval_version": llm_eval.version,
            "transform_id": str(transform.id),
        },
    )

    # create mock annotations
    annotation_1 = create_mock_annotation(
        trace_id=trace_id,
        annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL,
        annotation_score=1,
        continuous_eval_id=continuous_eval.id,
        run_status=ContinuousEvalRunStatus.PASSED,
    )
    annotation_2 = create_mock_annotation(
        trace_id=trace_id,
        annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL,
        annotation_score=0,
        continuous_eval_id=continuous_eval.id,
        run_status=ContinuousEvalRunStatus.FAILED,
    )
    annotation_3 = create_mock_annotation(
        trace_id=trace_id,
        annotation_type=AgenticAnnotationType.HUMAN,
        annotation_score=1,
    )
    annotation_4 = create_mock_annotation(
        trace_id=trace_id,
        annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL,
        annotation_score=0,
        continuous_eval_id=continuous_eval_2.id,
        run_status=ContinuousEvalRunStatus.FAILED,
    )
    annotations = [annotation_1, annotation_2, annotation_3, annotation_4]

    try:
        # Test filtering by annotation id
        status_code, received_run_results = client.list_continuous_eval_run_results(
            task_id=task_id,
            search_url=f"id={str(annotation_1.id)}",
        )
        assert status_code == 200
        assert len(received_run_results.annotations) == 1
        assert received_run_results.count == 1

        # Test filtering by trace id
        status_code, received_run_results = client.list_continuous_eval_run_results(
            task_id=task_id,
            search_url=f"trace_id={trace_id}",
        )
        assert status_code == 200
        assert len(received_run_results.annotations) == 3
        assert received_run_results.count == 3

        # Test filtering by continuous eval id
        status_code, received_run_results = client.list_continuous_eval_run_results(
            task_id=task_id,
            search_url=f"continuous_eval_id={continuous_eval.id}",
        )
        assert status_code == 200
        assert len(received_run_results.annotations) == 2
        assert received_run_results.count == 2

        status_code, received_run_results = client.list_continuous_eval_run_results(
            task_id=task_id,
            search_url=f"continuous_eval_id={continuous_eval_2.id}",
        )
        assert status_code == 200
        assert len(received_run_results.annotations) == 1
        assert received_run_results.count == 1

        # Test filtering by annotation score
        status_code, received_run_results = client.list_continuous_eval_run_results(
            task_id=task_id,
            search_url=f"annotation_score=1",
        )
        assert status_code == 200
        assert len(received_run_results.annotations) == 1
        assert received_run_results.count == 1

        # Test filtering by run status
        status_code, received_run_results = client.list_continuous_eval_run_results(
            task_id=task_id,
            search_url=f"run_status=passed",
        )
        assert status_code == 200
        assert len(received_run_results.annotations) == 1
        assert received_run_results.count == 1

        # Test filtering by run status
        status_code, received_run_results = client.list_continuous_eval_run_results(
            task_id=task_id,
            search_url=f"run_status=failed",
        )
        assert status_code == 200
        assert len(received_run_results.annotations) == 2
        assert received_run_results.count == 2

        continuous_eval_annotations = [annotation_1, annotation_2, annotation_4]
        continuous_eval_annotations = sorted(
            continuous_eval_annotations,
            key=lambda x: x.created_at,
        )
        # Test filtering by created after
        status_code, received_run_results = client.list_continuous_eval_run_results(
            task_id=task_id,
            search_url=f"created_after={continuous_eval_annotations[-1].created_at.isoformat()}",
        )
        assert status_code == 200
        assert len(received_run_results.annotations) == 1
        assert received_run_results.count == 1

        # Test filtering by created before
        status_code, received_run_results = client.list_continuous_eval_run_results(
            task_id=task_id,
            search_url=f"created_before={continuous_eval_annotations[1].created_at.isoformat()}",
        )
        assert status_code == 200
        assert len(received_run_results.annotations) == 1
        assert received_run_results.count == 1
    finally:
        client.delete_transform(transform.id)
        client.delete_llm_eval(task_id, llm_eval.name)
        client.delete_continuous_eval(continuous_eval.id)
        client.delete_continuous_eval(continuous_eval_2.id)
        for annotation in annotations:
            delete_mock_annotation(annotation.id)
        cleanup_test_data(test_data)


@pytest.mark.unit_tests
def test_list_continuous_eval_run_results_value_errors(
    client: GenaiEngineTestClientBase,
):
    """Test listing continuous eval run results returns 400 for ValueError"""
    test_data = setup_test_data()
    task_id = test_data["task_id"]

    try:
        status_code, error = client.list_continuous_eval_run_results(
            task_id=task_id,
            search_url="id=invalid_uuid",
        )
        assert status_code == 400
        assert error is not None
        assert "invalid uuid format for parameter 'id': invalid_uuid" in error.get("detail", "").lower()

        status_code, error = client.list_continuous_eval_run_results(
            task_id=task_id,
            search_url="continuous_eval_id=invalid_uuid",
        )
        assert status_code == 400
        assert error is not None
        assert "invalid uuid format for parameter 'continuous_eval_id': invalid_uuid" in error.get("detail", "").lower()
    finally:
        cleanup_test_data(test_data)


@pytest.mark.unit_tests
@patch("repositories.continuous_evals_repository.get_continuous_eval_queue_service")
def test_rerun_continuous_eval_success(
    mock_get_continuous_eval_queue_service,
    client: GenaiEngineTestClientBase,
):
    """Test rerunning a continuous eval successfully"""
    mock_get_continuous_eval_queue_service.return_value = MagicMock(
        spec=ContinuousEvalQueueService,
    )

    test_data = setup_test_data()
    task_id = test_data["task_id"]
    trace_id = test_data["trace_id"]

    # Save an llm eval
    status_code, llm_eval = create_test_llm_eval(client, task_id)
    assert status_code == 200

    # Create transforms
    status_code, transform = create_test_transform(client, task_id)
    assert status_code == 200

    # Save a continuous eval
    status_code, continuous_eval = client.save_continuous_eval(
        task_id=task_id,
        continuous_eval_data={
            "name": "test_continuous_eval",
            "description": "Test continuous eval description",
            "llm_eval_name": llm_eval.name,
            "llm_eval_version": llm_eval.version,
            "transform_id": str(transform.id),
            "transform_variable_mapping": [
                {
                    "transform_variable": "test_variable",
                    "eval_variable": "test_variable",
                },
            ],
        },
    )

    # create mock annotations
    annotation = create_mock_annotation(
        trace_id=trace_id,
        annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL,
        annotation_score=0,
        continuous_eval_id=continuous_eval.id,
        run_status=ContinuousEvalRunStatus.FAILED,
    )

    try:
        status_code, rerun_response = client.rerun_continuous_eval(annotation.id)
        assert status_code == 200
        assert rerun_response.run_id == annotation.id
        assert rerun_response.trace_id == trace_id
    finally:
        client.delete_transform(transform.id)
        client.delete_llm_eval(task_id, llm_eval.name)
        client.delete_continuous_eval(continuous_eval.id)
        delete_mock_annotation(annotation.id)
        cleanup_test_data(test_data)


@pytest.mark.unit_tests
@patch("repositories.continuous_evals_repository.get_continuous_eval_queue_service")
def test_rerun_continuous_eval_failures(
    mock_get_continuous_eval_queue_service,
    client: GenaiEngineTestClientBase,
):
    """Test rerunning a continuous eval failures"""
    mock_get_continuous_eval_queue_service.return_value = MagicMock(
        spec=ContinuousEvalQueueService,
    )

    test_data = setup_test_data()
    task_id = test_data["task_id"]
    trace_id = test_data["trace_id"]

    # Save an llm eval
    status_code, llm_eval = create_test_llm_eval(client, task_id)
    assert status_code == 200

    # Create transforms
    status_code, transform = create_test_transform(client, task_id)
    assert status_code == 200

    # Save a continuous eval
    status_code, continuous_eval = client.save_continuous_eval(
        task_id=task_id,
        continuous_eval_data={
            "name": "test_continuous_eval",
            "description": "Test continuous eval description",
            "llm_eval_name": llm_eval.name,
            "llm_eval_version": llm_eval.version,
            "transform_id": str(transform.id),
            "transform_variable_mapping": [
                {
                    "transform_variable": "test_variable",
                    "eval_variable": "test_variable",
                },
            ],
        },
    )

    # create mock annotations
    annotation = create_mock_annotation(
        trace_id=trace_id,
        annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL,
        annotation_score=0,
        continuous_eval_id=continuous_eval.id,
        run_status=ContinuousEvalRunStatus.FAILED,
    )

    human_annotation = create_mock_annotation(
        trace_id=trace_id,
        annotation_type=AgenticAnnotationType.HUMAN,
        annotation_score=1,
    )

    try:
        # try to rerun the continuous eval for a fake annotation id
        fake_run_id = uuid.uuid4()
        status_code, error = client.rerun_continuous_eval(str(fake_run_id))
        assert status_code == 404
        assert f"run {fake_run_id} not found." in error.get("detail", "").lower()

        # try to rerun for a non-continuous eval annotation
        status_code, error = client.rerun_continuous_eval(human_annotation.id)
        assert status_code == 400
        assert "run is not a continuous eval." in error.get("detail", "").lower()

        # try to rerun with queue service not available
        mock_get_continuous_eval_queue_service.return_value = None
        status_code, error = client.rerun_continuous_eval(annotation.id)
        assert status_code == 503
        assert (
            "continuous eval queue service is not available."
            in error.get("detail", "").lower()
        )
    finally:
        client.delete_transform(transform.id)
        client.delete_llm_eval(task_id, llm_eval.name)
        client.delete_continuous_eval(continuous_eval.id)
        delete_mock_annotation(annotation.id)
        delete_mock_annotation(human_annotation.id)
        cleanup_test_data(test_data)


def test_get_continuous_eval_variables_and_mappings_success(
    client: GenaiEngineTestClientBase,
):
    """Test getting continuous eval variables and mappings successfully"""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_get_continuous_eval_variables_and_mappings_success",
        is_agentic=True,
    )
    assert status_code == 200

    task_id = agentic_task.id

    # Save an llm eval
    status_code, llm_eval = create_test_llm_eval(client, task_id)
    assert status_code == 200

    # Create a transform
    status_code, transform = create_test_transform(client, task_id)
    assert status_code == 200

    try:
        # get the continuous eval variables and mappings
        status_code, continuous_eval_variables_and_mappings = (
            client.get_continuous_eval_variables_and_mappings(
                task_id=task_id,
                transform_id=transform.id,
                eval_name=llm_eval.name,
                eval_version=str(llm_eval.version),
            )
        )
        assert status_code == 200
        assert continuous_eval_variables_and_mappings.matching_variables == [
            "test_variable",
        ]
        assert continuous_eval_variables_and_mappings.transform_variables == [
            "test_variable",
        ]
        assert continuous_eval_variables_and_mappings.eval_variables == [
            "test_variable",
        ]
    finally:
        client.delete_llm_eval(task_id, llm_eval.name)
        client.delete_transform(transform.id)
        client.delete_task(agentic_task.id)


def test_get_continuous_eval_variables_and_mappings_no_matching_variables(
    client: GenaiEngineTestClientBase,
):
    """Test getting continuous eval variables and mappings with no matching variables"""
    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_get_continuous_eval_variables_and_mappings_no_matching_variables",
        is_agentic=True,
    )
    assert status_code == 200

    task_id = agentic_task.id

    # Save an llm eval
    status_code, llm_eval = create_test_llm_eval(client, task_id)
    assert status_code == 200

    # Create a transform
    status_code, transform = client.create_transform(
        task_id=task_id,
        name="test_transform",
        description="Test transform description",
        definition={
            "variables": [
                {
                    "variable_name": "test_variable2",
                    "span_name": "test_span",
                    "attribute_path": "test_attribute",
                },
            ],
        },
    )
    assert status_code == 200

    try:
        # get the continuous eval variables and mappings
        status_code, continuous_eval_variables_and_mappings = (
            client.get_continuous_eval_variables_and_mappings(
                task_id=task_id,
                transform_id=transform.id,
                eval_name=llm_eval.name,
                eval_version=str(llm_eval.version),
            )
        )
        assert status_code == 200
        assert continuous_eval_variables_and_mappings.matching_variables == []
        assert continuous_eval_variables_and_mappings.transform_variables == [
            "test_variable2",
        ]
        assert continuous_eval_variables_and_mappings.eval_variables == [
            "test_variable",
        ]
    finally:
        client.delete_llm_eval(task_id, llm_eval.name)
        client.delete_transform(transform.id)
        client.delete_task(agentic_task.id)


def test_get_continuous_eval_variables_and_mappings_missing_params(
    client: GenaiEngineTestClientBase,
):
    """Test getting continuous eval variables and mappings with missing params"""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_get_continuous_eval_variables_and_mappings_missing_params",
        is_agentic=True,
    )
    assert status_code == 200

    task_id = agentic_task.id

    # Save an llm eval
    status_code, llm_eval = create_test_llm_eval(client, task_id)
    assert status_code == 200

    # Create a transform
    status_code, transform = create_test_transform(client, task_id)
    assert status_code == 200

    try:
        # get the continuous eval variables and mappings with a fake transform id
        fake_transform_id = uuid.uuid4()
        status_code, response = client.get_continuous_eval_variables_and_mappings(
            task_id=task_id,
            transform_id=fake_transform_id,
            eval_name=llm_eval.name,
            eval_version=str(llm_eval.version),
        )
        assert status_code == 404
        assert (
            f"transform {fake_transform_id} not found"
            in response.get("detail", "").lower()
        )

        # get the continuous eval variables and mappings with a fake eval name
        status_code, response = client.get_continuous_eval_variables_and_mappings(
            task_id=task_id,
            transform_id=transform.id,
            eval_name="fake_llm_eval_name",
            eval_version=str(llm_eval.version),
        )
        assert status_code == 404
        assert (
            f"'fake_llm_eval_name' (version '{llm_eval.version}') not found for task '{task_id}'"
            in response.get("detail", "").lower()
        )

        # get the continuous eval variables and mappings with a non-existent eval version
        status_code, response = client.get_continuous_eval_variables_and_mappings(
            task_id=task_id,
            transform_id=transform.id,
            eval_name=llm_eval.name,
            eval_version="999999",
        )
        assert status_code == 404
        assert (
            f"'{llm_eval.name}' (version '999999') not found for task '{task_id}'"
            in response.get("detail", "").lower()
        )
    finally:
        client.delete_llm_eval(task_id, llm_eval.name)
        client.delete_transform(transform.id)
        client.delete_task(agentic_task.id)
