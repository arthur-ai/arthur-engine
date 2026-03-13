import logging
import uuid
from datetime import datetime
from typing import Any, List, Optional, Tuple
from uuid import UUID

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import PaginationSortMethod, RegisteredAgentProvider
from arthur_common.models.request_schemas import TraceQueryRequest
from arthur_common.models.response_schemas import TraceResponse
from google.protobuf.message import DecodeError
from openinference.semconv.trace import SpanAttributes
from opentelemetry import trace
from sqlalchemy import insert
from sqlalchemy.orm import Session

from db_models import DatabaseSpan
from repositories.metrics_repository import MetricRepository
from repositories.tasks_metrics_repository import TasksMetricsRepository
from schemas.internal_schemas import (
    AgenticAnnotation,
    SessionMetadata,
    Span,
    TraceMetadata,
    TraceQuerySchema,
    TraceUserMetadata,
)
from schemas.request_schemas import (
    AgenticAnnotationListFilterRequest,
    AgenticAnnotationRequest,
)
from services.trace.gcp_conversion_service import GcpConversionService
from services.trace.metrics_integration_service import MetricsIntegrationService
from services.trace.otel_conversion_service import OtelConversionService
from services.trace.span_query_service import SpanQueryService
from services.trace.trace_annotation_service import TraceAnnotationService
from services.trace.trace_ingestion_service import TraceIngestionService
from services.trace.tree_building_service import TreeBuildingService
from utils import trace as trace_utils
from utils.constants import (
    EXPECTED_SPAN_VERSION,
    SPAN_VERSION_KEY,
)
from utils.trace import validate_span_version

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

        # Initialize services
        self.trace_annotation_service = TraceAnnotationService(db_session)
        self.trace_ingestion_service = TraceIngestionService(db_session)
        self.span_query_service = SpanQueryService(db_session)
        self.metrics_integration_service = MetricsIntegrationService(
            db_session,
            tasks_metrics_repo,
            metrics_repo,
        )
        self.tree_building_service = TreeBuildingService()
        self.otel_conversion_service = OtelConversionService()
        self.gcp_conversion_service = GcpConversionService()

    # ============================================================================
    # Public API Methods - Used by Optimized Trace Endpoints
    # ============================================================================

    def get_traces_metadata(
        self,
        filters: TraceQueryRequest,
        pagination_parameters: PaginationParameters,
        user_ids: Optional[list[str]] = None,
        include_spans: bool = False,
        sort_by: str = "start_time",
    ) -> tuple[int, list[TraceMetadata]]:
        """Get lightweight trace metadata for browsing/filtering operations.

        Returns metadata only without spans or metrics for fast performance.
        When include_spans=True, also fetches and attaches all spans for each trace as a flat list.
        """
        # Convert to internal schema format
        internal_filters: TraceQuerySchema = TraceQuerySchema._from_request_model(
            filters,
        )

        # Add user_ids to filters if provided
        if user_ids:
            internal_filters.user_ids = user_ids

        if not internal_filters.task_ids:
            raise ValueError("task_ids are required for trace queries")

        # Get trace metadata without loading spans
        paginated_trace_ids, total_count = (
            self.span_query_service.get_paginated_trace_ids_with_filters(
                filters=internal_filters,
                pagination_parameters=pagination_parameters,
                sort_by=sort_by,
            )
        )

        if total_count == 0:
            return 0, []

        # Get trace metadata objects directly
        trace_metadata_list = self.span_query_service.get_trace_metadata_by_ids(
            trace_ids=paginated_trace_ids,
            sort_method=pagination_parameters.sort,
        )

        # Optionally fetch and attach spans as a flat list
        if include_spans and trace_metadata_list:
            # Fetch all spans for the paginated trace_ids
            spans, _ = self.span_query_service.query_spans_from_db(
                trace_ids=paginated_trace_ids,
            )

            # Validate spans
            valid_spans = self.span_query_service.validate_spans(spans)

            # Add metrics to spans (existing metrics only, no computation)
            if valid_spans:
                valid_spans = self.metrics_integration_service.add_metrics_to_spans(
                    valid_spans,
                    compute_new_metrics=False,
                )

            # Group spans by trace_id for easy lookup
            spans_by_trace: dict[str, list[Span]] = {}
            for span in valid_spans:
                if span.trace_id not in spans_by_trace:
                    spans_by_trace[span.trace_id] = []
                spans_by_trace[span.trace_id].append(span)

            # Attach spans to each trace_metadata
            for trace_metadata in trace_metadata_list:
                trace_metadata.spans = spans_by_trace.get(trace_metadata.trace_id, [])

        return total_count, trace_metadata_list

    def get_user_details(
        self,
        user_id: str,
        task_ids: list[str],
    ) -> Optional[TraceUserMetadata]:
        """Get detailed information for a single user."""
        if not task_ids:
            raise ValueError("task_ids are required for user queries")

        # Get user metadata
        user_metadata = self.span_query_service.get_user_metadata_by_id(
            user_id=user_id,
            task_ids=task_ids,
        )

        return user_metadata

    def get_trace_by_id(
        self,
        trace_id: str,
        include_metrics: bool = False,
        compute_new_metrics: bool = False,
    ) -> Optional[TraceResponse]:
        """Get complete trace tree with existing metrics (no computation).

        Returns full trace structure with spans.
        """
        # Query all spans for this trace
        spans, _ = self.span_query_service.query_spans_from_db(trace_ids=[trace_id])

        if not spans:
            return None

        # Validate spans
        valid_spans = self.span_query_service.validate_spans(spans)

        # Add existing metrics if requested
        if include_metrics and valid_spans:
            valid_spans = self.metrics_integration_service.add_metrics_to_spans(
                valid_spans,
                compute_new_metrics,
            )

        # Fetch trace metadata for input/output content
        trace_metadata_list = self.span_query_service.get_trace_metadata_by_ids(
            [trace_id],
            PaginationSortMethod.DESCENDING,
        )
        # Convert to database models for tree building service
        trace_metadata_db = [tm._to_database_model() for tm in trace_metadata_list]

        # Build trace tree structure with trace metadata
        traces = self.tree_building_service.group_spans_into_traces(
            valid_spans,
            PaginationSortMethod.DESCENDING,
            trace_metadata=trace_metadata_db,
        )

        if not traces or traces[0] is None:
            return None

        # add annotation info to trace responses if it exists
        return self.trace_annotation_service.append_annotation_info_to_trace_response(
            traces[0],
        )

    def compute_trace_metrics(
        self,
        trace_id: str,
    ) -> Optional[TraceResponse]:
        """Compute all missing metrics for trace spans on-demand.

        Returns full trace tree with computed metrics.
        """
        return self.get_trace_by_id(
            trace_id=trace_id,
            include_metrics=True,
            compute_new_metrics=True,
        )

    def get_span_by_id(
        self,
        span_id: str,
        include_metrics: bool = False,
        compute_new_metrics: bool = False,
    ) -> Optional[Span]:
        """Get single span with existing metrics (no computation).

        Returns full span object with any existing metrics.
        """
        # Query the specific span directly from database
        span = self.span_query_service.query_span_by_id(span_id)

        if not span:
            return None

        # Validate span version
        if not validate_span_version(span.raw_data):
            logger.warning(f"Span {span_id} failed version validation")
            return None

        # Add existing metrics if requested
        if include_metrics:
            spans_with_metrics = self.metrics_integration_service.add_metrics_to_spans(
                [span],
                compute_new_metrics,
            )
            return spans_with_metrics[0] if spans_with_metrics else span

        return span

    def compute_span_metrics(
        self,
        span_id: str,
    ) -> Optional[Span]:
        """Compute missing span metrics on-demand.

        Returns span with computed metrics.
        """
        # Query the specific span directly from database
        span = self.span_query_service.query_span_by_id(span_id)

        if not span:
            return None

        # Validate span version
        if not validate_span_version(span.raw_data):
            raise ValueError(f"Span {span_id} failed version validation")

        # Validate that this is an LLM span (required for metrics computation)
        self.span_query_service.validate_span_for_metrics(span, span_id)

        # Compute metrics for this span
        spans_with_metrics = self.metrics_integration_service.add_metrics_to_spans(
            [span],
            compute_new_metrics=True,
        )
        return spans_with_metrics[0] if spans_with_metrics else None

    def get_sessions_metadata(
        self,
        task_ids: list[str],
        pagination_parameters: PaginationParameters,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        user_ids: Optional[list[str]] = None,
        include_experiment_sessions: Optional[bool] = False,
    ) -> tuple[int, list[SessionMetadata]]:
        """Return session aggregation data.

        Returns aggregated session information with pagination.
        """
        if not task_ids:
            raise ValueError("task_ids are required for session queries")

        # Get session aggregation data from query service
        count, session_metadata_list = self.span_query_service.get_sessions_aggregated(
            task_ids=task_ids,
            pagination_parameters=pagination_parameters,
            start_time=start_time,
            end_time=end_time,
            user_ids=user_ids,
            include_experiment_sessions=include_experiment_sessions,
        )

        return count, session_metadata_list

    def get_session_traces(
        self,
        session_id: str,
        pagination_parameters: PaginationParameters,
    ) -> tuple[int, list[TraceResponse]]:
        """Get all trace trees in a session.

        Returns list of full trace trees with existing metrics (no computation).
        """
        # Get trace IDs for this session
        count, trace_ids = self.span_query_service.get_trace_ids_for_session(
            session_id=session_id,
            pagination_parameters=pagination_parameters,
        )

        if not trace_ids:
            return 0, []

        # Query all spans for these traces
        spans, _ = self.span_query_service.query_spans_from_db(
            trace_ids=trace_ids,
            sort=pagination_parameters.sort or PaginationSortMethod.DESCENDING,
        )

        # Validate spans and add existing metrics
        valid_spans = self.span_query_service.validate_spans(spans)
        if valid_spans:
            valid_spans = self.metrics_integration_service.add_metrics_to_spans(
                valid_spans,
                compute_new_metrics=False,  # Only include existing metrics
            )

        # Build trace tree structures
        traces = self.tree_building_service.group_spans_into_traces(
            valid_spans,
            pagination_parameters.sort or PaginationSortMethod.DESCENDING,
        )

        # add annotation info to trace responses if it exists
        traces = (
            self.trace_annotation_service.append_annotation_info_to_trace_responses(
                traces,
            )
        )

        return count, traces

    def compute_session_metrics(
        self,
        session_id: str,
        pagination_parameters: PaginationParameters,
    ) -> tuple[int, list[TraceResponse]]:
        """Get all traces in a session and compute missing metrics.

        Returns list of full trace trees with computed metrics.
        """
        # Get trace IDs for this session
        count, trace_ids = self.span_query_service.get_trace_ids_for_session(
            session_id=session_id,
            pagination_parameters=pagination_parameters,
        )

        if not trace_ids:
            return 0, []

        # Query all spans for these traces
        spans, _ = self.span_query_service.query_spans_from_db(
            trace_ids=trace_ids,
            sort=pagination_parameters.sort or PaginationSortMethod.DESCENDING,
        )

        # Validate spans and compute metrics
        valid_spans = self.span_query_service.validate_spans(spans)
        if valid_spans:
            valid_spans = self.metrics_integration_service.add_metrics_to_spans(
                valid_spans,
                compute_new_metrics=True,  # Compute missing metrics
            )

        # Build trace tree structures
        traces = self.tree_building_service.group_spans_into_traces(
            valid_spans,
            pagination_parameters.sort or PaginationSortMethod.DESCENDING,
        )

        # add annotation info to trace responses if it exists
        traces = (
            self.trace_annotation_service.append_annotation_info_to_trace_responses(
                traces,
            )
        )

        return count, traces

    def get_users_metadata(
        self,
        task_ids: list[str],
        pagination_parameters: PaginationParameters,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> tuple[int, list[TraceUserMetadata]]:
        """Return user aggregation data with pagination."""
        if not task_ids:
            raise ValueError("task_ids are required for user queries")

        # Get user aggregation data from query service
        count, user_metadata_list = self.span_query_service.get_users_aggregated(
            task_ids=task_ids,
            pagination_parameters=pagination_parameters,
            start_time=start_time,
            end_time=end_time,
        )

        return count, user_metadata_list

    # ============================================================================
    # Public API Methods - Used by Legacy Endpoints (ML Engine)
    # ============================================================================
    # These methods maintain backward compatibility with existing endpoints
    # in span_routes.py. They combine data retrieval with metrics computation
    # for compatibility with the original API design.

    def create_traces(
        self,
        trace_data: bytes,
    ) -> Tuple[list[DatabaseSpan], tuple[int, int, int, list[str]]]:
        """Process trace data from protobuf format and store in database."""
        try:
            return self.trace_ingestion_service.process_trace_data(trace_data)
        except DecodeError as e:
            raise DecodeError("Failed to parse protobuf message.") from e

    def create_traces_from_gcp(
        self,
        gcp_trace_data: dict[str, Any],
        task_id: str | None = None,
    ) -> Tuple[list[DatabaseSpan], tuple[int, int, int, list[str]]]:
        """
        Process GCP Cloud Trace data and store in database.

        This method directly converts GCP spans to DatabaseSpan objects without
        going through protobuf conversion.

        Args:
            gcp_trace_data: Dict in GCP Cloud Trace format with structure:
                {
                    "projectId": str,
                    "traceId": str,
                    "spans": [
                        {
                            "spanId": str,
                            "name": str,
                            "startTime": str (ISO8601),
                            "endTime": str (ISO8601),
                            "parentSpanId": str (optional),
                            "labels": dict[str, str]
                        }
                    ]
                }
            task_id: Optional task ID to inject into all spans

        Returns:
            Tuple of (database_spans, (total_spans, accepted_spans, rejected_spans, rejection_reasons))

        Raises:
            ValueError: If GCP trace format is invalid
        """
        # Validate basic structure
        if "spans" not in gcp_trace_data:
            raise ValueError("Invalid GCP trace format: missing 'spans' field")

        trace_id = gcp_trace_data.get("traceId", "")
        gcp_spans = gcp_trace_data.get("spans", [])

        total_spans = len(gcp_spans)
        accepted_spans = 0
        rejected_spans = 0
        rejected_reasons = []
        database_spans = []

        for gcp_span in gcp_spans:
            try:
                # Extract basic span info
                span_id_decimal = gcp_span.get("spanId", "")
                parent_span_id_decimal = gcp_span.get("parentSpanId", "")
                name = gcp_span.get("name", "")
                labels = gcp_span.get("labels", {})

                # Convert IDs to hex format
                span_id_hex = self.gcp_conversion_service.decimal_span_id_to_hex(
                    span_id_decimal,
                )
                parent_span_id_hex = (
                    self.gcp_conversion_service.decimal_span_id_to_hex(
                        parent_span_id_decimal,
                    )
                    if parent_span_id_decimal
                    else None
                )

                # Convert timestamps
                start_time = self.gcp_conversion_service.iso_timestamp_to_datetime(
                    gcp_span.get("startTime", ""),
                )
                end_time = self.gcp_conversion_service.iso_timestamp_to_datetime(
                    gcp_span.get("endTime", ""),
                )

                # Convert GCP labels to OpenInference attributes
                attributes = (
                    self.gcp_conversion_service.convert_gcp_labels_to_openinference(
                        labels,
                    )
                )

                # Extract span kind from attributes
                # Use get_nested_value because convert_gcp_labels_to_openinference
                # explodes dotted keys into nested dicts, so flat .get() won't find them.
                span_kind = trace_utils.get_nested_value(
                    attributes,
                    SpanAttributes.OPENINFERENCE_SPAN_KIND,
                    default="LLM",
                )

                # Extract session_id and user_id if present
                session_id = trace_utils.get_nested_value(
                    attributes, SpanAttributes.SESSION_ID
                )
                user_id = None  # GCP doesn't typically have user_id in labels

                # Build raw_data dict (similar to what would come from OTLP)
                raw_data = {
                    "name": name,
                    "traceId": trace_id,
                    "spanId": span_id_hex,
                    "parentSpanId": parent_span_id_hex,
                    "startTimeUnixNano": int(start_time.timestamp() * 1_000_000_000),
                    "endTimeUnixNano": int(end_time.timestamp() * 1_000_000_000),
                    "attributes": attributes,
                    SPAN_VERSION_KEY: EXPECTED_SPAN_VERSION,
                }

                # Extract token/cost info from attributes
                token_data = trace_utils.extract_token_cost_from_span(
                    raw_data,
                    span_kind,
                )

                # Create DatabaseSpan object
                db_span = DatabaseSpan(
                    id=str(uuid.uuid4()),
                    trace_id=trace_id,
                    span_id=span_id_hex,
                    parent_span_id=parent_span_id_hex,
                    span_kind=span_kind,
                    span_name=name,
                    start_time=start_time,
                    end_time=end_time,
                    task_id=task_id,  # Use provided task_id
                    session_id=session_id,
                    user_id=user_id,
                    status_code="Unset",  # GCP doesn't provide status
                    raw_data=raw_data,
                    prompt_token_count=token_data.prompt_token_count,
                    completion_token_count=token_data.completion_token_count,
                    total_token_count=token_data.total_token_count,
                    prompt_token_cost=token_data.prompt_token_cost,
                    completion_token_cost=token_data.completion_token_cost,
                    total_token_cost=token_data.total_token_cost,
                )

                database_spans.append(db_span)
                accepted_spans += 1

            except Exception as e:
                rejected_spans += 1
                error_msg = f"Failed to process GCP span: {str(e)}"
                rejected_reasons.append(error_msg)
                logger.error(f"Error processing GCP span: {e}", exc_info=True)
                continue

        # Store spans using the ingestion service method
        if database_spans:
            self.trace_ingestion_service._store_spans(database_spans, commit=True)
            logger.debug(f"Stored {len(database_spans)} GCP spans successfully")

        return database_spans, (
            total_spans,
            accepted_spans,
            rejected_spans,
            rejected_reasons,
        )

    def convert_and_send_traces_from_external_provider(
        self,
        traces: list[dict[str, Any]],
        provider: RegisteredAgentProvider,
        task_id: str,
    ) -> None:
        """Convert and send traces from a provider to the database."""
        for trace in traces:
            if provider == RegisteredAgentProvider.GCP:
                self.create_traces_from_gcp(trace, task_id)
            else:
                raise ValueError(f"Unsupported provider '{provider}'")

    def query_spans(
        self,
        sort: PaginationSortMethod,
        page: int,
        page_size: int = DEFAULT_PAGE_SIZE,
        trace_ids: Optional[list[str]] = None,
        task_ids: Optional[list[str]] = None,
        span_types: Optional[list[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        include_metrics: bool = False,
        compute_new_metrics: bool = True,
        filters: Optional[TraceQueryRequest] = None,
    ) -> tuple[list[Span], int]:
        """Query spans with optional metrics computation.

        Uses comprehensive filtering if filters parameter provided, otherwise uses basic filtering.

        Returns:
            tuple[list[Span], int]: (spans, total_count) where total_count is all items matching filters
        """
        # Use comprehensive filtering if filters parameter provided
        if filters is not None:

            # Convert filters to internal schema format
            internal_filters = TraceQuerySchema._from_request_model(filters)

            if not internal_filters.task_ids:
                raise ValueError("task_ids are required for span queries")

            # Use comprehensive span-based filtering
            spans, total_count = (
                self.span_query_service.get_paginated_spans_with_filters(
                    filters=internal_filters,
                    pagination_parameters=PaginationParameters(
                        sort=sort,
                        page=page,
                        page_size=page_size,
                    ),
                )
            )

            if spans is None:
                spans, total_count = [], 0
        else:
            # Use basic filtering (legacy behavior) - create minimal filter from parameters
            if not task_ids:
                raise ValueError("task_ids are required for span queries")

            if include_metrics and compute_new_metrics and not task_ids:
                raise ValueError(
                    "task_ids are required when include_metrics=True and compute_new_metrics=True",
                )

            # Query spans directly with basic filtering
            spans, total_count = self.span_query_service.query_spans_from_db(
                trace_ids=trace_ids,
                task_ids=task_ids,
                span_types=span_types,
                start_time=start_time,
                end_time=end_time,
                sort=sort,
                page=page,
                page_size=page_size,
            )

        # Validate spans and add metrics if requested
        valid_spans = self.span_query_service.validate_spans(spans)
        if include_metrics and valid_spans:
            valid_spans = self.metrics_integration_service.add_metrics_to_spans(
                valid_spans,
                compute_new_metrics,
            )

        return valid_spans, total_count

    def query_span_by_span_id_with_metrics(self, span_id: str) -> Span:
        """Query a single span by span_id and compute metrics for it."""
        # Query the specific span directly from database
        span = self.span_query_service.query_span_by_id(span_id)

        if not span:
            raise ValueError(f"Span with ID {span_id} not found")

        # Validate span version
        if not validate_span_version(span.raw_data):
            raise ValueError(f"Span {span_id} failed version validation")

        # Validate that this is an LLM span
        self.span_query_service.validate_span_for_metrics(span, span_id)

        # Compute metrics for this span
        spans_with_metrics = self.metrics_integration_service.add_metrics_to_spans(
            [span],
        )
        return spans_with_metrics[0]  # Return the single span

    def query_traces_with_filters(
        self,
        filters: TraceQueryRequest,
        pagination_parameters: PaginationParameters,
        include_metrics: bool = False,
        compute_new_metrics: bool = True,
        sort_by: str = "start_time",
    ) -> tuple[int, list[TraceResponse]]:
        """Query traces with comprehensive filtering and optional metrics computation."""
        # Validate parameters

        internal_filters: TraceQuerySchema = TraceQuerySchema._from_request_model(
            filters,
        )

        if not filters.task_ids:
            raise ValueError("task_ids are required for trace queries")

        # Trace-level pagination: get paginated trace IDs using optimized two-phase filtering
        result = self.span_query_service.get_paginated_trace_ids_with_filters(
            filters=internal_filters,
            pagination_parameters=pagination_parameters,
            sort_by=sort_by,
        )

        if not result:
            return 0, []

        paginated_trace_ids, total_count = result

        # Query all spans in the paginated traces
        spans, _ = self.span_query_service.query_spans_from_db(
            trace_ids=paginated_trace_ids,
            sort=pagination_parameters.sort or PaginationSortMethod.DESCENDING,
        )

        # Validate spans and add metrics if requested
        valid_spans = self.span_query_service.validate_spans(spans)
        if include_metrics and valid_spans:
            valid_spans = self.metrics_integration_service.add_metrics_to_spans(
                valid_spans,
                compute_new_metrics,
            )

        # Group spans by trace and build nested structure
        traces = self.tree_building_service.group_spans_into_traces(
            valid_spans,
            pagination_parameters.sort or PaginationSortMethod.DESCENDING,
        )

        # add annotation info to trace responses if it exists
        traces = (
            self.trace_annotation_service.append_annotation_info_to_trace_responses(
                traces,
            )
        )

        return total_count, traces

    def annotate_trace(
        self,
        trace_id: str,
        annotation_request: AgenticAnnotationRequest,
    ) -> AgenticAnnotation:
        """Annotate a trace with a score and description (1 = liked, 0 = disliked)."""
        return self.trace_annotation_service.annotate_trace(
            trace_id=trace_id,
            annotation_request=annotation_request,
        )

    def get_annotation_by_id(
        self,
        annotation_id: UUID,
    ) -> AgenticAnnotation | None:
        """Get an annotation by id."""
        return self.trace_annotation_service.get_annotation_by_id(
            annotation_id=annotation_id,
        )

    def list_annotations_for_trace(
        self,
        trace_id: str,
        pagination_parameters: PaginationParameters,
        filter_request: AgenticAnnotationListFilterRequest,
    ) -> List[AgenticAnnotation]:
        """List annotations for a trace."""
        return self.trace_annotation_service.list_annotations_for_trace(
            trace_id=trace_id,
            pagination_parameters=pagination_parameters,
            filter_request=filter_request,
        )

    def delete_annotation_from_trace(self, trace_id: str) -> None:
        """Delete an annotation from a trace."""
        self.trace_annotation_service.delete_annotation_by_trace_id(
            trace_id=trace_id,
        )

    def get_unregistered_root_spans_grouped(
        self,
        pagination_parameters: PaginationParameters | None = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Get grouped root spans for traces without task_id.

        Args:
            pagination_parameters: Optional pagination parameters for limiting results
            start_time: Optional start time filter (inclusive). If not provided, defaults to 7 days ago.
            end_time: Optional end time filter (exclusive). If not provided, defaults to now.

        Returns:
            tuple[list[dict], int]: (groups, total_count) where groups contains
                dicts with span_name and count (paginated), and total_count is the total number
                of root spans across ALL groups (before pagination)
        """
        results, total_count = (
            self.span_query_service.get_unregistered_root_spans_grouped(
                pagination_parameters=pagination_parameters,
                start_time=start_time,
                end_time=end_time,
            )
        )

        groups = [
            {
                "span_name": span_name,
                "count": count,
            }
            for span_name, count in results
        ]

        return groups, total_count

    # ============================================================================
    # Testing/Utility Methods
    # ============================================================================

    def _store_spans(self, spans: list[dict[str, Any]], commit: bool = True) -> None:
        """Store spans in the database with optional commit control.

        This method is primarily used for testing and direct span insertion.
        For normal operation, use create_traces() instead.
        """
        if not spans:
            return

        stmt = insert(DatabaseSpan).values(spans)
        self.db_session.execute(stmt)

        if commit:
            self.db_session.commit()

        logger.debug(f"Stored {len(spans)} spans (commit={commit})")
