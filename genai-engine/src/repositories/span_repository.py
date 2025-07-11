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
from sqlalchemy import and_, asc, desc, insert, select
from sqlalchemy.orm import Session

from db_models.db_models import DatabaseMetricResult, DatabaseSpan
from dependencies import get_metrics_engine
from repositories.metrics_repository import MetricRepository
from repositories.tasks_metrics_repository import TasksMetricsRepository
from schemas.enums import PaginationSortMethod
from schemas.internal_schemas import MetricResult, Span
from schemas.metric_schemas import MetricRequest
from utils import trace as trace_utils
from utils.constants import (
    EXPECTED_SPAN_VERSION,
    METADATA_KEY,
    SPAN_KIND_KEY,
    SPAN_KIND_LLM,
    SPAN_VERSION_KEY,
    TASK_ID_KEY,
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Constants
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
    # Public API Methods
    # ============================================================================

    @tracer.start_as_current_span("store_traces")
    def create_traces(self, trace_data: bytes) -> Tuple[int, int, int, list[str]]:
        """Process trace data from protobuf format and store in database."""
        try:
            json_traces = self._grpc_trace_to_dict(trace_data)
            spans_data, stats = self._extract_and_process_spans(json_traces)

            if spans_data:
                self._store_spans(spans_data, commit=True)
                logger.debug(f"Stored {len(spans_data)} spans successfully")

            return stats
        except DecodeError as e:
            raise DecodeError("Failed to parse protobuf message.") from e

    def query_spans(
        self,
        sort: PaginationSortMethod,
        page: int,
        page_size: int = DEFAULT_PAGE_SIZE,
        trace_ids: Optional[list[str]] = None,
        span_ids: Optional[list[str]] = None,
        task_ids: Optional[list[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        include_metrics: bool = False,
        compute_new_metrics: bool = True,
    ) -> list[Span]:
        """Query spans with optional metrics computation."""
        # Validate parameters
        if include_metrics and compute_new_metrics and not task_ids:
            raise ValueError(
                "task_ids are required when include_metrics=True and compute_new_metrics=True",
            )

        # Handle task ID to trace ID resolution
        trace_ids = self._resolve_trace_ids_for_task_ids(task_ids, trace_ids)

        # Apply trace-level pagination
        trace_ids = self._apply_trace_level_pagination(trace_ids, page, page_size)
        if not trace_ids:
            return []

        # Query spans from database
        spans = self._query_spans_from_db(
            trace_ids=trace_ids,
            span_ids=span_ids,
            start_time=start_time,
            end_time=end_time,
            sort=sort,
        )

        # Validate spans and add metrics if requested
        valid_spans = self._validate_spans(spans)
        if include_metrics and valid_spans:
            valid_spans = self._add_metrics_to_spans(valid_spans, compute_new_metrics)

        return valid_spans

    def query_spans_by_span_id_with_metrics(self, span_id: str) -> list[Span]:
        """Query a single span by span_id and compute metrics for it."""
        # Query the specific span directly from database
        query = select(DatabaseSpan).where(DatabaseSpan.span_id == span_id)
        results = self.db_session.execute(query).scalars().unique().all()

        if not results:
            raise ValueError(f"Span with ID {span_id} not found")

        span = Span._from_database_model(results[0])

        # Validate span version
        if not trace_utils.validate_span_version(span.raw_data):
            raise ValueError(f"Span {span_id} failed version validation")

        # Validate that this is an LLM span
        self._validate_span_for_metrics(span, span_id)

        # Compute metrics for this span
        return self._add_metrics_to_spans([span])

    # ============================================================================
    # Private Helper Methods - Query Logic
    # ============================================================================

    def _resolve_trace_ids_for_task_ids(
        self,
        task_ids: Optional[list[str]],
        trace_ids: Optional[list[str]],
    ) -> Optional[list[str]]:
        """Resolve trace IDs for given task IDs and intersect with provided trace IDs."""
        if not task_ids:
            return trace_ids

        associated_trace_ids = self._get_trace_ids_for_task_ids(task_ids)
        if trace_ids:
            return list(set(trace_ids) & set(associated_trace_ids))
        return associated_trace_ids

    def _apply_trace_level_pagination(
        self,
        trace_ids: Optional[list[str]],
        page: int,
        page_size: int,
    ) -> Optional[list[str]]:
        """Apply pagination to trace IDs."""
        if not trace_ids or page_size is None:
            return trace_ids

        start_idx = page * page_size
        end_idx = start_idx + page_size
        paginated_trace_ids = trace_ids[start_idx:end_idx]

        return paginated_trace_ids if paginated_trace_ids else None

    def _query_spans_from_db(
        self,
        trace_ids: Optional[list[str]] = None,
        span_ids: Optional[list[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        sort: PaginationSortMethod = PaginationSortMethod.DESCENDING,
    ) -> list[Span]:
        """Query spans from database with given filters."""
        query = self._build_spans_query(
            trace_ids=trace_ids,
            span_ids=span_ids,
            start_time=start_time,
            end_time=end_time,
            sort=sort,
        )

        results = self.db_session.execute(query).scalars().unique().all()
        return [Span._from_database_model(span) for span in results]

    def _validate_spans(self, spans: list[Span]) -> list[Span]:
        """Validate spans and return only valid ones."""
        valid_spans = []
        for span in spans:
            if trace_utils.validate_span_version(span.raw_data):
                valid_spans.append(span)
            else:
                logger.warning(
                    f"Skipping span {span.id} due to version validation failure",
                )
        return valid_spans

    def _validate_span_for_metrics(self, span: Span, span_id: str):
        """Validate that a span can have metrics computed for it."""
        if span.span_kind != SPAN_KIND_LLM:
            raise ValueError(
                f"Span {span_id} is not an LLM span (span_kind: {span.span_kind})",
            )

        if not span.task_id:
            raise ValueError(f"Span {span_id} has no task_id")

    # ============================================================================
    # Private Helper Methods - Task ID Resolution
    # ============================================================================

    def _get_trace_ids_for_task_ids(self, task_ids: list[str]) -> list[str]:
        """Get all trace IDs associated with the given task IDs."""
        if not task_ids:
            return []

        trace_ids_query = (
            self.db_session.query(DatabaseSpan.trace_id)
            .filter(DatabaseSpan.task_id.in_(task_ids))
            .distinct()
        )

        trace_ids = [row[0] for row in trace_ids_query.all()]
        logger.debug(f"Found {len(trace_ids)} trace IDs for task IDs: {task_ids}")
        return trace_ids

    # ============================================================================
    # Private Helper Methods - Metrics Computation
    # ============================================================================

    def _add_metrics_to_spans(
        self,
        spans: list[Span],
        compute_new_metrics: bool = True,
    ) -> list[Span]:
        """Add metrics to spans by computing missing metrics and embedding all results."""
        span_ids = [span.id for span in spans]
        existing_metric_results = self._get_metric_results_for_spans(span_ids)

        # Compute metrics for spans that don't have them (only if requested)
        if compute_new_metrics:
            spans_without_metrics = [
                span for span in spans if span.id not in existing_metric_results
            ]

            if spans_without_metrics:
                logger.debug(
                    f"Computing metrics for {len(spans_without_metrics)} spans",
                )
                new_metric_results = self._compute_metrics_for_spans(
                    spans_without_metrics,
                )
                self._store_metric_results(new_metric_results)
                existing_metric_results.update(new_metric_results)

        # Embed metrics into spans
        for span in spans:
            span.metric_results = existing_metric_results.get(span.id, [])

        return spans

    def _get_metric_results_for_spans(
        self,
        span_ids: list[str],
    ) -> dict[str, list[MetricResult]]:
        """Get existing metric results for the given span IDs."""
        if not span_ids:
            return {}

        metric_results = (
            self.db_session.query(DatabaseMetricResult)
            .filter(DatabaseMetricResult.span_id.in_(span_ids))
            .all()
        )

        # Group by span_id
        results_by_span = {}
        for db_result in metric_results:
            span_id = db_result.span_id
            if span_id not in results_by_span:
                results_by_span[span_id] = []
            results_by_span[span_id].append(
                MetricResult._from_database_model(db_result),
            )

        return results_by_span

    def _compute_metrics_for_spans(
        self,
        spans: list[Span],
    ) -> dict[str, list[MetricResult]]:
        """Compute metrics for the given spans."""
        if not spans:
            return {}

        metrics_engine = get_metrics_engine()
        metrics_results = {}

        logger.debug(f"Computing metrics for {len(spans)} spans")

        for span in spans:
            if not self._should_compute_metrics_for_span(span):
                continue

            try:
                results = self._compute_metrics_for_single_span(span, metrics_engine)
                if results:
                    metrics_results[span.id] = results
            except Exception as e:
                logger.error(f"Error computing metrics for span {span.id}: {e}")
                continue

        total_metrics = sum(len(results) for results in metrics_results.values())
        logger.debug(f"Total metrics computed: {total_metrics}")
        return metrics_results

    def _should_compute_metrics_for_span(self, span: Span) -> bool:
        """Check if metrics should be computed for a given span."""
        if not span.task_id:
            logger.warning(
                f"Span {span.id} has no task_id, skipping metric computation",
            )
            return False

        if span.span_kind != SPAN_KIND_LLM:
            logger.debug(
                f"Skipping metric computation for span {span.id} - span kind is {span.span_kind}, not LLM",
            )
            return False

        return True

    def _compute_metrics_for_single_span(
        self,
        span: Span,
        metrics_engine,
    ) -> list[MetricResult]:
        """Compute metrics for a single span."""
        # Convert span to MetricRequest format
        span_request = self._span_to_metric_request(span)

        # Get metrics for this task
        metric_ids = self.tasks_metrics_repo.get_task_metrics_ids_cached(span.task_id)
        metrics = self.metrics_repo.get_metrics_by_metric_id(metric_ids)

        if not metrics:
            logger.debug(f"No metrics found for task {span.task_id}")
            return []

        # Compute metrics
        results = metrics_engine.evaluate(span_request, metrics)

        # Set span_id and metric_id on results
        metric_results = []
        for i, result in enumerate(results):
            if i < len(metrics):
                metric_id = metrics[i].id
                result.span_id = span.id
                result.metric_id = metric_id
                metric_results.append(result)

        logger.debug(f"Computed {len(results)} metrics for span {span.id}")
        return metric_results

    def _span_to_metric_request(self, span: Span) -> MetricRequest:
        """Convert a Span to MetricRequest format for metric computation."""
        system_prompt = span.system_prompt or ""
        user_query = span.user_query or ""
        context = span.context or []
        response = (
            self._extract_response_content(span.response) if span.response else ""
        )

        return MetricRequest(
            system_prompt=system_prompt,
            user_query=user_query,
            context=context,
            response=response,
        )

    def _extract_response_content(self, response_data: Union[str, dict]) -> str:
        """Extract response content from span features."""
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

    def _store_metric_results(self, metrics_results: dict[str, list[MetricResult]]):
        """Store metric results in the database."""
        if not metrics_results:
            return

        # Collect all metric results to store
        metric_results_to_insert = []
        for span_id, results in metrics_results.items():
            for result in results:
                metric_results_to_insert.append(
                    {
                        "id": result.id,
                        "created_at": result.created_at,
                        "updated_at": result.updated_at,
                        "metric_type": result.metric_type.value,
                        "details": (
                            result.details.model_dump_json() if result.details else None
                        ),
                        "prompt_tokens": result.prompt_tokens,
                        "completion_tokens": result.completion_tokens,
                        "latency_ms": result.latency_ms,
                        "span_id": span_id,
                        "metric_id": result.metric_id,
                    },
                )

        # Bulk insert metric results
        if metric_results_to_insert:
            stmt = insert(DatabaseMetricResult).values(metric_results_to_insert)
            self.db_session.execute(stmt)
            self.db_session.commit()

        logger.debug(f"Stored {len(metric_results_to_insert)} metric results")

    # ============================================================================
    # Private Helper Methods - Database Operations
    # ============================================================================

    def _build_spans_query(
        self,
        trace_ids: Optional[list[str]] = None,
        span_ids: Optional[list[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        sort: PaginationSortMethod = PaginationSortMethod.DESCENDING,
    ) -> select:
        """Build a query for spans with the given filters."""
        query = select(DatabaseSpan)

        # Build filter conditions
        conditions = []
        if trace_ids:
            conditions.append(DatabaseSpan.trace_id.in_(trace_ids))
        if span_ids:
            conditions.append(DatabaseSpan.span_id.in_(span_ids))
        if start_time:
            conditions.append(DatabaseSpan.created_at >= start_time)
        if end_time:
            conditions.append(DatabaseSpan.created_at <= end_time)

        # Apply filters if any conditions exist
        if conditions:
            query = query.where(and_(*conditions))

        # Apply sorting
        if sort == PaginationSortMethod.DESCENDING:
            query = query.order_by(desc(DatabaseSpan.created_at))
        elif sort == PaginationSortMethod.ASCENDING:
            query = query.order_by(asc(DatabaseSpan.created_at))

        return query

    def _store_spans(self, spans: list[dict], commit: bool = True):
        """Store spans in the database with optional commit control."""
        if not spans:
            return

        stmt = insert(DatabaseSpan).values(spans)
        self.db_session.execute(stmt)

        if commit:
            self.db_session.commit()

        logger.debug(f"Stored {len(spans)} spans (commit={commit})")

    # ============================================================================
    # Private Helper Methods - Trace Processing
    # ============================================================================

    def _extract_and_process_spans(
        self,
        json_traces: dict,
    ) -> Tuple[list[dict], Tuple[int, int, int, list[str]]]:
        """Extract and process spans from JSON trace data."""
        total_spans = 0
        accepted_spans = 0
        rejected_spans = 0
        rejected_reasons = []
        spans_data = []

        for resource_span in json_traces.get("resourceSpans", []):
            for scope_span in resource_span.get("scopeSpans", []):
                for span_data in scope_span.get("spans", []):
                    total_spans += 1
                    processed_span = self._process_span_data(span_data)

                    if processed_span:
                        processed_span["id"] = str(uuid.uuid4())
                        spans_data.append(processed_span)
                        accepted_spans += 1
                    else:
                        rejected_spans += 1
                        rejected_reasons.append("Invalid span data format.")
                        logger.debug(
                            f"Rejected span due to invalid format: \n{span_data}",
                        )

        return spans_data, (
            total_spans,
            accepted_spans,
            rejected_spans,
            rejected_reasons,
        )

    def _grpc_trace_to_dict(self, trace_data: bytes) -> dict:
        """Convert gRPC trace data to dictionary format."""
        try:
            trace_request = ExportTraceServiceRequest()
            trace_request.ParseFromString(trace_data)
            return MessageToDict(trace_request)
        except DecodeError as e:
            raise DecodeError("Failed to decode protobuf message.") from e

    def _process_span_data(self, span_data: dict) -> Optional[dict]:
        """Process and clean span data, returning None if the span data is invalid."""
        normalized_span_data = self._normalize_span_attributes(span_data)

        # Extract basic span information
        span_dict = self._extract_basic_span_info(normalized_span_data)

        # Extract and validate task_id
        task_id = self._extract_and_validate_task_id(
            normalized_span_data,
            span_dict.get("parent_span_id"),
        )
        span_dict["task_id"] = task_id

        # Inject version into raw data
        normalized_span_data[SPAN_VERSION_KEY] = EXPECTED_SPAN_VERSION

        # Store the normalized span data
        span_dict["raw_data"] = normalized_span_data

        # Accept all spans - no discrimination on task_id or parent_id
        return span_dict

    def _extract_basic_span_info(self, span_data: dict) -> dict:
        """Extract basic span information from normalized span data."""
        span_dict = {
            "trace_id": trace_utils.convert_id_to_hex(span_data.get("traceId")),
            "span_id": trace_utils.convert_id_to_hex(span_data.get("spanId")),
        }

        # Extract parent span ID
        parent_span_id = self._get_parent_span_id(span_data)
        if parent_span_id:
            span_dict["parent_span_id"] = parent_span_id

        # Extract span kind
        span_kind = self._get_attribute_value(span_data, SPAN_KIND_KEY)
        if span_kind:
            span_dict["span_kind"] = span_kind

        # Extract timestamps
        start_time, end_time = self._extract_timestamps(span_data)
        span_dict["start_time"] = start_time
        span_dict["end_time"] = end_time

        return span_dict

    def _extract_and_validate_task_id(
        self,
        span_data: dict,
        parent_span_id: Optional[str],
    ) -> Optional[str]:
        """Extract task_id from span data or parent span."""
        # Extract metadata and task_id from normalized attributes
        metadata = self._get_metadata(span_data)
        task_id = metadata.get(TASK_ID_KEY)

        # If no task ID in current span, try to get it from parent span
        if not task_id and parent_span_id:
            task_id = self._get_task_id_from_parent(parent_span_id)
            if task_id:
                logger.debug(
                    f"Using task ID from parent span {parent_span_id}: {task_id}",
                )

        return task_id

    def _normalize_span_attributes(self, span_data: dict) -> dict:
        """Normalize span attributes from OpenTelemetry format to flat key-value pairs."""
        normalized_span = span_data.copy()

        if "attributes" in normalized_span:
            normalized_attributes = trace_utils.extract_attributes_from_raw_data(
                normalized_span,
            )
            normalized_span["attributes"] = normalized_attributes

        return normalized_span

    def _get_attribute_value(
        self,
        span_data: dict,
        attribute_key: str,
    ) -> Optional[str]:
        """Extract a specific attribute value from span data."""
        attributes = span_data.get("attributes", {})

        # Attributes should already be normalized (flat dict)
        if isinstance(attributes, dict):
            return attributes.get(attribute_key)

        # Fallback for backward compatibility with OpenTelemetry format
        if isinstance(attributes, list):
            for attr in attributes:
                key = attr.get("key")
                value = attr.get("value", {})
                if key == attribute_key:
                    return value.get("stringValue")

        return None

    def _get_parent_span_id(self, span_data: dict) -> Optional[str]:
        """Extract parent span ID from span data."""
        if "parentSpanId" in span_data:
            return trace_utils.convert_id_to_hex(span_data.get("parentSpanId"))
        return None

    def _get_task_id_from_parent(self, parent_span_id: str) -> Optional[str]:
        """Get the task ID from a parent span if it exists in the database."""
        if not parent_span_id:
            return None

        try:
            parent_span = (
                self.db_session.query(DatabaseSpan)
                .filter(DatabaseSpan.span_id == parent_span_id)
                .first()
            )
            return parent_span.task_id if parent_span else None
        except Exception as e:
            logger.warning(f"Error retrieving parent span {parent_span_id}: {e}")
            return None

    def _extract_timestamps(
        self,
        span_data: dict,
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Extract and convert timestamps from span data."""
        start_time = None
        end_time = None

        if "startTimeUnixNano" in span_data:
            start_time_ns = int(span_data.get("startTimeUnixNano", 0))
            start_time = trace_utils.timestamp_ns_to_datetime(start_time_ns)

        if "endTimeUnixNano" in span_data:
            end_time_ns = int(span_data.get("endTimeUnixNano", 0))
            end_time = trace_utils.timestamp_ns_to_datetime(end_time_ns)

        return start_time, end_time

    def _get_metadata(self, span_data: dict) -> dict:
        """Get the metadata from the span data."""
        metadata_str = self._get_attribute_value(span_data, METADATA_KEY)
        if metadata_str:
            try:
                return json.loads(metadata_str)
            except json.JSONDecodeError:
                return {}
        return {}
