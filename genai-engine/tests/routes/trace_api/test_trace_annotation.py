import uuid
from datetime import datetime
from typing import Optional

import pytest
from arthur_common.models.enums import AgenticAnnotationType, ContinuousEvalRunStatus
from arthur_common.models.response_schemas import TraceResponse

from db_models.agentic_annotation_models import DatabaseAgenticAnnotation
from db_models.llm_eval_models import DatabaseContinuousEval
from schemas.internal_schemas import AgenticAnnotation
from schemas.request_schemas import AgenticAnnotationRequest
from schemas.response_schemas import SessionTracesResponse
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)


def create_mock_continuous_eval(
    continuous_eval_id: uuid.UUID,
    task_id: str,
    name: str,
    llm_eval_name: str,
    llm_eval_version: int,
    transform_id: uuid.UUID,
) -> DatabaseContinuousEval:
    db_session = override_get_db_session()
    db_continuous_eval = DatabaseContinuousEval(
        id=continuous_eval_id,
        task_id=task_id,
        name=name,
        llm_eval_name=llm_eval_name,
        llm_eval_version=llm_eval_version,
        transform_id=transform_id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(db_continuous_eval)
    db_session.commit()
    db_session.refresh(db_continuous_eval)
    return db_continuous_eval


def delete_mock_continuous_eval(continuous_eval_id: uuid.UUID) -> None:
    db_session = override_get_db_session()
    db_continuous_eval = (
        db_session.query(DatabaseContinuousEval)
        .filter(DatabaseContinuousEval.id == continuous_eval_id)
        .first()
    )
    if db_continuous_eval:
        db_session.delete(db_continuous_eval)
        db_session.commit()


def create_mock_annotation(
    trace_id: str,
    annotation_type: AgenticAnnotationType,
    annotation_score: Optional[int] = None,
    continuous_eval_id: Optional[uuid.UUID] = None,
    run_status: Optional[ContinuousEvalRunStatus] = None,
    annotation_description: Optional[str] = None,
    input_variables: Optional[list] = None,
) -> DatabaseAgenticAnnotation:
    db_session = override_get_db_session()
    db_annotation = DatabaseAgenticAnnotation(
        id=uuid.uuid4(),
        annotation_type=annotation_type.value,
        trace_id=trace_id,
        annotation_score=annotation_score,
        annotation_description=annotation_description,
        input_variables=input_variables,
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
    assert len(data.traces[0].annotations) == 1
    assert data.traces[0].annotations[0].annotation_score == 1
    assert data.traces[0].annotations[0].annotation_type == "human"

    # Verify the response object after computing trace metrics has annotation info
    status_code, data = client.trace_api_compute_trace_metrics(
        trace_id=trace_id,
    )
    assert status_code == 200
    assert isinstance(data, TraceResponse)
    assert data.trace_id == trace_id
    assert len(data.annotations) == 1
    assert data.annotations[0].annotation_score == 1
    assert data.annotations[0].annotation_type == "human"

    # Verify the response object after computing trace metrics has annotation info
    status_code, data = client.trace_api_compute_trace_metrics(
        trace_id=trace_id,
    )
    assert status_code == 200
    assert isinstance(data, TraceResponse)
    assert data.trace_id == trace_id
    assert len(data.annotations) == 1
    assert data.annotations[0].annotation_score == 1
    assert data.annotations[0].annotation_type == "human"

    # Verify the response object after getting the session by id has annotation info
    status_code, data = client.trace_api_get_session_traces(
        session_id="session1",
    )
    assert status_code == 200
    assert isinstance(data, SessionTracesResponse)
    found_trace = False
    for trace in data.traces:
        if trace.trace_id == trace_id:
            assert len(trace.annotations) == 1
            assert trace.annotations[0].annotation_score == 1
            assert trace.annotations[0].annotation_type == "human"
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
            assert len(trace.annotations) == 1
            assert trace.annotations[0].annotation_score == 1
            assert trace.annotations[0].annotation_type == "human"
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
    assert data.traces[0].annotations is None

    # Verify the response object after computing trace metrics has annotation info
    status_code, data = client.trace_api_compute_trace_metrics(
        trace_id=trace_id,
    )
    assert status_code == 200
    assert isinstance(data, TraceResponse)
    assert data.trace_id == trace_id
    assert data.annotations is None

    # Verify the response object after computing trace metrics has annotation info
    status_code, data = client.trace_api_compute_trace_metrics(
        trace_id=trace_id,
    )
    assert status_code == 200
    assert isinstance(data, TraceResponse)
    assert data.trace_id == trace_id
    assert data.annotations is None

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
        assert trace.annotations is None
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
        assert trace.annotations is None
    assert found_trace


@pytest.mark.unit_tests
def test_get_annotation_by_id(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test getting an annotation by id successfully"""
    trace_id = "api_trace1"
    annotation_request = AgenticAnnotationRequest(
        annotation_score=1,
        annotation_description="Test annotation",
    )

    # Add an annotation to the trace
    status_code, annotation = client.trace_api_annotate_trace(
        trace_id,
        annotation_request,
    )
    assert status_code == 200
    assert isinstance(annotation, AgenticAnnotation)
    assert annotation.id is not None
    assert annotation.trace_id == trace_id
    assert annotation.annotation_score == 1
    assert annotation.annotation_description == "Test annotation"

    # Verify adding an annotation with a missing description works
    status_code, response = client.get_annotation_by_id(annotation.id)
    assert status_code == 200
    assert isinstance(annotation, AgenticAnnotation)
    assert response.id == annotation.id
    assert response.trace_id == trace_id
    assert response.annotation_score == 1
    assert response.annotation_description == "Test annotation"

    # test getting an non-existent annotation returns a 404
    fake_annotation_id = uuid.uuid4()
    status_code, error = client.get_annotation_by_id(fake_annotation_id)
    assert status_code == 404
    assert f"annotation {fake_annotation_id} not found" in error.lower()

    # Cleanup
    status_code, _ = client.trace_api_delete_annotation_from_trace(trace_id)
    assert status_code == 204


@pytest.mark.unit_tests
def test_list_trace_annotations_pagination(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test listing trace annotations with pagination"""
    annotations = []
    trace_id = str(uuid.uuid4())
    continuous_eval_id = uuid.uuid4()
    transform_id = uuid.uuid4()

    # Create a mock continuous eval to test the new fields
    continuous_eval = create_mock_continuous_eval(
        continuous_eval_id=continuous_eval_id,
        task_id="api_task1",
        name="Test Continuous Eval",
        llm_eval_name="test_hallucination_eval",
        llm_eval_version=1,
        transform_id=transform_id,
    )

    # Create a human annotation (no continuous eval fields)
    annotation = create_mock_annotation(
        trace_id=trace_id,
        annotation_type=AgenticAnnotationType.HUMAN,
        annotation_score=1,
        annotation_description="Human annotation description",
    )
    annotations.append(AgenticAnnotation.from_db_model(annotation))

    # Create continuous eval annotations (with continuous eval fields)
    for i in range(1, 10):
        annotation = create_mock_annotation(
            trace_id=trace_id,
            annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL,
            annotation_score=i % 2,
            annotation_description=f"Continuous eval annotation {i}",
            input_variables=[{"name": f"var_{i}", "value": f"value_{i}"}],
            continuous_eval_id=continuous_eval_id,
            run_status=(
                ContinuousEvalRunStatus.PASSED
                if i % 2 == 0
                else ContinuousEvalRunStatus.FAILED
            ),
        )
        annotations.append(AgenticAnnotation.from_db_model(annotation))

    # test default (sort=desc)
    annotations = sorted(annotations, key=lambda x: x.created_at, reverse=True)
    status_code, data = client.list_agentic_annotations_for_trace(
        trace_id=trace_id,
    )
    assert status_code == 200
    assert data.count == len(annotations)
    assert len(data.annotations) == len(annotations)
    for i in range(len(data.annotations)):
        response_model = annotations[i].to_response_model()
        assert data.annotations[i].id == response_model.id
        assert data.annotations[i].annotation_score == response_model.annotation_score
        assert data.annotations[i].annotation_type == response_model.annotation_type
        assert (
            data.annotations[i].continuous_eval_id == response_model.continuous_eval_id
        )
        assert data.annotations[i].run_status == response_model.run_status
        assert data.annotations[i].created_at == response_model.created_at
        assert data.annotations[i].updated_at == response_model.updated_at

        # Check fields that were previously excluded from metadata response
        assert (
            data.annotations[i].annotation_description
            == response_model.annotation_description
        )
        assert data.annotations[i].input_variables == response_model.input_variables

        # Check new continuous eval fields
        if annotations[i].annotation_type == AgenticAnnotationType.CONTINUOUS_EVAL:
            assert data.annotations[i].continuous_eval_name == "Test Continuous Eval"
            assert data.annotations[i].eval_name == "test_hallucination_eval"
            assert data.annotations[i].eval_version == 1
        else:
            # Human annotations should have None for these fields
            assert data.annotations[i].continuous_eval_name is None
            assert data.annotations[i].eval_name is None
            assert data.annotations[i].eval_version is None

    # test sort=asc
    annotations = sorted(annotations, key=lambda x: x.created_at)
    status_code, data = client.list_agentic_annotations_for_trace(
        trace_id=trace_id,
        search_url="sort=asc",
    )
    assert status_code == 200
    assert data.count == len(annotations)
    assert len(data.annotations) == len(annotations)
    for i in range(len(data.annotations)):
        response_model = annotations[i].to_response_model()
        assert data.annotations[i].id == response_model.id
        assert data.annotations[i].annotation_score == response_model.annotation_score
        assert data.annotations[i].annotation_type == response_model.annotation_type
        assert (
            data.annotations[i].continuous_eval_id == response_model.continuous_eval_id
        )
        assert data.annotations[i].run_status == response_model.run_status
        assert data.annotations[i].created_at == response_model.created_at
        assert data.annotations[i].updated_at == response_model.updated_at

        # Check fields that were previously excluded from metadata response
        assert (
            data.annotations[i].annotation_description
            == response_model.annotation_description
        )
        assert data.annotations[i].input_variables == response_model.input_variables

        # Check new continuous eval fields
        if annotations[i].annotation_type == AgenticAnnotationType.CONTINUOUS_EVAL:
            assert data.annotations[i].continuous_eval_name == "Test Continuous Eval"
            assert data.annotations[i].eval_name == "test_hallucination_eval"
            assert data.annotations[i].eval_version == 1
        else:
            # Human annotations should have None for these fields
            assert data.annotations[i].continuous_eval_name is None
            assert data.annotations[i].eval_name is None
            assert data.annotations[i].eval_version is None

    # test sort=asc and page_size=5
    status_code, data = client.list_agentic_annotations_for_trace(
        trace_id=trace_id,
        search_url="sort=asc&page_size=5",
    )
    assert status_code == 200
    assert data.count == len(annotations) // 2
    assert len(data.annotations) == len(annotations) // 2
    for i in range(len(data.annotations)):
        metadata_response = annotations[i].to_response_model()
        assert data.annotations[i].id == metadata_response.id
        assert (
            data.annotations[i].annotation_score == metadata_response.annotation_score
        )
        assert data.annotations[i].annotation_type == metadata_response.annotation_type
        assert (
            data.annotations[i].continuous_eval_id
            == metadata_response.continuous_eval_id
        )
        assert data.annotations[i].run_status == metadata_response.run_status
        assert data.annotations[i].created_at == metadata_response.created_at
        assert data.annotations[i].updated_at == metadata_response.updated_at

    # test sort=asc, page_size=5 and page=2  (over the number of items)
    status_code, data = client.list_agentic_annotations_for_trace(
        trace_id=trace_id,
        search_url="sort=asc&page_size=5&page=2",
    )
    assert status_code == 200
    assert data.count == 0
    assert len(data.annotations) == 0

    # Cleanup
    for annotation in annotations:
        delete_mock_annotation(annotation.id)
    delete_mock_continuous_eval(continuous_eval_id)


@pytest.mark.unit_tests
def test_list_trace_annotations_filtering(
    client: GenaiEngineTestClientBase,
    comprehensive_test_data,
):
    """Test listing trace annotations with filtering"""
    annotations = []
    continuous_eval_annotations = []
    trace_id = str(uuid.uuid4())
    continuous_eval_id = uuid.uuid4()

    human_annotation = create_mock_annotation(
        trace_id=trace_id,
        annotation_type=AgenticAnnotationType.HUMAN,
        annotation_score=0,
    )
    human_annotation = AgenticAnnotation.from_db_model(human_annotation)
    annotations.append(human_annotation)

    for i in range(1, 10):
        annotation = create_mock_annotation(
            trace_id=trace_id,
            annotation_type=AgenticAnnotationType.CONTINUOUS_EVAL,
            annotation_score=i % 2,
            continuous_eval_id=continuous_eval_id,
            run_status=(
                ContinuousEvalRunStatus.PASSED
                if i % 2 == 0
                else ContinuousEvalRunStatus.FAILED
            ),
        )
        agentic_annotation = AgenticAnnotation.from_db_model(annotation)
        annotations.append(agentic_annotation)
        continuous_eval_annotations.append(agentic_annotation)

    annotations = sorted(annotations, key=lambda x: x.created_at, reverse=True)
    continuous_eval_annotations = sorted(
        continuous_eval_annotations,
        key=lambda x: x.created_at,
        reverse=True,
    )

    # test filtering by continuous eval id
    status_code, data = client.list_agentic_annotations_for_trace(
        trace_id=trace_id,
        search_url=f"continuous_eval_id={continuous_eval_id}",
    )
    assert status_code == 200
    assert data.count == len(annotations) - 1
    assert len(data.annotations) == len(annotations) - 1
    for i in range(len(data.annotations)):
        metadata_response = continuous_eval_annotations[i].to_response_model()
        assert data.annotations[i].id == metadata_response.id
        assert (
            data.annotations[i].annotation_score == metadata_response.annotation_score
        )
        assert data.annotations[i].annotation_type == metadata_response.annotation_type
        assert (
            data.annotations[i].continuous_eval_id
            == metadata_response.continuous_eval_id
        )
        assert data.annotations[i].run_status == metadata_response.run_status
        assert data.annotations[i].created_at == metadata_response.created_at
        assert data.annotations[i].updated_at == metadata_response.updated_at

    # test filtering by annotation type
    status_code, data = client.list_agentic_annotations_for_trace(
        trace_id=trace_id,
        search_url=f"annotation_type={AgenticAnnotationType.HUMAN.value}",
    )
    assert status_code == 200
    assert data.count == 1
    assert len(data.annotations) == 1
    human_annotation_metadata_response = human_annotation.to_response_model()
    assert data.annotations[0].id == human_annotation_metadata_response.id
    assert (
        data.annotations[0].annotation_score
        == human_annotation_metadata_response.annotation_score
    )
    assert (
        data.annotations[0].annotation_type
        == human_annotation_metadata_response.annotation_type
    )
    assert (
        data.annotations[0].continuous_eval_id
        == human_annotation_metadata_response.continuous_eval_id
    )
    assert (
        data.annotations[0].run_status == human_annotation_metadata_response.run_status
    )
    assert (
        data.annotations[0].created_at == human_annotation_metadata_response.created_at
    )
    assert (
        data.annotations[0].updated_at == human_annotation_metadata_response.updated_at
    )

    status_code, data = client.list_agentic_annotations_for_trace(
        trace_id=trace_id,
        search_url=f"annotation_type={AgenticAnnotationType.CONTINUOUS_EVAL.value}",
    )
    assert status_code == 200
    assert data.count == len(annotations) - 1
    assert len(data.annotations) == len(annotations) - 1
    for i in range(len(data.annotations)):
        metadata_response = continuous_eval_annotations[i].to_response_model()
        assert data.annotations[i].id == metadata_response.id
        assert (
            data.annotations[i].annotation_score == metadata_response.annotation_score
        )
        assert data.annotations[i].annotation_type == metadata_response.annotation_type
        assert (
            data.annotations[i].continuous_eval_id
            == metadata_response.continuous_eval_id
        )
        assert data.annotations[i].run_status == metadata_response.run_status
        assert data.annotations[i].created_at == metadata_response.created_at
        assert data.annotations[i].updated_at == metadata_response.updated_at

    status_code, data = client.list_agentic_annotations_for_trace(
        trace_id=trace_id,
        search_url=f"annotation_type={AgenticAnnotationType.CONTINUOUS_EVAL.value}",
    )
    assert status_code == 200
    assert data.count == len(annotations) - 1
    assert len(data.annotations) == len(annotations) - 1
    for i in range(len(data.annotations)):
        metadata_response = continuous_eval_annotations[i].to_response_model()
        assert data.annotations[i].id == metadata_response.id
        assert (
            data.annotations[i].annotation_score == metadata_response.annotation_score
        )
        assert data.annotations[i].annotation_type == metadata_response.annotation_type
        assert (
            data.annotations[i].continuous_eval_id
            == metadata_response.continuous_eval_id
        )
        assert data.annotations[i].run_status == metadata_response.run_status
        assert data.annotations[i].created_at == metadata_response.created_at
        assert data.annotations[i].updated_at == metadata_response.updated_at

    # test filtering by annotation score
    status_code, data = client.list_agentic_annotations_for_trace(
        trace_id=trace_id,
        search_url=f"annotation_score=1",
    )
    assert status_code == 200
    assert data.count == len(annotations) // 2
    assert len(data.annotations) == len(annotations) // 2
    for annotation in data.annotations:
        assert annotation.annotation_score == 1

    # test filtering by run status
    status_code, data = client.list_agentic_annotations_for_trace(
        trace_id=trace_id,
        search_url=f"run_status=failed",
    )
    assert status_code == 200
    assert data.count == len(annotations) // 2
    assert len(data.annotations) == len(annotations) // 2
    for annotation in data.annotations:
        assert annotation.run_status == ContinuousEvalRunStatus.FAILED

    # test filtering by created after
    status_code, data = client.list_agentic_annotations_for_trace(
        trace_id=trace_id,
        search_url=f"created_after={annotations[0].created_at.isoformat()}",
    )
    assert status_code == 200
    assert data.count == 1
    assert len(data.annotations) == 1

    # test filtering by created before
    status_code, data = client.list_agentic_annotations_for_trace(
        trace_id=trace_id,
        search_url=f"created_before={annotations[-2].created_at.isoformat()}",
    )
    assert status_code == 200
    assert data.count == 1
    assert len(data.annotations) == 1

    # Cleanup
    for annotation in annotations:
        delete_mock_annotation(annotation.id)
