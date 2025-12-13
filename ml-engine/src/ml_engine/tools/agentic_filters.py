import logging
from typing import Any, Dict, Optional

from arthur_client.api_bindings import DataResultFilter, DataResultFilterOp
from arthur_common.models.enums import ToolClassEnum
from genai_client.models import AgenticAnnotationType, ContinuousEvalRunStatus

logger = logging.getLogger(__name__)

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

# Supported agentic filter fields
# Note: task_ids is NOT supported as a filter field because the task_id
# is specified via the dataset locator and passed directly to the API.
# Users cannot override or filter by additional task IDs.
AGENTIC_SUPPORTED_FIELDS = {
    "query_relevance",
    "response_relevance",
    "trace_duration",
    "tool_name",
    "span_types",
    "trace_ids",
    "span_ids",
    "session_ids",
    "user_ids",
    "span_name",
    "span_name_contains",
    "annotation_score",
    "annotation_type",
    "continuous_eval_run_status",
    "continuous_eval_name",
    "tool_selection",
    "tool_usage",
}


def _map_comparison_operator_to_suffix(op: DataResultFilterOp) -> Optional[str]:
    """Map DataResultFilterOp to TracesApi filter field suffix.

    Args:
        op: The comparison operator from DataResultFilter

    Returns:
        The corresponding suffix for TracesApi filter fields, or None if not supported

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


def build_and_validate_agentic_filter_params(
    filters: list[DataResultFilter],
) -> Dict[str, Any]:
    """Build filter parameters for the list_traces_metadata API.

    Converts DataResultFilter objects to the format expected by the TracesApi
    list_traces_metadata endpoint. The API itself will handle validation.
    """

    # Build filter parameters
    filter_params = {}

    # Check for unsupported fields and warn once
    unsupported_fields = {
        f.field_name for f in filters if f.field_name not in AGENTIC_SUPPORTED_FIELDS
    }
    if unsupported_fields:
        logger.warning(
            f"Ignoring unsupported agentic filters: {', '.join(sorted(unsupported_fields))}",
        )

    # Map DataResultFilter to TracesApi filter parameters
    for filter_item in filters:
        field_name = filter_item.field_name
        op = filter_item.op
        value = filter_item.value

        # Handle comparison operators for relevance and duration fields
        if field_name in ["query_relevance", "response_relevance", "trace_duration"]:
            suffix = _map_comparison_operator_to_suffix(op)
            if suffix:
                filter_params[f"{field_name}{suffix}"] = value

        # Handle list-based fields (support both EQUALS with list value and IN operator)
        elif field_name in ["trace_ids", "span_ids", "session_ids", "user_ids", "span_types"]:
            if op == DataResultFilterOp.EQUALS:
                filter_params[field_name] = (
                    [value] if isinstance(value, str) else value
                )
            elif op == DataResultFilterOp.IN:
                filter_params[field_name] = value

        # Handle string fields
        elif field_name in ["tool_name", "span_name", "span_name_contains", "continuous_eval_name"]:
            if op == DataResultFilterOp.EQUALS:
                filter_params[field_name] = value

        # Handle integer fields
        elif field_name == "annotation_score":
            if op == DataResultFilterOp.EQUALS:
                filter_params[field_name] = int(value)

        # Handle enum fields
        elif field_name == "annotation_type":
            if op == DataResultFilterOp.EQUALS:
                # Convert to AgenticAnnotationType if needed
                if isinstance(value, str):
                    filter_params[field_name] = AgenticAnnotationType(value)
                else:
                    filter_params[field_name] = value

        elif field_name == "continuous_eval_run_status":
            if op == DataResultFilterOp.EQUALS:
                # Convert to ContinuousEvalRunStatus if needed
                if isinstance(value, str):
                    filter_params[field_name] = ContinuousEvalRunStatus(value)
                else:
                    filter_params[field_name] = value

        # Handle tool classification enums
        elif field_name in ["tool_selection", "tool_usage"]:
            if op == DataResultFilterOp.EQUALS:
                # Convert to ToolClassEnum if needed
                if isinstance(value, int):
                    filter_params[field_name] = ToolClassEnum(value)
                else:
                    filter_params[field_name] = value

    # Return the filter parameters (API will handle validation)
    return filter_params


def validate_filters(
    filters: list[DataResultFilter],
    is_agentic: bool = False,
) -> list[DataResultFilter]:
    """Validate filters for agentic or non-agentic datasets."""
    if not is_agentic:
        # Keep existing non-agentic validation
        valid_filters = []
        invalid_fields = set()

        for f in filters:
            if _validate_basic_shield_filter(f):
                valid_filters.append(f)
            else:
                invalid_fields.add(f.field_name)

        if invalid_fields:
            logger.warning(
                f"Ignoring invalid Shield filters: {', '.join(sorted(invalid_fields))}",
            )

        return valid_filters

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
