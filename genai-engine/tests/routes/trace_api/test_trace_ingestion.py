import json
import random
from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

import pytest
from arthur_common.models.agent_governance_schemas import (
    GCPAgentCreationSource,
    TaskMetadata,
)
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue
from opentelemetry.proto.trace.v1.trace_pb2 import Status

from db_models import DatabaseServiceNameTaskMapping, DatabaseSpan, DatabaseTask
from services.trace.trace_ingestion_service import TraceIngestionService
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)
from tests.routes.trace_api.conftest import _create_base_trace_request, _create_span

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def get_all_spans_from_traces(traces):
    """Helper function to extract all spans from traces response."""
    spans = []
    for trace in traces:
        for root_span in trace.root_spans:
            spans.extend(get_all_spans_from_nested_span(root_span))
    return spans


def get_all_spans_from_nested_span(nested_span):
    """Helper function to extract all spans from a nested span structure recursively."""
    spans = [nested_span]
    for child in nested_span.children:
        spans.extend(get_all_spans_from_nested_span(child))
    return spans


# ============================================================================
# CORE TRACE INGESTION TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_trace_api_receive_traces_with_resource_attributes(
    client: GenaiEngineTestClientBase,
    sample_trace_api_protobuf,
):
    """Test trace ingestion via API with resource attributes for task ID extraction."""

    # Test spans with task IDs in resource attributes (should be accepted)
    status_code, response_text = client.trace_api_receive_traces(
        sample_trace_api_protobuf,
    )
    assert status_code == 200

    response_json = json.loads(response_text)
    assert response_json["total_spans"] == 1
    assert response_json["accepted_spans"] == 1
    assert response_json["rejected_spans"] == 0
    assert response_json["status"] == "success"


@pytest.mark.unit_tests
def test_trace_api_receive_traces_missing_task_id(
    client: GenaiEngineTestClientBase,
):
    """Test trace ingestion with missing task ID should be accepted (unregistered trace)."""

    # Create trace without task ID in resource attributes
    trace_request, resource_span, scope_span = _create_base_trace_request(task_id=None)

    # Create a span without a task ID
    span = _create_span(
        trace_id=b"missing_task_id_trace_api",
        span_id=b"missing_task_id_span_api",
        name="missing_task_id_guardrail_span_api",
        span_type="GUARDRAIL",
    )

    scope_span.spans.append(span)
    resource_span.scope_spans.append(scope_span)
    trace_request.resource_spans.append(resource_span)

    # Send the trace
    status_code, response_text = client.trace_api_receive_traces(
        trace_request.SerializeToString(),
    )
    assert status_code == 200

    response_json = json.loads(response_text)
    assert response_json["accepted_spans"] == 1
    assert response_json["rejected_spans"] == 0
    assert response_json["status"] == "success"


@pytest.mark.unit_tests
def test_trace_api_receive_traces_multiple_spans(
    client: GenaiEngineTestClientBase,
):
    """Test ingesting trace with multiple spans including parent-child relationships."""

    # Create trace with task ID in resource attributes
    task_id = "multi_span_task_api"
    trace_id = b"multi_span_trace_api"
    parent_span_id = b"parent_span_api"
    child_span_id = b"child_span_api"

    trace_request, resource_span, scope_span = _create_base_trace_request(
        task_id=task_id,
    )

    # Create parent span
    parent_span = _create_span(
        trace_id=trace_id,
        span_id=parent_span_id,
        name="parent_span_api",
        span_type="LLM",
        model_name="gpt-4-turbo",
    )

    # Create child span
    child_span = _create_span(
        trace_id=trace_id,
        parent_span_id=parent_span_id,
        span_id=child_span_id,
        name="child_span_api",
        span_type="CHAIN",
        status=Status(message="ok", code=Status.STATUS_CODE_OK),
    )

    # Add spans in order that tests SQLAlchemy handling of optional parent_span_id
    scope_span.spans.append(child_span)  # Child first
    scope_span.spans.append(parent_span)  # Parent second
    resource_span.scope_spans.append(scope_span)
    trace_request.resource_spans.append(resource_span)

    # Send the trace
    status_code, response_text = client.trace_api_receive_traces(
        trace_request.SerializeToString(),
    )
    assert status_code == 200

    response_json = json.loads(response_text)
    assert response_json["total_spans"] == 2
    assert response_json["accepted_spans"] == 2
    assert response_json["rejected_spans"] == 0
    assert response_json["status"] == "success"


@pytest.mark.unit_tests
def test_trace_api_receive_traces_error_handling(
    client: GenaiEngineTestClientBase,
    sample_trace_api_protobuf,
):
    """Test error handling in trace API ingestion endpoint."""

    # Test invalid protobuf
    invalid_trace = b"invalid_protobuf_data_api"
    status_code, response_text = client.trace_api_receive_traces(invalid_trace)
    assert status_code == 400
    assert "Invalid protobuf message format" in json.loads(response_text)["detail"]

    # Test server error using patch
    with patch(
        "repositories.span_repository.SpanRepository.create_traces",
        side_effect=Exception("API Test error"),
    ):
        status_code, response_text = client.trace_api_receive_traces(
            sample_trace_api_protobuf,
        )
        assert status_code == 500
        assert "API Test error" in json.loads(response_text)["detail"]


@pytest.mark.unit_tests
def test_trace_api_resource_attributes_processing(
    client: GenaiEngineTestClientBase,
    sample_trace_api_protobuf,
):
    """Test resource attributes processing including task ID extraction and version injection."""

    # Send trace
    status_code, response_text = client.trace_api_receive_traces(
        sample_trace_api_protobuf,
    )
    assert status_code == 200

    # Query the trace using API to verify processing
    status_code, traces_response = client.trace_api_list_traces_metadata(
        task_ids=["api_task_123"],
    )
    assert status_code == 200

    assert traces_response.count == 1
    assert len(traces_response.traces) == 1

    # Get the full trace to check spans
    trace_id = traces_response.traces[0].trace_id
    status_code, trace_data = client.trace_api_get_trace_by_id(trace_id)
    assert status_code == 200

    # Check that all spans have the correct task ID and version
    all_spans = get_all_spans_from_traces([trace_data])
    for span in all_spans:
        # Verify task ID extraction
        assert span.task_id == "api_task_123"
        # Verify version injection
        assert "arthur_span_version" in span.raw_data
        assert span.raw_data["arthur_span_version"] == "arthur_span_v1"


@pytest.mark.unit_tests
def test_trace_api_session_id_and_status_code_processing(
    client: GenaiEngineTestClientBase,
):
    """Test session_id and status_code extraction and normalization during trace ingestion."""

    # Test cases: (session_id, status_code, expected_normalized_status)
    test_cases = [
        ("session_api_123", Status.STATUS_CODE_OK, "Ok"),
        ("session_api_456", Status.STATUS_CODE_ERROR, "Error"),
        (None, Status.STATUS_CODE_OK, "Ok"),  # No session_id
    ]

    for i, (session_id, status_code, expected_status) in enumerate(test_cases):
        # Use unique task ID for each test case
        task_id = f"session_status_api_test_{i}"

        # Create trace request for this test case
        trace_request, resource_span, scope_span = _create_base_trace_request(
            task_id=task_id,
        )

        # Create span with specific session_id and status_code
        span = _create_span(
            trace_id=f"trace_session_api_test_{i}".encode(),
            span_id=f"span_session_api_test_{i}".encode(),
            name=f"test_span_api_{i}",
            span_type="LLM",
            status=Status(code=status_code),
            session_id=session_id,
        )

        scope_span.spans.append(span)
        resource_span.scope_spans.append(scope_span)
        trace_request.resource_spans.append(resource_span)

        # Send the trace
        status_code, response_text = client.trace_api_receive_traces(
            trace_request.SerializeToString(),
        )
        assert status_code == 200

        # Query the database to verify processing
        from db_models import DatabaseSpan
        from tests.clients.base_test_client import override_get_db_session

        db_session = override_get_db_session()

        # Find the span in the database by task_id
        db_spans = (
            db_session.query(DatabaseSpan).filter(DatabaseSpan.task_id == task_id).all()
        )
        assert (
            len(db_spans) == 1
        ), f"Expected 1 span, found {len(db_spans)} for task_id {task_id}"

        db_span = db_spans[0]

        # Verify session_id is correctly stored
        assert (
            db_span.session_id == session_id
        ), f"Expected session_id {session_id}, got {db_span.session_id}"

        # Verify status_code is correctly normalized and stored
        assert (
            db_span.status_code == expected_status
        ), f"Expected status_code {expected_status}, got {db_span.status_code}"


@pytest.mark.unit_tests
def test_trace_api_batch_ingestion_performance(
    client: GenaiEngineTestClientBase,
):
    """Test batch ingestion of multiple traces with multiple spans each."""

    # Create a large trace request with multiple traces
    task_id = "batch_test_api"
    trace_request, resource_span, scope_span = _create_base_trace_request(
        task_id=task_id,
    )

    # Create multiple traces with multiple spans each
    for trace_num in range(3):
        trace_id_bytes = f"batch_trace_api_{trace_num}".encode()

        # Create 2 spans per trace
        for span_num in range(2):
            span = _create_span(
                trace_id=trace_id_bytes,
                span_id=f"batch_span_api_{trace_num}_{span_num}".encode(),
                name=f"batch_span_{trace_num}_{span_num}",
                span_type="LLM" if span_num == 0 else "CHAIN",
                parent_span_id=(
                    f"batch_span_api_{trace_num}_0".encode() if span_num == 1 else None
                ),
            )
            scope_span.spans.append(span)

    resource_span.scope_spans.append(scope_span)
    trace_request.resource_spans.append(resource_span)

    # Send the batch
    status_code, response_text = client.trace_api_receive_traces(
        trace_request.SerializeToString(),
    )
    assert status_code == 200

    response_json = json.loads(response_text)
    assert response_json["total_spans"] == 6  # 3 traces * 2 spans each
    assert response_json["accepted_spans"] == 6
    assert response_json["rejected_spans"] == 0
    assert response_json["status"] == "success"

    # Verify traces were created correctly
    status_code, traces_data = client.trace_api_list_traces_metadata(task_ids=[task_id])
    assert status_code == 200
    assert traces_data.count == 3  # 3 traces created


@pytest.mark.unit_tests
def test_trace_api_token_count_calculation_from_messages(
    client: GenaiEngineTestClientBase,
):
    """Test that token counts and costs are calculated from messages when not provided."""

    # Create a trace with messages but no token count/cost attributes
    task_id = "token_calc_test_api"
    trace_request, resource_span, scope_span = _create_base_trace_request(
        task_id=task_id,
    )

    span = _create_span(
        trace_id=b"token_calc_trace_api",
        span_id=b"token_calc_span_api",
        name="token_calc_span",
        span_type="LLM",
        model_name="gpt-4-0613",
    )

    # Add input and output messages manually (no token count attributes)
    span.attributes.extend(
        [
            KeyValue(
                key="llm.input_messages.0.message.role",
                value=AnyValue(string_value="user"),
            ),
            KeyValue(
                key="llm.input_messages.0.message.content",
                value=AnyValue(string_value="Hello, how are you?"),
            ),
            KeyValue(
                key="llm.output_messages.0.message.role",
                value=AnyValue(string_value="assistant"),
            ),
            KeyValue(
                key="llm.output_messages.0.message.content",
                value=AnyValue(string_value="I'm doing well, thank you for asking!"),
            ),
        ],
    )

    scope_span.spans.append(span)
    resource_span.scope_spans.append(scope_span)
    trace_request.resource_spans.append(resource_span)

    # Send the trace
    status_code, response_text = client.trace_api_receive_traces(
        trace_request.SerializeToString(),
    )
    assert status_code == 200

    db_session = override_get_db_session()
    db_spans = (
        db_session.query(DatabaseSpan).filter(DatabaseSpan.task_id == task_id).all()
    )
    assert len(db_spans) == 1

    db_span = db_spans[0]

    assert db_span.prompt_token_count == 13
    assert db_span.completion_token_count == 17
    assert db_span.total_token_count == 30

    assert db_span.prompt_token_cost == 0.00039
    assert db_span.completion_token_cost == 0.00102
    assert db_span.total_token_cost == 0.00141


# ============================================================================
# RESOURCE METADATA TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_trace_api_resource_metadata_deduplication(
    client: GenaiEngineTestClientBase,
):
    """Test that traces with identical resource attributes share the same resource_id."""

    # Create two traces with identical resource attributes
    task_id = "resource_dedup_test"

    # First trace
    trace_request_1, resource_span_1, scope_span_1 = _create_base_trace_request(
        task_id=task_id,
    )
    span_1 = _create_span(
        trace_id=b"trace_dedup_1",
        span_id=b"span_dedup_1",
        name="dedup_span_1",
        span_type="LLM",
    )
    scope_span_1.spans.append(span_1)
    resource_span_1.scope_spans.append(scope_span_1)
    trace_request_1.resource_spans.append(resource_span_1)

    # Second trace with identical resource attributes
    trace_request_2, resource_span_2, scope_span_2 = _create_base_trace_request(
        task_id=task_id,
    )
    span_2 = _create_span(
        trace_id=b"trace_dedup_2",
        span_id=b"span_dedup_2",
        name="dedup_span_2",
        span_type="LLM",
    )
    scope_span_2.spans.append(span_2)
    resource_span_2.scope_spans.append(scope_span_2)
    trace_request_2.resource_spans.append(resource_span_2)

    # Send both traces
    status_code_1, _ = client.trace_api_receive_traces(
        trace_request_1.SerializeToString(),
    )
    assert status_code_1 == 200

    status_code_2, _ = client.trace_api_receive_traces(
        trace_request_2.SerializeToString(),
    )
    assert status_code_2 == 200

    # Query database to verify both spans reference the same resource_id
    from db_models import DatabaseResourceMetadata

    db_session = override_get_db_session()

    db_span_1 = (
        db_session.query(DatabaseSpan)
        .filter(DatabaseSpan.span_id == span_1.span_id.hex())
        .first()
    )
    db_span_2 = (
        db_session.query(DatabaseSpan)
        .filter(DatabaseSpan.span_id == span_2.span_id.hex())
        .first()
    )

    assert db_span_1 is not None
    assert db_span_2 is not None
    assert db_span_1.resource_id is not None
    assert db_span_2.resource_id is not None

    # Both spans should reference the same resource_id
    assert db_span_1.resource_id == db_span_2.resource_id

    # Verify only one resource metadata entry exists for this resource_id
    resource_count = (
        db_session.query(DatabaseResourceMetadata)
        .filter(DatabaseResourceMetadata.id == db_span_1.resource_id)
        .count()
    )
    assert resource_count == 1


@pytest.mark.unit_tests
def test_trace_api_resource_metadata_different_attributes(
    client: GenaiEngineTestClientBase,
):
    """Test that traces with different resource attributes get different resource_ids."""

    # First trace with task_id_1
    task_id_1 = "resource_diff_test_1"
    trace_request_1, resource_span_1, scope_span_1 = _create_base_trace_request(
        task_id=task_id_1,
    )
    span_1 = _create_span(
        trace_id=b"trace_diff_1",
        span_id=b"span_diff_1",
        name="diff_span_1",
        span_type="LLM",
    )
    scope_span_1.spans.append(span_1)
    resource_span_1.scope_spans.append(scope_span_1)
    trace_request_1.resource_spans.append(resource_span_1)

    # Second trace with task_id_2 (different resource attributes)
    task_id_2 = "resource_diff_test_2"
    trace_request_2, resource_span_2, scope_span_2 = _create_base_trace_request(
        task_id=task_id_2,
    )
    span_2 = _create_span(
        trace_id=b"trace_diff_2",
        span_id=b"span_diff_2",
        name="diff_span_2",
        span_type="LLM",
    )
    scope_span_2.spans.append(span_2)
    resource_span_2.scope_spans.append(scope_span_2)
    trace_request_2.resource_spans.append(resource_span_2)

    # Send both traces
    status_code_1, _ = client.trace_api_receive_traces(
        trace_request_1.SerializeToString(),
    )
    assert status_code_1 == 200

    status_code_2, _ = client.trace_api_receive_traces(
        trace_request_2.SerializeToString(),
    )
    assert status_code_2 == 200

    # Query database to verify spans have different resource_ids
    db_session = override_get_db_session()

    db_span_1 = (
        db_session.query(DatabaseSpan)
        .filter(DatabaseSpan.span_id == span_1.span_id.hex())
        .first()
    )
    db_span_2 = (
        db_session.query(DatabaseSpan)
        .filter(DatabaseSpan.span_id == span_2.span_id.hex())
        .first()
    )

    assert db_span_1 is not None
    assert db_span_2 is not None
    assert db_span_1.resource_id is not None
    assert db_span_2.resource_id is not None

    # Spans should have different resource_ids
    assert db_span_1.resource_id != db_span_2.resource_id


@pytest.mark.unit_tests
def test_trace_api_resource_metadata_storage(
    client: GenaiEngineTestClientBase,
):
    """Test that resource attributes are correctly stored in resource_metadata table."""

    task_id = "resource_storage_test"
    service_name = "test_service"

    trace_request, resource_span, scope_span = _create_base_trace_request(
        task_id=task_id,
    )

    # Verify resource attributes include service.name and arthur.task
    resource_attrs = {
        attr.key: attr.value.string_value for attr in resource_span.resource.attributes
    }
    assert resource_attrs.get("service.name") == service_name
    assert resource_attrs.get("arthur.task") == task_id

    span = _create_span(
        trace_id=b"trace_storage",
        span_id=b"span_storage",
        name="storage_span",
        span_type="LLM",
    )
    scope_span.spans.append(span)
    resource_span.scope_spans.append(scope_span)
    trace_request.resource_spans.append(resource_span)

    # Send trace
    status_code, _ = client.trace_api_receive_traces(
        trace_request.SerializeToString(),
    )
    assert status_code == 200

    # Query database to verify resource metadata storage
    from db_models import DatabaseResourceMetadata

    db_session = override_get_db_session()

    db_span = (
        db_session.query(DatabaseSpan)
        .filter(DatabaseSpan.span_id == span.span_id.hex())
        .first()
    )
    assert db_span is not None
    assert db_span.resource_id is not None

    # Retrieve resource metadata
    resource_metadata = (
        db_session.query(DatabaseResourceMetadata)
        .filter(DatabaseResourceMetadata.id == db_span.resource_id)
        .first()
    )
    assert resource_metadata is not None
    assert resource_metadata.service_name == service_name
    assert resource_metadata.resource_attributes is not None

    # Verify resource attributes are stored as JSON
    stored_attrs = resource_metadata.resource_attributes
    assert stored_attrs.get("service.name") == service_name
    assert stored_attrs.get("arthur.task") == task_id


@pytest.mark.unit_tests
def test_trace_api_trace_metadata_root_span_resource_id(
    client: GenaiEngineTestClientBase,
):
    """Test that trace_metadata correctly links to root span's resource_id."""

    task_id = "trace_metadata_resource_test"
    trace_id = b"trace_with_resource"
    parent_span_id = b"parent_span_resource"
    child_span_id = b"child_span_resource"

    trace_request, resource_span, scope_span = _create_base_trace_request(
        task_id=task_id,
    )

    # Create parent span (root span)
    parent_span = _create_span(
        trace_id=trace_id,
        span_id=parent_span_id,
        name="parent_span",
        span_type="LLM",
    )

    # Create child span
    child_span = _create_span(
        trace_id=trace_id,
        parent_span_id=parent_span_id,
        span_id=child_span_id,
        name="child_span",
        span_type="CHAIN",
    )

    scope_span.spans.append(parent_span)
    scope_span.spans.append(child_span)
    resource_span.scope_spans.append(scope_span)
    trace_request.resource_spans.append(resource_span)

    # Send trace
    status_code, _ = client.trace_api_receive_traces(
        trace_request.SerializeToString(),
    )
    assert status_code == 200

    # Query database to verify trace_metadata links to root span's resource_id
    from db_models import DatabaseTraceMetadata

    db_session = override_get_db_session()

    # Get the parent (root) span
    db_parent_span = (
        db_session.query(DatabaseSpan)
        .filter(DatabaseSpan.span_id == parent_span_id.hex())
        .first()
    )
    assert db_parent_span is not None
    assert db_parent_span.resource_id is not None
    assert db_parent_span.parent_span_id is None  # Verify it's the root span

    # Get trace metadata
    trace_metadata = (
        db_session.query(DatabaseTraceMetadata)
        .filter(DatabaseTraceMetadata.trace_id == trace_id.hex())
        .first()
    )
    assert trace_metadata is not None
    assert trace_metadata.root_span_resource_id is not None

    # Verify trace_metadata.root_span_resource_id matches root span's resource_id
    assert trace_metadata.root_span_resource_id == db_parent_span.resource_id


# ============================================================================
# GCP RESOURCE ID DEDUP TESTS (Phase 5)
# ============================================================================


def _create_gcp_task(db_session, engine_id: str, name: str = None) -> DatabaseTask:
    """Helper to create a GCP task with creation_source metadata."""
    task_id = str(uuid4())
    task_name = name or f"gcp_agent_{random.random()}"
    task_metadata = TaskMetadata(
        creation_source=GCPAgentCreationSource(
            gcp_project_id="test-project",
            gcp_region="us-central1",
            gcp_reasoning_engine_id=engine_id,
        ),
    )
    db_task = DatabaseTask(
        id=task_id,
        name=task_name,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        is_agentic=True,
        is_autocreated=False,
        task_metadata=task_metadata.model_dump(mode="json"),
        archived=False,
    )
    db_session.add(db_task)
    db_session.commit()
    return db_task


def _cleanup_task(db_session, task_id: str):
    """Helper to clean up a task and its service name mappings."""
    db_session.query(DatabaseServiceNameTaskMapping).filter(
        DatabaseServiceNameTaskMapping.task_id == task_id,
    ).delete(synchronize_session=False)
    db_session.query(DatabaseTask).filter(DatabaseTask.id == task_id).delete(
        synchronize_session=False,
    )
    db_session.commit()


@pytest.mark.unit_tests
def test_resolve_task_id_matches_gcp_task_via_cloud_resource_id():
    """Direct OTEL traces with cloud.resource_id should map to existing GCP tasks."""
    db_session = override_get_db_session()
    service = TraceIngestionService(db_session)

    engine_id = f"engine_{uuid4().hex[:8]}"
    gcp_task = _create_gcp_task(db_session, engine_id)

    try:
        service_name = f"test_service_{random.random()}"
        resource_attributes = {
            "cloud.resource_id": f"projects/test-project/locations/us-central1/reasoningEngines/{engine_id}",
        }

        # Mock find_by_gcp_engine_id since .astext is PostgreSQL-only
        with patch(
            "repositories.tasks_repository.TaskRepository.find_by_gcp_engine_id",
            return_value=gcp_task,
        ):
            resolved_id = service._resolve_task_id(
                explicit_task_id=None,
                service_name=service_name,
                resource_attributes=resource_attributes,
            )

        assert resolved_id == gcp_task.id
    finally:
        _cleanup_task(db_session, gcp_task.id)


@pytest.mark.unit_tests
def test_resolve_task_id_creates_mapping_after_gcp_match():
    """After matching via cloud.resource_id, a service_name mapping should be created."""
    db_session = override_get_db_session()
    service = TraceIngestionService(db_session)

    engine_id = f"engine_{uuid4().hex[:8]}"
    gcp_task = _create_gcp_task(db_session, engine_id)

    try:
        service_name = f"test_service_{random.random()}"
        resource_attributes = {
            "cloud.resource_id": f"projects/test-project/locations/us-central1/reasoningEngines/{engine_id}",
        }

        # Mock find_by_gcp_engine_id since .astext is PostgreSQL-only
        with patch(
            "repositories.tasks_repository.TaskRepository.find_by_gcp_engine_id",
            return_value=gcp_task,
        ):
            resolved_id = service._resolve_task_id(
                explicit_task_id=None,
                service_name=service_name,
                resource_attributes=resource_attributes,
            )
        assert resolved_id == gcp_task.id

        # Verify mapping was created for future cache hits
        mapping = (
            db_session.query(DatabaseServiceNameTaskMapping)
            .filter(DatabaseServiceNameTaskMapping.service_name == service_name)
            .first()
        )
        assert mapping is not None
        assert mapping.task_id == gcp_task.id
    finally:
        _cleanup_task(db_session, gcp_task.id)


@pytest.mark.unit_tests
def test_resolve_task_id_uses_cached_mapping_on_subsequent_calls():
    """Subsequent traces should use the service_name mapping (cache hit)."""
    db_session = override_get_db_session()
    service = TraceIngestionService(db_session)

    engine_id = f"engine_{uuid4().hex[:8]}"
    gcp_task = _create_gcp_task(db_session, engine_id)

    try:
        service_name = f"test_service_{random.random()}"
        resource_attributes = {
            "cloud.resource_id": f"projects/test-project/locations/us-central1/reasoningEngines/{engine_id}",
        }

        # First call: matches via cloud.resource_id, creates mapping
        # Mock find_by_gcp_engine_id since .astext is PostgreSQL-only
        with patch(
            "repositories.tasks_repository.TaskRepository.find_by_gcp_engine_id",
            return_value=gcp_task,
        ):
            first_id = service._resolve_task_id(
                explicit_task_id=None,
                service_name=service_name,
                resource_attributes=resource_attributes,
            )
        assert first_id == gcp_task.id

        # Second call: should use cached mapping (step 3), no mock needed
        second_id = service._resolve_task_id(
            explicit_task_id=None,
            service_name=service_name,
            resource_attributes=resource_attributes,
        )
        assert second_id == gcp_task.id
    finally:
        _cleanup_task(db_session, gcp_task.id)


@pytest.mark.unit_tests
def test_resolve_task_id_auto_creates_when_no_resource_id():
    """Traces without cloud.resource_id should auto-create OTEL tasks as before."""
    db_session = override_get_db_session()
    service = TraceIngestionService(db_session)

    service_name = f"new_otel_service_{random.random()}"
    created_task_id = None

    try:
        resolved_id = service._resolve_task_id(
            explicit_task_id=None,
            service_name=service_name,
            resource_attributes={},
        )

        assert resolved_id is not None
        created_task_id = resolved_id

        db_task = (
            db_session.query(DatabaseTask)
            .filter(DatabaseTask.id == resolved_id)
            .first()
        )
        assert db_task is not None
        assert db_task.name == service_name
        assert db_task.is_autocreated is True
    finally:
        if created_task_id:
            _cleanup_task(db_session, created_task_id)


@pytest.mark.unit_tests
def test_resolve_task_id_auto_creates_when_resource_id_doesnt_match():
    """Traces with cloud.resource_id that doesn't match any GCP task should auto-create."""
    db_session = override_get_db_session()
    service = TraceIngestionService(db_session)

    service_name = f"unknown_service_{random.random()}"
    resource_attributes = {
        "cloud.resource_id": "projects/test-project/locations/us-central1/reasoningEngines/nonexistent_engine",
    }
    created_task_id = None

    try:
        # Mock find_by_gcp_engine_id since .astext is PostgreSQL-only
        with patch(
            "repositories.tasks_repository.TaskRepository.find_by_gcp_engine_id",
            return_value=None,
        ):
            resolved_id = service._resolve_task_id(
                explicit_task_id=None,
                service_name=service_name,
                resource_attributes=resource_attributes,
            )

        assert resolved_id is not None
        created_task_id = resolved_id

        db_task = (
            db_session.query(DatabaseTask)
            .filter(DatabaseTask.id == resolved_id)
            .first()
        )
        assert db_task is not None
        assert db_task.name == service_name
        assert db_task.is_autocreated is True
    finally:
        if created_task_id:
            _cleanup_task(db_session, created_task_id)


@pytest.mark.unit_tests
def test_resolve_task_id_explicit_task_id_takes_priority():
    """Explicit task_id (arthur.task) should take priority over cloud.resource_id."""
    db_session = override_get_db_session()
    service = TraceIngestionService(db_session)

    engine_id = f"engine_{uuid4().hex[:8]}"
    gcp_task = _create_gcp_task(db_session, engine_id)
    explicit_id = "explicit-task-id-123"

    try:
        resource_attributes = {
            "cloud.resource_id": f"projects/test-project/locations/us-central1/reasoningEngines/{engine_id}",
        }

        resolved_id = service._resolve_task_id(
            explicit_task_id=explicit_id,
            service_name="some_service",
            resource_attributes=resource_attributes,
        )

        # Explicit task_id should win
        assert resolved_id == explicit_id
    finally:
        _cleanup_task(db_session, gcp_task.id)


@pytest.mark.unit_tests
def test_resolve_task_id_existing_mapping_takes_priority_over_resource_id():
    """Existing service_name mapping should take priority over cloud.resource_id matching."""
    db_session = override_get_db_session()
    service = TraceIngestionService(db_session)

    engine_id = f"engine_{uuid4().hex[:8]}"
    gcp_task = _create_gcp_task(db_session, engine_id)

    # Create a different task with a pre-existing mapping
    other_task_id = str(uuid4())
    other_task = DatabaseTask(
        id=other_task_id,
        name=f"other_task_{random.random()}",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        is_agentic=True,
        is_autocreated=True,
        archived=False,
    )
    db_session.add(other_task)
    db_session.commit()

    service_name = f"mapped_service_{random.random()}"
    mapping = DatabaseServiceNameTaskMapping(
        service_name=service_name,
        task_id=other_task_id,
        created_at=datetime.now(),
    )
    db_session.add(mapping)
    db_session.commit()

    try:
        resource_attributes = {
            "cloud.resource_id": f"projects/test-project/locations/us-central1/reasoningEngines/{engine_id}",
        }

        resolved_id = service._resolve_task_id(
            explicit_task_id=None,
            service_name=service_name,
            resource_attributes=resource_attributes,
        )

        # Existing mapping should win over cloud.resource_id
        assert resolved_id == other_task_id
    finally:
        _cleanup_task(db_session, gcp_task.id)
        _cleanup_task(db_session, other_task_id)


@pytest.mark.unit_tests
def test_resolve_task_id_handles_invalid_resource_id_gracefully():
    """Invalid cloud.resource_id should not crash; should fall through to auto-create."""
    db_session = override_get_db_session()
    service = TraceIngestionService(db_session)

    service_name = f"invalid_resource_service_{random.random()}"
    resource_attributes = {
        "cloud.resource_id": "not-a-valid-gcp-path",
    }
    created_task_id = None

    try:
        resolved_id = service._resolve_task_id(
            explicit_task_id=None,
            service_name=service_name,
            resource_attributes=resource_attributes,
        )

        # Should fall through to auto-create since parse_gcp_resource_path returns None
        assert resolved_id is not None
        created_task_id = resolved_id

        db_task = (
            db_session.query(DatabaseTask)
            .filter(DatabaseTask.id == resolved_id)
            .first()
        )
        assert db_task is not None
        assert db_task.is_autocreated is True
    finally:
        if created_task_id:
            _cleanup_task(db_session, created_task_id)
