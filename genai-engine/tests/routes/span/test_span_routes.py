import json
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue
from opentelemetry.proto.trace.v1.trace_pb2 import Span
from repositories.span_repository import SpanRepository
from repositories.tasks_metrics_repository import TasksMetricsRepository
from repositories.metrics_repository import MetricRepository

from tests.clients.base_test_client import GenaiEngineTestClientBase
from tests.conftest import override_get_db_session
from schemas.internal_schemas import Span as InternalSpan
from tests.routes.span.conftest import _delete_spans_from_db
import uuid

@pytest.mark.unit_tests
def test_receive_traces_happy_path(
    client: GenaiEngineTestClientBase,
    sample_openinference_trace,
):
    # Test with valid trace data
    status_code, response = client.receive_traces(sample_openinference_trace)
    assert status_code == 200
    # The response might be empty or a simple JSON object
    assert json.loads(response) == {
        "total_spans": 2,
        "accepted_spans": 2,
        "rejected_spans": 0,
        "rejection_reasons": [],
        "status": "success",
    }


@pytest.mark.unit_tests
def test_receive_traces_invalid_protobuf(client: GenaiEngineTestClientBase):
    # Test with invalid protobuf data
    invalid_trace = b"invalid_protobuf_data"

    status_code, response = client.receive_traces(invalid_trace)
    assert status_code == 400
    assert any(
        error_msg in response
        for error_msg in [
            "Invalid protobuf message format",
            "error parsing the body",
            "decode error",
            "json_invalid",
        ]
    )


@pytest.mark.unit_tests
def test_receive_traces_server_error(
    client: GenaiEngineTestClientBase,
    sample_openinference_trace,
):
    # Test with data that causes server error
    with patch(
        "repositories.span_repository.SpanRepository.create_traces",
        side_effect=Exception("Test error"),
    ):
        status_code, response = client.receive_traces(sample_openinference_trace)
        assert status_code == 500
        assert "Test error" in response or "An internal error occurred" in response


@pytest.mark.unit_tests
def test_receive_traces_response_types(
    client: GenaiEngineTestClientBase,
    sample_mixed_spans_trace,
    sample_all_rejected_spans_trace,
):
    # Test mixed spans - one with task ID (accepted), one without task ID and without parent ID (rejected)
    status_code, response = client.receive_traces(sample_mixed_spans_trace)
    assert status_code == 206  # Partial Content
    response_json = json.loads(response)
    assert response_json["status"] == "partial_success"
    assert response_json["accepted_spans"] == 1  # Span with task ID accepted
    assert response_json["rejected_spans"] == 1  # Span without task ID and without parent ID rejected

    # Test all spans without task IDs and without parent IDs - should all be rejected
    status_code, response = client.receive_traces(sample_all_rejected_spans_trace)
    assert status_code == 422  # Unprocessable Entity
    response_json = json.loads(response)
    assert response_json["status"] == "failure"
    assert response_json["accepted_spans"] == 0
    assert response_json["rejected_spans"] == 2  # Both spans rejected


@pytest.mark.unit_tests
def test_spans_missing_task_id(
    client: GenaiEngineTestClientBase,
    sample_span_missing_task_id,
):
    # Test with a span missing task ID and no parent ID - should be rejected
    status_code, response = client.receive_traces(sample_span_missing_task_id)
    response_json = json.loads(response)

    # Verify that the span was rejected
    assert status_code == 422  # Unprocessable Entity
    assert response_json["accepted_spans"] == 0
    assert response_json["rejected_spans"] == 1
    assert response_json["status"] == "failure"
    assert "Invalid span data. Span must have a task_id or a parent_id." in response_json["rejection_reasons"][0]


@pytest.mark.unit_tests
def test_spans_with_parent_id_but_no_task_id(
    client: GenaiEngineTestClientBase,
    sample_span_with_parent_id,
):
    # Test with a span that has a parent ID but no task ID - should be accepted
    status_code, response = client.receive_traces(sample_span_with_parent_id)
    response_json = json.loads(response)

    # Verify that the span was accepted
    assert status_code == 200
    assert response_json["accepted_spans"] == 1
    assert response_json["rejected_spans"] == 0
    assert response_json["status"] == "success"


@pytest.mark.unit_tests
def test_query_spans_with_metrics_happy_path(client: GenaiEngineTestClientBase, create_test_spans):
    # Test basic query with task IDs
    status_code, response = client.query_spans_with_metrics(task_ids=["task1"])
    assert status_code == 200
    assert response.count == 2  # task1 has 2 spans
    assert len(response.spans) == 2
    assert all(span.task_id == "task1" for span in response.spans)


@pytest.mark.unit_tests
def test_query_spans_with_metrics_multiple_task_ids(client: GenaiEngineTestClientBase, create_test_spans):
    # Test querying spans for multiple tasks
    status_code, response = client.query_spans_with_metrics(task_ids=["task1", "task2"])
    assert status_code == 200
    assert response.count == 4  # task1 has 2 spans, task2 has 2 spans
    assert len(response.spans) == 4
    task_ids = {span.task_id for span in response.spans}
    assert task_ids == {"task1", "task2"}


@pytest.mark.unit_tests
def test_query_spans_with_metrics_with_date_filters(client: GenaiEngineTestClientBase, create_test_spans):
    base_time = datetime.now()

    # Test querying spans within a specific time range
    status_code, response = client.query_spans_with_metrics(
        task_ids=["task1", "task2"],
        start_time=base_time - timedelta(days=1),
        end_time=base_time + timedelta(days=1),
    )
    assert status_code == 200
    assert response.count == 3  # spans 2, 3, and 4 fall within this range
    assert all(
        base_time - timedelta(days=1)
        <= span.created_at
        <= base_time + timedelta(days=1)
        for span in response.spans
    )


@pytest.mark.unit_tests
def test_query_spans_with_metrics_pagination(client: GenaiEngineTestClientBase, create_test_spans):
    # Test pagination parameters
    status_code, response = client.query_spans_with_metrics(
        task_ids=["task1", "task2", "task3"], 
        page=0, 
        page_size=2, 
        sort="desc"
    )
    assert status_code == 200
    assert response.count == 2  # page size is 2
    assert len(response.spans) == 2

    # Test second page
    status_code, response = client.query_spans_with_metrics(
        task_ids=["task1", "task2", "task3"], 
        page=1, 
        page_size=2, 
        sort="desc"
    )
    assert status_code == 200
    assert len(response.spans) == 2  # second page should have 2 spans

    # Test third page
    status_code, response = client.query_spans_with_metrics(
        task_ids=["task1", "task2", "task3"], 
        page=2, 
        page_size=2, 
        sort="desc"
    )
    assert status_code == 200
    assert len(response.spans) == 1  # third page should have 1 span


@pytest.mark.unit_tests
def test_query_spans_with_metrics_missing_task_ids(client: GenaiEngineTestClientBase):
    # Test with missing task IDs (should return 400)
    status_code, response = client.query_spans_with_metrics(task_ids=[])
    assert status_code == 400
    response_json = json.loads(response)
    assert "Field required" in response_json["detail"]


@pytest.mark.unit_tests
def test_query_spans_with_metrics_server_error(client: GenaiEngineTestClientBase):
    # Test with data that causes server error
    with patch(
        "repositories.span_repository.SpanRepository.query_spans",
        side_effect=Exception("Test error"),
    ):
        status_code, response = client.query_spans_with_metrics(task_ids=["task1"])
        assert status_code == 500
        assert "Test error" in response or "An internal error occurred" in response


@pytest.mark.unit_tests
def test_query_spans_with_metrics_no_spans_found(client: GenaiEngineTestClientBase):
    # Test querying for non-existent task IDs
    status_code, response = client.query_spans_with_metrics(task_ids=["non_existent_task"])
    assert status_code == 200
    assert response.count == 0
    assert len(response.spans) == 0


@pytest.mark.unit_tests
def test_query_spans_with_metrics_task_id_propagation(client: GenaiEngineTestClientBase, create_span_hierarchy_for_propagation):
    """Test that task IDs are propagated to child spans when querying with metrics."""
    # Query spans for the task - this should trigger task ID propagation
    status_code, response = client.query_spans_with_metrics(task_ids=["propagation_test_task"])
    assert status_code == 200
    
    # Should return all 6 spans (root + 2 children + 3 grandchildren)
    assert response.count == 6
    assert len(response.spans) == 6
    
    # All spans should have the propagated task_id
    for span in response.spans:
        assert span.task_id == "propagation_test_task", f"Span {span.span_id} should have task_id 'propagation_test_task', got {span.task_id}"
    
    # Verify we have the expected span hierarchy
    span_ids = {span.span_id for span in response.spans}
    expected_span_ids = {"root_span", "child_a", "child_b", "grandchild_a1", "grandchild_a2", "grandchild_b1"}
    assert span_ids == expected_span_ids
    
    # Verify span kinds are preserved
    span_kinds = {span.span_id: span.span_kind for span in response.spans}
    assert span_kinds["root_span"] == "LLM"
    assert span_kinds["child_a"] == "CHAIN"
    assert span_kinds["child_b"] == "AGENT"
    assert span_kinds["grandchild_a1"] == "TOOL"
    assert span_kinds["grandchild_a2"] == "RETRIEVER"
    assert span_kinds["grandchild_b1"] == "EMBEDDING"


@pytest.mark.unit_tests
def test_task_id_propagation_direct_repository(create_span_hierarchy_for_propagation):
    """Test task ID propagation directly in the repository layer."""
    from schemas.enums import PaginationSortMethod
    
    db_session = override_get_db_session()
    tasks_metrics_repo = TasksMetricsRepository(db_session)
    metrics_repo = MetricRepository(db_session)
    span_repo = SpanRepository(db_session, tasks_metrics_repo, metrics_repo)
    
    # Query spans without metrics first to see the original state
    spans_before = span_repo.query_spans(
        task_ids=["propagation_test_task"],
        sort=PaginationSortMethod.DESCENDING,
        page=0,
        page_size=10,
        include_metrics=False,
        propagate_task_ids=False  # Disable propagation to see original state
    )
    
    # Should only return the root span initially (others don't have task_id)
    assert len(spans_before) == 1
    assert spans_before[0].span_id == "root_span"
    assert spans_before[0].task_id == "propagation_test_task"
    
    # Now query with propagation enabled
    spans_after = span_repo.query_spans(
        task_ids=["propagation_test_task"],
        sort=PaginationSortMethod.DESCENDING,
        page=0,
        page_size=10,
        include_metrics=False,
        propagate_task_ids=True  # Enable propagation
    )
    
    # Should return all 6 spans with propagated task_ids
    assert len(spans_after) == 6
    for span in spans_after:
        assert span.task_id == "propagation_test_task"
    
    # Verify the propagation actually updated the database
    # Query again without propagation to confirm the database was updated
    spans_verify = span_repo.query_spans(
        task_ids=["propagation_test_task"],
        sort=PaginationSortMethod.DESCENDING,
        page=0,
        page_size=10,
        include_metrics=False,
        propagate_task_ids=False  # Disable propagation to verify database state
    )
    
    # Should still return all 6 spans because the database was updated
    assert len(spans_verify) == 6
    for span in spans_verify:
        assert span.task_id == "propagation_test_task"


@pytest.mark.unit_tests
def test_task_id_propagation_with_metrics(create_span_hierarchy_for_propagation):
    """Test that task ID propagation works correctly when including metrics."""
    from schemas.enums import PaginationSortMethod
    
    db_session = override_get_db_session()
    tasks_metrics_repo = TasksMetricsRepository(db_session)
    metrics_repo = MetricRepository(db_session)
    span_repo = SpanRepository(db_session, tasks_metrics_repo, metrics_repo)
    
    # Query spans with metrics and propagation enabled
    spans = span_repo.query_spans(
        task_ids=["propagation_test_task"],
        sort=PaginationSortMethod.DESCENDING,
        page=0,
        page_size=10,
        include_metrics=True,
        propagate_task_ids=True
    )
    
    # Should return all 6 spans with propagated task_ids
    assert len(spans) == 6
    for span in spans:
        assert span.task_id == "propagation_test_task"
    
    # Verify that LLM spans have metric_results field (even if empty)
    llm_spans = [span for span in spans if span.span_kind == "LLM"]
    assert len(llm_spans) == 1
    assert llm_spans[0].span_id == "root_span"
    assert hasattr(llm_spans[0], 'metric_results')
    assert llm_spans[0].metric_results is not None


@pytest.mark.unit_tests
def test_task_id_propagation_multiple_tasks(create_span_hierarchy_for_propagation):
    """Test task ID propagation with multiple tasks."""
    from schemas.enums import PaginationSortMethod
    
    db_session = override_get_db_session()
    tasks_metrics_repo = TasksMetricsRepository(db_session)
    metrics_repo = MetricRepository(db_session)
    span_repo = SpanRepository(db_session, tasks_metrics_repo, metrics_repo)
    
    # Create an additional span with a different task_id
    additional_span = InternalSpan(
        id=str(uuid.uuid4()),
        trace_id="other_trace",
        span_id="other_span",
        task_id="other_task",
        parent_span_id=None,
        span_kind="LLM",
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(seconds=1),
        raw_data={"model": "gpt-4"},
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    
    # Store the additional span
    additional_span_dict = additional_span.model_dump()
    additional_span_dict.pop("metric_results")
    span_repo.store_spans([additional_span_dict])
    
    try:
        # Query spans for both tasks
        spans = span_repo.query_spans(
            task_ids=["propagation_test_task", "other_task"],
            sort=PaginationSortMethod.DESCENDING,
            page=0,
            page_size=20,
            include_metrics=False,
            propagate_task_ids=True
        )
        
        # Should return 7 spans total (6 from propagation_test_task + 1 from other_task)
        assert len(spans) == 7
        
        # Verify task distribution
        propagation_spans = [span for span in spans if span.task_id == "propagation_test_task"]
        other_spans = [span for span in spans if span.task_id == "other_task"]
        
        assert len(propagation_spans) == 6
        assert len(other_spans) == 1
        assert other_spans[0].span_id == "other_span"
        
    finally:
        # Cleanup the additional span
        _delete_spans_from_db(db_session, ["other_span"])
