import logging
from datetime import datetime
from typing import Optional, Tuple

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import PaginationSortMethod
from arthur_common.models.request_schemas import TraceQueryRequest
from google.protobuf.message import DecodeError
from opentelemetry import trace
from sqlalchemy.orm import Session

from repositories.metrics_repository import MetricRepository
from repositories.tasks_metrics_repository import TasksMetricsRepository
from schemas.internal_schemas import (
    SessionMetadata,
    Span,
    TraceMetadata,
    TraceQuerySchema,
    TraceUserMetadata,
)
from services.trace.metrics_integration_service import MetricsIntegrationService
from services.trace.span_query_service import SpanQueryService
from services.trace.trace_ingestion_service import TraceIngestionService
from services.trace.tree_building_service import TreeBuildingService
from utils import trace as trace_utils

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
        self.trace_ingestion_service = TraceIngestionService(db_session)
        self.span_query_service = SpanQueryService(db_session)
        self.metrics_integration_service = MetricsIntegrationService(
            db_session,
            tasks_metrics_repo,
            metrics_repo,
        )
        self.tree_building_service = TreeBuildingService()

    # ============================================================================
    # Public API Methods - Used by Optimized Trace Endpoints
    # ============================================================================

    def get_traces_metadata(
        self,
        filters: TraceQueryRequest,
        pagination_parameters: PaginationParameters,
    ) -> tuple[int, list[TraceMetadata]]:
        """Get lightweight trace metadata for browsing/filtering operations.

        Returns metadata only without spans or metrics for fast performance.
        """
        # Convert to internal schema format
        filters = TraceQuerySchema._from_request_model(filters)

        if not filters.task_ids:
            raise ValueError("task_ids are required for trace queries")

        # Get trace metadata without loading spans
        paginated_trace_ids, total_count = (
            self.span_query_service.get_paginated_trace_ids_with_filters(
                filters=filters,
                pagination_parameters=pagination_parameters,
            )
        )

        if total_count == 0:
            return 0, []

        # Get trace metadata objects directly
        trace_metadata_list = self.span_query_service.get_trace_metadata_by_ids(
            trace_ids=paginated_trace_ids,
            sort_method=pagination_parameters.sort,
        )

        return total_count, trace_metadata_list

    def get_trace_by_id(
        self,
        trace_id: str,
        include_metrics: bool = False,
        compute_new_metrics: bool = False,
    ):
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

        # Build trace tree structure
        traces = self.tree_building_service.group_spans_into_traces(
            valid_spans,
            PaginationSortMethod.DESCENDING,
        )

        return traces[0] if traces else None

    def compute_trace_metrics(
        self,
        trace_id: str,
    ):
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
        if not trace_utils.validate_span_version(span.raw_data):
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
        if not trace_utils.validate_span_version(span.raw_data):
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
        )

        return count, session_metadata_list

    def get_session_traces(
        self,
        session_id: str,
        pagination_parameters: PaginationParameters,
    ) -> tuple[int, list]:
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
            sort=pagination_parameters.sort,
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
            pagination_parameters.sort,
        )

        return count, traces

    def compute_session_metrics(
        self,
        session_id: str,
        pagination_parameters: PaginationParameters,
    ) -> tuple[int, list]:
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
            sort=pagination_parameters.sort,
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
            pagination_parameters.sort,
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

    def get_user_sessions(
        self,
        user_id: str,
        pagination_parameters: PaginationParameters,
    ) -> tuple[int, list[SessionMetadata]]:
        """Get sessions for a specific user."""
        # Get session data for user from query service
        count, session_metadata_list = self.span_query_service.get_sessions_for_user(
            user_id=user_id,
            pagination_parameters=pagination_parameters,
        )

        return count, session_metadata_list

    def get_user_traces(
        self,
        user_id: str,
        pagination_parameters: PaginationParameters,
    ) -> tuple[int, list[TraceMetadata]]:
        """Get traces for a specific user."""
        # Get trace data for user from query service
        count, trace_metadata_list = self.span_query_service.get_traces_for_user(
            user_id=user_id,
            pagination_parameters=pagination_parameters,
        )

        return count, trace_metadata_list

    # ============================================================================
    # Public API Methods - Used by Legacy Endpoints (ML Engine)
    # ============================================================================
    # These methods maintain backward compatibility with existing endpoints
    # in span_routes.py. They combine data retrieval with metrics computation
    # for compatibility with the original API design.

    def create_traces(self, trace_data: bytes) -> Tuple[int, int, int, list[str]]:
        """Process trace data from protobuf format and store in database."""
        try:
            return self.trace_ingestion_service.process_trace_data(trace_data)
        except DecodeError as e:
            raise DecodeError("Failed to parse protobuf message.") from e

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
        if not trace_utils.validate_span_version(span.raw_data):
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
    ) -> tuple[int, list]:
        """Query traces with comprehensive filtering and optional metrics computation."""
        # Validate parameters

        filters = TraceQuerySchema._from_request_model(filters)

        if not filters.task_ids:
            raise ValueError("task_ids are required for trace queries")

        # Trace-level pagination: get paginated trace IDs using optimized two-phase filtering
        result = self.span_query_service.get_paginated_trace_ids_with_filters(
            filters=filters,
            pagination_parameters=pagination_parameters,
        )

        if not result:
            return 0, []

        paginated_trace_ids, total_count = result

        # Query all spans in the paginated traces
        spans, _ = self.span_query_service.query_spans_from_db(
            trace_ids=paginated_trace_ids,
            sort=pagination_parameters.sort,
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
            pagination_parameters.sort,
        )
        return total_count, traces

    # ============================================================================
    # Testing/Utility Methods
    # ============================================================================

    def _store_spans(self, spans: list[dict], commit: bool = True):
        """Store spans in the database with optional commit control.

        This method is primarily used for testing and direct span insertion.
        For normal operation, use create_traces() instead.
        """
        from sqlalchemy import insert

        from db_models import DatabaseSpan

        if not spans:
            return

        stmt = insert(DatabaseSpan).values(spans)
        self.db_session.execute(stmt)

        if commit:
            self.db_session.commit()

        logger.debug(f"Stored {len(spans)} spans (commit={commit})")
