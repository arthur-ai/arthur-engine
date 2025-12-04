"""Transform execution utilities for dataset transforms.

This module provides functionality to execute transforms against trace spans,
matching the behavior of the frontend transform executor in
genai-engine/ui/src/components/traces/components/add-to-dataset/utils/transformExecutor.ts
"""

import json
from typing import Any, List

from arthur_common.models.response_schemas import (
    NestedSpanWithMetricsResponse,
    TraceResponse,
)

from schemas.request_schemas import TraceTransformDefinition
from schemas.response_schemas import (
    TransformExtractionResponseList,
    TransformExtractionResponseVariable,
)
from utils.trace import get_nested_value


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

    # Iterate through variable definitions
    for var_def in transform_definition.variables:
        span_name = var_def.span_name
        variable_name = var_def.variable_name
        attribute_path = var_def.attribute_path
        fallback = var_def.fallback

        # Find matching spans by span_name
        matching_spans = [span for span in flat_spans if span.span_name == span_name]

        if not matching_spans:
            # No matching span found, use fallback
            value = fallback if fallback is not None else ""
        else:
            # Use the first matching span
            span = matching_spans[0]
            value = get_nested_value(span.raw_data, attribute_path)

            # Use value if found, otherwise use fallback
            if value is None:
                value = fallback if fallback is not None else ""

        variables.append(
            TransformExtractionResponseVariable(
                variable_name=variable_name,
                value=stringify_value(value),
            ),
        )

    return TransformExtractionResponseList(variables=variables)
