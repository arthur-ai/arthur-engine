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
        "repositories.span_repository.SpanRepository.query_spans_with_metrics",
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
