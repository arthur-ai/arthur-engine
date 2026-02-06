import json
from unittest.mock import patch

import pytest
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue
from opentelemetry.proto.trace.v1.trace_pb2 import ResourceSpans, ScopeSpans, Status

from db_models import DatabaseResourceMetadata, DatabaseSpan, DatabaseTask, DatabaseTraceMetadata
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)
from tests.routes.trace_api.conftest import _create_base_trace_request, _create_span
from utils.constants import SYSTEM_TASK_NAME

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
def test_trace_api_resource_metadata_creation(
    client: GenaiEngineTestClientBase,
):
    """Test that resource metadata is created and associated with spans."""
    task_id = "resource_metadata_test"
    trace_request, resource_span, scope_span = _create_base_trace_request(
        task_id=task_id,
    )

    # Add additional resource attributes
    resource_span.resource.attributes.extend([
        KeyValue(key="host.name", value=AnyValue(string_value="test-host-1")),
        KeyValue(key="service.version", value=AnyValue(string_value="1.0.0")),
    ])

    span = _create_span(
        trace_id=b"resource_meta_trace",
        span_id=b"resource_meta_span",
        name="test_span",
        span_type="LLM",
    )

    scope_span.spans.append(span)
    resource_span.scope_spans.append(scope_span)
    trace_request.resource_spans.append(resource_span)

    # Send the trace
    status_code, response_text = client.trace_api_receive_traces(
        trace_request.SerializeToString(),
    )
    assert status_code == 200

    # Verify resource metadata was created
    db_session = override_get_db_session()

    # Get the span
    db_spans = db_session.query(DatabaseSpan).filter(
        DatabaseSpan.task_id == task_id
    ).all()
    assert len(db_spans) == 1
    db_span = db_spans[0]

    # Verify span has resource_id
    assert db_span.resource_id is not None

    # Verify resource metadata exists
    resource_metadata = db_session.query(DatabaseResourceMetadata).filter(
        DatabaseResourceMetadata.id == db_span.resource_id
    ).first()
    assert resource_metadata is not None
    assert resource_metadata.service_name == "test_service"
    assert resource_metadata.resource_attributes is not None
    assert "service.name" in resource_metadata.resource_attributes
    assert "host.name" in resource_metadata.resource_attributes
    assert resource_metadata.resource_attributes["host.name"] == "test-host-1"
    assert resource_metadata.resource_attributes["service.version"] == "1.0.0"


@pytest.mark.unit_tests
def test_trace_api_resource_metadata_deduplication(
    client: GenaiEngineTestClientBase,
):
    """Test that identical resource attributes are deduplicated."""
    task_id = "resource_dedup_test"

    # Create first trace with specific resource attributes
    trace_request1, resource_span1, scope_span1 = _create_base_trace_request(
        task_id=task_id,
    )
    resource_span1.resource.attributes.extend([
        KeyValue(key="host.name", value=AnyValue(string_value="dedup-host")),
        KeyValue(key="service.version", value=AnyValue(string_value="2.0.0")),
    ])

    span1 = _create_span(
        trace_id=b"dedup_trace_1",
        span_id=b"dedup_span_1",
        name="span1",
        span_type="LLM",
    )
    scope_span1.spans.append(span1)
    resource_span1.scope_spans.append(scope_span1)
    trace_request1.resource_spans.append(resource_span1)

    # Send first trace
    status_code, _ = client.trace_api_receive_traces(
        trace_request1.SerializeToString(),
    )
    assert status_code == 200

    # Create second trace with IDENTICAL resource attributes
    trace_request2, resource_span2, scope_span2 = _create_base_trace_request(
        task_id=task_id,
    )
    resource_span2.resource.attributes.extend([
        KeyValue(key="host.name", value=AnyValue(string_value="dedup-host")),
        KeyValue(key="service.version", value=AnyValue(string_value="2.0.0")),
    ])

    span2 = _create_span(
        trace_id=b"dedup_trace_2",
        span_id=b"dedup_span_2",
        name="span2",
        span_type="LLM",
    )
    scope_span2.spans.append(span2)
    resource_span2.scope_spans.append(scope_span2)
    trace_request2.resource_spans.append(resource_span2)

    # Send second trace
    status_code, _ = client.trace_api_receive_traces(
        trace_request2.SerializeToString(),
    )
    assert status_code == 200

    # Verify both spans reference the same resource_id
    db_session = override_get_db_session()
    db_spans = db_session.query(DatabaseSpan).filter(
        DatabaseSpan.task_id == task_id
    ).all()
    assert len(db_spans) == 2

    # Both spans should have the same resource_id (deduplication)
    assert db_spans[0].resource_id == db_spans[1].resource_id

    # Verify only one resource metadata record was created
    resource_count = db_session.query(DatabaseResourceMetadata).filter(
        DatabaseResourceMetadata.id == db_spans[0].resource_id
    ).count()
    assert resource_count == 1


@pytest.mark.unit_tests
def test_trace_api_resource_metadata_different_attributes(
    client: GenaiEngineTestClientBase,
):
    """Test that different resource attributes create separate metadata records."""
    task_id = "resource_diff_test"

    # Create first trace with specific attributes
    trace_request1, resource_span1, scope_span1 = _create_base_trace_request(
        task_id=task_id,
    )
    resource_span1.resource.attributes.extend([
        KeyValue(key="host.name", value=AnyValue(string_value="host-a")),
    ])

    span1 = _create_span(
        trace_id=b"diff_trace_1",
        span_id=b"diff_span_1",
        name="span1",
        span_type="LLM",
    )
    scope_span1.spans.append(span1)
    resource_span1.scope_spans.append(scope_span1)
    trace_request1.resource_spans.append(resource_span1)

    status_code, _ = client.trace_api_receive_traces(
        trace_request1.SerializeToString(),
    )
    assert status_code == 200

    # Create second trace with DIFFERENT attributes
    trace_request2, resource_span2, scope_span2 = _create_base_trace_request(
        task_id=task_id,
    )
    resource_span2.resource.attributes.extend([
        KeyValue(key="host.name", value=AnyValue(string_value="host-b")),
    ])

    span2 = _create_span(
        trace_id=b"diff_trace_2",
        span_id=b"diff_span_2",
        name="span2",
        span_type="LLM",
    )
    scope_span2.spans.append(span2)
    resource_span2.scope_spans.append(scope_span2)
    trace_request2.resource_spans.append(resource_span2)

    status_code, _ = client.trace_api_receive_traces(
        trace_request2.SerializeToString(),
    )
    assert status_code == 200

    # Verify spans have different resource_ids
    db_session = override_get_db_session()
    db_spans = db_session.query(DatabaseSpan).filter(
        DatabaseSpan.task_id == task_id
    ).all()
    assert len(db_spans) == 2

    # Different resource attributes = different resource_ids
    assert db_spans[0].resource_id != db_spans[1].resource_id

    # Verify two separate resource metadata records exist
    resource_ids = {span.resource_id for span in db_spans}
    assert len(resource_ids) == 2


@pytest.mark.unit_tests
def test_trace_api_trace_metadata_has_root_span_resource_id(
    client: GenaiEngineTestClientBase,
):
    """Test that trace metadata captures the root span's resource_id."""
    task_id = "trace_meta_resource_test"
    trace_request, resource_span, scope_span = _create_base_trace_request(
        task_id=task_id,
    )

    # Create parent (root) span
    parent_span = _create_span(
        trace_id=b"trace_meta_resource",
        span_id=b"parent_span",
        name="parent",
        span_type="LLM",
    )

    # Create child span
    child_span = _create_span(
        trace_id=b"trace_meta_resource",
        span_id=b"child_span",
        parent_span_id=b"parent_span",
        name="child",
        span_type="CHAIN",
    )

    scope_span.spans.extend([parent_span, child_span])
    resource_span.scope_spans.append(scope_span)
    trace_request.resource_spans.append(resource_span)

    status_code, _ = client.trace_api_receive_traces(
        trace_request.SerializeToString(),
    )
    assert status_code == 200

    # Verify trace metadata has root_span_resource_id
    db_session = override_get_db_session()

    # Get all spans for this task
    db_spans = db_session.query(DatabaseSpan).filter(
        DatabaseSpan.task_id == task_id
    ).all()
    assert len(db_spans) == 2

    # Find the parent (root) span - the one without a parent_span_id
    parent_db_span = next((s for s in db_spans if s.parent_span_id is None), None)
    assert parent_db_span is not None
    assert parent_db_span.resource_id is not None

    # Get trace metadata
    trace_metadata = db_session.query(DatabaseTraceMetadata).filter(
        DatabaseTraceMetadata.task_id == task_id
    ).first()
    assert trace_metadata is not None
    assert trace_metadata.root_span_resource_id == parent_db_span.resource_id


# ============================================================================
# SYSTEM TASK TESTS
# ============================================================================


@pytest.mark.unit_tests
def test_trace_api_system_task_assignment_for_taskless_trace(
    client: GenaiEngineTestClientBase,
):
    """Test that traces without task_id are automatically assigned to system task."""
    # Create trace WITHOUT task ID
    trace_request, resource_span, scope_span = _create_base_trace_request(task_id=None)

    span = _create_span(
        trace_id=b"system_task_trace",
        span_id=b"system_task_span",
        name="taskless_span",
        span_type="LLM",
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

    # Verify span was assigned to system task
    db_session = override_get_db_session()

    # Get the system task
    system_task = db_session.query(DatabaseTask).filter(
        DatabaseTask.is_system_task == True,
        DatabaseTask.name == SYSTEM_TASK_NAME,
    ).first()
    assert system_task is not None
    assert system_task.is_agentic is True

    # Verify the span has the system task ID
    # Query by system task ID instead of hardcoded hex span_id
    db_spans = db_session.query(DatabaseSpan).filter(
        DatabaseSpan.task_id == system_task.id
    ).all()

    # Find our specific span by checking trace_id (there may be spans from other tests)
    db_span = next((s for s in db_spans if b"system_task_trace" in bytes.fromhex(s.trace_id)), None)
    assert db_span is not None
    assert db_span.task_id == system_task.id

    # Verify trace metadata also has system task ID
    trace_metadata = db_session.query(DatabaseTraceMetadata).filter(
        DatabaseTraceMetadata.trace_id == db_span.trace_id
    ).first()
    assert trace_metadata is not None
    assert trace_metadata.task_id == system_task.id


@pytest.mark.unit_tests
def test_trace_api_system_task_exists_and_properties(
    client: GenaiEngineTestClientBase,
):
    """Test that system task exists and has correct properties."""
    db_session = override_get_db_session()

    # Get the system task
    system_task = db_session.query(DatabaseTask).filter(
        DatabaseTask.is_system_task == True,
        DatabaseTask.name == SYSTEM_TASK_NAME,
    ).first()

    # Verify system task exists
    assert system_task is not None

    # Verify properties
    assert system_task.name == SYSTEM_TASK_NAME
    assert system_task.is_system_task is True
    assert system_task.is_agentic is True
    assert system_task.archived is False

    # Verify it's the only system task with this name
    system_task_count = db_session.query(DatabaseTask).filter(
        DatabaseTask.is_system_task == True,
        DatabaseTask.name == SYSTEM_TASK_NAME,
    ).count()
    assert system_task_count == 1


@pytest.mark.unit_tests
def test_trace_api_explicit_task_id_not_overridden_by_system_task(
    client: GenaiEngineTestClientBase,
):
    """Test that traces WITH explicit task_id are not assigned to system task."""
    explicit_task_id = "explicit_task_123"

    # Create trace WITH explicit task ID
    trace_request, resource_span, scope_span = _create_base_trace_request(
        task_id=explicit_task_id
    )

    span = _create_span(
        trace_id=b"explicit_task_trace",
        span_id=b"explicit_task_span",
        name="explicit_span",
        span_type="LLM",
    )

    scope_span.spans.append(span)
    resource_span.scope_spans.append(scope_span)
    trace_request.resource_spans.append(resource_span)

    # Send the trace
    status_code, response_text = client.trace_api_receive_traces(
        trace_request.SerializeToString(),
    )
    assert status_code == 200

    # Verify span has the explicit task ID, not system task ID
    db_session = override_get_db_session()

    # Query by the explicit task_id
    db_span = db_session.query(DatabaseSpan).filter(
        DatabaseSpan.task_id == explicit_task_id
    ).first()
    assert db_span is not None
    assert db_span.task_id == explicit_task_id

    # Verify it's NOT the system task
    system_task = db_session.query(DatabaseTask).filter(
        DatabaseTask.is_system_task == True,
    ).first()
    assert db_span.task_id != system_task.id


@pytest.mark.unit_tests
def test_trace_api_multiple_taskless_traces_share_system_task(
    client: GenaiEngineTestClientBase,
):
    """Test that multiple taskless traces all use the same system task."""
    # Create multiple taskless traces
    for i in range(3):
        trace_request, resource_span, scope_span = _create_base_trace_request(
            task_id=None
        )

        span = _create_span(
            trace_id=f"multi_taskless_trace_{i}".encode(),
            span_id=f"multi_taskless_span_{i}".encode(),
            name=f"taskless_span_{i}",
            span_type="LLM",
        )

        scope_span.spans.append(span)
        resource_span.scope_spans.append(scope_span)
        trace_request.resource_spans.append(resource_span)

        status_code, _ = client.trace_api_receive_traces(
            trace_request.SerializeToString(),
        )
        assert status_code == 200

    # Verify all spans use the same system task
    db_session = override_get_db_session()

    system_task = db_session.query(DatabaseTask).filter(
        DatabaseTask.is_system_task == True,
    ).first()
    assert system_task is not None

    # Get all spans from the system task
    system_task_spans = db_session.query(DatabaseSpan).filter(
        DatabaseSpan.task_id == system_task.id
    ).all()

    # Should have at least our 3 spans (could have more from other tests)
    assert len(system_task_spans) >= 3

    # Verify they all have the same task_id
    task_ids = {span.task_id for span in system_task_spans}
    assert len(task_ids) == 1
    assert task_ids.pop() == system_task.id
