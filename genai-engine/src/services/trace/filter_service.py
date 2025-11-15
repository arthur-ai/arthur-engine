"""
Filter service containing shared components for both trace-based and span-based filtering.
"""

import logging
from typing import List, Optional

from arthur_common.models.enums import ComparisonOperatorEnum, MetricType, ToolClassEnum
from openinference.semconv.trace import OpenInferenceSpanKindValues
from sqlalchemy import and_, exists, func, select
from sqlalchemy.orm import Session
from sqlalchemy.types import Float, Integer

from db_models import DatabaseMetricResult, DatabaseSpan
from schemas.internal_schemas import FloatRangeFilter, TraceQuerySchema
from utils.constants import SPAN_KIND_LLM, SPAN_KIND_TOOL

logger = logging.getLogger(__name__)


class FilterService:
    """
    Service containing shared filter building components.

    This service provides reusable methods for:
    - Filter validation and compatibility checking
    - Span type auto-detection from filter presence
    - Database-specific JSON extraction functions
    - Comparison condition building
    - Metric EXISTS clause generation
    """

    def __init__(self, db_session: Session):
        self.db_session = db_session

    # ============================================================================
    # Filter Validation and Auto-Detection
    # ============================================================================

    def auto_detect_span_types(self, filters: TraceQuerySchema) -> Optional[List[str]]:
        """Auto-detect required span types from filter presence.

        Returns:
            - Explicit span_types if provided
            - Detected span types if span-type-specific filters are present (LLM metrics, tool_name)
            - ALL span types if cross-span-type filters are present (status_code) but no span-type-specific filters
            - None if no span-level filtering is needed
        """
        if filters.span_types:
            return filters.span_types

        detected_types = set()

        # LLM span filters
        if self.has_llm_metric_filters(filters):
            detected_types.add(SPAN_KIND_LLM)

        # Tool span filters
        if filters.tool_name:
            detected_types.add(SPAN_KIND_TOOL)

        # If we detected specific span types, return them
        if detected_types:
            return list(detected_types)

        # If no span-type-specific filters but we have cross-span-type filters,
        # return all span types from OpenInference spec
        if filters.status_code:
            return [kind.value for kind in OpenInferenceSpanKindValues]

        return None

    def validate_filter_compatibility(self, filters: TraceQuerySchema) -> List[str]:
        """Validate filter combinations and return any compatibility issues."""
        issues = []
        span_types = self.auto_detect_span_types(filters)

        if not span_types:
            return issues

        # Check for incompatible combinations per TDD specification
        # LLM metric filters require LLM spans to be present
        if self.has_llm_metric_filters(filters) and SPAN_KIND_LLM not in span_types:
            issues.append(
                "LLM metric filters (query_relevance, response_relevance, tool_selection, tool_usage) require LLM spans to be included in span_types",
            )

        # Tool name filters require TOOL spans to be present
        if filters.tool_name and SPAN_KIND_TOOL not in span_types:
            issues.append(
                "tool_name filters require TOOL spans to be included in span_types",
            )

        return issues

    def has_llm_metric_filters(self, filters: TraceQuerySchema) -> bool:
        """Check if any LLM-specific metric filters are present."""
        return bool(
            filters.query_relevance_filters
            or filters.response_relevance_filters
            or filters.tool_selection is not None
            or filters.tool_usage is not None,
        )

    def has_span_level_filters(self, filters: TraceQuerySchema) -> bool:
        """Check if span-level filtering is needed."""
        return bool(
            filters.tool_name
            or filters.span_types
            or filters.status_code
            or self.has_llm_metric_filters(filters),
        )

    # ============================================================================
    # Database-Specific JSON Extraction
    # ============================================================================

    def extract_json_field(self, column, *path_components):
        """Extract JSON field using database-specific functions."""
        if self.db_session.bind.dialect.name == "postgresql":
            # PostgreSQL: jsonb_extract_path_text(column, 'path1', 'path2')
            return func.jsonb_extract_path_text(column, *path_components)
        else:  # SQLite
            # SQLite: json_extract(column, '$.path1.path2')
            json_path = "$." + ".".join(path_components)
            return func.json_extract(column, json_path)

    # ============================================================================
    # Comparison Condition Building
    # ============================================================================

    def build_comparison_condition(self, column, filter_item: FloatRangeFilter):
        """Build comparison condition for various operators."""
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
    # EXISTS Clause Generation for Metrics
    # ============================================================================

    def build_relevance_exists_clause(
        self,
        metric_type: MetricType,
        relevance_filters: List[FloatRangeFilter],
        task_ids: List[str],
        correlation_column,
    ):
        """Build optimized EXISTS clause for relevance filtering."""
        # Create aliases to avoid conflicts
        inner_span = DatabaseSpan.__table__.alias("inner_span")
        inner_metric = DatabaseMetricResult.__table__.alias("inner_metric")

        # Determine JSON path based on metric type
        paths = {
            MetricType.QUERY_RELEVANCE: "query_relevance",
            MetricType.RESPONSE_RELEVANCE: "response_relevance",
        }
        if metric_type not in paths:
            raise ValueError(f"Unsupported relevance metric type: {metric_type}")

        # Extract score using database-specific JSON functions
        score_path = self.extract_json_field(
            inner_metric.c.details,
            paths[metric_type],
            "llm_relevance_score",
        )

        # Build relevance conditions
        relevance_conditions = [
            self.build_comparison_condition(func.cast(score_path, Float), f)
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
                    inner_span.c.trace_id == correlation_column,
                    inner_span.c.task_id.in_(task_ids),
                    inner_span.c.span_kind == SPAN_KIND_LLM,
                    inner_metric.c.metric_type == metric_type.value,
                    *relevance_conditions,
                ),
            ),
        )

    def build_tool_classification_exists_clause(
        self,
        metric_type: MetricType,
        tool_class: ToolClassEnum,
        task_ids: List[str],
        field_name: str,
        correlation_column,
    ):
        """Build optimized EXISTS clause for tool classification filtering."""
        # Create aliases to avoid conflicts
        inner_span = DatabaseSpan.__table__.alias("inner_span")
        inner_metric = DatabaseMetricResult.__table__.alias("inner_metric")

        # Extract classification using database-specific JSON functions
        classification_path = self.extract_json_field(
            inner_metric.c.details,
            "tool_selection",
            field_name,
        )

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
                    inner_span.c.trace_id == correlation_column,
                    inner_span.c.task_id.in_(task_ids),
                    inner_span.c.span_kind == SPAN_KIND_LLM,
                    inner_metric.c.metric_type == metric_type.value,
                    classification_condition,
                ),
            ),
        )

    def build_all_metric_exists_conditions(
        self,
        filters: TraceQuerySchema,
        correlation_column,
    ) -> List:
        """Build all metric EXISTS conditions for the given filters."""
        exists_conditions = []

        # Relevance filters
        if filters.query_relevance_filters:
            exists_conditions.append(
                self.build_relevance_exists_clause(
                    MetricType.QUERY_RELEVANCE,
                    filters.query_relevance_filters,
                    filters.task_ids,
                    correlation_column,
                ),
            )

        if filters.response_relevance_filters:
            exists_conditions.append(
                self.build_relevance_exists_clause(
                    MetricType.RESPONSE_RELEVANCE,
                    filters.response_relevance_filters,
                    filters.task_ids,
                    correlation_column,
                ),
            )

        # Tool classification filters
        if filters.tool_selection is not None:
            exists_conditions.append(
                self.build_tool_classification_exists_clause(
                    MetricType.TOOL_SELECTION,
                    filters.tool_selection,
                    filters.task_ids,
                    "tool_selection",
                    correlation_column,
                ),
            )

        if filters.tool_usage is not None:
            exists_conditions.append(
                self.build_tool_classification_exists_clause(
                    MetricType.TOOL_SELECTION,
                    filters.tool_usage,
                    filters.task_ids,
                    "tool_usage",
                    correlation_column,
                ),
            )

        return exists_conditions

    # ============================================================================
    # Span Type Filtering Logic
    # ============================================================================

    def build_single_span_type_conditions(
        self,
        span_type: str,
        filters: TraceQuerySchema,
    ) -> List:
        """Build AND conditions for a single span type."""
        conditions = []

        # Span type condition
        conditions.append(DatabaseSpan.span_kind == span_type)

        # Type-specific filters
        if span_type == SPAN_KIND_TOOL and filters.tool_name:
            conditions.append(DatabaseSpan.span_name == filters.tool_name)

        # Cross-span-type filters (apply to all span types)
        if filters.status_code:
            conditions.append(DatabaseSpan.status_code == filters.status_code)

        return conditions

    def build_multiple_span_types_or_conditions(
        self,
        span_types: List[str],
        filters: TraceQuerySchema,
    ) -> List:
        """Build OR conditions for multiple span types with their specific filters."""
        or_groups = []

        for span_type in span_types:
            # Get conditions for this specific span type
            type_conditions = self.build_single_span_type_conditions(span_type, filters)

            if type_conditions:
                # Group conditions for this span type with AND
                or_groups.append(and_(*type_conditions))

        return or_groups

    # ============================================================================
    # Metric Filtering for Span-Based Queries
    # ============================================================================

    def build_span_metric_exists_conditions(
        self,
        filters: TraceQuerySchema,
        span_id_column,
    ) -> List:
        """Build metric EXISTS conditions for span-based queries (correlation via span.id)."""
        exists_conditions = []

        # Relevance filters
        if filters.query_relevance_filters:
            exists_conditions.append(
                self._build_span_relevance_exists(
                    MetricType.QUERY_RELEVANCE,
                    filters.query_relevance_filters,
                    span_id_column,
                ),
            )

        if filters.response_relevance_filters:
            exists_conditions.append(
                self._build_span_relevance_exists(
                    MetricType.RESPONSE_RELEVANCE,
                    filters.response_relevance_filters,
                    span_id_column,
                ),
            )

        # Tool classification filters
        if filters.tool_selection is not None:
            exists_conditions.append(
                self._build_span_tool_classification_exists(
                    MetricType.TOOL_SELECTION,
                    filters.tool_selection,
                    "tool_selection",
                    span_id_column,
                ),
            )

        if filters.tool_usage is not None:
            exists_conditions.append(
                self._build_span_tool_classification_exists(
                    MetricType.TOOL_SELECTION,
                    filters.tool_usage,
                    "tool_usage",
                    span_id_column,
                ),
            )

        return exists_conditions

    def _build_span_relevance_exists(
        self,
        metric_type: MetricType,
        relevance_filters: List[FloatRangeFilter],
        span_id_column,
    ):
        """Build relevance EXISTS clause for span-based queries."""
        inner_metric = DatabaseMetricResult.__table__.alias("inner_metric")

        # Determine JSON path based on metric type
        paths = {
            MetricType.QUERY_RELEVANCE: "query_relevance",
            MetricType.RESPONSE_RELEVANCE: "response_relevance",
        }
        if metric_type not in paths:
            raise ValueError(f"Unsupported relevance metric type: {metric_type}")

        # Extract score using database-specific functions
        score_path = self.extract_json_field(
            inner_metric.c.details,
            paths[metric_type],
            "llm_relevance_score",
        )

        # Build relevance conditions
        relevance_conditions = [
            self.build_comparison_condition(func.cast(score_path, Float), f)
            for f in relevance_filters
        ]

        return exists(
            select(1)
            .select_from(inner_metric)
            .where(
                and_(
                    inner_metric.c.span_id == span_id_column,
                    inner_metric.c.metric_type == metric_type.value,
                    *relevance_conditions,
                ),
            ),
        )

    def _build_span_tool_classification_exists(
        self,
        metric_type: MetricType,
        tool_class: ToolClassEnum,
        field_name: str,
        span_id_column,
    ):
        """Build tool classification EXISTS clause for span-based queries."""
        inner_metric = DatabaseMetricResult.__table__.alias("inner_metric")

        # Extract classification using database-specific functions
        classification_path = self.extract_json_field(
            inner_metric.c.details,
            "tool_selection",
            field_name,
        )

        classification_condition = (
            func.cast(classification_path, Integer) == tool_class.value
        )

        return exists(
            select(1)
            .select_from(inner_metric)
            .where(
                and_(
                    inner_metric.c.span_id == span_id_column,
                    inner_metric.c.metric_type == metric_type.value,
                    classification_condition,
                ),
            ),
        )
