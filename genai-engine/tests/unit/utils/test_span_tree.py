"""tree_order: one order for a trace's spans, built from the flat span list."""

import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import pytest

from utils.span_tree import tree_order

T0 = datetime(2026, 11, 7, 19, 0, 0)


@dataclass
class Span:
    span_id: str
    parent_span_id: Optional[str]
    start_time: datetime


def span(span_id: str, parent: Optional[str], start: float) -> Span:
    return Span(span_id, parent, T0 + timedelta(seconds=start))


def ids(spans: list[Span]) -> list[str]:
    return [s.span_id for s in spans]


@pytest.mark.unit_tests
def test_depth_first_with_the_earliest_child_first():
    spans = [
        span("root", None, 0),
        span("b", "root", 2),
        span("a", "root", 1),
        span("a1", "a", 1.5),
    ]
    assert ids(tree_order(spans)) == ["root", "a", "a1", "b"]


@pytest.mark.unit_tests
def test_siblings_with_the_same_start_time_order_by_span_id():
    spans = [span("root", None, 0), span("y", "root", 1), span("x", "root", 1)]
    assert ids(tree_order(spans)) == ["root", "x", "y"]


@pytest.mark.unit_tests
def test_child_that_starts_before_its_parent_still_comes_after_it():
    spans = [span("child", "root", 0), span("root", None, 1)]
    assert ids(tree_order(spans)) == ["root", "child"]


@pytest.mark.unit_tests
def test_spans_in_a_parent_cycle_or_with_a_missing_parent_are_kept():
    spans = [
        span("root", None, 0),
        span("a", "b", 1),
        span("b", "a", 2),
        span("orphan", "gone", 3),
        span("self", "self", 4),
    ]
    # the cycle is entered at its earliest span; orphans and self-parents become roots
    assert ids(tree_order(spans)) == ["root", "a", "b", "orphan", "self"]


@pytest.mark.unit_tests
def test_same_order_whatever_the_row_order():
    spans = [span("root", None, 0)] + [
        span(f"s{i}", "root" if i < 5 else f"s{i - 5}", i) for i in range(10)
    ]
    expected = ids(tree_order(spans))
    for seed in range(5):
        shuffled = spans[:]
        random.Random(seed).shuffle(shuffled)
        assert ids(tree_order(shuffled)) == expected


@pytest.mark.unit_tests
def test_empty():
    assert tree_order([]) == []
