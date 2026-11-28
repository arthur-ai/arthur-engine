import json

import pytest

from services.chatbot.tool_result_budget import (
    MAX_TOOL_RESULT_CHARS,
    NARROW_HINT,
    bound_tool_result,
)


def _traces_body(traces: int, spans: int, content_chars: int) -> str:
    """A GET /traces?include_spans=true body shaped like the one that overflowed."""
    return json.dumps(
        {
            "count": 1547,
            "traces": [
                {
                    "trace_id": f"trace-{t}",
                    "input_content": "q" * content_chars,
                    "spans": [
                        {
                            "span_id": f"span-{t}-{s}",
                            "span_name": "llm_call",
                            "output_content": "a" * content_chars,
                        }
                        for s in range(spans)
                    ],
                }
                for t in range(traces)
            ],
        },
    )


def _preview(content: str) -> str:
    """The preview part of a truncated result: after the status line and the note."""
    return content.split("\n", 2)[2]


@pytest.mark.unit_tests
def test_result_that_fits_is_unchanged():
    assert bound_tool_result(200, '{"items": []}') == 'HTTP 200\n{"items": []}'


@pytest.mark.unit_tests
def test_oversized_json_becomes_a_bounded_valid_preview():
    body = _traces_body(traces=50, spans=15, content_chars=8_000)
    assert len(body) > 6_000_000

    content = bound_tool_result(200, body)

    assert len(content) <= MAX_TOOL_RESULT_CHARS
    assert content.startswith("HTTP 200\n[Response truncated: the body is ")
    assert NARROW_HINT in content
    preview = json.loads(_preview(content))
    # Top-level fields survive, and the list says how many items were left out
    assert preview["count"] == 1547
    shown = [t for t in preview["traces"] if isinstance(t, dict)]
    assert 0 < len(shown) < 50
    assert preview["traces"][-1] == f"… {50 - len(shown)} more items not shown"
    # A trace's spans are cut to a few, and long values to a head and tail
    first = shown[0]
    assert first["trace_id"] == "trace-0"
    assert first["spans"][-1] == "… 10 more not shown"
    assert "chars cut]" in first["input_content"]
    assert len(first["input_content"]) <= 300


@pytest.mark.unit_tests
def test_oversized_text_keeps_head_and_tail():
    body = "start-" + "x" * 200_000 + "-end"

    content = bound_tool_result(500, body)

    assert len(content) <= MAX_TOOL_RESULT_CHARS
    assert content.startswith("HTTP 500\n")
    preview = _preview(content)
    assert preview.startswith("start-")
    assert preview.endswith("-end")
    assert "chars cut]" in preview
