import uuid
from datetime import datetime, timedelta
from typing import Generator, List

import pytest
from arthur_common.models.enums import MetricType
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue
from opentelemetry.proto.trace.v1.trace_pb2 import (
    ResourceSpans,
    ScopeSpans,
    Span,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from db_models import (
    DatabaseMetric,
    DatabaseMetricResult,
    DatabaseSpan,
    DatabaseTask,
    DatabaseTaskToMetrics,
    DatabaseTraceMetadata,
)
from dependencies import get_application_config
from repositories.metrics_repository import MetricRepository
from repositories.span_repository import SpanRepository
from repositories.tasks_metrics_repository import TasksMetricsRepository
from schemas.internal_schemas import Span as InternalSpan
from services.trace.span_normalization_service import SpanNormalizationService
from services.trace.trace_ingestion_service import TraceIngestionService
from tests.clients.base_test_client import override_get_db_session
from tests.clients.unit_test_client import get_genai_engine_test_client


@pytest.fixture(scope="function")
def client():
    """Create a test client for the trace API endpoints."""
    return get_genai_engine_test_client()


@pytest.fixture(scope="function")
def trace_api_setup():
    """Setup for trace API testing with automatic cleanup."""
    db_session: Session = override_get_db_session()
    trace_ingestion_service = TraceIngestionService(db_session)
    created_trace_ids = []
    created_span_ids = []

    yield db_session, trace_ingestion_service, created_trace_ids, created_span_ids

    # Cleanup: Delete created spans and trace metadata
    _delete_spans_from_db(db_session, created_span_ids)
    _delete_trace_metadata_from_db(db_session, created_trace_ids)


def _delete_spans_from_db(db_session, span_ids):
    """Helper function to delete spans directly from the database."""
    if not span_ids:
        return

    # Delete spans with the given span_ids
    db_session.query(DatabaseSpan).filter(DatabaseSpan.span_id.in_(span_ids)).delete(
        synchronize_session=False,
    )
    db_session.commit()


def _delete_trace_metadata_from_db(db_session: Session, trace_ids: List[str]):
    """Helper function to delete trace metadata directly from the database."""
    if not trace_ids:
        return

    db_session.query(DatabaseTraceMetadata).filter(
        DatabaseTraceMetadata.trace_id.in_(trace_ids),
    ).delete(synchronize_session=False)
    db_session.commit()


def _get_trace_metadata(db_session: Session, trace_id: str) -> DatabaseTraceMetadata:
    """Helper to retrieve trace metadata from database."""
    return db_session.execute(
        select(DatabaseTraceMetadata).where(DatabaseTraceMetadata.trace_id == trace_id),
    ).scalar_one_or_none()


def _create_base_trace_request(task_id=None):
    """Create a base ExportTraceServiceRequest with resource attributes."""
    trace_request = ExportTraceServiceRequest()
    resource_span = ResourceSpans()

    # Add service name attribute
    resource_span.resource.attributes.extend(
        [KeyValue(key="service.name", value=AnyValue(string_value="test_service"))],
    )

    # Add task ID to resource attributes if provided
    if task_id:
        resource_span.resource.attributes.extend(
            [KeyValue(key="arthur.task", value=AnyValue(string_value=task_id))],
        )

    scope_span = ScopeSpans()
    scope_span.scope.name = "test_scope"

    return trace_request, resource_span, scope_span


def _create_span(
    trace_id,
    span_id,
    name,
    span_type="LLM",
    model_name="gpt-4",
    parent_span_id=None,
    status=None,
    session_id=None,
):
    """Helper function to create a span with specified type and optional parent ID."""
    span = Span(status=status)
    span.trace_id = trace_id
    span.span_id = span_id
    span.name = name
    span.kind = Span.SPAN_KIND_INTERNAL
    span.start_time_unix_nano = int(datetime.now().timestamp() * 1e9)
    span.end_time_unix_nano = int(
        (datetime.now() + timedelta(seconds=1)).timestamp() * 1e9,
    )

    # Add parent span ID if provided
    if parent_span_id:
        span.parent_span_id = parent_span_id

    # Basic span attributes
    attributes = [
        KeyValue(key="openinference.span.kind", value=AnyValue(string_value=span_type)),
    ]

    # Add model-specific attributes for LLM spans
    if span_type == "LLM":
        attributes.append(
            KeyValue(key="llm.model_name", value=AnyValue(string_value=model_name)),
        )

    metadata = {
        "ls_provider": "openai",
        "ls_model_name": model_name,
        "ls_model_type": "chat",
    }

    metadata_str = str(metadata).replace("'", '"')
    attributes.append(
        KeyValue(
            key="metadata",
            value=AnyValue(string_value=metadata_str),
        ),
    )

    # Add session_id if provided
    if session_id:
        attributes.append(
            KeyValue(key="session.id", value=AnyValue(string_value=session_id)),
        )

    span.attributes.extend(attributes)
    return span


def _create_database_span(
    trace_id: str,
    span_id: str,
    task_id: str,
    start_time: datetime,
    end_time: datetime,
    parent_span_id: str = None,
    span_kind: str = "LLM",
    session_id: str = None,
) -> DatabaseSpan:
    """Helper to create a test DatabaseSpan for trace metadata testing."""
    return DatabaseSpan(
        id=str(uuid.uuid4()),
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=parent_span_id,
        span_kind=span_kind,
        start_time=start_time,
        end_time=end_time,
        task_id=task_id,
        session_id=session_id,
        raw_data={
            "name": f"Test Span {span_id}",
            "spanId": span_id,
            "traceId": trace_id,
            "attributes": {"openinference.span.kind": span_kind},
            "arthur_span_version": "arthur_span_v1",
        },
    )


@pytest.fixture(scope="function")
def sample_trace_api_protobuf() -> bytes:
    """Create a sample OpenInference trace in protobuf format for API testing."""
    # Create trace with task ID in resource attributes
    task_id = "api_task_123"
    trace_request, resource_span, scope_span = _create_base_trace_request(
        task_id=task_id,
    )

    # Create a simple LLM span
    span = _create_span(
        trace_id=b"api_trace_123",
        span_id=b"api_span_456",
        name="api_test_span",
        span_type="LLM",
        model_name="gpt-4-turbo",
    )

    # Add token count attributes to the LLM span
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
def comprehensive_test_data() -> Generator[List[InternalSpan], None, None]:
    """Create comprehensive test data with multiple traces, spans, and sessions."""
    db_session = override_get_db_session()
    application_config = get_application_config(session=db_session)
    tasks_metrics_repo = TasksMetricsRepository(db_session)
    metrics_repo = MetricRepository(db_session)
    span_repo = SpanRepository(db_session, tasks_metrics_repo, metrics_repo)
    span_normalizer = SpanNormalizationService()

    # Create spans with different attributes for comprehensive testing
    spans = []
    base_time = datetime.now()

    # Session 1, Task1, Trace1 - LLM span with features
    span1_raw_data = span_normalizer.normalize_span_to_nested_dict(
        {
            "kind": "SPAN_KIND_INTERNAL",
            "name": "ChatOpenAI",
            "spanId": "api_span1",
            "traceId": "api_trace1",
            "attributes": {
                "openinference.span.kind": "LLM",
                "llm.model_name": "gpt-4",
                "llm.input_messages.0.message.role": "system",
                "llm.input_messages.0.message.content": "You are a helpful assistant.",
                "llm.input_messages.1.message.role": "user",
                "llm.input_messages.1.message.content": "What is the weather like today?",
                "llm.output_messages.0.message.role": "assistant",
                "llm.output_messages.0.message.content": "I don't have access to real-time weather information.",
                "session.id": "session1",
                "user.id": "user1",
                "metadata": '{"ls_provider": "openai", "ls_model_name": "gpt-4", "ls_model_type": "chat"}',
            },
        },
    )
    span1_raw_data["arthur_span_version"] = "arthur_span_v1"

    span1 = InternalSpan(
        id=str(uuid.uuid4()),
        trace_id="api_trace1",
        span_id="api_span1",
        task_id="api_task1",
        parent_span_id=None,
        span_kind="LLM",
        start_time=base_time - timedelta(days=2),
        end_time=base_time - timedelta(days=2) + timedelta(seconds=1),
        session_id="session1",
        user_id="user1",
        raw_data=span1_raw_data,
        created_at=base_time - timedelta(days=2) + timedelta(seconds=1),
        updated_at=base_time - timedelta(days=2) + timedelta(seconds=1),
    )
    spans.append(span1)

    # Session 1, Task1, Trace1 - CHAIN span with parent
    span2_raw_data = span_normalizer.normalize_span_to_nested_dict(
        {
            "kind": "SPAN_KIND_INTERNAL",
            "name": "Chain",
            "spanId": "api_span2",
            "traceId": "api_trace1",
            "attributes": {
                "openinference.span.kind": "CHAIN",
                "session.id": "session1",
                "user.id": "user1",
                "metadata": '{"ls_provider": "langchain", "ls_model_name": "chain_model", "ls_model_type": "chain"}',
            },
        },
    )
    span2_raw_data["arthur_span_version"] = "arthur_span_v1"

    span2 = InternalSpan(
        id=str(uuid.uuid4()),
        trace_id="api_trace1",
        span_id="api_span2",
        task_id="api_task1",
        parent_span_id="api_span1",
        span_kind="CHAIN",
        start_time=base_time - timedelta(days=1),
        end_time=base_time - timedelta(days=1) + timedelta(seconds=1),
        session_id="session1",
        user_id="user1",
        raw_data=span2_raw_data,
        created_at=base_time - timedelta(days=1) + timedelta(seconds=1),
        updated_at=base_time - timedelta(days=1) + timedelta(seconds=1),
    )
    spans.append(span2)

    # Session 1, Task1, Trace2 - Another LLM span in same session
    span3_raw_data = span_normalizer.normalize_span_to_nested_dict(
        {
            "kind": "SPAN_KIND_INTERNAL",
            "name": "ChatOpenAI",
            "spanId": "api_span3",
            "traceId": "api_trace2",
            "attributes": {
                "openinference.span.kind": "LLM",
                "llm.model_name": "gpt-3.5-turbo",
                "llm.input_messages.0.message.role": "user",
                "llm.input_messages.0.message.content": "Follow-up question",
                "llm.output_messages.0.message.role": "assistant",
                "llm.output_messages.0.message.content": "Follow-up response",
                "session.id": "session1",
                "user.id": "user1",
                "metadata": '{"ls_provider": "openai", "ls_model_name": "gpt-3.5-turbo", "ls_model_type": "chat"}',
            },
        },
    )
    span3_raw_data["arthur_span_version"] = "arthur_span_v1"

    span3 = InternalSpan(
        id=str(uuid.uuid4()),
        trace_id="api_trace2",
        span_id="api_span3",
        task_id="api_task1",
        parent_span_id=None,
        span_kind="LLM",
        start_time=base_time - timedelta(hours=12),
        end_time=base_time - timedelta(hours=12) + timedelta(seconds=2),
        session_id="session1",
        user_id="user1",
        raw_data=span3_raw_data,
        created_at=base_time - timedelta(hours=12) + timedelta(seconds=2),
        updated_at=base_time - timedelta(hours=12) + timedelta(seconds=2),
    )
    spans.append(span3)

    # Session 2, Task2, Trace3 - AGENT span in different session/task
    span4_raw_data = span_normalizer.normalize_span_to_nested_dict(
        {
            "kind": "SPAN_KIND_INTERNAL",
            "name": "Agent",
            "spanId": "api_span4",
            "traceId": "api_trace3",
            "attributes": {
                "openinference.span.kind": "AGENT",
                "session.id": "session2",
                "user.id": "user2",
                "metadata": '{"ls_provider": "langchain", "ls_model_name": "agent_model", "ls_model_type": "agent"}',
            },
        },
    )
    span4_raw_data["arthur_span_version"] = "arthur_span_v1"

    span4 = InternalSpan(
        id=str(uuid.uuid4()),
        trace_id="api_trace3",
        span_id="api_span4",
        task_id="api_task2",
        parent_span_id=None,
        span_kind="AGENT",
        start_time=base_time,
        end_time=base_time + timedelta(seconds=1),
        session_id="session2",
        user_id="user2",
        raw_data=span4_raw_data,
        created_at=base_time + timedelta(seconds=1),
        updated_at=base_time + timedelta(seconds=1),
    )
    spans.append(span4)

    # Session 2, Task2, Trace3 - RETRIEVER span with parent
    span5_raw_data = span_normalizer.normalize_span_to_nested_dict(
        {
            "kind": "SPAN_KIND_INTERNAL",
            "name": "Retriever",
            "spanId": "api_span5",
            "traceId": "api_trace3",
            "attributes": {
                "openinference.span.kind": "RETRIEVER",
                "session.id": "session2",
                "user.id": "user2",
                "metadata": '{"ls_provider": "langchain", "ls_model_name": "retriever_model", "ls_model_type": "retriever"}',
            },
        },
    )
    span5_raw_data["arthur_span_version"] = "arthur_span_v1"

    span5 = InternalSpan(
        id=str(uuid.uuid4()),
        trace_id="api_trace3",
        span_id="api_span5",
        task_id="api_task2",
        parent_span_id="api_span4",
        span_kind="RETRIEVER",
        start_time=base_time + timedelta(seconds=30),
        end_time=base_time + timedelta(seconds=31),
        session_id="session2",
        user_id="user2",
        raw_data=span5_raw_data,
        created_at=base_time + timedelta(seconds=31),
        updated_at=base_time + timedelta(seconds=31),
    )
    spans.append(span5)

    # No session, Task1, Trace4 - TOOL span for tool filtering tests
    span6_raw_data = span_normalizer.normalize_span_to_nested_dict(
        {
            "kind": "SPAN_KIND_INTERNAL",
            "name": "test_tool",
            "spanId": "api_span6",
            "traceId": "api_trace4",
            "attributes": {
                "openinference.span.kind": "TOOL",
                "tool.name": "test_tool",
                "user.id": "user1",
                "metadata": '{"ls_provider": "custom", "ls_model_name": "tool_model", "ls_model_type": "tool"}',
            },
        },
    )
    span6_raw_data["arthur_span_version"] = "arthur_span_v1"

    span6 = InternalSpan(
        id=str(uuid.uuid4()),
        trace_id="api_trace4",
        span_id="api_span6",
        task_id="api_task1",
        parent_span_id=None,
        span_kind="TOOL",
        start_time=base_time + timedelta(hours=1),
        end_time=base_time + timedelta(hours=1) + timedelta(seconds=1),
        session_id=None,
        user_id="user1",
        raw_data=span6_raw_data,
        created_at=base_time + timedelta(hours=1) + timedelta(seconds=1),
        updated_at=base_time + timedelta(hours=1) + timedelta(seconds=1),
    )
    spans.append(span6)

    # Convert to DatabaseSpan objects and store
    database_spans = []
    for span in spans:
        database_span = DatabaseSpan(
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
            raw_data=span.raw_data,
            created_at=span.created_at,
            updated_at=span.updated_at,
        )
        database_spans.append(database_span)

    # Store spans directly to preserve IDs
    db_session.add_all(database_spans)
    db_session.commit()

    # Create trace metadata
    trace_metadatas = []
    for trace_id in set(span.trace_id for span in spans):
        trace_spans = [span for span in spans if span.trace_id == trace_id]
        trace_start_time = min(span.start_time for span in trace_spans)
        trace_end_time = max(span.end_time for span in trace_spans)

        trace_metadata = DatabaseTraceMetadata(
            task_id=trace_spans[0].task_id,
            trace_id=trace_id,
            session_id=trace_spans[0].session_id,
            user_id=trace_spans[0].user_id,
            span_count=len(trace_spans),
            start_time=trace_start_time,
            end_time=trace_end_time,
            created_at=trace_start_time,
            updated_at=trace_end_time,
        )
        trace_metadatas.append(trace_metadata)

    db_session.add_all(trace_metadatas)
    db_session.commit()

    # Create tasks
    task1 = DatabaseTask(
        id="api_task1",
        name="API Test Task 1",
        created_at=base_time,
        updated_at=base_time,
    )
    task2 = DatabaseTask(
        id="api_task2",
        name="API Test Task 2",
        created_at=base_time,
        updated_at=base_time,
    )
    db_session.add(task1)
    db_session.add(task2)
    db_session.commit()

    # Create test metrics
    query_relevance_metric = DatabaseMetric(
        id=str(uuid.uuid4()),
        created_at=base_time,
        updated_at=base_time,
        type=MetricType.QUERY_RELEVANCE.value,
        name="API Test Query Relevance",
        metric_metadata="Test metric for LLM spans",
        config=None,
    )
    response_relevance_metric = DatabaseMetric(
        id=str(uuid.uuid4()),
        created_at=base_time,
        updated_at=base_time,
        type=MetricType.RESPONSE_RELEVANCE.value,
        name="API Test Response Relevance",
        metric_metadata="Test metric for LLM spans",
        config=None,
    )
    db_session.add(query_relevance_metric)
    db_session.add(response_relevance_metric)
    db_session.commit()

    # Create task-to-metric links
    task1_query_metric_link = DatabaseTaskToMetrics(
        task_id="api_task1",
        metric_id=query_relevance_metric.id,
        enabled=True,
    )
    task1_response_metric_link = DatabaseTaskToMetrics(
        task_id="api_task1",
        metric_id=response_relevance_metric.id,
        enabled=True,
    )
    task2_query_metric_link = DatabaseTaskToMetrics(
        task_id="api_task2",
        metric_id=query_relevance_metric.id,
        enabled=True,
    )
    db_session.add(task1_query_metric_link)
    db_session.add(task1_response_metric_link)
    db_session.add(task2_query_metric_link)
    db_session.commit()

    # Create metric results for LLM spans
    span1_query_metric_result = DatabaseMetricResult(
        id=str(uuid.uuid4()),
        created_at=base_time,
        updated_at=base_time,
        metric_type=MetricType.QUERY_RELEVANCE.value,
        details={
            "query_relevance": {"llm_relevance_score": 0.85},
            "reason": "Query is highly relevant to the task",
        },
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=1500,
        span_id=span1.id,
        metric_id=query_relevance_metric.id,
    )
    span1_response_metric_result = DatabaseMetricResult(
        id=str(uuid.uuid4()),
        created_at=base_time,
        updated_at=base_time,
        metric_type=MetricType.RESPONSE_RELEVANCE.value,
        details={
            "response_relevance": {"llm_relevance_score": 0.92},
            "reason": "Response is highly relevant",
        },
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=1500,
        span_id=span1.id,
        metric_id=response_relevance_metric.id,
    )

    span3_query_metric_result = DatabaseMetricResult(
        id=str(uuid.uuid4()),
        created_at=base_time,
        updated_at=base_time,
        metric_type=MetricType.QUERY_RELEVANCE.value,
        details={
            "query_relevance": {"llm_relevance_score": 0.45},
            "reason": "Query is moderately relevant",
        },
        prompt_tokens=80,
        completion_tokens=30,
        latency_ms=1200,
        span_id=span3.id,
        metric_id=query_relevance_metric.id,
    )

    db_session.add(span1_query_metric_result)
    db_session.add(span1_response_metric_result)
    db_session.add(span3_query_metric_result)
    db_session.commit()

    yield spans

    # Cleanup
    span_ids = [span.span_id for span in spans]
    _delete_spans_from_db(db_session, span_ids)

    # Cleanup trace metadata
    trace_ids = list(set(span.trace_id for span in spans))
    db_session.query(DatabaseTraceMetadata).filter(
        DatabaseTraceMetadata.trace_id.in_(trace_ids),
    ).delete(synchronize_session=False)

    # Cleanup metric results, task-to-metric links, metrics, and tasks
    db_session.query(DatabaseMetricResult).filter(
        DatabaseMetricResult.span_id.in_([span.id for span in spans]),
    ).delete(synchronize_session=False)
    db_session.query(DatabaseTaskToMetrics).filter(
        DatabaseTaskToMetrics.task_id.in_(["api_task1", "api_task2"]),
    ).delete(synchronize_session=False)
    db_session.query(DatabaseMetric).filter(
        DatabaseMetric.id.in_(
            [query_relevance_metric.id, response_relevance_metric.id],
        ),
    ).delete(synchronize_session=False)
    db_session.query(DatabaseTask).filter(
        DatabaseTask.id.in_(["api_task1", "api_task2"]),
    ).delete(synchronize_session=False)
    db_session.commit()
