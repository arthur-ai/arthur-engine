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
    Status,
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
from services.trace_ingestion_service import TraceIngestionService
from tests.clients.base_test_client import override_get_db_session
from tests.clients.unit_test_client import get_genai_engine_test_client


@pytest.fixture(scope="function")
def client():
    """Create a test client for the API endpoints."""
    return get_genai_engine_test_client()


@pytest.fixture(scope="function")
def trace_metadata_setup():
    """Setup for trace metadata testing with automatic cleanup."""
    db_session: Session = override_get_db_session()
    trace_ingestion_service = TraceIngestionService(db_session)
    created_trace_ids = []

    yield db_session, trace_ingestion_service, created_trace_ids

    # Cleanup: Delete created trace metadata using the existing helper
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


def _get_trace_metadata(db_session: Session, trace_id: str) -> DatabaseTraceMetadata:
    """Helper to retrieve trace metadata from database."""
    return db_session.execute(
        select(DatabaseTraceMetadata).where(DatabaseTraceMetadata.trace_id == trace_id),
    ).scalar_one_or_none()


def _delete_trace_metadata_from_db(db_session: Session, trace_ids: List[str]):
    """Helper function to delete trace metadata directly from the database."""
    if not trace_ids:
        return

    db_session.query(DatabaseTraceMetadata).filter(
        DatabaseTraceMetadata.trace_id.in_(trace_ids),
    ).delete(synchronize_session=False)
    db_session.commit()


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


@pytest.fixture(scope="function")
def create_span() -> Generator[InternalSpan, None, None]:
    db_session = override_get_db_session()
    application_config = get_application_config(session=db_session)
    tasks_metrics_repo = TasksMetricsRepository(db_session)
    metrics_repo = MetricRepository(db_session)
    span_repo = SpanRepository(db_session, tasks_metrics_repo, metrics_repo)

    now = datetime.now()

    # Create a test span with proper raw_data structure matching real spans
    span = InternalSpan(
        id=str(uuid.uuid4()),
        trace_id="test_trace_id",
        span_id="test_span_id",
        task_id="test_task",
        parent_span_id=None,
        span_kind="LLM",
        start_time=now,
        end_time=now + timedelta(seconds=1),
        raw_data={
            "kind": "SPAN_KIND_INTERNAL",
            "name": "ChatOpenAI",
            "spanId": "test_span_id",
            "traceId": "test_trace_id",
            "attributes": {
                "openinference.span.kind": "LLM",
                "llm.model_name": "gpt-4",
                "llm.input_messages.0.message.role": "system",
                "llm.input_messages.0.message.content": "You are a helpful assistant.",
                "llm.input_messages.1.message.role": "user",
                "llm.input_messages.1.message.content": "What is the weather like today?",
                "llm.output_messages.0.message.role": "assistant",
                "llm.output_messages.0.message.content": "I don't have access to real-time weather information.",
                "metadata": '{"ls_provider": "openai", "ls_model_name": "gpt-4", "ls_model_type": "chat"}',
            },
            "arthur_span_version": "arthur_span_v1",
        },
        created_at=now,
        updated_at=now,
    )

    # Convert to dict for insertion
    span_dict = span.model_dump()
    span_dict.pop("metric_results")
    span_repo._store_spans([span_dict])

    yield span

    # Cleanup: Delete the span from the database after the test
    _delete_spans_from_db(db_session, [span.span_id])


@pytest.fixture(scope="function")
def create_test_spans() -> Generator[List[InternalSpan], None, None]:
    """Create multiple test spans with different attributes for query testing."""
    db_session = override_get_db_session()
    application_config = get_application_config(session=db_session)
    tasks_metrics_repo = TasksMetricsRepository(db_session)
    metrics_repo = MetricRepository(db_session)
    span_repo = SpanRepository(db_session, tasks_metrics_repo, metrics_repo)

    # Create spans with different attributes
    spans = []
    base_time = datetime.now()

    # Span 1: Task1, Trace1 - LLM span with features
    span1 = InternalSpan(
        id=str(uuid.uuid4()),
        trace_id="trace1",
        span_id="span1",
        task_id="task1",
        parent_span_id=None,
        span_kind="LLM",
        start_time=base_time - timedelta(days=2),
        end_time=base_time - timedelta(days=2) + timedelta(seconds=1),
        raw_data={
            "kind": "SPAN_KIND_INTERNAL",
            "name": "ChatOpenAI",
            "spanId": "span1",
            "traceId": "trace1",
            "attributes": {
                "openinference.span.kind": "LLM",
                "llm.model_name": "gpt-4",
                "llm.input_messages.0.message.role": "system",
                "llm.input_messages.0.message.content": "You are a helpful assistant.",
                "llm.input_messages.1.message.role": "user",
                "llm.input_messages.1.message.content": "What is the weather like today?",
                "llm.output_messages.0.message.role": "assistant",
                "llm.output_messages.0.message.content": "I don't have access to real-time weather information.",
                "metadata": '{"ls_provider": "openai", "ls_model_name": "gpt-4", "ls_model_type": "chat"}',
            },
            "arthur_span_version": "arthur_span_v1",
        },
        created_at=base_time - timedelta(days=2) + timedelta(seconds=1),
        updated_at=base_time - timedelta(days=2) + timedelta(seconds=1),
    )
    spans.append(span1)

    # Span 2: Task1, Trace1 - CHAIN span with parent
    span2 = InternalSpan(
        id=str(uuid.uuid4()),
        trace_id="trace1",
        span_id="span2",
        task_id="task1",
        parent_span_id="span1",
        span_kind="CHAIN",
        start_time=base_time - timedelta(days=1),
        end_time=base_time - timedelta(days=1) + timedelta(seconds=1),
        raw_data={
            "kind": "SPAN_KIND_INTERNAL",
            "name": "Chain",
            "spanId": "span2",
            "traceId": "trace1",
            "attributes": {
                "openinference.span.kind": "CHAIN",
                "metadata": '{"ls_provider": "langchain", "ls_model_name": "chain_model", "ls_model_type": "chain"}',
            },
            "arthur_span_version": "arthur_span_v1",
        },
        created_at=base_time - timedelta(days=1) + timedelta(seconds=1),
        updated_at=base_time - timedelta(days=1) + timedelta(seconds=1),
    )
    spans.append(span2)

    # Span 3: Task2, Trace2 - AGENT span
    span3 = InternalSpan(
        id=str(uuid.uuid4()),
        trace_id="trace2",
        span_id="span3",
        task_id="task2",
        parent_span_id=None,
        span_kind="AGENT",
        start_time=base_time,
        end_time=base_time + timedelta(seconds=1),
        raw_data={
            "kind": "SPAN_KIND_INTERNAL",
            "name": "Agent",
            "spanId": "span3",
            "traceId": "trace2",
            "attributes": {
                "openinference.span.kind": "AGENT",
                "metadata": '{"ls_provider": "langchain", "ls_model_name": "agent_model", "ls_model_type": "agent"}',
            },
            "arthur_span_version": "arthur_span_v1",
        },
        created_at=base_time + timedelta(seconds=1),
        updated_at=base_time + timedelta(seconds=1),
    )
    spans.append(span3)

    # Span 4: Task2, Trace2 - RETRIEVER span with parent
    span4 = InternalSpan(
        id=str(uuid.uuid4()),
        trace_id="trace2",
        span_id="span4",
        task_id="task2",
        parent_span_id="span3",
        span_kind="RETRIEVER",
        start_time=base_time + timedelta(seconds=30),
        end_time=base_time + timedelta(seconds=31),
        raw_data={
            "kind": "SPAN_KIND_INTERNAL",
            "name": "Retriever",
            "spanId": "span4",
            "traceId": "trace2",
            "attributes": {
                "openinference.span.kind": "RETRIEVER",
                "metadata": '{"ls_provider": "langchain", "ls_model_name": "retriever_model", "ls_model_type": "retriever"}',
            },
            "arthur_span_version": "arthur_span_v1",
        },
        created_at=base_time + timedelta(seconds=31),
        updated_at=base_time + timedelta(seconds=31),
    )
    spans.append(span4)

    # Span 5: Task1, Trace3 - TOOL span for tool filtering tests
    span5 = InternalSpan(
        id=str(uuid.uuid4()),
        trace_id="trace3",
        span_id="span5",
        task_id="task1",
        parent_span_id=None,
        span_kind="TOOL",
        start_time=base_time + timedelta(hours=1),
        end_time=base_time + timedelta(hours=1) + timedelta(seconds=1),
        raw_data={
            "kind": "SPAN_KIND_INTERNAL",
            "name": "test_tool",  # This will be used for tool_name filtering
            "spanId": "span5",
            "traceId": "trace3",
            "attributes": {
                "openinference.span.kind": "TOOL",
                "tool.name": "test_tool",
                "metadata": '{"ls_provider": "custom", "ls_model_name": "tool_model", "ls_model_type": "tool"}',
            },
            "arthur_span_version": "arthur_span_v1",
        },
        created_at=base_time + timedelta(hours=1) + timedelta(seconds=1),
        updated_at=base_time + timedelta(hours=1) + timedelta(seconds=1),
    )
    spans.append(span5)

    # Span 6: Task1, Trace3 - Another LLM span for more metric testing
    span6 = InternalSpan(
        id=str(uuid.uuid4()),
        trace_id="trace3",
        span_id="span6",
        task_id="task1",
        parent_span_id="span5",
        span_kind="LLM",
        start_time=base_time + timedelta(hours=1) + timedelta(seconds=2),
        end_time=base_time + timedelta(hours=1) + timedelta(seconds=4),
        raw_data={
            "kind": "SPAN_KIND_INTERNAL",
            "name": "ChatOpenAI",
            "spanId": "span6",
            "traceId": "trace3",
            "attributes": {
                "openinference.span.kind": "LLM",
                "llm.model_name": "gpt-3.5-turbo",
                "llm.input_messages.0.message.role": "user",
                "llm.input_messages.0.message.content": "Test query with different metrics",
                "llm.output_messages.0.message.role": "assistant",
                "llm.output_messages.0.message.content": "Test response with different metrics",
                "metadata": '{"ls_provider": "openai", "ls_model_name": "gpt-3.5-turbo", "ls_model_type": "chat"}',
            },
            "arthur_span_version": "arthur_span_v1",
        },
        created_at=base_time + timedelta(hours=1) + timedelta(seconds=4),
        updated_at=base_time + timedelta(hours=1) + timedelta(seconds=4),
    )
    spans.append(span6)

    # Convert to DatabaseSpan objects
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
            raw_data=span.raw_data,
            created_at=span.created_at,
            updated_at=span.updated_at,
        )
        database_spans.append(database_span)

    # Store spans directly to preserve IDs for metric linking
    db_session.add_all(database_spans)
    db_session.commit()

    # Create trace metadata manually since we bypassed trace ingestion service
    trace_metadatas = []
    for trace_id in set(span.trace_id for span in spans):
        trace_spans = [span for span in spans if span.trace_id == trace_id]
        trace_start_time = min(span.start_time for span in trace_spans)
        trace_end_time = max(span.end_time for span in trace_spans)

        trace_metadata = DatabaseTraceMetadata(
            task_id=trace_spans[0].task_id,
            trace_id=trace_id,
            session_id=trace_spans[0].session_id,  # Use session_id from first span
            span_count=len(trace_spans),
            start_time=trace_start_time,
            end_time=trace_end_time,
            created_at=trace_start_time,
            updated_at=trace_end_time,
        )
        trace_metadatas.append(trace_metadata)

    db_session.add_all(trace_metadatas)
    db_session.commit()

    # Create metrics and metric results for LLM spans

    # Create tasks first
    task1 = DatabaseTask(
        id="task1",
        name="Test Task 1",
        created_at=base_time,
        updated_at=base_time,
    )
    task2 = DatabaseTask(
        id="task2",
        name="Test Task 2",
        created_at=base_time,
        updated_at=base_time,
    )
    db_session.add(task1)
    db_session.add(task2)
    db_session.commit()

    # Create test metrics for different types
    query_relevance_metric = DatabaseMetric(
        id=str(uuid.uuid4()),
        created_at=base_time,
        updated_at=base_time,
        type=MetricType.QUERY_RELEVANCE.value,
        name="Test Query Relevance",
        metric_metadata="Test metric for LLM spans",
        config=None,
    )
    response_relevance_metric = DatabaseMetric(
        id=str(uuid.uuid4()),
        created_at=base_time,
        updated_at=base_time,
        type=MetricType.RESPONSE_RELEVANCE.value,
        name="Test Response Relevance",
        metric_metadata="Test metric for LLM spans",
        config=None,
    )
    tool_selection_metric = DatabaseMetric(
        id=str(uuid.uuid4()),
        created_at=base_time,
        updated_at=base_time,
        type=MetricType.TOOL_SELECTION.value,
        name="Test Tool Selection",
        metric_metadata="Test metric for tool selection and usage",
        config=None,
    )
    db_session.add(query_relevance_metric)
    db_session.add(response_relevance_metric)
    db_session.add(tool_selection_metric)
    db_session.commit()

    # Create task-to-metric links for task1 and task2
    task1_query_metric_link = DatabaseTaskToMetrics(
        task_id="task1",
        metric_id=query_relevance_metric.id,
        enabled=True,
    )
    task1_response_metric_link = DatabaseTaskToMetrics(
        task_id="task1",
        metric_id=response_relevance_metric.id,
        enabled=True,
    )
    task1_tool_selection_metric_link = DatabaseTaskToMetrics(
        task_id="task1",
        metric_id=tool_selection_metric.id,
        enabled=True,
    )
    task2_query_metric_link = DatabaseTaskToMetrics(
        task_id="task2",
        metric_id=query_relevance_metric.id,
        enabled=True,
    )
    task2_response_metric_link = DatabaseTaskToMetrics(
        task_id="task2",
        metric_id=response_relevance_metric.id,
        enabled=True,
    )
    task2_tool_selection_metric_link = DatabaseTaskToMetrics(
        task_id="task2",
        metric_id=tool_selection_metric.id,
        enabled=True,
    )
    db_session.add(task1_query_metric_link)
    db_session.add(task1_response_metric_link)
    db_session.add(task1_tool_selection_metric_link)
    db_session.add(task2_query_metric_link)
    db_session.add(task2_response_metric_link)
    db_session.add(task2_tool_selection_metric_link)
    db_session.commit()

    # Create metric results for span1 (LLM span in trace1) with high relevance scores
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

    # Create metric results for span6 (LLM span in trace3) with lower relevance scores
    span6_query_metric_result = DatabaseMetricResult(
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
        span_id=span6.id,
        metric_id=query_relevance_metric.id,
    )
    span6_response_metric_result = DatabaseMetricResult(
        id=str(uuid.uuid4()),
        created_at=base_time,
        updated_at=base_time,
        metric_type=MetricType.RESPONSE_RELEVANCE.value,
        details={
            "response_relevance": {"llm_relevance_score": 0.38},
            "reason": "Response is moderately relevant",
        },
        prompt_tokens=80,
        completion_tokens=30,
        latency_ms=1200,
        span_id=span6.id,
        metric_id=response_relevance_metric.id,
    )

    # Create tool selection metric results for span1 (LLM span in trace1) with CORRECT tool selection and usage
    span1_tool_selection_metric_result = DatabaseMetricResult(
        id=str(uuid.uuid4()),
        created_at=base_time,
        updated_at=base_time,
        metric_type=MetricType.TOOL_SELECTION.value,
        details={
            "tool_selection": {
                "tool_selection": 1,  # CORRECT
                "tool_usage": 1,  # CORRECT
                "tool_selection_reason": "Correct tool was selected for the task",
                "tool_usage_reason": "Tool was used correctly",
            },
        },
        prompt_tokens=120,
        completion_tokens=60,
        latency_ms=1800,
        span_id=span1.id,
        metric_id=tool_selection_metric.id,
    )

    # Create tool selection metric results for span6 (LLM span in trace3) with INCORRECT tool selection and usage
    span6_tool_selection_metric_result = DatabaseMetricResult(
        id=str(uuid.uuid4()),
        created_at=base_time,
        updated_at=base_time,
        metric_type=MetricType.TOOL_SELECTION.value,
        details={
            "tool_selection": {
                "tool_selection": 0,  # INCORRECT
                "tool_usage": 0,  # INCORRECT
                "tool_selection_reason": "Wrong tool was selected for the task",
                "tool_usage_reason": "Tool was used incorrectly",
            },
        },
        prompt_tokens=90,
        completion_tokens=40,
        latency_ms=1400,
        span_id=span6.id,
        metric_id=tool_selection_metric.id,
    )

    db_session.add(span1_query_metric_result)
    db_session.add(span1_response_metric_result)
    db_session.add(span1_tool_selection_metric_result)
    db_session.add(span6_query_metric_result)
    db_session.add(span6_response_metric_result)
    db_session.add(span6_tool_selection_metric_result)
    db_session.commit()

    yield spans

    # Cleanup: Delete all created spans from the database after the test
    span_ids = [span.span_id for span in spans]
    _delete_spans_from_db(db_session, span_ids)

    # Cleanup: Delete trace metadata created by trace ingestion service
    trace_ids = list(set(span.trace_id for span in spans))  # Remove duplicates
    db_session.query(DatabaseTraceMetadata).filter(
        DatabaseTraceMetadata.trace_id.in_(trace_ids),
    ).delete(synchronize_session=False)

    # Cleanup: Delete metric results, task-to-metric links, metrics, and tasks
    db_session.query(DatabaseMetricResult).filter(
        DatabaseMetricResult.span_id.in_([span.id for span in spans]),
    ).delete(synchronize_session=False)
    db_session.query(DatabaseTaskToMetrics).filter(
        DatabaseTaskToMetrics.task_id.in_(["task1", "task2"]),
    ).delete(synchronize_session=False)
    db_session.query(DatabaseMetric).filter(
        DatabaseMetric.id.in_(
            [
                query_relevance_metric.id,
                response_relevance_metric.id,
                tool_selection_metric.id,
            ],
        ),
    ).delete(synchronize_session=False)
    db_session.query(DatabaseTask).filter(
        DatabaseTask.id.in_(["task1", "task2"]),
    ).delete(synchronize_session=False)
    db_session.commit()


@pytest.fixture(scope="function")
def sample_openinference_trace() -> bytes:
    """Create a sample OpenInference trace in protobuf format."""
    # Create trace with task ID in resource attributes
    task_id = "task_id_123"
    trace_request, resource_span, scope_span = _create_base_trace_request(
        task_id=task_id,
    )

    # Create a simple LLM span
    span = _create_span(
        trace_id=b"test_trace_id_123",
        span_id=b"test_span_id_456",
        name="test_llm_span",
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
def sample_openinference_trace_multiple_spans() -> bytes:
    """Create a sample OpenInference trace in protobuf format."""
    # Create trace with task ID in resource attributes
    task_id = "task_id_123"
    trace_id = b"test_trace_id_777"
    parent_span_id = b"test_span_id_parent_777"
    child_span_id = b"test_span_id_child_777"
    trace_request, resource_span, scope_span = _create_base_trace_request(
        task_id=task_id,
    )

    # Create a simple LLM span
    parent_span = _create_span(
        trace_id=trace_id,
        span_id=parent_span_id,
        name="test_llm_span",
        span_type="LLM",
        model_name="gpt-4-turbo",
    )

    # Add token count attributes to the LLM span
    parent_span.attributes.extend(
        [
            KeyValue(key="llm.token_count.prompt", value=AnyValue(int_value=100)),
            KeyValue(key="llm.token_count.completion", value=AnyValue(int_value=50)),
        ],
    )

    # create a child span from the parent
    child_span = _create_span(
        trace_id=trace_id,
        parent_span_id=parent_span_id,
        span_id=child_span_id,
        name="test_llm_span",
        span_type="LLM",
        model_name="gpt-4-turbo",
        status=Status(message="ok", code=Status.STATUS_CODE_OK),
    )

    # Add token count attributes to the LLM span
    child_span.attributes.extend(
        [
            KeyValue(key="llm.token_count.prompt", value=AnyValue(int_value=100)),
            KeyValue(key="llm.token_count.completion", value=AnyValue(int_value=50)),
        ],
    )

    # IMPORTANT, for this test to properly test the insert functionality,
    # child span needs to come first in the list before parent.
    # This tests for an issue where SQLAlchemy only looks at the first record for values to insert
    # Since the parent span does not have a parent_span_id set, SQLAlchemy fails to insert that row
    # because it expects each object to have a parent_span_id after inspecting the child span's values
    scope_span.spans.append(child_span)
    scope_span.spans.append(parent_span)
    resource_span.scope_spans.append(scope_span)
    trace_request.resource_spans.append(resource_span)
    yield trace_request.SerializeToString()

    # Cleanup
    span_ids = [parent_span.span_id.hex(), child_span.span_id.hex()]
    db_session = override_get_db_session()
    _delete_spans_from_db(db_session, span_ids)


@pytest.fixture(scope="function")
def sample_span_missing_task_id() -> bytes:
    """Create a sample trace with a span missing task ID."""
    # Create trace without task ID in resource attributes
    trace_request, resource_span, scope_span = _create_base_trace_request(task_id=None)

    # Create a span without a task ID
    span = _create_span(
        trace_id=b"missing_task_id_trace",
        span_id=b"missing_task_id_span",
        name="missing_task_id_guardrail_span",
        span_type="GUARDRAIL",
    )

    scope_span.spans.append(span)
    resource_span.scope_spans.append(scope_span)
    trace_request.resource_spans.append(resource_span)

    yield trace_request.SerializeToString()

    # Cleanup - span will be accepted since all spans are now accepted
    span_ids = [span.span_id.hex()]
    db_session = override_get_db_session()
    _delete_spans_from_db(db_session, span_ids)
