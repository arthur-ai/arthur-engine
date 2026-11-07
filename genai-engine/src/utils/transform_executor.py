"""Transform execution utilities for dataset transforms.

This module provides functionality to execute transforms against trace spans,
matching the behavior of the frontend transform executor in
genai-engine/ui/src/components/traces/components/add-to-dataset/utils/transformExecutor.ts
"""

import json
from typing import Any, List, Optional

from arthur_common.models.common_schemas import VariableTemplateValue
from arthur_common.models.response_schemas import (
    NestedSpanWithMetricsResponse,
    TraceResponse,
)
from arthur_common.models.task_eval_schemas import TraceTransformDefinition

from schemas.common_schemas import ContinuousEvalTraceFilterCondition
from schemas.enums import ContinuousEvalTraceFilterOperator
from schemas.response_schemas import (
    TransformExtractionResponseList,
)
from utils.trace import get_nested_value, get_nested_value_wildcard


def stringify_value(value: Any) -> str:
    """Convert value to string: primitives as-is, objects/arrays via JSON.stringify.

    Args:
        value: The value to convert to string

    Returns:
        String representation of the value
    """
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)

    try:
        return json.dumps(value)
    except Exception:
        return str(value)


def _flatten_spans(
    span: NestedSpanWithMetricsResponse,
) -> List[NestedSpanWithMetricsResponse]:
    """Flatten nested span structure into a flat list.

    Args:
        span: The root span with potential children

    Returns:
        Flat list of all spans in the tree
    """
    result = [span]
    if span.children:
        for child in span.children:
            result.extend(_flatten_spans(child))
    return result


def execute_transform(
    trace: TraceResponse,
    transform_definition: TraceTransformDefinition,
) -> TransformExtractionResponseList:
    """Execute transform on a trace, returns raw extracted values.

    Base extraction function that returns raw variable names and values without
    formatting them into specific structures.

    Uses first match if multiple spans found. This matches the behavior of the
    frontend executeTransform function.

    Args:
        trace: TraceResponse object containing root_spans
        transform_definition: TraceTransformDefinition object containing variables to extract

    Returns:
        TransformExtractionResponseList containing list of variable names and values
    """
    # Flatten the nested span structure into a flat list
    flat_spans: List[NestedSpanWithMetricsResponse] = []
    for span in trace.root_spans:
        flat_spans.extend(_flatten_spans(span))

    variables = []
    missing_spans = []
    missing_variables = []

    # Iterate through variable definitions
    for var_def in transform_definition.variables:
        span_name = var_def.span_name
        variable_name = var_def.variable_name
        attribute_path = var_def.attribute_path
        fallback = var_def.fallback

        # Find matching spans by span_name
        matching_spans = [span for span in flat_spans if span.span_name == span_name]

        is_missing = False
        if not matching_spans:
            # No matching span found, use fallback
            if fallback is None:
                missing_spans.append(span_name)
                value = ""
            else:
                value = fallback
        else:
            # Use the first matching span
            span = matching_spans[0]
            if "*" in attribute_path:
                value = get_nested_value_wildcard(span.raw_data, attribute_path)
            else:
                value = get_nested_value(span.raw_data, attribute_path)

            # Use value if found, otherwise use fallback
            if value is None:
                value = fallback if fallback is not None else ""
                if fallback is None:
                    is_missing = True

        if is_missing:
            missing_variables.append(variable_name)

        variables.append(
            VariableTemplateValue(
                name=variable_name,
                value=stringify_value(value),
            ),
        )

    return TransformExtractionResponseList(
        variables=variables,
        missing_variables=missing_variables,
        missing_spans=missing_spans,
    )


def _filter_value_string(value: Any) -> str:
    # JSON booleans compare as "true"/"false", the way they appear in the span.
    if isinstance(value, bool):
        return "true" if value else "false"
    return stringify_value(value)


def _trace_filter_condition_holds(
    flat_spans: List[NestedSpanWithMetricsResponse],
    condition: ContinuousEvalTraceFilterCondition,
) -> bool:
    spans = [
        span
        for span in flat_spans
        if condition.span_name is None or span.span_name == condition.span_name
    ]
    found: List[str] = []
    for span in spans:
        if "*" in condition.attribute_path:
            # A wildcard path collects one value per matched item; each is compared
            # on its own, so "contains" on a list means "any item contains".
            matches = get_nested_value_wildcard(span.raw_data, condition.attribute_path)
            values = matches if isinstance(matches, list) else [matches]
        else:
            values = [get_nested_value(span.raw_data, condition.attribute_path)]
        found.extend(_filter_value_string(v) for v in values if v is not None)

    match condition.operator:
        case ContinuousEvalTraceFilterOperator.EXISTS:
            return len(found) > 0
        case ContinuousEvalTraceFilterOperator.EQUALS:
            return condition.value in found
        case ContinuousEvalTraceFilterOperator.NOT_EQUALS:
            # A span without the attribute doesn't hold the value, so it counts as
            # not equal: "plan != paid" keeps traces that never set a plan.
            return condition.value not in found
        case ContinuousEvalTraceFilterOperator.CONTAINS:
            return any(str(condition.value) in value for value in found)
    raise ValueError(f"Unknown trace filter operator: {condition.operator}")


def trace_matches_filter(
    trace: TraceResponse,
    trace_filter: Optional[List[ContinuousEvalTraceFilterCondition]],
) -> bool:
    """Check a trace against a continuous eval's trace filter.

    Every condition must hold. Over the checked spans (only spans named `span_name`,
    when set): `equals`, `contains` and `exists` hold when any value at
    `attribute_path` meets them; `not_equals` holds when no value equals it, so a
    trace without the attribute counts as not equal. Paths resolve against each
    span's raw data, the same as transforms; a wildcard path compares each matched
    item.

    Args:
        trace: TraceResponse object containing root_spans
        trace_filter: The conditions, or None/empty for no filter

    Returns:
        True when the trace should be judged
    """
    if not trace_filter:
        return True

    flat_spans: List[NestedSpanWithMetricsResponse] = []
    for span in trace.root_spans:
        flat_spans.extend(_flatten_spans(span))

    return all(
        _trace_filter_condition_holds(flat_spans, condition)
        for condition in trace_filter
    )
