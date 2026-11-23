"""serialize_trace: one trace as judge-ready text, in tree order, within a budget."""

import json
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

import pytest

from utils import trace_serializer
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
                                "function": {"name": n, "arguments": json.dumps(a)},
                            },
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
                    "value": "Done, a refund of $21 for order C3001 has been issued.",
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
                            ("refund_order", {"order_id": "C3001", "reason": "late"}),
                        ],
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
                        "value": json.dumps({"order_id": "C3001", "reason": "late"}),
                    },
                    "output": {"value": json.dumps(result)},
                },
            ),
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
                        ),
                    ),
                },
            },
        ),
    )
    return spans


@pytest.mark.unit_tests
def test_tree_order_history_labels_and_tools_line():
    text, stats = serialize_trace(support_turn())
    lines = text.splitlines()

    assert lines[0].startswith(
        f"TRACE v{FORMAT_VERSION} spans=4 agent=1 llm=2 tool=1 errors=0",
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
                            "exception": {"type": "TimeoutError", "message": "30 s"},
                        },
                    },
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
        ),
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
            ),
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


@pytest.mark.unit_tests
def test_tool_calls_in_earlier_turns_are_kept_as_history():
    history = messages(("user", "Find order C3001."))
    history.append(
        {
            "message": {
                "role": "assistant",
                "tool_calls": [
                    {
                        "tool_call": {
                            "function": {
                                "name": "lookup_order",
                                "arguments": '{"order_id": "C3001"}',
                            },
                        },
                    },
                ],
            },
        },
    )
    history += messages(("user", "Refund it."))
    spans = [
        span("root", None, "AGENT", "agent", 0.0, {"input": {"value": "Refund it."}}),
        span(
            "plan",
            "root",
            "LLM",
            "plan",
            0.1,
            {"llm": {"input_messages": history}},
        ),
    ]
    text, _ = serialize_trace(spans)
    assert 'history.call lookup_order: {"order_id":"C3001"}' in text
    assert "in.user: Refund it." in text


@pytest.mark.unit_tests
def test_a_long_tool_list_is_cut_at_the_budget_stage_and_reported():
    tools = [{"name": f"tool_number_{i:03d}"} for i in range(150)]
    spans = [
        span("root", None, "AGENT", "agent", 0.0, {"input": {"value": "go"}}),
        span(
            "plan",
            "root",
            "LLM",
            "plan",
            0.1,
            {
                "llm": {
                    "tools": [{"tool": {"json_schema": json.dumps(t)}} for t in tools],
                    "input_messages": messages(("user", "go")),
                },
            },
        ),
    ]
    text, stats = serialize_trace(spans, max_chars=MIN_MAX_CHARS)
    assert len(text) <= MIN_MAX_CHARS
    assert stats.truncated and stats.fields_shortened >= 1
    assert "[TRUNCATED view of 2 spans" in text
    assert stats.full_chars > len("\n".join(t["name"] for t in tools))


@pytest.mark.unit_tests
def test_a_repeat_shows_its_value_when_the_target_body_is_left_out():
    """The long value first appears in a middle span, whose body is left out first;
    the last span repeats it and must show it, not point at a missing body."""
    shared = "the shared report text " * 20
    spans = [
        span(
            "root",
            None,
            "AGENT",
            "agent",
            0.0,
            {"input": {"value": "go"}, "output": {"value": "done"}},
        ),
    ]
    for i in range(30):
        output = shared if i in (14, 29) else f"file {i}: " + "x" * 900
        spans.append(
            span(
                f"t{i}",
                "root",
                "TOOL",
                "read",
                1.0 + i,
                {"input": {"value": f"{i}"}, "output": {"value": output}},
            ),
        )
    full, _ = serialize_trace(spans)
    assert "result: (same as [16] result)" in full  # t29 points at t14
    omitted_any = False
    for max_chars in (MIN_MAX_CHARS, 2500, 3000, 3500):
        text, stats = serialize_trace(spans, max_chars=max_chars)
        omitted_any = omitted_any or stats.bodies_omitted > 0
        # every reference left in the text resolves: its target's body is shown, or a
        # "(value of [n] ...)" copy of the value appears above it
        lines = text.splitlines()
        for at, line in enumerate(lines):
            if "(same as [" not in line:
                continue
            target = line.split("(same as [")[1].split("]")[0]
            head = next(
                i for i, h in enumerate(lines) if h.strip().startswith(f"[{target}] ")
            )
            body_shown = (
                lines[head + 1]
                .strip()
                .startswith(
                    ("args:", "result:", "input:", "output:"),
                )
            )
            copy_above = any(f"(value of [{target}] " in l for l in lines[:at])
            assert body_shown or copy_above, (max_chars, target)
    assert omitted_any


@pytest.mark.unit_tests
def test_an_exception_on_an_unset_status_counts_as_an_error():
    spans = [
        span("root", None, "AGENT", "agent", 0.0, {"input": {"value": "go"}}),
        span(
            "t",
            "root",
            "TOOL",
            "fetch",
            0.1,
            {"input": {"value": "{}"}},
            raw_extra={
                "events": [
                    {
                        "name": "exception",
                        "attributes": {
                            "exception": {"type": "TimeoutError", "message": "30 s"},
                        },
                    },
                ],
            },
        ),
    ]
    text, _ = serialize_trace(spans)
    assert "errors=1" in text.splitlines()[0]
    assert "[2] TOOL fetch +0.1s dur=0.5s ERROR" in text


@pytest.mark.unit_tests
def test_leaving_out_a_body_never_makes_the_text_longer(monkeypatch):
    """A middle tool's long result repeats in a later span's (protected) error text.
    Leaving out the tool's body moves the value to the repeat without growing the
    text, so the omission search picks the smallest number of bodies that fits."""
    shared = "shared report " + "z" * 900
    spans = [
        span(
            "root",
            None,
            "AGENT",
            "agent",
            0.0,
            {"input": {"value": "go"}, "output": {"value": "done"}},
        ),
    ]
    for i in range(14):
        output = shared if i == 7 else f"file {i} " + "x" * 900
        spans.append(
            span(
                f"t{i}",
                "root",
                "TOOL",
                "read",
                1.0 + i,
                {"input": {"value": str(i)}, "output": {"value": output}},
            ),
        )
    spans.append(
        span(
            "err",
            "root",
            "TOOL",
            "send",
            100.0,
            {"input": {"value": "x"}},
            status="Error",
            raw_extra={"status": {"message": shared}},
        ),
    )

    assert_smallest_omission(spans, (2000, 3050, 3500), monkeypatch)


def assert_smallest_omission(spans, budgets, monkeypatch) -> None:
    """Brute force: leaving out more bodies never makes the text longer, and
    serialize_trace leaves out the smallest number of bodies that fits."""
    captured: dict = {}
    real_render = trace_serializer._render

    def spy(header, rows, caps, bodiless, collapse=False, expand_references=False):
        if not collapse and not expand_references:
            captured["args"] = (header, rows, dict(caps))
        return real_render(header, rows, caps, bodiless, collapse, expand_references)

    for max_chars in budgets:
        monkeypatch.setattr(trace_serializer, "_render", spy)
        _, stats = serialize_trace(spans, max_chars=max_chars)
        monkeypatch.setattr(trace_serializer, "_render", real_render)
        header, rows, caps = captured["args"]
        middle = (len(rows) + 1) / 2
        droppable = [
            row.number
            for row in sorted(
                (row for row in rows if not row.is_root),
                key=lambda row: (row.is_error, abs(row.number - middle), row.number),
            )
        ]
        sizes = [
            len(real_render(header, rows, caps, set(droppable[:k]))[0])
            for k in range(len(droppable) + 1)
        ]
        assert all(b <= a for a, b in zip(sizes, sizes[1:])), (max_chars, sizes)
        smallest = next(
            k
            for k, size in enumerate(sizes)
            if size + trace_serializer.FOOTER_RESERVE <= max_chars
        )
        assert stats.bodies_omitted == smallest, (max_chars, smallest)


@pytest.mark.unit_tests
def test_many_repeats_under_a_long_label_never_grow_the_text(monkeypatch):
    """A tool result repeats as the arguments of 12 later tool calls with a long
    function name. References keep naming the first field, so leaving out its body
    moves the value to one tagged copy and no reference gets longer."""
    shared = "shared report " + "z" * 900
    long_fn = "lookup_customer_order_history_with_full_audit_trail_and_metadata"
    spans = [
        span(
            "root",
            None,
            "AGENT",
            "agent",
            0.0,
            {"input": {"value": "go"}, "output": {"value": "done"}},
        ),
    ]
    for i in range(14):
        output = shared if i == 7 else f"file {i} " + "x" * 900
        spans.append(
            span(
                f"t{i}",
                "root",
                "TOOL",
                "read",
                1.0 + i,
                {"input": {"value": str(i)}, "output": {"value": output}},
            ),
        )
    call = {
        "message": {
            "role": "assistant",
            "tool_calls": [
                {"tool_call": {"function": {"name": long_fn, "arguments": shared}}},
            ],
        },
    }
    for j in range(12):
        spans.append(
            span(
                f"llm{j}",
                "root",
                "LLM",
                "plan",
                50.0 + j,
                {"llm": {"output_messages": [call]}},
            ),
        )
    assert_smallest_omission(spans, (2000, 4000, 6000, 8000), monkeypatch)


@pytest.mark.unit_tests
def test_a_multiline_value_moved_to_a_deeper_repeat_never_grows_the_text(monkeypatch):
    """A multi-line tool result repeats as the args of a TOOL span four levels deep.
    The moved copy keeps a fixed indent, so the extra depth cannot make it longer."""
    shared = "a\n" * 100 + "z"
    spans = [
        span(
            "root",
            None,
            "AGENT",
            "agent",
            0.0,
            {"input": {"value": "go"}, "output": {"value": "done"}},
        ),
    ]
    for i in range(14):
        output = shared if i == 7 else f"file {i} " + "x" * 900
        spans.append(
            span(
                f"t{i}",
                "root",
                "TOOL",
                "read",
                1.0 + i,
                {"input": {"value": str(i)}, "output": {"value": output}},
            ),
        )
    spans += [
        span("c1", "root", "CHAIN", "step", 60.0, {}),
        span("c2", "c1", "CHAIN", "step", 61.0, {}),
        span("c3", "c2", "CHAIN", "step", 62.0, {}),
        span("deep", "c3", "TOOL", "send", 63.0, {"input": {"value": shared}}),
    ]
    assert_smallest_omission(spans, (2000, 3000, 4000, 6000), monkeypatch)
