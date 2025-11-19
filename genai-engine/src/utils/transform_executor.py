"""Transform execution utilities for dataset transforms.

This module provides functionality to execute transforms against trace spans,
matching the behavior of the frontend transform executor in
genai-engine/ui/src/components/traces/components/add-to-dataset/utils/transformExecutor.ts
"""

import json
from typing import Any, Dict, List

from arthur_common.models.response_schemas import NestedSpanWithMetricsResponse

from schemas.common_schemas import NewDatasetVersionRowColumnItemRequest
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


def execute_transform(
    spans: List[NestedSpanWithMetricsResponse],
    transform_definition: Dict[str, Any],
) -> List[NewDatasetVersionRowColumnItemRequest]:
    """Execute transform on spans, returns extracted columns.

    Uses first match if multiple spans found. This matches the behavior of the
    frontend executeTransform function.

    Args:
        spans: List of spans from the trace
        transform_definition: Transform definition containing columns to extract

    Returns:
        List of column items ready to be used in NewDatasetVersionRowRequest
    """
    columns: List[NewDatasetVersionRowColumnItemRequest] = []

    # Get columns from transform definition
    transform_columns = transform_definition.get("columns", [])

    for col_def in transform_columns:
        span_name = col_def.get("span_name")
        column_name = col_def.get("column_name")
        attribute_path = col_def.get("attribute_path")
        fallback = col_def.get("fallback")

        # Find matching spans by span_name
        matching_spans = [span for span in spans if span.span_name == span_name]

        if not matching_spans:
            # No matching span found, use fallback
            columns.append(
                NewDatasetVersionRowColumnItemRequest(
                    column_name=column_name,
                    column_value=stringify_value(fallback if fallback is not None else ""),
                )
            )
        else:
            # Use the first matching span
            span = matching_spans[0]
            value = get_nested_value(span.raw_data, attribute_path)

            # Use value if found, otherwise use fallback
            if value is not None:
                column_value = stringify_value(value)
            else:
                column_value = stringify_value(fallback if fallback is not None else "")

            columns.append(
                NewDatasetVersionRowColumnItemRequest(
                    column_name=column_name,
                    column_value=column_value,
                )
            )

    return columns


def flatten_spans(span: NestedSpanWithMetricsResponse) -> List[NestedSpanWithMetricsResponse]:
    """Flatten nested span structure into a flat list.

    Args:
        span: The root span with potential children

    Returns:
        Flat list of all spans in the tree
    """
    result = [span]
    if span.children:
        for child in span.children:
            result.extend(flatten_spans(child))
    return result
