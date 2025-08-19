import json
import logging
import uuid
from datetime import datetime
from typing import Optional, Tuple, Union

from google.protobuf.json_format import MessageToDict
from google.protobuf.message import DecodeError
from opentelemetry import trace
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)
from sqlalchemy import and_, asc, desc, func, insert, select
from sqlalchemy.orm import Session

from db_models.db_models import DatabaseMetricResult, DatabaseSpan
from dependencies import get_metrics_engine
from repositories.metrics_repository import MetricRepository
from repositories.tasks_metrics_repository import TasksMetricsRepository
from schemas.enums import PaginationSortMethod
from schemas.internal_schemas import MetricResult, Span
from schemas.metric_schemas import MetricRequest
from schemas.response_schemas import TraceResponse
from utils import trace as trace_utils
from utils.constants import (
    EXPECTED_SPAN_VERSION,
    SPAN_KIND_KEY,
    SPAN_KIND_LLM,
    SPAN_VERSION_KEY,
    TASK_ID_KEY,
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

DEFAULT_PAGE_SIZE = 5


class SpanRepository:
    def __init__(
        self,
        db_session: Session,
        tasks_metrics_repo: TasksMetricsRepository,
        metrics_repo: MetricRepository,
    ):
        self.db_session = db_session
        self.tasks_metrics_repo = tasks_metrics_repo
        self.metrics_repo = metrics_repo

    # ============================================================================
    # Public API - Trace Storage
    # ============================================================================

    @tracer.start_as_current_span("store_traces")
    def create_traces(self, trace_data: bytes) -> Tuple[int, int, int, list[str]]:
        """Process trace data from protobuf format and store in database."""
        try:
            json_traces = self._parse_protobuf_traces(trace_data)
            spans_data, stats = self._extract_spans_from_traces(json_traces)

            if spans_data:
                self._store_spans(spans_data)
                logger.debug(f"Stored {len(spans_data)} spans successfully")

            return stats
        except DecodeError as e:
            raise DecodeError("Failed to parse protobuf message.") from e

    # ============================================================================
    # Public API - Span Queries
    # ============================================================================

    def query_spans(
        self,
        task_ids: list[str],
        sort: PaginationSortMethod = PaginationSortMethod.DESCENDING,
        page: int = 0,
        page_size: int = DEFAULT_PAGE_SIZE,
        trace_ids: Optional[list[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        include_metrics: bool = False,
        compute_new_metrics: bool = True,
    ) -> list[Span]:
        """Query spans with optional metrics."""
        # Get trace IDs for the task IDs with sorting/pagination
        trace_ids = self._get_paginated_trace_ids(
            task_ids,
            trace_ids,
            sort,
            page,
            page_size,
            start_time,
            end_time,
        )
        if not trace_ids:
            return []

        # Query spans and add metrics if requested
        spans = self._execute_span_query(
            trace_filter=DatabaseSpan.trace_id.in_(trace_ids),
            start_time=start_time,
            end_time=end_time,
            sort=sort,
            include_metrics=include_metrics,
        )

        if include_metrics and compute_new_metrics:
            spans = self._add_missing_metrics(spans)

        return spans

    def query_span_by_span_id_with_metrics(self, span_id: str) -> Span:
        """Get single span with metrics."""
        spans = self._execute_span_query(
            trace_filter=DatabaseSpan.span_id == span_id,
            include_metrics=True,
        )
        if not spans:
            raise ValueError(f"Span with ID {span_id} not found")

        span = spans[0]
        if span.span_kind != SPAN_KIND_LLM or not span.task_id:
            raise ValueError(f"Span {span_id} is not an LLM span or has no task_id")

        if not span.metric_results:
            spans = self._add_missing_metrics([span])
            span = spans[0]

        return span

    def query_spans_as_traces(
        self,
        task_ids: list[str],
        sort: PaginationSortMethod = PaginationSortMethod.DESCENDING,
        page: int = 0,
        page_size: int = DEFAULT_PAGE_SIZE,
        trace_ids: Optional[list[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        include_metrics: bool = False,
        compute_new_metrics: bool = True,
    ) -> tuple[int, list]:
        """Query spans grouped into trace structure."""
        spans = self.query_spans(
            task_ids,
            sort,
            page,
            page_size,
            trace_ids,
            start_time,
            end_time,
            include_metrics,
            compute_new_metrics,
        )
        traces = self._group_spans_into_traces(spans, sort)
        return len(traces), traces

    def query_spans_with_metrics_as_traces(
        self,
        task_ids: list[str],
        sort: PaginationSortMethod = PaginationSortMethod.DESCENDING,
        page: int = 0,
        page_size: int = DEFAULT_PAGE_SIZE,
        trace_ids: Optional[list[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> tuple[int, list]:
        """Query spans with metrics grouped into trace structure."""
        return self.query_spans_as_traces(
            task_ids,
            sort,
            page,
            page_size,
            trace_ids,
            start_time,
            end_time,
            include_metrics=True,
            compute_new_metrics=True,
        )

    # ============================================================================
    # Private - Query Helpers
    # ============================================================================

    def _get_paginated_trace_ids(
        self,
        task_ids: list[str],
        trace_ids: Optional[list[str]],
        sort: PaginationSortMethod,
        page: int,
        page_size: int,
        start_time: Optional[datetime],
        end_time: Optional[datetime],
    ) -> list[str]:
        """Get trace IDs for task IDs with sorting and pagination."""
        # Build subquery for trace start times
        trace_times = self.db_session.query(
            DatabaseSpan.trace_id,
            func.min(DatabaseSpan.start_time).label("trace_start_time"),
        ).filter(DatabaseSpan.task_id.in_(task_ids))

        # Apply time filters
        if start_time:
            trace_times = trace_times.filter(DatabaseSpan.start_time >= start_time)
        if end_time:
            trace_times = trace_times.filter(DatabaseSpan.start_time <= end_time)

        trace_times = trace_times.group_by(DatabaseSpan.trace_id).subquery()

        # Query with sorting and pagination
        query = self.db_session.query(trace_times.c.trace_id)

        if sort == PaginationSortMethod.DESCENDING:
            query = query.order_by(desc(trace_times.c.trace_start_time))
        else:
            query = query.order_by(asc(trace_times.c.trace_start_time))

        query = query.offset(page * page_size).limit(page_size)
        result_trace_ids = [row[0] for row in query.all()]

        # Intersect with provided trace_ids if any
        if trace_ids:
            result_trace_ids = list(set(trace_ids) & set(result_trace_ids))

        return result_trace_ids

    def _execute_span_query(
        self,
        trace_filter,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        sort: PaginationSortMethod = PaginationSortMethod.DESCENDING,
        include_metrics: bool = False,
    ) -> list[Span]:
        """Execute span query with optional metrics JOIN."""
        # Build base query
        if include_metrics:
            query = select(DatabaseSpan, DatabaseMetricResult).select_from(
                DatabaseSpan.__table__.outerjoin(
                    DatabaseMetricResult.__table__,
                    DatabaseSpan.id == DatabaseMetricResult.span_id,
                ),
            )
        else:
            query = select(DatabaseSpan)

        # Apply filters
        conditions = [
            DatabaseSpan.raw_data.op("->>")("span_version").astext
            == EXPECTED_SPAN_VERSION,
            trace_filter,
        ]

        if start_time:
            conditions.append(DatabaseSpan.created_at >= start_time)
        if end_time:
            conditions.append(DatabaseSpan.created_at <= end_time)

        query = query.where(and_(*conditions))

        # Apply sorting
        if sort == PaginationSortMethod.DESCENDING:
            query = query.order_by(desc(DatabaseSpan.created_at))
        else:
            query = query.order_by(asc(DatabaseSpan.created_at))

        # Execute and process results
        results = self.db_session.execute(query).all()
        return self._build_spans_from_results(results, include_metrics)

    def _build_spans_from_results(self, results, include_metrics: bool) -> list[Span]:
        """Convert query results to Span objects."""
        spans_dict = {}

        for row in results:
            if include_metrics:
                span_data, metric_data = row
            else:
                span_data = row
                metric_data = None

            span_id = span_data.id

            # Create span if not exists
            if span_id not in spans_dict:
                span = Span._from_database_model(span_data)
                span.metric_results = []
                spans_dict[span_id] = span

            # Add metric if exists
            if metric_data:
                metric_result = MetricResult._from_database_model(metric_data)
                spans_dict[span_id].metric_results.append(metric_result)

        return list(spans_dict.values())

    # ============================================================================
    # Private - Metrics Processing
    # ============================================================================

    def _add_missing_metrics(self, spans: list[Span]) -> list[Span]:
        """Compute metrics for LLM spans that don't have any."""
        llm_spans_needing_metrics = [
            span
            for span in spans
            if (
                span.span_kind == SPAN_KIND_LLM
                and span.task_id
                and not span.metric_results
            )
        ]

        if not llm_spans_needing_metrics:
            return spans

        logger.info(f"Computing metrics for {len(llm_spans_needing_metrics)} LLM spans")

        try:
            metrics_engine = get_metrics_engine()
        except Exception as e:
            logger.error(f"Error getting metrics engine: {e}")
            return spans

        # Compute metrics for each span
        for span in llm_spans_needing_metrics:
            try:
                # Get metrics for this task
                metric_ids = self.tasks_metrics_repo.get_task_metrics_ids_cached(
                    span.task_id,
                )
                metrics = self.metrics_repo.get_metrics_by_metric_id(metric_ids)

                if not metrics:
                    continue

                # Convert span to metric request
                span_request = MetricRequest(
                    system_prompt=span.system_prompt or "",
                    user_query=span.user_query or "",
                    context=span.context or [],
                    response=(
                        self._extract_response_content(span.response)
                        if span.response
                        else ""
                    ),
                )

                # Compute metrics
                results = metrics_engine.evaluate(span_request, metrics)

                # Store results
                metric_results = []
                for i, result in enumerate(results):
                    if i < len(metrics):
                        result.span_id = span.id
                        result.metric_id = metrics[i].id
                        metric_results.append(result)

                if metric_results:
                    self._store_metric_results(span.id, metric_results)
                    span.metric_results = metric_results

            except Exception as e:
                logger.error(f"Error computing metrics for span {span.id}: {e}")
                continue

        return spans

    def _extract_response_content(self, response_data: Union[str, dict]) -> str:
        """Extract response content from span response."""
        if isinstance(response_data, str):
            return response_data
        elif isinstance(response_data, dict):
            if "content" in response_data:
                return response_data["content"]
            elif "tool_calls" in response_data:
                return json.dumps(response_data["tool_calls"])
            else:
                return json.dumps(response_data)
        else:
            return str(response_data)

    def _store_metric_results(self, span_id: str, results: list[MetricResult]):
        """Store metric results in database."""
        if not results:
            return

        metric_data = [
            {
                "id": result.id,
                "created_at": result.created_at,
                "updated_at": result.updated_at,
                "metric_type": result.metric_type.value,
                "details": result.details.model_dump_json() if result.details else None,
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "latency_ms": result.latency_ms,
                "span_id": span_id,
                "metric_id": result.metric_id,
            }
            for result in results
        ]

        stmt = insert(DatabaseMetricResult).values(metric_data)
        self.db_session.execute(stmt)
        self.db_session.commit()

    # ============================================================================
    # Private - Trace Processing & Storage
    # ============================================================================

    def _parse_protobuf_traces(self, trace_data: bytes) -> dict:
        """Convert protobuf trace data to dict."""
        trace_request = ExportTraceServiceRequest()
        trace_request.ParseFromString(trace_data)
        return MessageToDict(trace_request)

    def _extract_spans_from_traces(
        self,
        json_traces: dict,
    ) -> Tuple[list[dict], Tuple[int, int, int, list[str]]]:
        """Extract and process spans from trace data."""
        total_spans = 0
        accepted_spans = 0
        rejected_spans = 0
        rejected_reasons = []
        spans_data = []

        for resource_span in json_traces.get("resourceSpans", []):
            # Extract task ID from resource
            task_id = self._extract_task_id_from_resource(resource_span)
            if not task_id:
                # Reject all spans in this resource
                for scope_span in resource_span.get("scopeSpans", []):
                    spans_count = len(scope_span.get("spans", []))
                    total_spans += spans_count
                    rejected_spans += spans_count
                    rejected_reasons.extend(["Invalid task ID"] * spans_count)
                continue

            # Process spans in this resource
            for scope_span in resource_span.get("scopeSpans", []):
                for span_data in scope_span.get("spans", []):
                    total_spans += 1
                    processed_span = self._process_span_data(span_data, task_id)

                    if processed_span:
                        processed_span["id"] = str(uuid.uuid4())
                        spans_data.append(processed_span)
                        accepted_spans += 1
                    else:
                        rejected_spans += 1
                        rejected_reasons.append("Invalid span data format")

        return spans_data, (
            total_spans,
            accepted_spans,
            rejected_spans,
            rejected_reasons,
        )

    def _extract_task_id_from_resource(self, resource_span: dict) -> Optional[str]:
        """Extract task ID from resource attributes."""
        attributes = resource_span.get("resource", {}).get("attributes", [])

        for attr in attributes:
            if isinstance(attr, dict) and attr.get("key") == TASK_ID_KEY:
                value = attr.get("value", {})
                if "stringValue" in value:
                    return value["stringValue"]
        return None

    def _process_span_data(self, span_data: dict, task_id: str) -> Optional[dict]:
        """Process raw span data into database format."""
        # Normalize attributes
        normalized_span = span_data.copy()
        if "attributes" in normalized_span:
            normalized_attributes = trace_utils.extract_attributes_from_raw_data(
                normalized_span,
            )
            normalized_span["attributes"] = normalized_attributes

        # Extract basic info
        span_dict = {
            "trace_id": trace_utils.convert_id_to_hex(normalized_span.get("traceId")),
            "span_id": trace_utils.convert_id_to_hex(normalized_span.get("spanId")),
            "task_id": task_id,
        }

        # Extract optional fields
        if "parentSpanId" in normalized_span:
            span_dict["parent_span_id"] = trace_utils.convert_id_to_hex(
                normalized_span.get("parentSpanId"),
            )

        span_kind = normalized_span.get("attributes", {}).get(SPAN_KIND_KEY)
        if span_kind:
            span_dict["span_kind"] = span_kind

        # Extract timestamps
        if "startTimeUnixNano" in normalized_span:
            start_time_ns = int(normalized_span.get("startTimeUnixNano", 0))
            span_dict["start_time"] = trace_utils.timestamp_ns_to_datetime(
                start_time_ns,
            )

        if "endTimeUnixNano" in normalized_span:
            end_time_ns = int(normalized_span.get("endTimeUnixNano", 0))
            span_dict["end_time"] = trace_utils.timestamp_ns_to_datetime(end_time_ns)

        # Add version and store raw data
        normalized_span[SPAN_VERSION_KEY] = EXPECTED_SPAN_VERSION
        span_dict["raw_data"] = normalized_span

        return span_dict

    def _store_spans(self, spans: list[dict]):
        """Store spans in database."""
        if not spans:
            return

        stmt = insert(DatabaseSpan).values(spans)
        self.db_session.execute(stmt)
        self.db_session.commit()

    # ============================================================================
    # Private - Trace Grouping
    # ============================================================================

    def _group_spans_into_traces(
        self,
        spans: list[Span],
        sort: PaginationSortMethod,
    ) -> list:
        """Group spans into nested trace structure."""
        if not spans:
            return []

        # Group by trace_id
        traces_dict = {}
        for span in spans:
            trace_id = span.trace_id
            if trace_id not in traces_dict:
                traces_dict[trace_id] = []
            traces_dict[trace_id].append(span)

        # Build trace responses
        traces = []
        for trace_id, trace_spans in traces_dict.items():
            start_time = min(span.start_time for span in trace_spans)
            end_time = max(span.end_time for span in trace_spans)
            root_spans = self._build_span_tree(trace_spans)

            traces.append(
                TraceResponse(
                    trace_id=trace_id,
                    start_time=start_time,
                    end_time=end_time,
                    root_spans=root_spans,
                ),
            )

        # Sort traces
        reverse = sort == PaginationSortMethod.DESCENDING
        traces.sort(key=lambda t: t.start_time, reverse=reverse)
        return traces

    def _build_span_tree(self, spans: list[Span]) -> list:
        """Build nested span tree from flat list."""
        if not spans:
            return []

        # Group children by parent
        children_by_parent = {}
        root_spans = []

        for span in spans:
            if span.parent_span_id is None:
                root_spans.append(span)
            else:
                if span.parent_span_id not in children_by_parent:
                    children_by_parent[span.parent_span_id] = []
                children_by_parent[span.parent_span_id].append(span)

        # Build nested structure
        def build_nested_span(span: Span):
            children = children_by_parent.get(span.span_id, [])
            children.sort(key=lambda s: s.start_time)
            nested_children = [build_nested_span(child) for child in children]
            return span._to_nested_metrics_response_model(children=nested_children)

        root_spans.sort(key=lambda s: s.start_time)
        return [build_nested_span(root_span) for root_span in root_spans]
