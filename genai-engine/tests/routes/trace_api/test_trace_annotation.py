import pytest
from arthur_common.models.response_schemas import TraceResponse

from schemas.internal_schemas import AgenticAnnotation
from schemas.request_schemas import AgenticAnnotationRequest
from schemas.response_schemas import SessionTracesResponse
from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.mark.unit_tests
def test_adding_an_annotation_to_a_trace(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    trace_id = "api_trace1"
    annotation_request = AgenticAnnotationRequest(
        annotation_score=1,
        annotation_description="Test annotation",
    )

    """Test adding an annotation to a trace."""
    # Add an annotation to a non-existent trace
    status_code, response = client.trace_api_annotate_trace(
        "non_existent_trace_id",
        annotation_request,
    )
    assert status_code == 404
    assert "Trace non_existent_trace_id not found" in response

    # Add an annotation to the trace
    status_code, response = client.trace_api_annotate_trace(
        trace_id,
        annotation_request,
    )
    assert status_code == 200
    assert isinstance(response, AgenticAnnotation)
    assert response.trace_id == trace_id
    assert response.annotation_score == 1
    assert response.annotation_description == "Test annotation"

    annotation_request = AgenticAnnotationRequest(
        annotation_score=0,
        annotation_description="Updated annotation",
    )

    # Update the annotation for this trace
    status_code, response = client.trace_api_annotate_trace(
        trace_id,
        annotation_request,
    )
    assert status_code == 200
    assert isinstance(response, AgenticAnnotation)
    assert response.trace_id == trace_id
    assert response.annotation_score == 0
    assert response.annotation_description == "Updated annotation"

    annotation_request = AgenticAnnotationRequest(
        annotation_score=0,
        annotation_description=None,
    )

    # Verify adding an annotation with a missing description works
    status_code, response = client.trace_api_annotate_trace(
        trace_id,
        annotation_request,
    )
    assert status_code == 200
    assert isinstance(response, AgenticAnnotation)
    assert response.trace_id == trace_id
    assert response.annotation_score == 0
    assert response.annotation_description is None

    annotation_request = {
        "annotation_description": "Updated annotation",
    }

    # Verify adding an annotation with a missing score raises an error
    status_code, response = client.trace_api_annotate_trace(
        trace_id,
        annotation_request,
    )
    assert status_code == 400

    # Cleanup
    status_code, _ = client.trace_api_delete_annotation_from_trace(trace_id)
    assert status_code == 204


@pytest.mark.unit_tests
def test_deleting_an_annotation_from_a_trace(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test deleting an annotation from a trace."""
    trace_id = "api_trace1"

    # Deleting a non-existent annotation from an existing trace should raise a 404 error
    status_code, response = client.trace_api_delete_annotation_from_trace(trace_id)
    assert status_code == 404
    assert "Annotation for trace api_trace1 not found" in response

    annotation_request = AgenticAnnotationRequest(
        annotation_score=1,
        annotation_description="Test annotation",
    )

    # Add an annotation to the trace
    status_code, response = client.trace_api_annotate_trace(
        trace_id,
        annotation_request,
    )
    assert status_code == 200
    assert isinstance(response, AgenticAnnotation)
    assert response.trace_id == trace_id
    assert response.annotation_score == 1
    assert response.annotation_description == "Test annotation"

    # Successfully delete the annotation
    status_code, response = client.trace_api_delete_annotation_from_trace(trace_id)
    assert status_code == 204
    assert response == ""

    # Verify annotation doesn't exist anymore
    status_code, response = client.trace_api_delete_annotation_from_trace(trace_id)
    assert status_code == 404
    assert "Annotation for trace api_trace1 not found" in response


@pytest.mark.unit_tests
def test_get_trace_requests_return_annotation_info(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test deleting an annotation from a trace."""
    trace_id = "api_trace1"

    # Add an annotation to the trace
    annotation_request = AgenticAnnotationRequest(
        annotation_score=1,
        annotation_description="Test annotation",
    )
    status_code, response = client.trace_api_annotate_trace(
        trace_id,
        annotation_request,
    )
    assert status_code == 200
    assert isinstance(response, AgenticAnnotation)
    assert response.trace_id == trace_id
    assert response.annotation_score == 1
    assert response.annotation_description == "Test annotation"

    #########################################################################################
    # Assert annotation information is returned for all the following existing endpoints
    #########################################################################################

    # Verify listing metadata returns annotation info
    status_code, data = client.trace_api_list_traces_metadata(
        task_ids=["api_task1"],
        trace_ids=[trace_id],
    )

    assert data.count == 1
    assert len(data.traces) == 1
    assert data.traces[0].trace_id == trace_id
    assert data.traces[0].annotation.annotation_score == 1
    assert data.traces[0].annotation.annotation_description == "Test annotation"

    # Verify the response object after computing trace metrics has annotation info
    status_code, data = client.trace_api_compute_trace_metrics(
        trace_id=trace_id,
    )
    assert status_code == 200
    assert isinstance(data, TraceResponse)
    assert data.trace_id == trace_id
    assert data.annotation.annotation_score == 1
    assert data.annotation.annotation_description == "Test annotation"

    # Verify the response object after computing trace metrics has annotation info
    status_code, data = client.trace_api_compute_trace_metrics(
        trace_id=trace_id,
    )
    assert status_code == 200
    assert isinstance(data, TraceResponse)
    assert data.trace_id == trace_id
    assert data.annotation.annotation_score == 1
    assert data.annotation.annotation_description == "Test annotation"

    # Verify the response object after getting the session by id has annotation info
    status_code, data = client.trace_api_get_session_traces(
        session_id="session1",
    )
    assert status_code == 200
    assert isinstance(data, SessionTracesResponse)
    found_trace = False
    for trace in data.traces:
        if trace.trace_id == trace_id:
            assert trace.annotation.annotation_score == 1
            assert trace.annotation.annotation_description == "Test annotation"
            found_trace = True
            break
    assert found_trace

    # Verify the response object after computing session metrics has annotation info
    status_code, data = client.trace_api_compute_session_metrics(
        session_id="session1",
    )
    assert status_code == 200
    assert isinstance(data, SessionTracesResponse)
    found_trace = False
    for trace in data.traces:
        if trace.trace_id == trace_id:
            assert trace.annotation.annotation_score == 1
            assert trace.annotation.annotation_description == "Test annotation"
            found_trace = True
            break
    assert found_trace

    # Delete the annotation
    status_code, response = client.trace_api_delete_annotation_from_trace(trace_id)
    assert status_code == 204
    assert response == ""

    #########################################################################################
    # Assert annotation information is not returned for all the following existing endpoints
    # and the endpoints still succeed if the annotation does not exist for the trace
    #########################################################################################

    # Verify listing metadata returns annotation info
    status_code, data = client.trace_api_list_traces_metadata(
        task_ids=["api_task1"],
        trace_ids=[trace_id],
    )

    assert data.count == 1
    assert len(data.traces) == 1
    assert data.traces[0].trace_id == trace_id
    assert data.traces[0].annotation is None

    # Verify the response object after computing trace metrics has annotation info
    status_code, data = client.trace_api_compute_trace_metrics(
        trace_id=trace_id,
    )
    assert status_code == 200
    assert isinstance(data, TraceResponse)
    assert data.trace_id == trace_id
    assert data.annotation is None

    # Verify the response object after computing trace metrics has annotation info
    status_code, data = client.trace_api_compute_trace_metrics(
        trace_id=trace_id,
    )
    assert status_code == 200
    assert isinstance(data, TraceResponse)
    assert data.trace_id == trace_id
    assert data.annotation is None

    # Verify the response object after getting the session by id has annotation info
    status_code, data = client.trace_api_get_session_traces(
        session_id="session1",
    )
    assert status_code == 200
    assert isinstance(data, SessionTracesResponse)
    found_trace = False
    for trace in data.traces:
        if trace.trace_id == trace_id:
            found_trace = True
        assert trace.annotation is None
    assert found_trace

    # Verify the response object after computing session metrics has annotation info
    status_code, data = client.trace_api_compute_session_metrics(
        session_id="session1",
    )
    assert status_code == 200
    assert isinstance(data, SessionTracesResponse)
    found_trace = False
    for trace in data.traces:
        if trace.trace_id == trace_id:
            found_trace = True
        assert trace.annotation is None
    assert found_trace
