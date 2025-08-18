import json
import uuid
from datetime import datetime, timedelta
from typing import Generator, List

import pytest
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue
from opentelemetry.proto.trace.v1.trace_pb2 import ResourceSpans, ScopeSpans, Span

from db_models.db_models import DatabaseSpan
from dependencies import get_application_config
from repositories.metrics_repository import MetricRepository
from repositories.span_repository import SpanRepository
from repositories.tasks_metrics_repository import TasksMetricsRepository
from schemas.internal_schemas import Span as InternalSpan
from tests.clients.base_test_client import override_get_db_session
from tests.clients.unit_test_client import get_genai_engine_test_client


@pytest.fixture(scope="function")
def client():
    """Create a test client for the API endpoints."""
    return get_genai_engine_test_client()


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


def _create_span(
    trace_id,
    span_id,
    name,
    span_type="LLM",
    model_name="gpt-4",
    parent_span_id=None,
):
    """Helper function to create a span with specified type and optional parent ID."""
    span = Span()
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
        created_at=base_time - timedelta(days=2),
        updated_at=base_time - timedelta(days=2),
    )
    spans.append(span1)

    # Span 2: Task1, Trace1 - CHAIN span with parent
    span2 = InternalSpan(
        id=str(uuid.uuid4()),
        trace_id="trace1",
        span_id="span2",
        task_id=None,  # No task_id - spans without task_id are not processed for metrics
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
        created_at=base_time,
        updated_at=base_time,
    )
    spans.append(span3)

    # Span 4: Task2, Trace2 - RETRIEVER span with parent
    span4 = InternalSpan(
        id=str(uuid.uuid4()),
        trace_id="trace2",
        span_id="span4",
        task_id=None,  # No task_id - spans without task_id are not processed for metrics
        parent_span_id="span3",
        span_kind="RETRIEVER",
        start_time=base_time + timedelta(days=1),
        end_time=base_time + timedelta(days=1) - timedelta(seconds=1),
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
        created_at=base_time + timedelta(days=1) - timedelta(seconds=1),
        updated_at=base_time + timedelta(days=1) - timedelta(seconds=1),
    )
    spans.append(span4)

    # Store spans in database
    spans_to_store = [span.model_dump() for span in spans]
    [span.pop("metric_results") for span in spans_to_store]
    span_repo._store_spans(spans_to_store)

    # Create metrics and metric results for LLM spans
    from db_models.db_models import (
        DatabaseMetric,
        DatabaseMetricResult,
        DatabaseTask,
        DatabaseTaskToMetrics,
    )
    from schemas.enums import MetricType

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

    # Create a test metric
    test_metric = DatabaseMetric(
        id=str(uuid.uuid4()),
        created_at=base_time,
        updated_at=base_time,
        type=MetricType.QUERY_RELEVANCE.value,
        name="Test Query Relevance",
        metric_metadata="Test metric for LLM spans",
        config=None,
    )
    db_session.add(test_metric)
    db_session.commit()

    # Create task-to-metric links for task1 and task2
    task1_metric_link = DatabaseTaskToMetrics(
        task_id="task1",
        metric_id=test_metric.id,
        enabled=True,
    )
    task2_metric_link = DatabaseTaskToMetrics(
        task_id="task2",
        metric_id=test_metric.id,
        enabled=True,
    )
    db_session.add(task1_metric_link)
    db_session.add(task2_metric_link)
    db_session.commit()

    # Create metric results for the LLM span (span1)
    metric_result = DatabaseMetricResult(
        id=str(uuid.uuid4()),
        created_at=base_time,
        updated_at=base_time,
        metric_type=MetricType.QUERY_RELEVANCE.value,
        details=json.dumps({"score": 0.85, "reason": "Query is relevant to the task"}),
        prompt_tokens=100,
        completion_tokens=50,
        latency_ms=1500,
        span_id=span1.id,
        metric_id=test_metric.id,
    )
    db_session.add(metric_result)
    db_session.commit()

    yield spans

    # Cleanup: Delete all created spans from the database after the test
    span_ids = [span.span_id for span in spans]
    _delete_spans_from_db(db_session, span_ids)

    # Cleanup: Delete metric results, task-to-metric links, metrics, and tasks
    db_session.query(DatabaseMetricResult).filter(
        DatabaseMetricResult.span_id.in_([span.id for span in spans]),
    ).delete(synchronize_session=False)
    db_session.query(DatabaseTaskToMetrics).filter(
        DatabaseTaskToMetrics.task_id.in_(["task1", "task2"]),
    ).delete(synchronize_session=False)
    db_session.query(DatabaseMetric).filter(DatabaseMetric.id == test_metric.id).delete(
        synchronize_session=False,
    )
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
