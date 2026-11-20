"""Transform execution utilities for dataset transforms.

This module provides functionality to execute transforms against trace spans,
matching the behavior of the frontend transform executor in
genai-engine/ui/src/components/traces/components/add-to-dataset/utils/transformExecutor.ts

Every caller (the extraction preview, experiments, continuous evals and dataset
add) reads a trace the same way: from its flat span list, in tree order (see
utils/span_tree.py), so spans with a missing parent or in a parent cycle are read
too.
"""

import json
from datetime import datetime
from typing import Any, List, Optional, Protocol, Sequence

from arthur_common.models.common_schemas import VariableTemplateValue
from arthur_common.models.response_schemas import (
    NestedSpanWithMetricsResponse,
    TraceResponse,
)

from schemas.response_schemas import (
    TransformExtractionResponseList,
    TransformVariableSpans,
)
from schemas.transform_schemas import (
    TraceTransformDefinition,
    TransformVariableSource,
)
from utils.span_tree import tree_order
from utils.trace import get_nested_value, get_nested_value_wildcard
from utils.trace_serializer import DEFAULT_MAX_CHARS, serialize_trace


class TransformableSpan(Protocol):
    """A span a transform can read: API responses and DB rows both fit."""

    @property
    def span_id(self) -> str: ...

    @property
    def parent_span_id(self) -> Optional[str]: ...

    @property
    def span_kind(self) -> Optional[str]: ...

    @property
    def span_name(self) -> Optional[str]: ...

    @property
    def status_code(self) -> Optional[str]: ...

    @property
    def start_time(self) -> datetime: ...

    @property
    def end_time(self) -> datetime: ...

    @property
    def raw_data(self) -> Any: ...


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


def flatten_trace_spans(trace: TraceResponse) -> List[NestedSpanWithMetricsResponse]:
    """Every span of a trace tree, as a flat list."""
    flat_spans: List[NestedSpanWithMetricsResponse] = []
    for span in trace.root_spans:
        flat_spans.extend(_flatten_spans(span))
    return flat_spans


def _read_span(span: TransformableSpan, attribute_path: str) -> Any:
    if "*" in attribute_path:
        return get_nested_value_wildcard(span.raw_data, attribute_path)
    return get_nested_value(span.raw_data, attribute_path)


def _read_spans(spans: Sequence[TransformableSpan], attribute_path: str) -> Any:
    """One matching span: its value, as before. Several: every value in tree order,
    each headed by its span id so a judge can say which call it means (the first
    attempt of a retried tool call failing, the last succeeding). None when no span
    has the attribute."""
    if len(spans) == 1:
        return _read_span(spans[0], attribute_path)
    blocks = []
    for span in spans:
        value = _read_span(span, attribute_path)
        if value is not None:
            blocks.append(f"[span {span.span_id}]\n{stringify_value(value)}")
    return "\n\n".join(blocks) if blocks else None


def execute_transform_on_spans(
    spans: Sequence[TransformableSpan],
    transform_definition: TraceTransformDefinition,
) -> TransformExtractionResponseList:
    """Execute a transform on a trace's flat span list, returns raw extracted values.

    A span variable reads attribute_path from every span named span_name, in tree
    order; a whole-trace variable (source='trace') is the trace serialized as
    judge-ready text within its max_chars.

    Args:
        spans: Every span of one trace, in any order
        transform_definition: TraceTransformDefinition object containing variables to extract

    Returns:
        TransformExtractionResponseList containing list of variable names and values
    """
    ordered = tree_order(spans)

    variables = []
    missing_spans = []
    missing_variables = []
    variable_spans = []

    # Iterate through variable definitions
    for var_def in transform_definition.variables:
        variable_name = var_def.variable_name

        if var_def.source == TransformVariableSource.TRACE:
            text, _ = serialize_trace(
                ordered,
                max_chars=var_def.max_chars or DEFAULT_MAX_CHARS,
            )
            variables.append(VariableTemplateValue(name=variable_name, value=text))
            variable_spans.append(
                TransformVariableSpans(
                    variable_name=variable_name,
                    span_ids=[span.span_id for span in ordered],
                ),
            )
            continue

        span_name = var_def.span_name
        attribute_path = var_def.attribute_path
        fallback = var_def.fallback

        # Find matching spans by span_name, in tree order
        matching_spans = [span for span in ordered if span.span_name == span_name]

        is_missing = False
        value: Any
        if not matching_spans:
            # No matching span found, use fallback
            if fallback is None:
                missing_spans.append(span_name)
                value = ""
            else:
                value = fallback
        else:
            value = _read_spans(matching_spans, attribute_path)

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
        variable_spans.append(
            TransformVariableSpans(
                variable_name=variable_name,
                span_ids=[span.span_id for span in matching_spans],
            ),
        )

    return TransformExtractionResponseList(
        variables=variables,
        missing_variables=missing_variables,
        missing_spans=missing_spans,
        variable_spans=variable_spans,
    )


def execute_transform(
    trace: TraceResponse,
    transform_definition: TraceTransformDefinition,
) -> TransformExtractionResponseList:
    """Execute transform on a trace tree: execute_transform_on_spans over its spans.

    Callers that can load the flat span list should use execute_transform_on_spans,
    since the tree builder leaves out spans caught in a parent cycle.

    Args:
        trace: TraceResponse object containing root_spans
        transform_definition: TraceTransformDefinition object containing variables to extract

    Returns:
        TransformExtractionResponseList containing list of variable names and values
    """
    return execute_transform_on_spans(flatten_trace_spans(trace), transform_definition)
