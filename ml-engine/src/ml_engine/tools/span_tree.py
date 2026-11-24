# Copied from the GenAI Engine's genai-engine/src/utils/span_tree.py (arthur-engine
# commit 73b594eef). Keep the two in step until the module has a shared home.

"""One order for a trace's spans, shared by transforms and the per-span eval fan-out.

Tree order: depth-first from the roots, with siblings (and roots) sorted by
(start_time, span_id). Start time alone is not enough: a child can start before its
parent, and two spans can share a start time.

The order is built from the flat span list, so it does not depend on a tree built
elsewhere. Spans whose parent is not in the trace become roots, and one member of each
parent cycle is promoted to a root too; no span is ever dropped.
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

    def cycle_member(span: SpanT) -> SpanT:
        """The earliest span of the parent cycle above an unreached span: walking up
        from any span no root reaches always loops, and its descendants (even one
        that starts before them) stay below it."""
        path: list[SpanT] = []
        on_path: dict[str, int] = {}
        while span.span_id not in on_path:
            on_path[span.span_id] = len(path)
            path.append(span)
            span = by_id[span.parent_span_id]  # type: ignore[index]
        return min(path[on_path[span.span_id] :], key=_sibling_key)

    # Spans no root reaches sit in or under a parent cycle: promote the cycle's
    # earliest member to a root, take its subtree, and repeat until all are placed.
    by_id = {span.span_id: span for span in spans}
    seen: set[int] = set()
    for root in roots:
        subtree(root)
    for span in sorted(spans, key=_sibling_key):
        if id(span) not in seen:
            member = cycle_member(span)
            roots.append(member)
            subtree(member)

    seen = set()
    ordered: list[SpanT] = []
    for root in sorted(roots, key=_sibling_key):
        ordered.extend(subtree(root))
    return ordered
