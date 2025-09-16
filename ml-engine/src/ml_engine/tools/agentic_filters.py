from typing import Any, Optional
from arthur_client.api_bindings import DataResultFilter, DataResultFilterOp

# Constants moved from shield_connector.py
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

# OpenInference span kinds (from openinference.semconv.trace import OpenInferenceSpanKindValues)
VALID_SPAN_KINDS = [
    "TOOL", "CHAIN", "LLM", "RETRIEVER", "EMBEDDING", 
    "AGENT", "RERANKER", "UNKNOWN", "GUARDRAIL", "EVALUATOR"
]

COMPARISON_OPS = [DataResultFilterOp.EQUALS, DataResultFilterOp.GREATER_THAN,
                       DataResultFilterOp.GREATER_THAN_OR_EQUAL, DataResultFilterOp.LESS_THAN,
                       DataResultFilterOp.LESS_THAN_OR_EQUAL]

AGENTIC_COMPARISON_FILTER_FIELDS = ["query_relevance", "response_relevance", "trace_duration"]

# Supported agentic filters
AGENTIC_FILTER_SUPPORT = {
    "trace_ids": [DataResultFilterOp.EQUALS, DataResultFilterOp.IN],
    "tool_name": [DataResultFilterOp.EQUALS],
    "span_types": [DataResultFilterOp.IN, DataResultFilterOp.EQUALS],
    "query_relevance": COMPARISON_OPS,
    "response_relevance": COMPARISON_OPS,
    "trace_duration": COMPARISON_OPS,
    "tool_selection": [DataResultFilterOp.EQUALS],
    "tool_usage": [DataResultFilterOp.EQUALS],
    **{field: COMPARISON_OPS for field in AGENTIC_COMPARISON_FILTER_FIELDS},
}


def validate_filters(
    filters: list[DataResultFilter],
    is_agentic: bool = False,
) -> list[DataResultFilter]:
    """Validate filters for agentic or non-agentic datasets."""
    allowed_filters = []
    for filter in filters:
        if is_agentic:
            # For agentic datasets, validate against agentic filter support
            if filter.field_name in AGENTIC_FILTER_SUPPORT:
                _validate_agentic_filter(filter)
                allowed_filters.append(filter)
            elif filter.field_name in SHIELD_ALLOWED_FILTERS.keys():
                # Fall back to basic Shield validation for non-agentic filters
                if _validate_basic_shield_filter(filter):
                    allowed_filters.append(filter)
            # Skip unsupported filters silently - let caller handle logging
        else:
            # For non-agentic datasets, use existing validation
            if _validate_basic_shield_filter(filter):
                allowed_filters.append(filter)
    
    return allowed_filters

def _validate_basic_shield_filter(filter: DataResultFilter) -> bool:
    """Existing basic Shield filter validation."""
    if filter.field_name not in SHIELD_ALLOWED_FILTERS.keys():
        return False
    
    if not isinstance(filter.value, SHIELD_ALLOWED_FILTERS[filter.field_name]):
        return False
    
    if filter.op != DataResultFilterOp.EQUALS:
        return False
    
    return True

def add_default_sort_filter(
    filters: Optional[list[DataResultFilter]],
) -> list[DataResultFilter]:
    """Add default sort descending filter if not overridden in user-defined list of filters."""
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

def _is_agentic_filter_supported(filter: DataResultFilter) -> bool:
    """Check if filter is supported for agentic datasets."""
    field_name = filter.field_name
    op = filter.op
    
    # Check if field is supported
    if field_name not in AGENTIC_FILTER_SUPPORT:
        return False
    
    # Check if operator is supported for this field
    return op in AGENTIC_FILTER_SUPPORT[field_name]

def _validate_agentic_filter(filter: DataResultFilter) -> None:
    """Validate agentic filter - raise errors for invalid filters."""
    field_name = filter.field_name
    op = filter.op
    value = filter.value
    
    # Check field/operator support
    if not _is_agentic_filter_supported(filter):
        supported_ops = AGENTIC_FILTER_SUPPORT.get(field_name, [])
        if supported_ops:
            # Case where the field is supported, but the operator is not
            raise ValueError(
                f"Filter '{field_name}' with operator '{op}' is not supported. "
                f"Supported operators for {field_name}: {supported_ops}"
            )
        else:
            # Case where the field is not supported at all
            raise ValueError(f"Filter field '{field_name}' is not supported for agentic datasets.")
    
    # Validate values
    _validate_agentic_filter_value(field_name, value)

def _validate_list_of_strings(field_name: str, value: any, allow_single_string: bool = False) -> None:
    """Validate that a value is a list of strings, optionally allowing a single string."""
    if allow_single_string and isinstance(value, str):
        if not value.strip():
            raise ValueError(f"{field_name} cannot be empty string")
        return
    
    if not isinstance(value, list):
        if allow_single_string:
            raise ValueError(f"{field_name} must be a string or list of strings, got {type(value)}")
        else:
            raise ValueError(f"{field_name} must be a list of strings, got {type(value)}")
    
    if not all(isinstance(item, str) for item in value):
        raise ValueError(f"{field_name} must be a list of strings, got {value}")
    
    if not value:  # Empty list
        raise ValueError(f"{field_name} cannot be empty")

def _validate_agentic_filter_value(field_name: str, value: any) -> None:
    """Validate filter values with specific error messages."""
    if field_name in ["query_relevance", "response_relevance"]:
        if not isinstance(value, (int, float)) or not (0.0 <= value <= 1.0):
            raise ValueError(f"{field_name} must be a number between 0.0 and 1.0, got {value}")
    
    elif field_name == "trace_duration":
        if not isinstance(value, (int, float)) or value <= 0:
            raise ValueError(f"trace_duration must be a positive number, got {value}")
    
    elif field_name == "span_types":
        _validate_list_of_strings(field_name, value, allow_single_string=False)
        
        invalid_types = [t for t in value if t not in VALID_SPAN_KINDS]
        if invalid_types:
            raise ValueError(f"Invalid span_types: {invalid_types}. Valid values: {VALID_SPAN_KINDS}")
    
    elif field_name in ["tool_selection", "tool_usage"]:
        if value not in [0, 1, 2]:
            raise ValueError(f"{field_name} must be 0, 1, or 2, got {value}")
    
    elif field_name == "trace_ids":
        _validate_list_of_strings(field_name, value, allow_single_string=True)

def map_agentic_filter_to_parameter(filter: DataResultFilter) -> tuple[str, any]:
    """Map DataResultFilter to GenAI Engine API parameter."""
    field_name = filter.field_name
    op = filter.op
    value = filter.value
    
    # Comparison field mapping (add operator suffix)
    if field_name in ["query_relevance", "response_relevance", "trace_duration"]:
        suffix_map = {
            DataResultFilterOp.EQUALS: "_eq",
            DataResultFilterOp.GREATER_THAN: "_gt", 
            DataResultFilterOp.GREATER_THAN_OR_EQUAL: "_gte",
            DataResultFilterOp.LESS_THAN: "_lt",
            DataResultFilterOp.LESS_THAN_OR_EQUAL: "_lte"
        }
        return f"{field_name}{suffix_map[op]}", value
    
    # Direct mapping fields
    elif field_name in ["span_types", "tool_name", "tool_selection", "tool_usage", "trace_ids"]:
        return field_name, value
    
    return None, None

def build_agentic_filter_parameters(filters: list[DataResultFilter]) -> dict[str, any]:
    """Build GenAI Engine parameters from validated filters."""
    params = {}
    
    for filter in filters:
        param_name, param_value = map_agentic_filter_to_parameter(filter)
        if param_name and param_value is not None:
            params[param_name] = param_value
    
    return params