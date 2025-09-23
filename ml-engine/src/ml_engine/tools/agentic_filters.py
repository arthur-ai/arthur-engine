from datetime import datetime
from typing import Any, Dict, Optional

from arthur_client.api_bindings import DataResultFilter, DataResultFilterOp
from arthur_common.models.enums import ToolClassEnum
from arthur_common.models.request_schemas import TraceQueryRequest

# Constants for backward compatibility
SHIELD_SORT_FILTER = "sort"
SHIELD_SORT_DESC = "desc"
SHIELD_ALLOWED_FILTERS = {
    "conversation_id": str,
    "inference_id": str,
    "user_id": str,
    "rule_types": list,
    "rule_statuses": list,
    "prompt_statuses": list,
    "response_statuses": list,
    SHIELD_SORT_FILTER: str,
    "page": int,
    "page_size": int,
}


def _map_comparison_operator_to_suffix(op: DataResultFilterOp) -> Optional[str]:
    """Map DataResultFilterOp to TraceQueryRequest field suffix.

    Args:
        op: The comparison operator from DataResultFilter

    Returns:
        The corresponding suffix for TraceQueryRequest fields, or None if not supported

    Examples:
        _map_comparison_operator_to_suffix(DataResultFilterOp.GREATER_THAN) -> "_gt"
        _map_comparison_operator_to_suffix(DataResultFilterOp.LESS_THAN_OR_EQUAL) -> "_lte"
    """
    suffix_map = {
        DataResultFilterOp.EQUALS: "_eq",
        DataResultFilterOp.GREATER_THAN: "_gt",
        DataResultFilterOp.GREATER_THAN_OR_EQUAL: "_gte",
        DataResultFilterOp.LESS_THAN: "_lt",
        DataResultFilterOp.LESS_THAN_OR_EQUAL: "_lte",
    }
    return suffix_map.get(op)


def build_validated_filter_params(
    task_ids: list[str],
    filters: list[DataResultFilter],
    start_time: datetime,
    end_time: datetime,
) -> Dict[str, Any]:
    """Build and validate filter parameters, returning only the filter fields.

    Uses TraceQueryRequest for validation but returns only the filter parameters
    that should be passed to the API (excludes task_ids, start_time, end_time).
    """

    # Build filter parameters
    filter_params = {}

    # Map DataResultFilter to TraceQueryRequest fields
    for filter_item in filters:
        field_name = filter_item.field_name
        op = filter_item.op
        value = filter_item.value

        # Handle comparison operators for relevance and duration fields
        if field_name in ["query_relevance", "response_relevance", "trace_duration"]:
            suffix = _map_comparison_operator_to_suffix(op)
            if suffix:
                filter_params[f"{field_name}{suffix}"] = value

        # Handle direct mapping fields
        elif field_name in ["tool_name", "span_types", "trace_ids"]:
            if op == DataResultFilterOp.EQUALS:
                if field_name in ["trace_ids", "span_types"]:
                    filter_params[field_name] = (
                        [value] if isinstance(value, str) else value
                    )
                else:
                    filter_params[field_name] = value
            elif op == DataResultFilterOp.IN:
                filter_params[field_name] = value

        # Handle tool classification enums
        elif field_name in ["tool_selection", "tool_usage"]:
            if op == DataResultFilterOp.EQUALS:
                # Convert to ToolClassEnum if needed
                if isinstance(value, int):
                    filter_params[field_name] = ToolClassEnum(value)
                else:
                    filter_params[field_name] = value

    # Validate all parameters by creating TraceQueryRequest (this will raise ValidationError if invalid)
    TraceQueryRequest(
        task_ids=task_ids,
        start_time=start_time,
        end_time=end_time,
        **filter_params,
    )

    # Return only the filter parameters
    return filter_params


def validate_filters(
    filters: list[DataResultFilter],
    is_agentic: bool = False,
) -> list[DataResultFilter]:
    """Validate filters for agentic or non-agentic datasets."""
    if not is_agentic:
        # Keep existing non-agentic validation
        return [f for f in filters if _validate_basic_shield_filter(f)]

    # For agentic filters, validation happens through TraceQueryRequest
    return filters


def _validate_basic_shield_filter(filter_item: DataResultFilter) -> bool:
    """Basic Shield filter validation for non-agentic datasets."""
    if filter_item.field_name not in SHIELD_ALLOWED_FILTERS.keys():
        return False

    if not isinstance(
        filter_item.value,
        SHIELD_ALLOWED_FILTERS[filter_item.field_name],
    ):
        return False

    if filter_item.op != DataResultFilterOp.EQUALS:
        return False

    return True


def add_default_sort_filter(
    filters: Optional[list[DataResultFilter]],
) -> list[DataResultFilter]:
    """Add default sort descending filter if not overridden."""
    if not filters:
        filters = [
            DataResultFilter(
                field_name=SHIELD_SORT_FILTER,
                op=DataResultFilterOp.EQUALS,
                value=SHIELD_SORT_DESC,
            ),
        ]
    else:
        for data_filter in filters:
            if data_filter.field_name == SHIELD_SORT_FILTER:
                break
        else:
            filters.append(
                DataResultFilter(
                    field_name=SHIELD_SORT_FILTER,
                    op=DataResultFilterOp.EQUALS,
                    value=SHIELD_SORT_DESC,
                ),
            )
    return filters
