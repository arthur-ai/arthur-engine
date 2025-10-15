"""
SpanQueryService with optimized query strategies.
"""

import logging
from datetime import datetime
from typing import List, Optional, Tuple

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import (
    ComparisonOperatorEnum,
    MetricType,
    PaginationSortMethod,
    ToolClassEnum,
)
from sqlalchemy import and_, asc, cast, desc, exists, func, select
from sqlalchemy.orm import Session
from sqlalchemy.types import Float, Integer, Numeric

from db_models import (
    DatabaseMetricResult,
    DatabaseSpan,
    DatabaseTraceMetadata,
)
from schemas.internal_schemas import (
    FloatRangeFilter,
    SessionMetadata,
    Span,
    TraceMetadata,
    TraceQuerySchema,
)
from utils import trace as trace_utils
from utils.constants import SPAN_KIND_LLM, SPAN_KIND_TOOL

logger = logging.getLogger(__name__)

# Constants
DEFAULT_PAGE_SIZE = 5


class SpanQueryService:
    """
    SpanQueryService with single-query strategy. This implements the proposed optimizations for comparison.
    """

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def get_paginated_trace_ids_with_filters(
        self,
        filters: TraceQuerySchema,
        pagination_parameters: PaginationParameters,
    ) -> Optional[Tuple[List[str], int]]:
        """
        Single-query strategy that combines all filters and uses database pagination.
        Returns tuple of (trace_ids, total_count).
        """
        if not filters.task_ids:
            return None, 0

        # Build comprehensive query with all filters combined
        base_query = self._build_unified_trace_query(filters)

        # Get total count before pagination
        count_query = select(func.count()).select_from(base_query.subquery())
        total_count = self.db_session.execute(count_query).scalar()

        # Apply sorting and pagination at database level
        query = self._apply_sorting_and_pagination(base_query, pagination_parameters)

        # Execute with database-level pagination
        results = self.db_session.execute(query).scalars().all()
        trace_ids = [tm.trace_id for tm in results]

        return trace_ids, total_count

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
    ) -> tuple[list[Span], int]:
        """Query individual spans with basic filtering and pagination.

        Returns:
            tuple[list[Span], int]: (spans, total_count) where total_count is all items matching filters
        """
        base_query = self._build_spans_query(
            trace_ids=trace_ids,
            task_ids=task_ids,
            span_types=span_types,
            start_time=start_time,
            end_time=end_time,
            sort=sort,
        )

        # Always get total count before pagination
        count_query = select(func.count()).select_from(base_query.subquery())
        total_count = self.db_session.execute(count_query).scalar()

        # Apply pagination if provided
        query = base_query
        if page is not None and page_size is not None:
            offset = page * page_size
            query = query.offset(offset).limit(page_size)

        results = self.db_session.execute(query).scalars().unique().all()
        spans = [Span._from_database_model(span) for span in results]

        return spans, total_count

    def query_span_by_id(self, span_id: str) -> Optional[Span]:
        """Query a single span by span_id."""
        query = select(DatabaseSpan).where(DatabaseSpan.span_id == span_id)
        results = self.db_session.execute(query).scalars().unique().all()

        if not results:
            return None

        return Span._from_database_model(results[0])

    def validate_spans(self, spans: list[Span]) -> list[Span]:
        """Validate spans and return only valid ones."""
        valid_spans = [
            span for span in spans if trace_utils.validate_span_version(span.raw_data)
        ]
        invalid_count = len(spans) - len(valid_spans)
        if invalid_count > 0:
            logger.warning(
                f"Skipped {invalid_count} spans due to version validation failure",
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

    def _build_unified_trace_query(self, filters: TraceQuerySchema) -> select:
        """
        Build a single query that combines all filtering logic using JOINs.
        This replaces the current two-phase approach.
        """
        # Start with base metadata query
        query = select(DatabaseTraceMetadata).where(
            DatabaseTraceMetadata.task_id.in_(filters.task_ids),
        )

        # Apply trace-level filters (fast indexed operations)
        query = self._apply_trace_level_filters(query, filters)

        # Apply span-level filters using JOINs instead of EXISTS
        if self._has_span_level_filters(filters):
            query = self._apply_span_level_filters_with_joins(query, filters)

        return query

    def _apply_trace_level_filters(
        self,
        query: select,
        filters: TraceQuerySchema,
    ) -> select:
        """Apply fast indexed trace-level filters."""
        conditions = []

        # Direct trace metadata filters
        if filters.trace_ids:
            conditions.append(DatabaseTraceMetadata.trace_id.in_(filters.trace_ids))
        if filters.start_time:
            conditions.append(DatabaseTraceMetadata.start_time >= filters.start_time)
        if filters.end_time:
            conditions.append(DatabaseTraceMetadata.end_time <= filters.end_time)

        # Duration filters with optimized calculation
        if filters.trace_duration_filters:
            duration_conditions = []
            for filter_item in filters.trace_duration_filters:
                #  duration calculation
                start_epoch = func.extract("epoch", DatabaseTraceMetadata.start_time)
                end_epoch = func.extract("epoch", DatabaseTraceMetadata.end_time)
                duration_seconds = func.round(cast(end_epoch - start_epoch, Numeric), 3)

                duration_conditions.append(
                    self._build_comparison_condition(duration_seconds, filter_item),
                )
            conditions.extend(duration_conditions)

        if conditions:
            query = query.where(and_(*conditions))

        return query

    def _apply_span_level_filters_with_joins(
        self,
        query: select,
        filters: TraceQuerySchema,
    ) -> select:
        """
        Apply span-level filters using JOINs for simple filters and EXISTS for metric filters.
        """

        span_conditions = []

        # Build JOINs for simple span filters
        if filters.tool_name or filters.span_types:
            query = query.join(
                DatabaseSpan,
                and_(
                    DatabaseTraceMetadata.trace_id == DatabaseSpan.trace_id,
                    DatabaseSpan.task_id.in_(filters.task_ids),
                ),
            )

            # Tool name filter
            if filters.tool_name:
                span_conditions.extend(
                    [
                        DatabaseSpan.span_kind == SPAN_KIND_TOOL,
                        DatabaseSpan.span_name == filters.tool_name,
                    ],
                )

            # Span types filter
            if filters.span_types:
                span_conditions.append(DatabaseSpan.span_kind.in_(filters.span_types))

            # Apply span conditions
            if span_conditions:
                query = query.where(and_(*span_conditions))

            # Use DISTINCT to avoid duplicate traces from JOINs
            # Note: DISTINCT() without arguments works across all databases
            query = query.distinct()

        # Use EXISTS for metric filters (handles multiple metric types correctly)
        if self._has_metric_filters(filters):
            exists_conditions = self._build_metric_exists_conditions(filters)
            if exists_conditions:
                query = query.where(and_(*exists_conditions))

        return query

    def _build_metric_exists_conditions(self, filters: TraceQuerySchema) -> list:
        """Build optimized EXISTS conditions for metric filtering."""
        exists_conditions = []

        # Relevance filters
        if filters.query_relevance_filters:
            exists_conditions.append(
                self._build_relevance_exists(
                    MetricType.QUERY_RELEVANCE,
                    filters.query_relevance_filters,
                    filters.task_ids,
                ),
            )

        if filters.response_relevance_filters:
            exists_conditions.append(
                self._build_relevance_exists(
                    MetricType.RESPONSE_RELEVANCE,
                    filters.response_relevance_filters,
                    filters.task_ids,
                ),
            )

        # Tool classification filters
        if filters.tool_selection is not None:
            exists_conditions.append(
                self._build_tool_classification_exists(
                    MetricType.TOOL_SELECTION,
                    filters.tool_selection,
                    filters.task_ids,
                    "tool_selection",
                ),
            )

        if filters.tool_usage is not None:
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
        """Optimized relevance filtering using EXISTS."""
        # Create aliases to avoid conflicts
        inner_span = DatabaseSpan.__table__.alias("inner_span")
        inner_metric = DatabaseMetricResult.__table__.alias("inner_metric")

        # Build relevance conditions
        paths = {
            MetricType.QUERY_RELEVANCE: "query_relevance",
            MetricType.RESPONSE_RELEVANCE: "response_relevance",
        }
        if metric_type not in paths:
            raise ValueError(f"Unsupported relevance metric type: {metric_type}")

        # Use database-specific JSON extraction functions
        if self.db_session.bind.dialect.name == "postgresql":
            # PostgreSQL: jsonb_extract_path_text(column, 'path1', 'path2')
            score_path = func.jsonb_extract_path_text(
                inner_metric.c.details,
                paths[metric_type],
                "llm_relevance_score",
            )
        else:  # SQLite
            # SQLite: json_extract(column, '$.path1.path2')
            json_path = f"$.{paths[metric_type]}.llm_relevance_score"
            score_path = func.json_extract(inner_metric.c.details, json_path)

        relevance_conditions = [
            self._build_comparison_condition(func.cast(score_path, Float), f)
            for f in relevance_filters
        ]

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
                    inner_span.c.trace_id
                    == DatabaseTraceMetadata.trace_id,  # Correlation
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
        """Optimized tool classification filtering using EXISTS."""
        # Create aliases to avoid conflicts
        inner_span = DatabaseSpan.__table__.alias("inner_span")
        inner_metric = DatabaseMetricResult.__table__.alias("inner_metric")

        # Use database-specific JSON extraction for tool classification
        if self.db_session.bind.dialect.name == "postgresql":
            # PostgreSQL: jsonb_extract_path_text(column, 'path1', 'path2')
            classification_path = func.jsonb_extract_path_text(
                inner_metric.c.details,
                "tool_selection",
                field_name,
            )
        else:  # SQLite
            # SQLite: json_extract(column, '$.path1.path2')
            json_path = f"$.tool_selection.{field_name}"
            classification_path = func.json_extract(inner_metric.c.details, json_path)

        classification_condition = (
            func.cast(classification_path, Integer) == tool_class.value
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
                    inner_span.c.trace_id
                    == DatabaseTraceMetadata.trace_id,  # Correlation
                    inner_span.c.task_id.in_(task_ids),
                    inner_span.c.span_kind == SPAN_KIND_LLM,
                    inner_metric.c.metric_type == metric_type.value,
                    classification_condition,
                ),
            ),
        )

    def _apply_sorting_and_pagination(
        self,
        query: select,
        pagination_parameters: PaginationParameters,
    ) -> select:
        """Apply database-level sorting and pagination."""
        # Apply sorting
        if pagination_parameters.sort == PaginationSortMethod.DESCENDING:
            query = query.order_by(desc(DatabaseTraceMetadata.start_time))
        else:
            query = query.order_by(asc(DatabaseTraceMetadata.start_time))

        # Apply database-level pagination (much more efficient)
        offset = pagination_parameters.page * pagination_parameters.page_size
        query = query.offset(offset).limit(pagination_parameters.page_size)

        return query

    def _has_span_level_filters(self, filters: TraceQuerySchema) -> bool:
        """Check if span-level filtering is needed."""
        return bool(
            filters.tool_name
            or filters.span_types
            or self._has_metric_filters(filters),
        )

    def _has_metric_filters(self, filters: TraceQuerySchema) -> bool:
        """Check if metric filtering is needed."""
        return bool(
            filters.query_relevance_filters
            or filters.response_relevance_filters
            or filters.tool_selection is not None
            or filters.tool_usage is not None,
        )

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
        if trace_ids is not None:
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

    def _build_comparison_condition(self, column, filter_item: FloatRangeFilter):
        """Build comparison condition (reuse existing implementation)."""
        if filter_item.operator == ComparisonOperatorEnum.EQUAL:
            return column == filter_item.value
        elif filter_item.operator == ComparisonOperatorEnum.GREATER_THAN:
            return column > filter_item.value
        elif filter_item.operator == ComparisonOperatorEnum.GREATER_THAN_OR_EQUAL:
            return column >= filter_item.value
        elif filter_item.operator == ComparisonOperatorEnum.LESS_THAN:
            return column < filter_item.value
        elif filter_item.operator == ComparisonOperatorEnum.LESS_THAN_OR_EQUAL:
            return column <= filter_item.value
        else:
            raise ValueError(f"Unsupported operator: {filter_item.operator}")

    # ============================================================================
    # New methods for optimized trace endpoints
    # ============================================================================

    def get_trace_metadata_by_ids(self, trace_ids: list[str]) -> list[TraceMetadata]:
        """Query trace metadata table directly by trace IDs."""
        if not trace_ids:
            return []

        query = select(DatabaseTraceMetadata).where(
            DatabaseTraceMetadata.trace_id.in_(trace_ids),
        )

        results = self.db_session.execute(query).scalars().all()
        return [TraceMetadata._from_database_model(tm) for tm in results]

    def get_sessions_aggregated(
        self,
        task_ids: list[str],
        pagination_parameters: PaginationParameters,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> tuple[int, list[SessionMetadata]]:
        """Perform session-level aggregations with filtering."""
        if not task_ids:
            return 0, []

        # Build base query for session aggregation
        # Group by both session_id and task_id to ensure clean session boundaries
        query = select(
            DatabaseTraceMetadata.session_id,
            DatabaseTraceMetadata.task_id,
            func.array_agg(DatabaseTraceMetadata.trace_id).label("trace_ids"),
            func.sum(DatabaseTraceMetadata.span_count).label("span_count"),
            func.min(DatabaseTraceMetadata.start_time).label("earliest_start_time"),
            func.max(DatabaseTraceMetadata.end_time).label("latest_end_time"),
        ).where(
            and_(
                DatabaseTraceMetadata.task_id.in_(task_ids),
                DatabaseTraceMetadata.session_id.is_not(None),
            ),
        )

        # Apply time range filters
        if start_time:
            query = query.where(DatabaseTraceMetadata.start_time >= start_time)
        if end_time:
            query = query.where(DatabaseTraceMetadata.end_time <= end_time)

        # Group by both session_id and task_id to ensure proper session boundaries
        query = query.group_by(
            DatabaseTraceMetadata.session_id,
            DatabaseTraceMetadata.task_id,
        )

        # Apply sorting
        if pagination_parameters.sort == PaginationSortMethod.DESCENDING:
            query = query.order_by(desc("earliest_start_time"))
        else:
            query = query.order_by(asc("earliest_start_time"))

        # Get total count before pagination
        count_query = select(func.count()).select_from(query.subquery())
        total_count = self.db_session.execute(count_query).scalar()

        # Apply pagination
        offset = pagination_parameters.page * pagination_parameters.page_size
        query = query.offset(offset).limit(pagination_parameters.page_size)

        # Execute query
        results = self.db_session.execute(query).all()

        # Convert to SessionMetadata objects
        sessions = []
        for row in results:
            sessions.append(
                SessionMetadata(
                    session_id=row.session_id,
                    task_id=row.task_id,
                    trace_ids=row.trace_ids,
                    span_count=row.span_count,
                    earliest_start_time=row.earliest_start_time,
                    latest_end_time=row.latest_end_time,
                ),
            )

        return total_count, sessions

    def get_trace_ids_for_session(
        self,
        session_id: str,
        pagination_parameters: PaginationParameters,
    ) -> tuple[int, list[str]]:
        """Get paginated trace IDs for a specific session."""
        # Build query for traces in this session
        query = select(DatabaseTraceMetadata.trace_id).where(
            DatabaseTraceMetadata.session_id == session_id,
        )

        # Apply sorting
        if pagination_parameters.sort == PaginationSortMethod.DESCENDING:
            query = query.order_by(desc(DatabaseTraceMetadata.start_time))
        else:
            query = query.order_by(asc(DatabaseTraceMetadata.start_time))

        # Get total count before pagination
        count_query = select(func.count(DatabaseTraceMetadata.trace_id)).where(
            DatabaseTraceMetadata.session_id == session_id,
        )
        total_count = self.db_session.execute(count_query).scalar()

        # Apply pagination
        offset = pagination_parameters.page * pagination_parameters.page_size
        query = query.offset(offset).limit(pagination_parameters.page_size)

        # Execute query
        results = self.db_session.execute(query).scalars().all()
        trace_ids = [trace_id for trace_id in results]

        return total_count, trace_ids
