"""One order for a trace's spans, shared by transforms and the per-span eval fan-out.

Tree order: depth-first from the roots, with siblings (and roots) sorted by
(start_time, span_id). Start time alone is not enough: a child can start before its
parent, and two spans can share a start time.

The order is built from the flat span list, so it does not depend on a tree built
elsewhere. Spans whose parent is not in the trace become roots, and spans caught in
a parent cycle are promoted to roots too; no span is ever dropped.
"""

from datetime import datetime
from typing import Optional, Protocol, Sequence, TypeVar


class OrderableSpan(Protocol):
    """A span the tree order can place: API responses and DB rows both fit."""

    @property
    def span_id(self) -> str: ...

    @property
    def parent_span_id(self) -> Optional[str]: ...

    @property
    def start_time(self) -> datetime: ...


SpanT = TypeVar("SpanT", bound=OrderableSpan)


def _sibling_key(span: OrderableSpan) -> tuple[datetime, str]:
    return (span.start_time, span.span_id)


def tree_order(spans: Sequence[SpanT]) -> list[SpanT]:
    """Return the spans in tree order (see the module docstring)."""
    span_ids = {span.span_id for span in spans}
    children: dict[str, list[SpanT]] = {}
    roots: list[SpanT] = []
    for span in spans:
        parent = span.parent_span_id
        if parent is None or parent not in span_ids or parent == span.span_id:
            roots.append(span)
        else:
            children.setdefault(parent, []).append(span)
    for siblings in children.values():
        siblings.sort(key=_sibling_key)

    def subtree(root: SpanT) -> list[SpanT]:
        """root and its descendants, depth-first, earliest child first."""
        found: list[SpanT] = []
        stack = [root]
        while stack:
            span = stack.pop()
            if id(span) in seen:
                continue
            seen.add(id(span))
            found.append(span)
            # Reversed so the earliest child is popped first.
            stack.extend(reversed(children.get(span.span_id, [])))
        return found

    # Spans no root reaches sit in a parent cycle: promote the earliest unreached
    # span to a root, take its subtree, and repeat until every span is placed.
    seen: set[int] = set()
    for root in roots:
        subtree(root)
    for span in sorted(spans, key=_sibling_key):
        if id(span) not in seen:
            roots.append(span)
            subtree(span)

    seen = set()
    ordered: list[SpanT] = []
    for root in sorted(roots, key=_sibling_key):
        ordered.extend(subtree(root))
    return ordered
