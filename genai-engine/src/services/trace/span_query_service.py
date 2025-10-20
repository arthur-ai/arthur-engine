"""
SpanQueryService with optimized query strategies.
"""

import logging
from datetime import datetime
from typing import List, Optional, Tuple

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import PaginationSortMethod
from sqlalchemy import and_, asc, cast, desc, exists, func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.types import Numeric

from db_models import (
    DatabaseSpan,
    DatabaseTraceMetadata,
)
from schemas.internal_schemas import (
    SessionMetadata,
    Span,
    TraceMetadata,
    TraceQuerySchema,
    UserMetadata,
)
from services.trace.filter_service import FilterService
from utils import trace as trace_utils
from utils.constants import SPAN_KIND_LLM

logger = logging.getLogger(__name__)

# Constants
DEFAULT_PAGE_SIZE = 5


class SpanQueryService:
    """
    SpanQueryService with single-query strategy. This implements the proposed optimizations for comparison.
    """

    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.filter_service = FilterService(db_session)

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
        This implements the trace-based filtering pattern from the TDD.
        """
        # Validate filter compatibility first
        compatibility_issues = self.filter_service.validate_filter_compatibility(
            filters,
        )
        if compatibility_issues:
            logger.warning(
                f"Filter compatibility issues detected: {compatibility_issues}",
            )

        # Start with base metadata query
        query = select(DatabaseTraceMetadata).where(
            DatabaseTraceMetadata.task_id.in_(filters.task_ids),
        )

        # Apply trace-level filters (fast indexed operations)
        query = self._apply_trace_level_filters(query, filters)

        # Apply span-level filters using optimized JOINs and EXISTS
        if self.filter_service.has_span_level_filters(filters):
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
                # Database-level duration calculation
                start_epoch = func.extract("epoch", DatabaseTraceMetadata.start_time)
                end_epoch = func.extract("epoch", DatabaseTraceMetadata.end_time)
                duration_seconds = func.round(cast(end_epoch - start_epoch, Numeric), 3)

                duration_conditions.append(
                    self.filter_service.build_comparison_condition(
                        duration_seconds,
                        filter_item,
                    ),
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
        Apply span-level filters using optimized JOINs for simple filters and EXISTS for metrics.

        Strategy:
        - Simple span filters (tool_name, span_types): Use JOINs
        - Metric filters: Use EXISTS clauses
        - Multiple span types: Use OR logic with proper grouping
        """
        span_types = self.filter_service.auto_detect_span_types(filters)

        if not span_types:
            return query

        # Handle single vs multiple span types differently for optimization
        if len(span_types) == 1:
            query = self._apply_single_span_type_filters(query, filters, span_types[0])
        else:
            query = self._apply_multiple_span_types_filters(query, filters, span_types)

        # Apply metric filters using EXISTS (works for both single and multiple span types)
        if self.filter_service.has_llm_metric_filters(filters):
            metric_exists_conditions = (
                self.filter_service.build_all_metric_exists_conditions(
                    filters,
                    DatabaseTraceMetadata.trace_id,
                )
            )
            if metric_exists_conditions:
                query = query.where(and_(*metric_exists_conditions))

        return query

    def _apply_single_span_type_filters(
        self,
        query: select,
        filters: TraceQuerySchema,
        span_type: str,
    ) -> select:
        """Apply filters for a single span type using JOINs for better performance."""
        # Join with spans for direct filtering
        query = query.join(
            DatabaseSpan,
            and_(
                DatabaseTraceMetadata.trace_id == DatabaseSpan.trace_id,
                DatabaseSpan.task_id.in_(filters.task_ids),
            ),
        )

        # Build span conditions using filter service
        span_conditions = self.filter_service.build_single_span_type_conditions(
            span_type,
            filters,
        )

        if span_conditions:
            query = query.where(and_(*span_conditions))

        # Use DISTINCT to avoid duplicate traces from JOINs
        query = query.distinct()

        return query

    def _apply_multiple_span_types_filters(
        self,
        query: select,
        filters: TraceQuerySchema,
        span_types: List[str],
    ) -> select:
        """Apply filters for multiple span types using EXISTS clauses."""
        # For multiple span types, use EXISTS with OR logic
        or_conditions = self.filter_service.build_multiple_span_types_or_conditions(
            span_types,
            filters,
        )

        if or_conditions:
            # Create EXISTS clause with OR conditions
            exists_condition = exists(
                select(1)
                .select_from(DatabaseSpan)
                .where(
                    and_(
                        DatabaseSpan.trace_id == DatabaseTraceMetadata.trace_id,
                        DatabaseSpan.task_id.in_(filters.task_ids),
                        or_(*or_conditions),  # OR across span types
                    ),
                ),
            )
            query = query.where(exists_condition)

        return query

    def _apply_sorting_and_pagination(
        self,
        query: select,
        pagination_parameters: PaginationParameters,
        sort_column=None,
    ) -> select:
        """Apply database-level sorting and pagination."""
        # Default to trace metadata start_time if no column specified
        if sort_column is None:
            sort_column = DatabaseTraceMetadata.start_time

        # Apply sorting
        if pagination_parameters.sort == PaginationSortMethod.DESCENDING:
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))

        # Apply database-level pagination
        offset = pagination_parameters.page * pagination_parameters.page_size
        query = query.offset(offset).limit(pagination_parameters.page_size)

        return query

    def _apply_sorting(
        self,
        query: select,
        pagination_parameters: PaginationParameters,
        sort_column_or_label,
    ) -> select:
        """Apply sorting to a query."""
        if pagination_parameters.sort == PaginationSortMethod.DESCENDING:
            return query.order_by(desc(sort_column_or_label))
        else:
            return query.order_by(asc(sort_column_or_label))

    def _get_count_from_query(self, query: select) -> int:
        """Get total count from a query using subquery approach."""
        count_query = select(func.count()).select_from(query.subquery())
        return self.db_session.execute(count_query).scalar()

    def _get_count_with_where(self, count_column, where_clause) -> int:
        """Get count with custom WHERE clause (for edge cases)."""
        count_query = select(func.count(count_column)).where(where_clause)
        return self.db_session.execute(count_query).scalar()

    def _apply_pagination(
        self,
        query: select,
        pagination_parameters: PaginationParameters,
    ) -> select:
        """Apply OFFSET and LIMIT to a query."""
        offset = pagination_parameters.page * pagination_parameters.page_size
        return query.offset(offset).limit(pagination_parameters.page_size)

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

    # ============================================================================
    # Span-Based Filtering Methods (New Pattern)
    # ============================================================================

    def get_paginated_spans_with_filters(
        self,
        filters: TraceQuerySchema,
        pagination_parameters: PaginationParameters,
    ) -> Optional[Tuple[List[Span], int]]:
        """
        Span-based filtering that finds individual spans matching criteria.
        Returns tuple of (spans, total_count).

        This implements the span-first query pattern from the TDD:
        - Base Query: SELECT DatabaseSpan WHERE task_id IN (...)
        - Trace Filters: JOIN with DatabaseTraceMetadata when needed
        - Single Span Type: Direct WHERE conditions + metric EXISTS clauses
        - Multiple Span Types: OR conditions grouping span type + filters
        - Result: Single query returning individual spans
        """
        if not filters.task_ids:
            return None, 0

        # Validate filter compatibility
        compatibility_issues = self.filter_service.validate_filter_compatibility(
            filters,
        )
        if compatibility_issues:
            logger.warning(
                f"Filter compatibility issues detected: {compatibility_issues}",
            )
            # Return empty results for incompatible filter combinations
            return [], 0

        # Build comprehensive span-based query
        base_query = self._build_unified_span_query(filters)

        # Get total count before pagination
        count_query = select(func.count()).select_from(base_query.subquery())
        total_count = self.db_session.execute(count_query).scalar()

        # Apply sorting and pagination at database level
        query = self._apply_sorting_and_pagination(
            base_query,
            pagination_parameters,
            DatabaseSpan.start_time,
        )

        # Execute with database-level pagination
        results = self.db_session.execute(query).scalars().unique().all()
        spans = [Span._from_database_model(span) for span in results]

        return spans, total_count

    def _build_unified_span_query(self, filters: TraceQuerySchema) -> select:
        """
        Build a single query that starts from spans and finds individual matching spans.
        This implements the span-based filtering pattern from the TDD.
        """
        # Start with base span query
        query = select(DatabaseSpan).where(
            DatabaseSpan.task_id.in_(filters.task_ids),
        )

        # Apply trace-level filters if needed (requires JOIN)
        if self._needs_trace_metadata_join(filters):
            query = self._apply_trace_filters_with_join(query, filters)

        # Apply span-level filters
        if self.filter_service.has_span_level_filters(filters):
            query = self._apply_span_level_filters_direct(query, filters)

        return query

    def _needs_trace_metadata_join(self, filters: TraceQuerySchema) -> bool:
        """Check if we need to join with trace metadata for trace-level filters."""
        return bool(
            filters.trace_ids
            or filters.start_time
            or filters.end_time
            or filters.trace_duration_filters,
        )

    def _apply_trace_filters_with_join(
        self,
        query: select,
        filters: TraceQuerySchema,
    ) -> select:
        """Apply trace-level filters by joining with trace metadata."""
        # Join with trace metadata
        query = query.join(
            DatabaseTraceMetadata,
            and_(
                DatabaseSpan.trace_id == DatabaseTraceMetadata.trace_id,
                DatabaseTraceMetadata.task_id.in_(filters.task_ids),
            ),
        )

        conditions = []

        # Direct trace metadata filters
        if filters.trace_ids:
            conditions.append(DatabaseTraceMetadata.trace_id.in_(filters.trace_ids))
        if filters.start_time:
            conditions.append(DatabaseTraceMetadata.start_time >= filters.start_time)
        if filters.end_time:
            conditions.append(DatabaseTraceMetadata.end_time <= filters.end_time)

        # Duration filters
        if filters.trace_duration_filters:
            duration_conditions = []
            for filter_item in filters.trace_duration_filters:
                start_epoch = func.extract("epoch", DatabaseTraceMetadata.start_time)
                end_epoch = func.extract("epoch", DatabaseTraceMetadata.end_time)
                duration_seconds = func.round(cast(end_epoch - start_epoch, Numeric), 3)

                duration_conditions.append(
                    self.filter_service.build_comparison_condition(
                        duration_seconds,
                        filter_item,
                    ),
                )
            conditions.extend(duration_conditions)

        if conditions:
            query = query.where(and_(*conditions))

        return query

    def _apply_span_level_filters_direct(
        self,
        query: select,
        filters: TraceQuerySchema,
    ) -> select:
        """
        Apply span-level filters directly on the span query.

        Strategy for span-based queries:
        - Single Span Type: Direct WHERE conditions + metric EXISTS clauses
        - Multiple Span Types: OR conditions grouping span type + filters
        """
        span_types = self.filter_service.auto_detect_span_types(filters)

        if not span_types:
            return query

        # Handle single vs multiple span types
        if len(span_types) == 1:
            query = self._apply_single_span_type_direct(query, filters, span_types[0])
        else:
            query = self._apply_multiple_span_types_direct(query, filters, span_types)

        # Apply metric filters using EXISTS clauses (correlation via span.id)
        if self.filter_service.has_llm_metric_filters(filters):
            metric_exists_conditions = (
                self.filter_service.build_span_metric_exists_conditions(
                    filters,
                    DatabaseSpan.id,
                )
            )
            if metric_exists_conditions:
                query = query.where(and_(*metric_exists_conditions))

        return query

    def _apply_single_span_type_direct(
        self,
        query: select,
        filters: TraceQuerySchema,
        span_type: str,
    ) -> select:
        """Apply direct WHERE conditions for a single span type."""
        span_conditions = self.filter_service.build_single_span_type_conditions(
            span_type,
            filters,
        )

        if span_conditions:
            query = query.where(and_(*span_conditions))

        return query

    def _apply_multiple_span_types_direct(
        self,
        query: select,
        filters: TraceQuerySchema,
        span_types: List[str],
    ) -> select:
        """Apply OR conditions for multiple span types."""
        or_conditions = self.filter_service.build_multiple_span_types_or_conditions(
            span_types,
            filters,
        )

        if or_conditions:
            query = query.where(or_(*or_conditions))

        return query

    # ============================================================================
    # New methods for optimized trace endpoints
    # ============================================================================

    def get_trace_metadata_by_ids(
        self,
        trace_ids: list[str],
        sort_method: Optional[PaginationSortMethod] = None,
    ) -> list[TraceMetadata]:
        """Query trace metadata table directly by trace IDs.

        Args:
            trace_ids: List of trace IDs to fetch metadata for
            sort_method: Optional sort method to apply to results by start_time
        """
        if not trace_ids:
            return []

        query = select(DatabaseTraceMetadata).where(
            DatabaseTraceMetadata.trace_id.in_(trace_ids),
        )

        results = self.db_session.execute(query).scalars().all()
        trace_metadata_list = [TraceMetadata._from_database_model(tm) for tm in results]

        # Apply sorting if specified (IN clause doesn't preserve order)
        if sort_method is not None:
            if sort_method == PaginationSortMethod.DESCENDING:
                trace_metadata_list.sort(key=lambda tm: tm.start_time, reverse=True)
            else:
                trace_metadata_list.sort(key=lambda tm: tm.start_time, reverse=False)

        return trace_metadata_list

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

        # Use database-appropriate aggregation function
        if self.db_session.bind.dialect.name == "postgresql":
            trace_ids_agg = func.array_agg(DatabaseTraceMetadata.trace_id).label(
                "trace_ids",
            )
        else:  # SQLite and others
            trace_ids_agg = func.group_concat(DatabaseTraceMetadata.trace_id).label(
                "trace_ids",
            )

        query = select(
            DatabaseTraceMetadata.session_id,
            DatabaseTraceMetadata.task_id,
            trace_ids_agg,
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

        # Apply pagination with bite-sized functions
        query = self._apply_sorting(query, pagination_parameters, "earliest_start_time")
        total_count = self._get_count_from_query(query)
        query = self._apply_pagination(query, pagination_parameters)
        results = self.db_session.execute(query).all()

        # Convert to SessionMetadata objects
        sessions = []
        for row in results:
            # Handle trace_ids based on database type
            if self.db_session.bind.dialect.name == "postgresql":
                trace_ids = row.trace_ids  # Already a list from array_agg
            else:  # SQLite - split the group_concat result
                trace_ids = row.trace_ids.split(",") if row.trace_ids else []

            sessions.append(
                SessionMetadata(
                    session_id=row.session_id,
                    task_id=row.task_id,
                    trace_ids=trace_ids,
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

        # Apply pagination with bite-sized functions
        query = self._apply_sorting(
            query,
            pagination_parameters,
            DatabaseTraceMetadata.start_time,
        )
        total_count = self._get_count_with_where(
            DatabaseTraceMetadata.trace_id,
            DatabaseTraceMetadata.session_id == session_id,
        )
        query = self._apply_pagination(query, pagination_parameters)
        results = self.db_session.execute(query).scalars().all()
        trace_ids = [trace_id for trace_id in results]

        return total_count, trace_ids

    def get_users_aggregated(
        self,
        task_ids: list[str],
        pagination_parameters: PaginationParameters,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> tuple[int, list[UserMetadata]]:
        """Perform user-level aggregations with filtering."""
        if not task_ids:
            return 0, []

        # Use database-appropriate aggregation functions
        if self.db_session.bind.dialect.name == "postgresql":
            session_ids_agg = (
                func.array_agg(func.distinct(DatabaseTraceMetadata.session_id))
                .filter(DatabaseTraceMetadata.session_id.is_not(None))
                .label("session_ids")
            )
            trace_ids_agg = func.array_agg(DatabaseTraceMetadata.trace_id).label(
                "trace_ids",
            )
        else:  # SQLite
            session_ids_agg = func.group_concat(
                func.distinct(DatabaseTraceMetadata.session_id),
            ).label("session_ids")
            trace_ids_agg = func.group_concat(DatabaseTraceMetadata.trace_id).label(
                "trace_ids",
            )

        query = select(
            DatabaseTraceMetadata.user_id,
            DatabaseTraceMetadata.task_id,
            session_ids_agg,
            trace_ids_agg,
            func.sum(DatabaseTraceMetadata.span_count).label("span_count"),
            func.min(DatabaseTraceMetadata.start_time).label("earliest_start_time"),
            func.max(DatabaseTraceMetadata.end_time).label("latest_end_time"),
        ).where(
            and_(
                DatabaseTraceMetadata.task_id.in_(task_ids),
                DatabaseTraceMetadata.user_id.is_not(None),
            ),
        )

        # Apply time range filters
        if start_time:
            query = query.where(DatabaseTraceMetadata.start_time >= start_time)
        if end_time:
            query = query.where(DatabaseTraceMetadata.end_time <= end_time)

        # Group by both user_id and task_id to ensure proper boundaries
        query = query.group_by(
            DatabaseTraceMetadata.user_id,
            DatabaseTraceMetadata.task_id,
        )

        # Apply pagination with bite-sized functions
        query = self._apply_sorting(query, pagination_parameters, "earliest_start_time")
        total_count = self._get_count_from_query(query)
        query = self._apply_pagination(query, pagination_parameters)
        results = self.db_session.execute(query).all()

        # Convert to UserMetadata objects
        users = []
        for row in results:
            # Handle aggregated IDs based on database type
            if self.db_session.bind.dialect.name == "postgresql":
                session_ids = [
                    sid for sid in (row.session_ids or []) if sid
                ]  # Filter nulls
                trace_ids = row.trace_ids or []
            else:  # SQLite
                session_ids = [
                    sid
                    for sid in (row.session_ids.split(",") if row.session_ids else [])
                    if sid
                ]
                trace_ids = row.trace_ids.split(",") if row.trace_ids else []

            users.append(
                UserMetadata(
                    user_id=row.user_id,
                    task_id=row.task_id,
                    session_ids=session_ids,
                    trace_ids=trace_ids,
                    span_count=row.span_count or 0,
                    earliest_start_time=row.earliest_start_time,
                    latest_end_time=row.latest_end_time,
                ),
            )

        return total_count, users

    def get_sessions_for_user(
        self,
        user_id: str,
        pagination_parameters: PaginationParameters,
    ) -> tuple[int, list[SessionMetadata]]:
        """Get paginated sessions for a specific user."""
        # Use same aggregation logic as get_sessions_aggregated but filter by user_id

        # Use database-appropriate aggregation function
        if self.db_session.bind.dialect.name == "postgresql":
            trace_ids_agg = func.array_agg(DatabaseTraceMetadata.trace_id).label(
                "trace_ids",
            )
        else:  # SQLite
            trace_ids_agg = func.group_concat(DatabaseTraceMetadata.trace_id).label(
                "trace_ids",
            )

        query = select(
            DatabaseTraceMetadata.session_id,
            DatabaseTraceMetadata.task_id,
            trace_ids_agg,
            func.sum(DatabaseTraceMetadata.span_count).label("span_count"),
            func.min(DatabaseTraceMetadata.start_time).label("earliest_start_time"),
            func.max(DatabaseTraceMetadata.end_time).label("latest_end_time"),
        ).where(
            and_(
                DatabaseTraceMetadata.user_id == user_id,
                DatabaseTraceMetadata.session_id.is_not(None),
            ),
        )

        # Group by both session_id and task_id
        query = query.group_by(
            DatabaseTraceMetadata.session_id,
            DatabaseTraceMetadata.task_id,
        )

        # Apply pagination with bite-sized functions
        query = self._apply_sorting(query, pagination_parameters, "earliest_start_time")
        total_count = self._get_count_from_query(query)
        query = self._apply_pagination(query, pagination_parameters)
        results = self.db_session.execute(query).all()

        # Convert to SessionMetadata objects
        sessions = []
        for row in results:
            # Handle trace_ids based on database type
            if self.db_session.bind.dialect.name == "postgresql":
                trace_ids = row.trace_ids or []
            else:  # SQLite
                trace_ids = row.trace_ids.split(",") if row.trace_ids else []

            sessions.append(
                SessionMetadata(
                    session_id=row.session_id,
                    task_id=row.task_id,
                    trace_ids=trace_ids,
                    span_count=row.span_count or 0,
                    earliest_start_time=row.earliest_start_time,
                    latest_end_time=row.latest_end_time,
                ),
            )

        return total_count, sessions

    def get_traces_for_user(
        self,
        user_id: str,
        pagination_parameters: PaginationParameters,
    ) -> tuple[int, list[TraceMetadata]]:
        """Get paginated traces for a specific user."""
        query = select(DatabaseTraceMetadata).where(
            DatabaseTraceMetadata.user_id == user_id,
        )

        # Apply pagination with bite-sized functions
        query = self._apply_sorting(
            query,
            pagination_parameters,
            DatabaseTraceMetadata.start_time,
        )
        total_count = self._get_count_with_where(
            DatabaseTraceMetadata.trace_id,
            DatabaseTraceMetadata.user_id == user_id,
        )
        query = self._apply_pagination(query, pagination_parameters)
        results = self.db_session.execute(query).scalars().all()
        traces = [TraceMetadata._from_database_model(tm) for tm in results]

        return total_count, traces
