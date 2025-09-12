import logging
from datetime import datetime
from typing import Optional

from arthur_common.models.common_schemas import PaginationParameters
from arthur_common.models.enums import MetricType, PaginationSortMethod
from sqlalchemy import and_, asc, cast, desc, exists, func, select
from sqlalchemy.orm import Session
from sqlalchemy.types import Float, Integer

from db_models.db_models import (
    DatabaseMetricResult,
    DatabaseSpan,
    DatabaseTraceMetadata,
)
from schemas.enums import ComparisonOperatorEnum, ToolClassEnum
from schemas.internal_schemas import (
    FloatRangeFilter,
    Span,
    TraceQuerySchema,
)
from utils import trace as trace_utils
from utils.constants import SPAN_KIND_LLM, SPAN_KIND_TOOL

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
        """Main entry point for trace filtering using optimized two-phase strategy."""
        if not filters.task_ids:
            return None

        # Phase 1: Get candidate traces from TraceMetadata table
        candidate_trace_metadata = self._get_all_candidate_traces_from_metadata(
            filters,
            pagination_parameters.sort,
        )
        if not candidate_trace_metadata:
            return None

        # Phase 2: Apply span-level filtering if needed
        if self._has_span_level_filters(filters):
            candidate_trace_ids = [tm.trace_id for tm in candidate_trace_metadata]
            qualifying_trace_ids = self._get_qualifying_traces_from_spans(
                filters,
                candidate_trace_ids,
            )
            qualifying_metadata = [
                tm
                for tm in candidate_trace_metadata
                if tm.trace_id in qualifying_trace_ids
            ]
        else:
            qualifying_metadata = candidate_trace_metadata

        # Phase 3: Apply pagination and extract trace IDs
        paginated_metadata = self._apply_pagination_to_metadata(
            qualifying_metadata,
            pagination_parameters,
        )
        trace_ids = [tm.trace_id for tm in paginated_metadata]
        logger.debug(
            f"Found {len(trace_ids)} trace IDs for task IDs: {filters.task_ids} (page={pagination_parameters.page}, page_size={pagination_parameters.page_size}, sort={pagination_parameters.sort})",
        )
        return trace_ids

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
        """Query individual spans with basic filtering and pagination."""
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

    def _get_all_candidate_traces_from_metadata(
        self,
        filters: TraceQuerySchema,
        sort: PaginationSortMethod,
    ) -> Optional[list[DatabaseTraceMetadata]]:
        """Fast trace-level filtering using TraceMetadata table."""
        # Base query on optimized trace_metadata table
        query = select(DatabaseTraceMetadata).where(
            DatabaseTraceMetadata.task_id.in_(filters.task_ids),
        )

        # Fast indexed filters
        if filters.trace_ids:
            query = query.where(DatabaseTraceMetadata.trace_id.in_(filters.trace_ids))
        if filters.start_time:
            query = query.where(DatabaseTraceMetadata.start_time >= filters.start_time)
        if filters.end_time:
            query = query.where(DatabaseTraceMetadata.end_time <= filters.end_time)

        # Duration filters using dialect-agnostic calculation
        if filters.trace_duration_filters:
            duration_conditions = []
            for filter_item in filters.trace_duration_filters:
                # Dialect-agnostic duration calculation with sub-second precision
                # Cast to Float ensures proper fractional seconds support across databases
                start_epoch = func.extract("epoch", DatabaseTraceMetadata.start_time)
                end_epoch = func.extract("epoch", DatabaseTraceMetadata.end_time)
                duration_seconds = func.round(cast(end_epoch - start_epoch, Float), 3)

                duration_conditions.append(
                    self._build_comparison_condition(duration_seconds, filter_item),
                )
            query = query.where(and_(*duration_conditions))

        # Apply early sorting in database (much more efficient than memory sorting)
        if sort == PaginationSortMethod.DESCENDING:
            query = query.order_by(desc(DatabaseTraceMetadata.start_time))
        else:
            query = query.order_by(asc(DatabaseTraceMetadata.start_time))

        results = self.db_session.execute(query).scalars().all()
        return list(results) if results else None

    def _apply_pagination_to_metadata(
        self,
        metadata_list: list[DatabaseTraceMetadata],
        pagination_parameters: PaginationParameters,
    ) -> list[DatabaseTraceMetadata]:
        """Apply pagination to filtered metadata (already sorted in database)."""
        start_idx = pagination_parameters.page * pagination_parameters.page_size
        end_idx = start_idx + pagination_parameters.page_size
        return metadata_list[start_idx:end_idx]

    def _get_qualifying_traces_from_spans(
        self,
        filters: TraceQuerySchema,
        candidate_trace_ids: list[str],
    ) -> set[str]:
        """Find traces containing spans matching span-level criteria."""
        qualifying_traces = set(candidate_trace_ids)
        if filters.tool_name:
            tool_name_traces = self._get_traces_with_tool_name(
                filters.tool_name,
                candidate_trace_ids,
            )
            qualifying_traces.intersection_update(tool_name_traces)

        if filters.span_types:
            span_type_traces = self._get_traces_with_span_types(
                filters.span_types,
                candidate_trace_ids,
            )
            qualifying_traces.intersection_update(span_type_traces)

        if self._has_metric_filters(filters):
            metric_traces = self._get_traces_with_metrics(
                filters,
                candidate_trace_ids,
            )
            qualifying_traces.intersection_update(metric_traces)
        return qualifying_traces

    def _get_traces_with_tool_name(
        self,
        tool_name: str,
        candidate_trace_ids: list[str],
    ) -> set[str]:
        """Optimized tool name filtering using span_name column."""
        query = select(DatabaseSpan.trace_id.distinct()).where(
            and_(
                DatabaseSpan.trace_id.in_(candidate_trace_ids),
                DatabaseSpan.span_kind == SPAN_KIND_TOOL,
                DatabaseSpan.span_name == tool_name,
            ),
        )

        results = self.db_session.execute(query).scalars().all()
        return set(results)

    def _get_traces_with_span_types(
        self,
        span_types: list[str],
        candidate_trace_ids: list[str],
    ) -> set[str]:
        """Find traces containing spans of the specified types."""
        query = select(DatabaseSpan.trace_id.distinct()).where(
            and_(
                DatabaseSpan.trace_id.in_(candidate_trace_ids),
                DatabaseSpan.span_kind.in_(span_types),
            ),
        )

        results = self.db_session.execute(query).scalars().all()
        return set(results)

    def _get_traces_with_metrics(
        self,
        filters: TraceQuerySchema,
        candidate_trace_ids: list[str],
    ) -> set[str]:
        """Find traces with metric conditions, restricted to candidates."""
        base_query = select(DatabaseSpan.trace_id.distinct()).where(
            DatabaseSpan.trace_id.in_(candidate_trace_ids),
        )
        exists_conditions = self._build_metric_exists_conditions(
            filters,
            candidate_trace_ids,
        )
        if exists_conditions:
            base_query = base_query.where(and_(*exists_conditions))
        return set(self.db_session.execute(base_query).scalars().all())

    def _has_metric_filters(self, filters: TraceQuerySchema) -> bool:
        """Check if we need expensive metric-based filtering."""
        return bool(
            filters.query_relevance_filters
            or filters.response_relevance_filters
            or filters.tool_selection
            or filters.tool_usage,
        )

    def _build_metric_exists_conditions(
        self,
        filters: TraceQuerySchema,
        candidate_trace_ids: list[str],
    ) -> list:
        """Build optimized EXISTS conditions for metric filtering on candidate traces."""
        exists_conditions = []

        # Relevance filters
        for relevance_filters, metric_type in [
            (filters.query_relevance_filters, MetricType.QUERY_RELEVANCE),
            (filters.response_relevance_filters, MetricType.RESPONSE_RELEVANCE),
        ]:
            if relevance_filters:
                exists_conditions.append(
                    self._build_relevance_exists(
                        metric_type,
                        relevance_filters,
                        filters.task_ids,
                        candidate_trace_ids,
                    ),
                )

        # Tool classification filters
        for tool_class, field_name in [
            (filters.tool_selection, "tool_selection"),
            (filters.tool_usage, "tool_usage"),
        ]:
            if tool_class:
                exists_conditions.append(
                    self._build_tool_classification_exists(
                        MetricType.TOOL_SELECTION,
                        tool_class,
                        filters.task_ids,
                        field_name,
                        candidate_trace_ids,
                    ),
                )

        return exists_conditions

    def _build_comparison_condition(self, column, filter_item: FloatRangeFilter):
        """Build comparison condition (column OP value) from FloatRangeFilter."""
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

    def _build_relevance_exists(
        self,
        metric_type: MetricType,
        relevance_filters: list[FloatRangeFilter],
        task_ids: list[str],
        candidate_trace_ids: list[str],
    ):
        """Optimized relevance filtering restricted to candidate traces."""
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
                    inner_span.c.trace_id == DatabaseSpan.trace_id,  # Correlation
                    inner_span.c.trace_id.in_(
                        candidate_trace_ids,
                    ),  # Restrict to candidates
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
        candidate_trace_ids: list[str],
    ):
        """Optimized tool classification filtering restricted to candidate traces."""
        # Create aliases to avoid conflicts
        inner_span = DatabaseSpan.__table__.alias("inner_span")
        inner_metric = DatabaseMetricResult.__table__.alias("inner_metric")

        # Tool classification path
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
                    inner_span.c.trace_id == DatabaseSpan.trace_id,  # Correlation
                    inner_span.c.trace_id.in_(
                        candidate_trace_ids,
                    ),  # Restrict to candidates
                    inner_span.c.task_id.in_(task_ids),
                    inner_span.c.span_kind == SPAN_KIND_LLM,
                    inner_metric.c.metric_type == metric_type.value,
                    classification_condition,
                ),
            ),
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
        """Check if we need expensive span-level filtering."""
        return bool(
            filters.tool_name
            or filters.span_types
            or filters.query_relevance_filters
            or filters.response_relevance_filters
            or filters.tool_selection
            or filters.tool_usage,
        )
