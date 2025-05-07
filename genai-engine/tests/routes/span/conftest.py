import uuid
from datetime import datetime, timedelta
from typing import Generator, List

import pytest
from dependencies import get_application_config, get_bi_client
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue
from opentelemetry.proto.trace.v1.trace_pb2 import ResourceSpans, ScopeSpans, Span
from repositories.span_repository import SpanRepository
from schemas.internal_schemas import Span as InternalSpan

from shield.db_models.db_models import DatabaseSpan
from tests.test_client import override_get_db_session


def _delete_spans_from_db(db_session, span_ids):
    """Helper function to delete spans directly from the database."""
    if not span_ids:
        return

    # Delete spans with the given span_ids
    db_session.query(DatabaseSpan).filter(DatabaseSpan.span_id.in_(span_ids)).delete(
        synchronize_session=False,
    )
    db_session.commit()


def _create_base_trace_request():
    """Create a base ExportTraceServiceRequest with resource attributes."""
    trace_request = ExportTraceServiceRequest()
    resource_span = ResourceSpans()
    resource_span.resource.attributes.extend(
        [KeyValue(key="service.name", value=AnyValue(string_value="test_service"))],
    )
    scope_span = ScopeSpans()
    scope_span.scope.name = "test_scope"

    return trace_request, resource_span, scope_span


def _create_llm_span(trace_id, span_id, name, include_task_id=True, model_name="gpt-4"):
    """Helper function to create an LLM span with or without task ID."""
    span = Span()
    span.trace_id = trace_id
    span.span_id = span_id
    span.name = name
    span.kind = Span.SPAN_KIND_INTERNAL
    span.start_time_unix_nano = int(datetime.now().timestamp() * 1e9)
    span.end_time_unix_nano = int(
        (datetime.now() + timedelta(seconds=1)).timestamp() * 1e9,
    )

    # Basic LLM attribute
    attributes = [
        KeyValue(key="openinference.span.kind", value=AnyValue(string_value="LLM")),
        KeyValue(key="llm.model_name", value=AnyValue(string_value=model_name)),
    ]

    # Metadata with or without task ID
    metadata = {
        "ls_provider": "openai",
        "ls_model_name": model_name,
        "ls_model_type": "chat",
    }

    if include_task_id:
        metadata["arthur.task"] = f"task_id_{span_id.hex()}"

    metadata_str = str(metadata).replace("'", '"')
    attributes.append(
        KeyValue(
            key="metadata",
            value=AnyValue(string_value=metadata_str),
        ),
    )

    span.attributes.extend(attributes)
    return span


@pytest.fixture(scope="function")
def create_span() -> Generator[InternalSpan, None, None]:
    db_session = override_get_db_session()
    application_config = get_application_config(session=db_session)
    bi_client = get_bi_client()
    span_repo = SpanRepository(db_session)

    now = datetime.now()

    # Create a test span
    span = InternalSpan(
        id=str(uuid.uuid4()),
        trace_id="test_trace_id",
        span_id="test_span_id",
        task_id="test_task",
        start_time=now,
        end_time=now + timedelta(seconds=1),
        raw_data={},
        created_at=now,
        updated_at=now,
    )

    span_repo.store_spans([span])

    yield span

    # Cleanup: Delete the span from the database after the test
    _delete_spans_from_db(db_session, [span.span_id])


@pytest.fixture(scope="function")
def create_test_spans() -> Generator[List[InternalSpan], None, None]:
    """Create multiple test spans with different attributes for query testing."""
    db_session = override_get_db_session()
    application_config = get_application_config(session=db_session)
    bi_client = get_bi_client()
    span_repo = SpanRepository(db_session)

    # Create spans with different attributes
    spans = []
    base_time = datetime.now()

    # Span 1: User1, Task1, Trace1
    span1 = InternalSpan(
        id=str(uuid.uuid4()),
        trace_id="trace1",
        span_id="span1",
        task_id="task1",
        start_time=base_time - timedelta(days=2),
        end_time=base_time - timedelta(days=2) + timedelta(seconds=1),
        raw_data={"model": "gpt-4"},
        created_at=base_time - timedelta(days=2),
        updated_at=base_time - timedelta(days=2),
    )
    spans.append(span1)

    # Span 2: User1, Task2, Trace1
    span2 = InternalSpan(
        id=str(uuid.uuid4()),
        trace_id="trace1",
        span_id="span2",
        task_id="task2",
        start_time=base_time - timedelta(days=1),
        end_time=base_time - timedelta(days=1) + timedelta(seconds=1),
        raw_data={"model": "gpt-3.5"},
        created_at=base_time - timedelta(days=1) + timedelta(seconds=1),
        updated_at=base_time - timedelta(days=1) + timedelta(seconds=1),
    )
    spans.append(span2)

    # Span 3: User2, Task1, Trace2
    span3 = InternalSpan(
        id=str(uuid.uuid4()),
        trace_id="trace2",
        span_id="span3",
        task_id="task1",
        start_time=base_time,
        end_time=base_time + timedelta(seconds=1),
        raw_data={"model": "gpt-4"},
        created_at=base_time,
        updated_at=base_time,
    )
    spans.append(span3)

    # Span 4: User2, Task2, Trace2
    span4 = InternalSpan(
        id=str(uuid.uuid4()),
        trace_id="trace2",
        span_id="span4",
        task_id="task2",
        start_time=base_time + timedelta(days=1),
        end_time=base_time + timedelta(days=1) - timedelta(seconds=1),
        raw_data={"model": "gpt-3.5"},
        created_at=base_time + timedelta(days=1) - timedelta(seconds=1),
        updated_at=base_time + timedelta(days=1) - timedelta(seconds=1),
    )
    spans.append(span4)

    # Span 5: User3, Task3, Trace3
    span5 = InternalSpan(
        id=str(uuid.uuid4()),
        trace_id="trace3",
        span_id="span5",
        task_id="task3",
        start_time=base_time + timedelta(days=2),
        end_time=base_time + timedelta(days=2) + timedelta(seconds=1),
        raw_data={"model": "gpt-4"},
        created_at=base_time + timedelta(days=2),
        updated_at=base_time + timedelta(days=2),
    )
    spans.append(span5)
    spans_to_store = [span.model_dump() for span in spans]
    span_repo.store_spans(spans_to_store)

    yield spans

    # Cleanup: Delete all created spans from the database after the test
    span_ids = [span.span_id for span in spans]
    _delete_spans_from_db(db_session, span_ids)


@pytest.fixture(scope="function")
def sample_openinference_trace() -> bytes:
    """Create a sample OpenInference trace in protobuf format."""
    trace_request, resource_span, scope_span = _create_base_trace_request()

    # Create a valid span with task ID
    span = _create_llm_span(
        trace_id=b"test_trace_id_123",
        span_id=b"test_span_id_456",
        name="test_span",
        include_task_id=True,
        model_name="gpt-4-turbo",
    )

    # Add token count attributes
    span.attributes.extend(
        [
            KeyValue(key="llm.token_count.prompt", value=AnyValue(int_value=100)),
            KeyValue(key="llm.token_count.completion", value=AnyValue(int_value=50)),
        ],
    )

    scope_span.spans.append(span)
    resource_span.scope_spans.append(scope_span)
    trace_request.resource_spans.append(resource_span)
    yield trace_request.SerializeToString()

    # Cleanup
    span_ids = [span.span_id.hex()]
    db_session = override_get_db_session()
    _delete_spans_from_db(db_session, span_ids)


@pytest.fixture(scope="function")
def sample_span_missing_task_id() -> bytes:
    """Create a sample trace with a span missing task ID."""
    trace_request, resource_span, scope_span = _create_base_trace_request()

    # Create a span without a task ID
    span = _create_llm_span(
        trace_id=b"missing_task_id_trace",
        span_id=b"missing_task_id_span",
        name="missing_task_id_span",
        include_task_id=False,
    )

    scope_span.spans.append(span)
    resource_span.scope_spans.append(scope_span)
    trace_request.resource_spans.append(resource_span)

    yield trace_request.SerializeToString()

    # No cleanup needed as the span should be rejected


@pytest.fixture(scope="function")
def sample_mixed_spans_trace() -> bytes:
    """Create a sample with mixed valid and invalid spans for testing partial success."""
    trace_request, resource_span, scope_span = _create_base_trace_request()

    # Valid span with task ID
    valid_span = _create_llm_span(
        trace_id=b"valid_trace_id_123",
        span_id=b"valid_span_id_456",
        name="valid_span",
        include_task_id=True,
    )

    # Reuse the span generator to create an invalid span without task ID
    invalid_span = _create_llm_span(
        trace_id=b"invalid_trace_id_789",
        span_id=b"invalid_span_id_012",
        name="invalid_span",
        include_task_id=False,
    )

    scope_span.spans.extend([valid_span, invalid_span])
    resource_span.scope_spans.append(scope_span)
    trace_request.resource_spans.append(resource_span)

    yield trace_request.SerializeToString()

    # Cleanup valid span only (invalid one won't be stored)
    span_ids = [valid_span.span_id.hex()]
    db_session = override_get_db_session()
    _delete_spans_from_db(db_session, span_ids)


@pytest.fixture(scope="function")
def sample_all_rejected_spans_trace() -> bytes:
    """Create a sample with all spans being rejected (missing task IDs)."""
    trace_request, resource_span, scope_span = _create_base_trace_request()

    # Create two invalid spans without task IDs
    rejected_span1 = _create_llm_span(
        trace_id=b"rejected_trace_id_123",
        span_id=b"rejected_span_id_456",
        name="rejected_span1",
        include_task_id=False,
        model_name="gpt-4",
    )

    rejected_span2 = _create_llm_span(
        trace_id=b"rejected_trace_id_789",
        span_id=b"rejected_span_id_012",
        name="rejected_span2",
        include_task_id=False,
        model_name="gpt-3.5-turbo",
    )

    scope_span.spans.extend([rejected_span1, rejected_span2])
    resource_span.scope_spans.append(scope_span)
    trace_request.resource_spans.append(resource_span)

    yield trace_request.SerializeToString()

    # No cleanup needed as all spans should be rejected and not stored
