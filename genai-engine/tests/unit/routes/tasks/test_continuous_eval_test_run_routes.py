import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from arthur_common.models.enums import AgenticAnnotationType, ContinuousEvalRunStatus

from db_models.agentic_annotation_models import DatabaseAgenticAnnotation
from db_models.continuous_eval_test_run_models import DatabaseContinuousEvalTestRun
from db_models.task_models import DatabaseTask
from db_models.telemetry_models import DatabaseSpan, DatabaseTraceMetadata
from schemas.enums import TestRunStatus
from schemas.internal_schemas import Span as InternalSpan
from services.continuous_eval.continuous_eval_queue_service import (
    ContinuousEvalQueueService,
)
from services.trace.span_normalization_service import SpanNormalizationService
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)

MOCK_QUEUE_PATH = "repositories.continuous_eval_test_run_repository.get_continuous_eval_queue_service"


def create_test_transform(client, task_id):
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


def create_test_llm_eval(client, task_id, llm_eval_name="test_llm_eval"):
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


def create_test_continuous_eval(client, task_id, llm_eval, transform):
    return client.save_continuous_eval(
        task_id=task_id,
        continuous_eval_data={
            "name": "test_continuous_eval",
            "description": "Test continuous eval",
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


def setup_traces(task_id, count=3):
    """Create trace metadata and root spans for testing."""
    db_session = override_get_db_session()
    span_normalizer = SpanNormalizationService()
    trace_ids = []
    base_time = datetime.now()

    for i in range(count):
        trace_id = str(uuid.uuid4())
        trace_ids.append(trace_id)

        span_raw_data = span_normalizer.normalize_span_to_nested_dict(
            {
                "kind": "SPAN_KIND_INTERNAL",
                "name": "test_span",
                "spanId": f"span_{uuid.uuid4()}",
                "traceId": trace_id,
                "attributes": {
                    "openinference.span.kind": "LLM",
                },
            },
        )
        span_raw_data["arthur_span_version"] = "arthur_span_v1"

        span = InternalSpan(
            id=str(uuid.uuid4()),
            trace_id=trace_id,
            span_id=span_raw_data["spanId"],
            task_id=task_id,
            parent_span_id=None,
            span_kind="LLM",
            start_time=base_time,
            end_time=base_time,
            session_id=None,
            user_id=None,
            raw_data=span_raw_data,
            created_at=base_time,
            updated_at=base_time,
        )

        db_span = DatabaseSpan(
            id=span.id,
            trace_id=trace_id,
            span_id=span.span_id,
            span_name="test_span",
            task_id=task_id,
            parent_span_id=None,
            span_kind="LLM",
            start_time=base_time,
            end_time=base_time,
            status_code="Ok",
            raw_data=span.raw_data,
            created_at=base_time,
            updated_at=base_time,
        )
        db_session.add(db_span)

        trace_metadata = DatabaseTraceMetadata(
            task_id=task_id,
            trace_id=trace_id,
            span_count=1,
            start_time=base_time,
            end_time=base_time,
            created_at=base_time,
            updated_at=base_time,
        )
        db_session.add(trace_metadata)

    db_session.commit()
    return trace_ids


def cleanup_traces(trace_ids):
    db_session = override_get_db_session()
    for trace_id in trace_ids:
        db_session.query(DatabaseAgenticAnnotation).filter(
            DatabaseAgenticAnnotation.trace_id == trace_id,
        ).delete()
        db_session.query(DatabaseSpan).filter(
            DatabaseSpan.trace_id == trace_id,
        ).delete()
        db_session.query(DatabaseTraceMetadata).filter(
            DatabaseTraceMetadata.trace_id == trace_id,
        ).delete()
    db_session.commit()


def cleanup_test_run(test_run_id):
    db_session = override_get_db_session()
    run_id = uuid.UUID(test_run_id) if isinstance(test_run_id, str) else test_run_id
    db_session.query(DatabaseAgenticAnnotation).filter(
        DatabaseAgenticAnnotation.test_run_id == run_id,
    ).delete()
    db_session.query(DatabaseContinuousEvalTestRun).filter(
        DatabaseContinuousEvalTestRun.id == run_id,
    ).delete()
    db_session.commit()


# ============================================================================
# Create Test Run
# ============================================================================


@pytest.mark.unit_tests
@patch(MOCK_QUEUE_PATH)
def test_create_test_run_success(mock_queue, client: GenaiEngineTestClientBase):
    mock_queue.return_value = MagicMock(spec=ContinuousEvalQueueService)
    """Test creating a test run successfully."""
    status_code, task = client.create_task(
        name="test_create_test_run_success",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        status_code, llm_eval = create_test_llm_eval(client, task.id)
        assert status_code == 200

        status_code, transform = create_test_transform(client, task.id)
        assert status_code == 200

        status_code, continuous_eval = create_test_continuous_eval(
            client, task.id, llm_eval, transform,
        )
        assert status_code == 200

        trace_ids = setup_traces(task.id, count=3)

        try:
            status_code, test_run = client.create_test_run(
                eval_id=str(continuous_eval.id),
                trace_ids=trace_ids,
            )
            assert status_code == 200
            assert test_run.id is not None
            assert test_run.continuous_eval_id == continuous_eval.id
            assert test_run.task_id == task.id
            assert test_run.status == TestRunStatus.RUNNING
            assert test_run.total_count == 3
            assert test_run.completed_count == 0
            assert test_run.passed_count == 0
            assert test_run.failed_count == 0
            assert test_run.error_count == 0
            assert test_run.skipped_count == 0

            # Verify annotations were created
            status_code, results = client.get_test_run_results(str(test_run.id))
            assert status_code == 200
            assert results.count == 3
            for annotation in results.annotations:
                assert annotation.run_status == ContinuousEvalRunStatus.PENDING
                assert annotation.trace_id in trace_ids

            cleanup_test_run(str(test_run.id))
        finally:
            cleanup_traces(trace_ids)
    finally:
        client.delete_task(task.id)


@pytest.mark.unit_tests
@patch(MOCK_QUEUE_PATH)
def test_create_test_run_deduplicates_trace_ids(mock_queue, client: GenaiEngineTestClientBase):
    mock_queue.return_value = MagicMock(spec=ContinuousEvalQueueService)
    """Test that duplicate trace IDs are deduplicated."""
    status_code, task = client.create_task(
        name="test_create_test_run_dedup",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        status_code, llm_eval = create_test_llm_eval(client, task.id)
        assert status_code == 200

        status_code, transform = create_test_transform(client, task.id)
        assert status_code == 200

        status_code, continuous_eval = create_test_continuous_eval(
            client, task.id, llm_eval, transform,
        )
        assert status_code == 200

        trace_ids = setup_traces(task.id, count=2)
        duplicated_ids = trace_ids + [trace_ids[0]]  # 3 IDs, but only 2 unique

        try:
            status_code, test_run = client.create_test_run(
                eval_id=str(continuous_eval.id),
                trace_ids=duplicated_ids,
            )
            assert status_code == 200
            assert test_run.total_count == 2

            cleanup_test_run(str(test_run.id))
        finally:
            cleanup_traces(trace_ids)
    finally:
        client.delete_task(task.id)


@pytest.mark.unit_tests
@patch(MOCK_QUEUE_PATH)
def test_create_test_run_invalid_trace_ids(mock_queue, client: GenaiEngineTestClientBase):
    mock_queue.return_value = MagicMock(spec=ContinuousEvalQueueService)
    """Test that creating a test run with nonexistent trace IDs returns 404."""
    status_code, task = client.create_task(
        name="test_create_test_run_invalid_traces",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        status_code, llm_eval = create_test_llm_eval(client, task.id)
        assert status_code == 200

        status_code, transform = create_test_transform(client, task.id)
        assert status_code == 200

        status_code, continuous_eval = create_test_continuous_eval(
            client, task.id, llm_eval, transform,
        )
        assert status_code == 200

        status_code, response = client.create_test_run(
            eval_id=str(continuous_eval.id),
            trace_ids=["nonexistent_trace_1", "nonexistent_trace_2"],
        )
        assert status_code == 404
    finally:
        client.delete_task(task.id)


@pytest.mark.unit_tests
@patch(MOCK_QUEUE_PATH)
def test_create_test_run_invalid_eval_id(mock_queue, client: GenaiEngineTestClientBase):
    mock_queue.return_value = MagicMock(spec=ContinuousEvalQueueService)
    """Test that creating a test run with a nonexistent eval ID returns 404."""
    status_code, task = client.create_task(
        name="test_create_test_run_invalid_eval",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        trace_ids = setup_traces(task.id, count=1)
        try:
            status_code, response = client.create_test_run(
                eval_id=str(uuid.uuid4()),
                trace_ids=trace_ids,
            )
            assert status_code == 404
        finally:
            cleanup_traces(trace_ids)
    finally:
        client.delete_task(task.id)


@pytest.mark.unit_tests
@patch(MOCK_QUEUE_PATH)
def test_create_test_run_empty_trace_ids(mock_queue, client: GenaiEngineTestClientBase):
    mock_queue.return_value = MagicMock(spec=ContinuousEvalQueueService)
    """Test that creating a test run with empty trace IDs returns 400."""
    status_code, task = client.create_task(
        name="test_create_test_run_empty",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        status_code, llm_eval = create_test_llm_eval(client, task.id)
        assert status_code == 200

        status_code, transform = create_test_transform(client, task.id)
        assert status_code == 200

        status_code, continuous_eval = create_test_continuous_eval(
            client, task.id, llm_eval, transform,
        )
        assert status_code == 200

        status_code, response = client.create_test_run(
            eval_id=str(continuous_eval.id),
            trace_ids=[],
        )
        assert status_code == 400
    finally:
        client.delete_task(task.id)


# ============================================================================
# Get / List Test Runs
# ============================================================================


@pytest.mark.unit_tests
@patch(MOCK_QUEUE_PATH)
def test_get_test_run(mock_queue, client: GenaiEngineTestClientBase):
    mock_queue.return_value = MagicMock(spec=ContinuousEvalQueueService)
    """Test getting a test run by ID."""
    status_code, task = client.create_task(
        name="test_get_test_run",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        status_code, llm_eval = create_test_llm_eval(client, task.id)
        assert status_code == 200

        status_code, transform = create_test_transform(client, task.id)
        assert status_code == 200

        status_code, continuous_eval = create_test_continuous_eval(
            client, task.id, llm_eval, transform,
        )
        assert status_code == 200

        trace_ids = setup_traces(task.id, count=2)

        try:
            status_code, test_run = client.create_test_run(
                eval_id=str(continuous_eval.id),
                trace_ids=trace_ids,
            )
            assert status_code == 200

            # Get the test run
            status_code, fetched = client.get_test_run(str(test_run.id))
            assert status_code == 200
            assert fetched.id == test_run.id
            assert fetched.total_count == 2
            assert fetched.status == TestRunStatus.RUNNING

            cleanup_test_run(str(test_run.id))
        finally:
            cleanup_traces(trace_ids)
    finally:
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_get_test_run_not_found(client: GenaiEngineTestClientBase):
    """Test getting a nonexistent test run returns 404."""
    status_code, response = client.get_test_run(str(uuid.uuid4()))
    assert status_code == 404


@pytest.mark.unit_tests
@patch(MOCK_QUEUE_PATH)
def test_list_test_runs(mock_queue, client: GenaiEngineTestClientBase):
    mock_queue.return_value = MagicMock(spec=ContinuousEvalQueueService)
    """Test listing test runs for a continuous eval."""
    status_code, task = client.create_task(
        name="test_list_test_runs",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        status_code, llm_eval = create_test_llm_eval(client, task.id)
        assert status_code == 200

        status_code, transform = create_test_transform(client, task.id)
        assert status_code == 200

        status_code, continuous_eval = create_test_continuous_eval(
            client, task.id, llm_eval, transform,
        )
        assert status_code == 200

        trace_ids = setup_traces(task.id, count=2)

        try:
            # Create two test runs
            status_code, test_run_1 = client.create_test_run(
                eval_id=str(continuous_eval.id),
                trace_ids=trace_ids[:1],
            )
            assert status_code == 200

            status_code, test_run_2 = client.create_test_run(
                eval_id=str(continuous_eval.id),
                trace_ids=trace_ids[1:],
            )
            assert status_code == 200

            # List test runs
            status_code, list_response = client.list_test_runs(str(continuous_eval.id))
            assert status_code == 200
            assert list_response.count == 2
            assert len(list_response.test_runs) == 2

            cleanup_test_run(str(test_run_1.id))
            cleanup_test_run(str(test_run_2.id))
        finally:
            cleanup_traces(trace_ids)
    finally:
        client.delete_task(task.id)


# ============================================================================
# Delete Test Run
# ============================================================================


@pytest.mark.unit_tests
@patch(MOCK_QUEUE_PATH)
def test_delete_test_run(mock_queue, client: GenaiEngineTestClientBase):
    """Test deleting a test run removes it and its annotations."""
    mock_queue.return_value = MagicMock(spec=ContinuousEvalQueueService)
    status_code, task = client.create_task(
        name="test_delete_test_run",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        status_code, llm_eval = create_test_llm_eval(client, task.id)
        assert status_code == 200

        status_code, transform = create_test_transform(client, task.id)
        assert status_code == 200

        status_code, continuous_eval = create_test_continuous_eval(
            client, task.id, llm_eval, transform,
        )
        assert status_code == 200

        trace_ids = setup_traces(task.id, count=2)

        try:
            status_code, test_run = client.create_test_run(
                eval_id=str(continuous_eval.id),
                trace_ids=trace_ids,
            )
            assert status_code == 200

            # Verify it exists
            status_code, _ = client.get_test_run(str(test_run.id))
            assert status_code == 200

            # Delete it
            status_code, _ = client.delete_test_run(str(test_run.id))
            assert status_code == 204

            # Verify it's gone
            status_code, _ = client.get_test_run(str(test_run.id))
            assert status_code == 404

            # Verify annotations are also gone (CASCADE)
            status_code, results = client.get_test_run_results(str(test_run.id))
            assert status_code == 200
            assert results.count == 0
        finally:
            cleanup_traces(trace_ids)
    finally:
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_delete_test_run_not_found(client: GenaiEngineTestClientBase):
    """Test deleting a nonexistent test run returns 404."""
    status_code, _ = client.delete_test_run(str(uuid.uuid4()))
    assert status_code == 404


# ============================================================================
# Test Run Results Isolation
# ============================================================================


@pytest.mark.unit_tests
@patch(MOCK_QUEUE_PATH)
def test_test_run_annotations_excluded_from_production_results(
    mock_queue,
    client: GenaiEngineTestClientBase,
):
    mock_queue.return_value = MagicMock(spec=ContinuousEvalQueueService)
    """Test that test run annotations don't appear in production continuous eval results."""
    status_code, task = client.create_task(
        name="test_isolation",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        status_code, llm_eval = create_test_llm_eval(client, task.id)
        assert status_code == 200

        status_code, transform = create_test_transform(client, task.id)
        assert status_code == 200

        status_code, continuous_eval = create_test_continuous_eval(
            client, task.id, llm_eval, transform,
        )
        assert status_code == 200

        trace_ids = setup_traces(task.id, count=2)

        try:
            # Create a test run (creates annotations with test_run_id set)
            status_code, test_run = client.create_test_run(
                eval_id=str(continuous_eval.id),
                trace_ids=trace_ids,
            )
            assert status_code == 200

            # Production results should NOT include test run annotations
            status_code, production_results = client.list_continuous_eval_run_results(
                task_id=task.id,
            )
            assert status_code == 200
            assert production_results.count == 0

            # Test run results should include them
            status_code, test_results = client.get_test_run_results(str(test_run.id))
            assert status_code == 200
            assert test_results.count == 2

            cleanup_test_run(str(test_run.id))
        finally:
            cleanup_traces(trace_ids)
    finally:
        client.delete_task(task.id)


@pytest.mark.unit_tests
@patch(MOCK_QUEUE_PATH)
def test_test_run_annotations_excluded_from_trace_list(
    mock_queue,
    client: GenaiEngineTestClientBase,
):
    """Test that test run annotations don't appear on traces returned by GET /api/v1/traces."""
    mock_queue.return_value = MagicMock(spec=ContinuousEvalQueueService)
    status_code, task = client.create_task(
        name="test_trace_list_isolation",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        status_code, llm_eval = create_test_llm_eval(client, task.id)
        assert status_code == 200

        status_code, transform = create_test_transform(client, task.id)
        assert status_code == 200

        status_code, continuous_eval = create_test_continuous_eval(
            client, task.id, llm_eval, transform,
        )
        assert status_code == 200

        trace_ids = setup_traces(task.id, count=1)

        try:
            # Create a test run — this creates annotations with test_run_id set
            status_code, test_run = client.create_test_run(
                eval_id=str(continuous_eval.id),
                trace_ids=trace_ids,
            )
            assert status_code == 200

            # List traces — annotations on traces should NOT include test run annotations
            status_code, trace_list = client.trace_api_list_traces_metadata(
                task_ids=[task.id],
            )
            assert status_code == 200
            assert trace_list.count == 1
            trace = trace_list.traces[0]
            assert trace.annotations is None or len(trace.annotations) == 0

            cleanup_test_run(str(test_run.id))
        finally:
            cleanup_traces(trace_ids)
    finally:
        client.delete_task(task.id)


@pytest.mark.unit_tests
@patch(MOCK_QUEUE_PATH)
def test_test_run_annotations_excluded_from_single_trace(
    mock_queue,
    client: GenaiEngineTestClientBase,
):
    """Test that test run annotations don't appear on GET /api/v1/traces/{trace_id}."""
    mock_queue.return_value = MagicMock(spec=ContinuousEvalQueueService)
    status_code, task = client.create_task(
        name="test_single_trace_isolation",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        status_code, llm_eval = create_test_llm_eval(client, task.id)
        assert status_code == 200

        status_code, transform = create_test_transform(client, task.id)
        assert status_code == 200

        status_code, continuous_eval = create_test_continuous_eval(
            client, task.id, llm_eval, transform,
        )
        assert status_code == 200

        trace_ids = setup_traces(task.id, count=1)

        try:
            # Create a test run
            status_code, test_run = client.create_test_run(
                eval_id=str(continuous_eval.id),
                trace_ids=trace_ids,
            )
            assert status_code == 200

            # Get single trace — annotations should NOT include test run annotations
            status_code, trace = client.trace_api_get_trace_by_id(trace_ids[0])
            assert status_code == 200
            assert trace.annotations is None or len(trace.annotations) == 0

            cleanup_test_run(str(test_run.id))
        finally:
            cleanup_traces(trace_ids)
    finally:
        client.delete_task(task.id)
