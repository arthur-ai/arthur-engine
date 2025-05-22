import json
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from repositories.span_repository import SpanRepository

from tests.clients.base_test_client import GenaiEngineTestClientBase, override_get_db_session


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
        "total_spans": 1,
        "accepted_spans": 1,
        "unnecessary_spans": 0,
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
    # Test partial success response (some accepted, some rejected)
    status_code, response = client.receive_traces(sample_mixed_spans_trace)
    assert status_code == 206  # Partial Content
    response_json = json.loads(response)
    assert response_json["status"] == "partial_success"
    assert response_json["accepted_spans"] > 0
    assert response_json["rejected_spans"] > 0

    # Test failure response (all rejected)
    status_code, response = client.receive_traces(sample_all_rejected_spans_trace)
    assert status_code == 422  # Unprocessable Entity
    response_json = json.loads(response)
    assert response_json["status"] == "failure"
    assert response_json["accepted_spans"] == 0
    assert response_json["rejected_spans"] > 0


@pytest.mark.unit_tests
def test_is_llm_span():
    span_repo =SpanRepository(override_get_db_session())
    # Test positive case - is an LLM span
    llm_span_data = {
        "attributes": [
            {"key": "openinference.span.kind", "value": {"stringValue": "LLM"}},
            {"key": "other.attribute", "value": {"stringValue": "value"}},
        ],
    }
    assert span_repo._is_llm_span(llm_span_data) is True

    # Test negative case - not an LLM span
    non_llm_span_data = {
        "attributes": [
            {"key": "openinference.span.kind", "value": {"stringValue": "OTHER"}},
            {"key": "other.attribute", "value": {"stringValue": "value"}},
        ],
    }
    assert span_repo._is_llm_span(non_llm_span_data) is False

    # Test negative case - no attributes
    no_attributes_span_data = {}
    assert span_repo._is_llm_span(no_attributes_span_data) is False

    # Test negative case - empty attributes
    empty_attributes_span_data = {"attributes": []}
    assert span_repo._is_llm_span(empty_attributes_span_data) is False


@pytest.mark.unit_tests
def test_spans_missing_task_id(
    client: GenaiEngineTestClientBase,
    sample_span_missing_task_id,
):
    # Test with a span missing task ID
    status_code, response = client.receive_traces(sample_span_missing_task_id)
    response_json = json.loads(response)

    # Verify that the span was rejected
    assert response_json["rejected_spans"] > 0
    assert "Missing task ID" in response_json["rejection_reasons"]


@pytest.mark.unit_tests
def test_query_spans_happy_path(client: GenaiEngineTestClientBase, create_test_spans):
    # Test basic query without filters
    status_code, response = client.query_spans()
    assert status_code == 200
    assert response.count == 5  # We created 5 spans
    assert len(response.spans) == 5


@pytest.mark.unit_tests
def test_query_spans_with_trace_ids(client: GenaiEngineTestClientBase, create_test_spans):
    # Test querying spans for trace1
    status_code, response = client.query_spans(trace_ids=["trace1"])
    assert status_code == 200
    assert response.count == 2  # trace1 has 2 spans
    assert all(span.trace_id == "trace1" for span in response.spans)


@pytest.mark.unit_tests
def test_query_spans_with_span_ids(client: GenaiEngineTestClientBase, create_test_spans):
    # Test querying specific spans
    status_code, response = client.query_spans(span_ids=["span1", "span3"])
    assert status_code == 200
    assert response.count == 2
    assert {span.span_id for span in response.spans} == {"span1", "span3"}


@pytest.mark.unit_tests
def test_query_spans_with_task_ids(client: GenaiEngineTestClientBase, create_test_spans):
    # Test querying spans for task1
    status_code, response = client.query_spans(task_ids=["task1"])
    assert status_code == 200
    assert response.count == 2  # task1 has 2 spans
    assert all(span.task_id == "task1" for span in response.spans)


@pytest.mark.unit_tests
def test_query_spans_with_date_filters(client: GenaiEngineTestClientBase, create_test_spans):
    base_time = datetime.now()

    # Test querying spans within a specific time range
    status_code, response = client.query_spans(
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
def test_query_spans_pagination(client: GenaiEngineTestClientBase, create_test_spans):
    # Test pagination parameters
    status_code, response = client.query_spans(page=0, page_size=2, sort="desc")
    assert status_code == 200
    assert response.count == 2  # total count should be 5
    assert len(response.spans) == 2  # page size is 2

    # Test second page
    status_code, response = client.query_spans(page=1, page_size=2, sort="desc")
    assert status_code == 200
    assert len(response.spans) == 2  # second page should have 2 spans

    # Test third page
    status_code, response = client.query_spans(page=2, page_size=2, sort="desc")
    assert status_code == 200
    assert len(response.spans) == 1  # third page should have 1 span


@pytest.mark.unit_tests
def test_query_spans_invalid_page_size(client: GenaiEngineTestClientBase):
    # Test with invalid page size
    status_code, response = client.query_spans(page_size=5001)
    assert status_code == 400
    assert "Invalid page size, must be greater than 0 and less than 5000" in response


@pytest.mark.unit_tests
def test_query_spans_server_error(client: GenaiEngineTestClientBase):
    # Test with data that causes server error
    with patch(
        "repositories.span_repository.SpanRepository.query_spans",
        side_effect=Exception("Test error"),
    ):
        status_code, response = client.query_spans()
        assert status_code == 500
        assert "Test error" in response or "An internal error occurred" in response
