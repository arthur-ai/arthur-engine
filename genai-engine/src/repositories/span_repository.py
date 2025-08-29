import logging
from datetime import datetime
from typing import Optional, Tuple

from google.protobuf.message import DecodeError
from opentelemetry import trace
from sqlalchemy.orm import Session

from repositories.metrics_repository import MetricRepository
from repositories.tasks_metrics_repository import TasksMetricsRepository
from arthur_common.models.enums import PaginationSortMethod
from schemas.internal_schemas import Span
from services.metrics_integration_service import MetricsIntegrationService
from services.span_query_service import SpanQueryService
from services.trace_ingestion_service import TraceIngestionService
from services.tree_building_service import TreeBuildingService
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
    # Public API Methods
    # ============================================================================

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
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        include_metrics: bool = False,
        compute_new_metrics: bool = True,
    ) -> list[Span]:
        """Query spans with optional metrics computation."""
        # Validate parameters
        if not task_ids:
            raise ValueError("task_ids are required for span queries")

        if include_metrics and compute_new_metrics and not task_ids:
            raise ValueError(
                "task_ids are required when include_metrics=True and compute_new_metrics=True",
            )

        # Get paginated trace IDs directly from database with proper ordering
        trace_ids = self.span_query_service.get_paginated_trace_ids_for_task_ids(
            task_ids=task_ids,
            trace_ids=trace_ids,
            start_time=start_time,
            end_time=end_time,
            sort=sort,
            page=page,
            page_size=page_size,
        )

        if not trace_ids:
            return []

        # Query spans from database
        spans = self.span_query_service.query_spans_from_db(
            trace_ids=trace_ids,
            start_time=start_time,
            end_time=end_time,
            sort=sort,
        )

        # Validate spans and add metrics if requested
        valid_spans = self.span_query_service.validate_spans(spans)
        if include_metrics and valid_spans:
            valid_spans = self.metrics_integration_service.add_metrics_to_spans(
                valid_spans,
                compute_new_metrics,
            )

        return valid_spans

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

    def query_spans_as_traces(
        self,
        sort: PaginationSortMethod,
        page: int,
        page_size: int = DEFAULT_PAGE_SIZE,
        trace_ids: Optional[list[str]] = None,
        task_ids: Optional[list[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        include_metrics: bool = False,
        compute_new_metrics: bool = True,
    ) -> tuple[int, list]:
        """Query spans grouped by traces with nested structure."""
        # Get spans using existing logic
        spans = self.query_spans(
            sort=sort,
            page=page,
            page_size=page_size,
            trace_ids=trace_ids,
            task_ids=task_ids,
            start_time=start_time,
            end_time=end_time,
            include_metrics=include_metrics,
            compute_new_metrics=compute_new_metrics,
        )

        # Group spans by trace and build nested structure
        traces = self.tree_building_service.group_spans_into_traces(spans, sort)
        return len(traces), traces

    def query_spans_with_metrics_as_traces(
        self,
        sort: PaginationSortMethod,
        page: int,
        page_size: int = DEFAULT_PAGE_SIZE,
        trace_ids: Optional[list[str]] = None,
        task_ids: Optional[list[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> tuple[int, list]:
        """Query spans with metrics grouped by traces with nested structure."""
        return self.query_spans_as_traces(
            sort=sort,
            page=page,
            page_size=page_size,
            trace_ids=trace_ids,
            task_ids=task_ids,
            start_time=start_time,
            end_time=end_time,
            include_metrics=True,
            compute_new_metrics=True,
        )

    # ============================================================================
    # Testing/Utility Methods
    # ============================================================================

    def _store_spans(self, spans: list[dict], commit: bool = True):
        """Store spans in the database with optional commit control.

        This method is primarily used for testing and direct span insertion.
        For normal operation, use create_traces() instead.
        """
        from sqlalchemy import insert

        from db_models.db_models import DatabaseSpan

        if not spans:
            return

        stmt = insert(DatabaseSpan).values(spans)
        self.db_session.execute(stmt)

        if commit:
            self.db_session.commit()

        logger.debug(f"Stored {len(spans)} spans (commit={commit})")
