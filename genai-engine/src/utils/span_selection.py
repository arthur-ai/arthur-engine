"""Which spans a span-scope continuous eval judges.

Used by the worker's fan-out and by the spend estimate for a new span-scope eval.
"""

from typing import Any, Optional, Protocol, Sequence

from schemas.common_schemas import ContinuousEvalSpanFilter
from utils.transform_executor import FilterableSpan, span_meets_condition


class SelectableSpan(FilterableSpan, Protocol):
    @property
    def span_id(self) -> str: ...

    @property
    def span_kind(self) -> Optional[str]: ...


def span_matches_filter(
    span: SelectableSpan,
    span_filter: ContinuousEvalSpanFilter,
) -> bool:
    """Name, kind and every condition, checked against this span alone."""
    if span_filter.span_name is not None and span.span_name != span_filter.span_name:
        return False
    if span_filter.span_kind is not None and span.span_kind != span_filter.span_kind:
        return False
    return all(span_meets_condition(span, c) for c in span_filter.conditions)


def select_spans(
    ordered_spans: Sequence[Any],
    span_filter: ContinuousEvalSpanFilter,
) -> list[Any]:
    """The spans to judge, in the given (tree) order."""
    return [span for span in ordered_spans if span_matches_filter(span, span_filter)]
