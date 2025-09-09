import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import and_, asc, desc, exists, func, select
from sqlalchemy.orm import Session

from db_models.db_models import DatabaseMetricResult, DatabaseSpan
from schemas.common_schemas import PaginationParameters
from schemas.enums import MetricType, PaginationSortMethod, ToolClassEnum
from schemas.internal_schemas import (
    ComparisonOperators,
    FloatRangeFilter,
    Span,
    TraceQuerySchema,
)
from utils import trace as trace_utils
from utils.constants import SPAN_KIND_LLM

logger = logging.getLogger(__name__)

# Constants
DEFAULT_PAGE_SIZE = 5


class SpanQueryService:
    """Service responsible for querying spans from the database."""

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def get_paginated_trace_ids_with_filters(
        self,
        filters: TraceQuerySchema,
        pagination_parameters: PaginationParameters,
    ) -> Optional[list[str]]:
        """
        Main entry point for trace filtering with comprehensive filter support.

        Uses two-phase strategy: fast trace-level filters first, then expensive
        span-level filters only if needed. Results are paginated and sorted.
        """

        if not filters.task_ids:
            return None

        # Build unified query with modular filtering
        query = self._build_trace_ids_query(filters, pagination_parameters.sort)

        # Apply pagination
        offset = pagination_parameters.page * pagination_parameters.page_size
        query = query.offset(offset).limit(pagination_parameters.page_size)

        # Execute query
        results = self.db_session.execute(query).scalars().all()
        trace_ids_result = list(results)

        logger.debug(
            f"Found {len(trace_ids_result)} trace IDs for task IDs: {filters.task_ids} "
            f"(page={pagination_parameters.page}, page_size={pagination_parameters.page_size}, sort={pagination_parameters.sort})",
        )

        return trace_ids_result if trace_ids_result else None

    def query_spans_from_db(
        self,
        trace_ids: Optional[list[str]] = None,
        task_ids: Optional[list[str]] = None,
        span_types: Optional[list[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        sort: PaginationSortMethod = PaginationSortMethod.DESCENDING,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> list[Span]:
        """
        Query individual spans (not traces) with basic filtering and pagination.

        Unlike trace filtering, this applies filters directly to spans and returns
        span objects, not trace IDs. Used for span-level queries and metrics.
        """
        query = self._build_spans_query(
            trace_ids=trace_ids,
            task_ids=task_ids,
            span_types=span_types,
            start_time=start_time,
            end_time=end_time,
            sort=sort,
        )

        # Apply pagination if provided
        if page is not None and page_size is not None:
            offset = page * page_size
            query = query.offset(offset).limit(page_size)

        results = self.db_session.execute(query).scalars().unique().all()
        return [Span._from_database_model(span) for span in results]

    def query_span_by_id(self, span_id: str) -> Optional[Span]:
        """Query a single span by span_id."""
        query = select(DatabaseSpan).where(DatabaseSpan.span_id == span_id)
        results = self.db_session.execute(query).scalars().unique().all()

        if not results:
            return None

        return Span._from_database_model(results[0])

    def validate_spans(self, spans: list[Span]) -> list[Span]:
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

    def validate_span_for_metrics(self, span: Span, span_id: str):
        """Validate that a span can have metrics computed for it."""
        if span.span_kind != SPAN_KIND_LLM:
            raise ValueError(
                f"Span {span_id} is not an LLM span (span_kind: {span.span_kind})",
            )

        if not span.task_id:
            raise ValueError(f"Span {span_id} has no task_id")

    def _build_trace_ids_query(
        self,
        filters: TraceQuerySchema,
        sort: PaginationSortMethod,
    ) -> select:
        """
        Orchestrates two-phase filtering: fast trace-level filters, then expensive span-level filters.

        Phase 1: Apply trace filters (task_ids, time, duration) - fast indexed operations
        Phase 2: Apply span filters (tool_name, metrics) - expensive, only if needed
        Then intersect results while preserving trace query structure and ordering.
        """

        # Phase 1: Apply trace-level filters to get candidate traces (fast)
        candidate_traces_query = self._build_trace_level_filters(filters, sort)

        # Phase 2: If span-level filters exist, intersect with spans matching criteria (slower)
        if self._has_span_level_filters(filters):
            qualifying_traces_query = self._build_span_level_filters(filters)
            return self._intersect_trace_queries(
                candidate_traces_query,
                qualifying_traces_query,
                sort,
            )

        return candidate_traces_query

    def _build_trace_level_filters(
        self,
        filters: TraceQuerySchema,
        sort: PaginationSortMethod,
    ) -> select:
        """
        Apply trace-level filters: task_ids, trace_ids, time range, duration.

        These operate on trace boundaries (not individual spans) using indexed
        columns for fast filtering. Always calculates timing info for sorting.
        """

        # Basic trace filters (very fast)
        conditions = [DatabaseSpan.task_id.in_(filters.task_ids)]
        if filters.trace_ids:
            conditions.append(DatabaseSpan.trace_id.in_(filters.trace_ids))
        if filters.start_time:
            conditions.append(DatabaseSpan.start_time >= filters.start_time)
        if filters.end_time:
            conditions.append(DatabaseSpan.start_time <= filters.end_time)

        # Use unified trace timing subquery (always calculate timing info, apply duration filters if needed)
        return self._build_unified_trace_query(
            conditions,
            filters.trace_duration_filters,
            sort,
        )

    def _build_unified_trace_query(
        self,
        base_conditions: list,
        duration_filters: Optional[list[FloatRangeFilter]],
        sort: PaginationSortMethod,
    ) -> select:
        """
        Groups spans by trace_id to calculate trace timing (start, end, duration).

        Aggregates span timestamps to compute trace boundaries, applies optional
        duration filters, and maintains sort order for pagination.
        """

        # Create subquery that always calculates trace timing information
        trace_timing_subquery = (
            select(
                DatabaseSpan.trace_id,
                func.min(DatabaseSpan.start_time).label("trace_start"),
                func.max(DatabaseSpan.end_time).label("trace_end"),
                (
                    func.max(DatabaseSpan.end_time) - func.min(DatabaseSpan.start_time)
                ).label("trace_duration"),
            )
            .where(and_(*base_conditions))
            .group_by(DatabaseSpan.trace_id)
            .subquery()
        )

        # Start with base query
        query = select(trace_timing_subquery.c.trace_id)

        # Apply duration filters if they exist
        if duration_filters:
            duration_conditions = []
            for filter_item in duration_filters:
                duration_conditions.append(
                    self._build_comparison_condition(
                        trace_timing_subquery.c.trace_duration,
                        filter_item,
                    ),
                )
            query = query.where(and_(*duration_conditions))

        # Apply ordering based on trace start time
        if sort == PaginationSortMethod.DESCENDING:
            query = query.order_by(desc(trace_timing_subquery.c.trace_start))
        elif sort == PaginationSortMethod.ASCENDING:
            query = query.order_by(asc(trace_timing_subquery.c.trace_start))

        return query

    def _build_comparison_condition(self, column, filter_item: FloatRangeFilter):
        """Build comparison condition (column OP value) from FloatRangeFilter."""
        if filter_item.operator == ComparisonOperators.EQUALS:
            return column == filter_item.value
        elif filter_item.operator == ComparisonOperators.GREATER_THAN:
            return column > filter_item.value
        elif filter_item.operator == ComparisonOperators.GREATER_THAN_OR_EQUAL:
            return column >= filter_item.value
        elif filter_item.operator == ComparisonOperators.LESS_THAN:
            return column < filter_item.value
        elif filter_item.operator == ComparisonOperators.LESS_THAN_OR_EQUAL:
            return column <= filter_item.value
        else:
            raise ValueError(f"Unsupported operator: {filter_item.operator}")

    # ============================================================================
    # Span-Level Filtering
    # ============================================================================

    def _build_span_level_filters(self, filters: TraceQuerySchema) -> select:
        """
        Find traces containing spans matching ALL span-level criteria using EXISTS clauses.

        Handles two span types separately:
        - tool_name: Finds TOOL spans with specific names (JSON queries)
        - metrics: Finds LLM spans with metric scores (table joins)
        Uses EXISTS for each filter, then ANDs them together.
        """

        # Start with base query for traces with the required task_ids
        base_query = select(DatabaseSpan.trace_id.distinct()).where(
            DatabaseSpan.task_id.in_(filters.task_ids),
        )

        exists_conditions = []

        # Add EXISTS condition for tool name filtering
        if filters.tool_name:
            # Alias for inner query to avoid conflicts
            inner_span = DatabaseSpan.__table__.alias("inner_span")
            exists_conditions.append(
                exists(
                    select(1)
                    .select_from(inner_span)
                    .where(
                        and_(
                            inner_span.c.trace_id
                            == DatabaseSpan.trace_id,  # Proper correlation
                            inner_span.c.task_id.in_(filters.task_ids),
                            inner_span.c.span_kind == "TOOL",
                            inner_span.c.raw_data["name"].astext == filters.tool_name,
                        ),
                    ),
                ),
            )

        # Add EXISTS conditions for metric-based filtering
        exists_conditions.extend(self._build_metric_exists_conditions(filters))

        # Apply all EXISTS conditions to the base query
        if exists_conditions:
            base_query = base_query.where(and_(*exists_conditions))

        return base_query

    def _build_metric_exists_conditions(self, filters: TraceQuerySchema) -> list:
        exists_conditions = []

        # Query relevance filtering
        if filters.query_relevance_filters:
            exists_conditions.append(
                self._build_relevance_exists(
                    MetricType.QUERY_RELEVANCE,
                    filters.query_relevance_filters,
                    filters.task_ids,
                ),
            )

        # Response relevance filtering
        if filters.response_relevance_filters:
            exists_conditions.append(
                self._build_relevance_exists(
                    MetricType.RESPONSE_RELEVANCE,
                    filters.response_relevance_filters,
                    filters.task_ids,
                ),
            )

        # Tool selection filtering
        if filters.tool_selection:
            exists_conditions.append(
                self._build_tool_classification_exists(
                    MetricType.TOOL_SELECTION,
                    filters.tool_selection,
                    filters.task_ids,
                    "tool_selection",
                ),
            )

        # Tool usage filtering
        if filters.tool_usage:
            exists_conditions.append(
                self._build_tool_classification_exists(
                    MetricType.TOOL_SELECTION,
                    filters.tool_usage,
                    filters.task_ids,
                    "tool_usage",
                ),
            )

        return exists_conditions

    def _build_relevance_exists(
        self,
        metric_type: MetricType,
        relevance_filters: list[FloatRangeFilter],
        task_ids: list[str],
    ):

        # Create aliases to avoid conflicts
        inner_span = DatabaseSpan.__table__.alias("inner_span")
        inner_metric = DatabaseMetricResult.__table__.alias("inner_metric")

        # Build relevance conditions
        relevance_conditions = []
        for filter_item in relevance_filters:
            if metric_type == MetricType.QUERY_RELEVANCE:
                score_path = inner_metric.c.details["query_relevance"][
                    "llm_relevance_score"
                ].astext
            elif metric_type == MetricType.RESPONSE_RELEVANCE:
                score_path = inner_metric.c.details["response_relevance"][
                    "llm_relevance_score"
                ].astext
            else:
                raise ValueError(f"Unsupported relevance metric type: {metric_type}")

            score_condition = self._build_comparison_condition(
                func.cast(score_path, func.Float()),
                filter_item,
            )
            relevance_conditions.append(score_condition)

        return exists(
            select(1)
            .select_from(
                inner_span.join(
                    inner_metric,
                    inner_span.c.id == inner_metric.c.span_id,
                ),
            )
            .where(
                and_(
                    inner_span.c.trace_id == DatabaseSpan.trace_id,  # Correlation
                    inner_span.c.task_id.in_(task_ids),
                    inner_span.c.span_kind == SPAN_KIND_LLM,
                    inner_metric.c.metric_type == metric_type.value,
                    *relevance_conditions,
                ),
            ),
        )

    def _build_tool_classification_exists(
        self,
        metric_type: MetricType,
        tool_class: ToolClassEnum,
        task_ids: list[str],
        field_name: str,
    ):

        # Create aliases to avoid conflicts
        inner_span = DatabaseSpan.__table__.alias("inner_span")
        inner_metric = DatabaseMetricResult.__table__.alias("inner_metric")

        # Tool classification path
        classification_condition = (
            func.cast(
                inner_metric.c.details["tool_selection"][field_name].astext,
                func.Integer(),
            )
            == tool_class.value
        )

        return exists(
            select(1)
            .select_from(
                inner_span.join(
                    inner_metric,
                    inner_span.c.id == inner_metric.c.span_id,
                ),
            )
            .where(
                and_(
                    inner_span.c.trace_id == DatabaseSpan.trace_id,  # Correlation
                    inner_span.c.task_id.in_(task_ids),
                    inner_span.c.span_kind == SPAN_KIND_LLM,
                    inner_metric.c.metric_type == metric_type.value,
                    classification_condition,
                ),
            ),
        )

    def _intersect_trace_queries(
        self,
        trace_query: select,
        span_query: select,
        sort: PaginationSortMethod,
    ) -> select:
        """
        Combine trace-level and span-level results using IN clause.

        Finds traces that appear in BOTH result sets while preserving
        trace_query structure (timing calculations and ordering).
        """

        # Extract the trace_id column from the trace_query (first selected column)
        trace_id_column = trace_query.selected_columns[0]

        # Find intersection: traces that appear in BOTH query results
        # Keep the trace_query structure (timing calculations, ordering) but restrict to overlapping IDs
        intersected_query = trace_query.where(trace_id_column.in_(span_query))

        logger.debug(
            f"Intersecting trace-level and span-level query results to find overlapping trace IDs",
        )

        return intersected_query

    def _build_spans_query(
        self,
        trace_ids: Optional[list[str]] = None,
        task_ids: Optional[list[str]] = None,
        span_types: Optional[list[str]] = None,
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
        if task_ids:
            conditions.append(DatabaseSpan.task_id.in_(task_ids))
        if span_types:
            conditions.append(DatabaseSpan.span_kind.in_(span_types))
        if start_time:
            conditions.append(DatabaseSpan.start_time >= start_time)
        if end_time:
            conditions.append(DatabaseSpan.start_time <= end_time)

        # Apply filters if any conditions exist
        if conditions:
            query = query.where(and_(*conditions))

        # Apply sorting
        if sort == PaginationSortMethod.DESCENDING:
            query = query.order_by(desc(DatabaseSpan.start_time))
        elif sort == PaginationSortMethod.ASCENDING:
            query = query.order_by(asc(DatabaseSpan.start_time))

        return query

    def _has_span_level_filters(self, filters: TraceQuerySchema) -> bool:
        return bool(
            filters.tool_name
            or filters.query_relevance_filters
            or filters.response_relevance_filters
            or filters.tool_selection
            or filters.tool_usage,
        )
