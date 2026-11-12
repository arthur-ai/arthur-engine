"""Transform execution utilities for dataset transforms.

This module provides functionality to execute transforms against trace spans. It is
the only implementation: the UI preview calls the extraction endpoint and reads the
span ids it returns rather than matching spans itself.
"""

import json
from datetime import datetime
from typing import Any, List, Optional, Protocol, Sequence

from arthur_common.models.common_schemas import VariableTemplateValue
from arthur_common.models.response_schemas import (
    NestedSpanWithMetricsResponse,
    TraceResponse,
)

from schemas.common_schemas import ContinuousEvalTraceFilterCondition
from schemas.enums import ContinuousEvalTraceFilterOperator
from schemas.response_schemas import (
    TransformExtractionResponseList,
    TransformVariableSpans,
)
from schemas.transform_schemas import (
    TraceTransformDefinition,
    TraceTransformVariableDefinition,
    TransformSpanSelector,
)
from utils.span_tree import tree_order
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


class TransformableSpan(Protocol):
    """A span a transform can read: API responses and DB rows both fit."""

    @property
    def span_id(self) -> str: ...

    @property
    def parent_span_id(self) -> Optional[str]: ...

    @property
    def start_time(self) -> datetime: ...

    @property
    def span_name(self) -> Optional[str]: ...

    @property
    def span_kind(self) -> Optional[str]: ...

    @property
    def raw_data(self) -> Any: ...


def _read_span(span: TransformableSpan, attribute_path: str) -> Any:
    if "*" in attribute_path:
        return get_nested_value_wildcard(span.raw_data, attribute_path)
    return get_nested_value(span.raw_data, attribute_path)


def _read_all_spans(
    spans: Sequence[TransformableSpan],
    attribute_path: str,
) -> tuple[Optional[str], list[str]]:
    """Every matching span's value in the given (tree) order, each headed by its
    span id so a judge can say which call it means, and the ids that had a value.
    The value is None when no span has the attribute."""
    blocks = []
    read_ids = []
    for span in spans:
        value = _read_span(span, attribute_path)
        if value is not None:
            blocks.append(f"[span {span.span_id}]\n{stringify_value(value)}")
            read_ids.append(span.span_id)
    return ("\n\n".join(blocks) if blocks else None), read_ids


def span_matches_variable(
    span: TransformableSpan,
    var_def: TraceTransformVariableDefinition,
) -> bool:
    """A span matches on span_name, span_kind or both, whichever the variable sets."""
    if var_def.span_name is not None and span.span_name != var_def.span_name:
        return False
    if var_def.span_kind is not None and span.span_kind != var_def.span_kind:
        return False
    return True


def flatten_trace_spans(trace: TraceResponse) -> List[NestedSpanWithMetricsResponse]:
    flat_spans: List[NestedSpanWithMetricsResponse] = []
    for span in trace.root_spans:
        flat_spans.extend(_flatten_spans(span))
    return flat_spans


def execute_transform(
    trace: TraceResponse,
    transform_definition: TraceTransformDefinition,
) -> TransformExtractionResponseList:
    """Execute transform on a trace, returns raw extracted values.

    Base extraction function that returns raw variable names and values without
    formatting them into specific structures. See execute_transform_on_spans.

    Args:
        trace: TraceResponse object containing root_spans
        transform_definition: TraceTransformDefinition object containing variables to extract

    Returns:
        TransformExtractionResponseList containing list of variable names and values
    """
    return execute_transform_on_spans(flatten_trace_spans(trace), transform_definition)


def execute_transform_on_spans(
    spans: Sequence[TransformableSpan],
    transform_definition: TraceTransformDefinition,
) -> TransformExtractionResponseList:
    """Execute a transform over a trace's spans given as a flat list.

    Spans are put in tree order first (utils.span_tree), the one order every
    span_selector uses: 'first' and 'last' are its two ends, 'all' reads every
    match in it. The response names the spans each value was read from, so the UI
    preview shows the same spans the worker judges.
    """
    ordered_spans = tree_order(spans)

    variables = []
    missing_spans: list[str] = []
    missing_variables = []
    variable_spans = []

    # Iterate through variable definitions
    for var_def in transform_definition.variables:
        variable_name = var_def.variable_name
        attribute_path = var_def.attribute_path
        fallback = var_def.fallback

        matching_spans = [
            span for span in ordered_spans if span_matches_variable(span, var_def)
        ]

        is_missing = False
        read_ids: list[str] = []
        value: Any
        if not matching_spans:
            # No matching span found, use fallback
            if fallback is None:
                described = var_def.describe_spans()
                if described not in missing_spans:
                    missing_spans.append(described)
                value = ""
            else:
                value = fallback
        else:
            selector = var_def.span_selector
            if selector == TransformSpanSelector.ALL:
                value, read_ids = _read_all_spans(matching_spans, attribute_path)
            else:
                span = (
                    matching_spans[-1]
                    if selector == TransformSpanSelector.LAST
                    else matching_spans[0]
                )
                value = _read_span(span, attribute_path)
                if value is not None:
                    read_ids = [span.span_id]

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
            TransformVariableSpans(variable_name=variable_name, span_ids=read_ids),
        )

    return TransformExtractionResponseList(
        variables=variables,
        missing_variables=missing_variables,
        missing_spans=missing_spans,
        variable_spans=variable_spans,
    )


def _filter_value_string(value: Any) -> str:
    # JSON booleans compare as "true"/"false", the way they appear in the span.
    if isinstance(value, bool):
        return "true" if value else "false"
    return stringify_value(value)


class FilterableSpan(Protocol):
    """A span the trace filter can read: API responses and DB rows both fit."""

    @property
    def span_name(self) -> Optional[str]: ...

    @property
    def raw_data(self) -> Any: ...


def _trace_filter_condition_holds(
    flat_spans: Sequence[FilterableSpan],
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

    return spans_match_filter(flatten_trace_spans(trace), trace_filter)


def spans_match_filter(
    spans: Sequence[FilterableSpan],
    trace_filter: Optional[List[ContinuousEvalTraceFilterCondition]],
) -> bool:
    """trace_matches_filter over a trace's spans given as a flat list."""
    if not trace_filter:
        return True
    return all(
        _trace_filter_condition_holds(spans, condition) for condition in trace_filter
    )
