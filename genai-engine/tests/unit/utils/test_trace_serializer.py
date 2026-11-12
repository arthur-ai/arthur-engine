"""serialize_trace: one trace as judge-ready text, in tree order, within a budget."""

import json
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

import pytest

from utils.trace_serializer import (
    FORMAT_VERSION,
    MIN_MAX_CHARS,
    serialize_trace,
)

T0 = datetime(2026, 11, 7, 19, 0, 0)

SYSTEM = "You are a support agent. Use the tools to answer; remember the order id the customer gave."
TOOLS = [
    {"name": "lookup_order", "parameters": {"order_id": "string"}},
    {
        "type": "function",
        "function": {
            "name": "refund_order",
            "description": "Refund a delivered or late order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "reason": {"type": "string"},
                },
            },
        },
    },
]


@dataclass
class Span:
    span_id: str
    parent_span_id: Optional[str]
    span_kind: Optional[str]
    span_name: Optional[str]
    start_time: datetime
    end_time: datetime
    raw_data: Any
    status_code: Optional[str] = "Unset"


def span(
    span_id: str,
    parent: Optional[str],
    kind: str,
    name: str,
    start: float,
    attributes: dict[str, Any],
    status: str = "Unset",
    raw_extra: Optional[dict[str, Any]] = None,
) -> Span:
    return Span(
        span_id=span_id,
        parent_span_id=parent,
        span_kind=kind,
        span_name=name,
        start_time=T0 + timedelta(seconds=start),
        end_time=T0 + timedelta(seconds=start + 0.5),
        raw_data={"attributes": attributes, **(raw_extra or {})},
        status_code=status,
    )


def messages(
    *pairs: tuple[str, Optional[str]],
    calls: Optional[list[tuple[str, dict[str, Any]]]] = None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = [
        {"message": {"role": role, "content": content}} for role, content in pairs
    ]
    if calls:
        out.append(
            {
                "message": {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "tool_call": {
                                "function": {"name": n, "arguments": json.dumps(a)}
                            }
                        }
                        for n, a in calls
                    ],
                },
            },
        )
    return out


def support_turn(retry: bool = False) -> list[Span]:
    """Turn 2 of a support conversation: plan, tool call(s), reply."""
    history = [
        ("system", SYSTEM),
        ("user", "Hi, where is my order C3001?"),
        ("assistant", "Order C3001 was delivered late on 2026-11-05."),
        ("user", "It came late, I'd like a refund please."),
    ]
    spans = [
        span(
            "root",
            None,
            "AGENT",
            "support-agent",
            0.0,
            {
                "input": {"value": "It came late, I'd like a refund please."},
                "output": {
                    "value": "Done, a refund of $21 for order C3001 has been issued."
                },
            },
        ),
        span(
            "plan",
            "root",
            "LLM",
            "plan",
            0.1,
            {
                "llm": {
                    "model_name": "planner",
                    "tools": [{"tool": {"json_schema": json.dumps(t)}} for t in TOOLS],
                    "input_messages": messages(*history),
                    "output_messages": messages(
                        calls=[
                            ("refund_order", {"order_id": "C3001", "reason": "late"})
                        ]
                    ),
                },
            },
        ),
    ]
    results = [{"error": "upstream timeout"}] if retry else []
    results.append({"refund_id": "R0001", "amount_usd": 21, "status": "issued"})
    for i, result in enumerate(results):
        spans.append(
            span(
                f"tool{i}",
                "root",
                "TOOL",
                "refund_order",
                1.0 + i,
                {
                    "input": {
                        "value": json.dumps({"order_id": "C3001", "reason": "late"})
                    },
                    "output": {"value": json.dumps(result)},
                },
            )
        )
    spans.append(
        span(
            "respond",
            "root",
            "LLM",
            "respond",
            3.0,
            {
                "llm": {
                    "input_messages": messages(*history),
                    "output_messages": messages(
                        (
                            "assistant",
                            "Done, a refund of $21 for order C3001 has been issued.",
                        )
                    ),
                },
            },
        )
    )
    return spans


@pytest.mark.unit_tests
def test_tree_order_history_labels_and_tools_line():
    text, stats = serialize_trace(support_turn())
    lines = text.splitlines()

    assert lines[0].startswith(
        f"TRACE v{FORMAT_VERSION} spans=4 agent=1 llm=2 tool=1 errors=0"
    )
    heads = [
        line.strip().split(" ")[:3] for line in lines if line.strip().startswith("[")
    ]
    assert heads == [
        ["[1]", "AGENT", "support-agent"],
        ["[2]", "LLM", "plan"],
        ["[3]", "TOOL", "refund_order"],
        ["[4]", "LLM", "respond"],
    ]
    # earlier turns are labelled history; the latest user message is this turn's input
    assert "history.user: Hi, where is my order C3001?" in text
    assert "history.assistant: Order C3001 was delivered late on 2026-11-05." in text
    assert "in.user: It came late, I'd like a refund please." in text
    # tools: flat {name: type} params and JSON-schema properties both keep their names
    assert "tools: lookup_order(order_id)" in text
    assert "refund_order(order_id, reason): Refund a delivered or late order." in text
    assert 'out.call refund_order: {"order_id":"C3001","reason":"late"}' in text
    assert stats.truncated is False and stats.chars == len(text)


@pytest.mark.unit_tests
def test_same_bytes_whatever_the_row_order():
    spans = support_turn(retry=True)
    expected, _ = serialize_trace(spans)
    for seed in range(5):
        shuffled = spans[:]
        random.Random(seed).shuffle(shuffled)
        assert serialize_trace(shuffled)[0] == expected


@pytest.mark.unit_tests
def test_long_repeats_become_back_references():
    text, stats = serialize_trace(support_turn())
    # the system prompt and history repeat in the respond span
    assert "in.system: (same as [2] in.system)" in text
    assert stats.duplicate_chars_replaced >= len(SYSTEM)
    no_dedupe, _ = serialize_trace(support_turn(), dedupe=False)
    assert "(same as" not in no_dedupe


@pytest.mark.unit_tests
def test_planner_with_no_tool_calls_and_no_text_says_so():
    spans = [
        span(
            "root",
            None,
            "AGENT",
            "agent",
            0.0,
            {"input": {"value": "hi"}, "output": {"value": "hello"}},
        ),
        span(
            "plan",
            "root",
            "LLM",
            "plan",
            0.1,
            {
                "llm": {
                    "input_messages": messages(("user", "hi")),
                    "output_messages": [{"message": {"role": "assistant"}}],
                },
            },
        ),
    ]
    assert "out: (no tool calls, no text)" in serialize_trace(spans)[0]


@pytest.mark.unit_tests
def test_errors_show_status_message_and_exception_events():
    spans = [
        span("root", None, "AGENT", "agent", 0.0, {"input": {"value": "go"}}),
        span(
            "t",
            "root",
            "TOOL",
            "fetch",
            0.1,
            {"input": {"value": "{}"}},
            status="Error",
            raw_extra={
                "status": {"message": "connection reset"},
                "events": [
                    {
                        "name": "exception",
                        "attributes": {
                            "exception": {"type": "TimeoutError", "message": "30 s"}
                        },
                    }
                ],
            },
        ),
        span(
            "t2",
            "root",
            "TOOL",
            "fetch",
            0.2,
            {"input": {"value": "{}"}},
            status="Error",
        ),
    ]
    text, _ = serialize_trace(spans)
    assert "errors=2" in text.splitlines()[0]
    assert "[2] TOOL fetch +0.1s dur=0.5s ERROR" in text
    assert "error: connection reset | TimeoutError: 30 s" in text
    assert "error: status=Error (no message recorded)" in text


@pytest.mark.unit_tests
def test_cyclic_and_orphan_spans_are_kept_at_top_level():
    spans = [
        span("root", None, "AGENT", "agent", 0.0, {"input": {"value": "go"}}),
        span("a", "b", "TOOL", "cycle-a", 1.0, {"input": {"value": "a"}}),
        span("b", "a", "TOOL", "cycle-b", 2.0, {"input": {"value": "b"}}),
        span("o", "gone", "TOOL", "orphan", 3.0, {"input": {"value": "o"}}),
    ]
    text, stats = serialize_trace(spans)
    assert "parent_missing=1" in text and "detached_groups=1" in text
    assert "cycle-a +1.0s dur=0.5s (detached: parent link is cyclic)" in text
    assert (
        "\n  [3] TOOL cycle-b" in text
    )  # child of the detached span, indented under it
    assert "\n[4] TOOL orphan" in text
    assert (stats.orphans, stats.detached, stats.spans) == (1, 1, 4)


def big_trace(n_tools: int = 120) -> list[Span]:
    spans = [
        span(
            "root",
            None,
            "AGENT",
            "agent",
            0.0,
            {
                "input": {"value": "Summarise every file. " * 40},
                "output": {"value": "Done. " * 60},
            },
        )
    ]
    for i in range(n_tools):
        status = "Error" if i == 60 else "Unset"
        spans.append(
            span(
                f"t{i:03d}",
                "root",
                "TOOL",
                "read_file",
                1.0 + i,
                {
                    "input": {"value": json.dumps({"path": f"/repo/file_{i}.py"})},
                    "output": {"value": f"contents of file {i}: " + "x" * 3000},
                },
                status=status,
            )
        )
    return spans


@pytest.mark.unit_tests
@pytest.mark.parametrize("max_chars", [MIN_MAX_CHARS, 12_000, 48_000])
def test_never_over_budget_and_says_what_was_cut(max_chars: int):
    spans = big_trace()
    text, stats = serialize_trace(spans, max_chars=max_chars)
    assert len(text) <= max_chars
    assert stats.truncated and "[TRUNCATED view of 121 spans" in text
    assert stats.full_chars > max_chars
    assert text.startswith("TRACE v")
    if not stats.hard_cut:
        assert "[1] AGENT agent" in text  # the root is never omitted
        assert "[62] TOOL read_file" in text and "ERROR" in text  # error span kept


@pytest.mark.unit_tests
def test_budget_below_minimum_is_refused():
    with pytest.raises(ValueError):
        serialize_trace(support_turn(), max_chars=MIN_MAX_CHARS - 1)


@pytest.mark.unit_tests
def test_empty_trace():
    text, stats = serialize_trace([])
    assert text == f"TRACE v{FORMAT_VERSION} spans=0" and stats.spans == 0
