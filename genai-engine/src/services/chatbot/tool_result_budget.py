"""Keeps one tool result from filling the model's context window.

The chatbot sends each API response back to the model as a tool message. A list call
with spans can return megabytes of JSON, more than the model can read at once, and the
next model call then fails. A result over the budget is replaced by a preview that keeps
its shape (a few items, long values cut) plus a hint to narrow the request. Claude Code
and Codex cap tool output the same way, at 25,000 and 10,000 tokens.
"""

import json
from typing import Any

# About 20,000 tokens of trace JSON, which tokenizes at roughly 2.4 characters per token.
MAX_TOOL_RESULT_CHARS = 50_000

# In a preview, long values (span input and output) keep this many characters...
_PREVIEW_VALUE_CHARS = 300
# ...and lists inside the response's items (a trace's spans) keep this many entries.
_PREVIEW_NESTED_ITEMS = 5

NARROW_HINT = (
    "Narrow the request rather than asking for more of this one: use a smaller "
    "page_size (10 or less), leave include_spans off, filter by time range or name, "
    "or fetch a single item by its ID (for example GET /api/v1/traces/{trace_id})."
)


def bound_tool_result(
    status_code: int,
    body: str,
    max_chars: int = MAX_TOOL_RESULT_CHARS,
) -> str:
    """The tool message for an API response: in full when it fits, else a preview."""
    status_line = f"HTTP {status_code}\n"
    if len(status_line) + len(body) <= max_chars:
        return status_line + body
    note = (
        f"[Response truncated: the body is {len(body):,} characters, more than the "
        f"{max_chars:,} that fit. Below is a preview. {NARROW_HINT}]\n"
    )
    budget = max(max_chars - len(status_line) - len(note), 0)
    return status_line + note + _preview(body, budget)


def _preview(body: str, budget: int) -> str:
    try:
        data = json.loads(body)
    except ValueError:
        return _cut(body, budget)
    shrunk = _shrink(data)
    text = _dump(shrunk)
    if len(text) <= budget:
        return text
    return _fit_main_list(shrunk, budget) or _cut(text, budget)


def _shrink(value: Any, depth: int = 0) -> Any:
    if isinstance(value, str):
        return _cut(value, _PREVIEW_VALUE_CHARS)
    if isinstance(value, dict):
        return {key: _shrink(item, depth + 1) for key, item in value.items()}
    if isinstance(value, list):
        # The response's own list (depth 0 or 1) is fitted to the budget later;
        # lists inside its items are cut here.
        if depth > 1 and len(value) > _PREVIEW_NESTED_ITEMS:
            kept = [_shrink(item, depth + 1) for item in value[:_PREVIEW_NESTED_ITEMS]]
            return kept + [f"… {len(value) - _PREVIEW_NESTED_ITEMS} more not shown"]
        return [_shrink(item, depth + 1) for item in value]
    return value


def _fit_main_list(data: Any, budget: int) -> str | None:
    """Keep as many leading items of the response's largest list as the budget allows."""
    if isinstance(data, list):
        key, items = None, data
    elif isinstance(data, dict):
        lists = [(k, v) for k, v in data.items() if isinstance(v, list)]
        if not lists:
            return None
        key, items = max(lists, key=lambda kv: len(_dump(kv[1])))
    else:
        return None

    def render(count: int) -> str:
        kept = items[:count]
        if count < len(items):
            kept = kept + [f"… {len(items) - count} more items not shown"]
        return _dump(kept if key is None else {**data, key: kept})

    best = None
    low, high = 0, len(items)
    while low <= high:
        middle = (low + high) // 2
        text = render(middle)
        if len(text) <= budget:
            best, low = text, middle + 1
        else:
            high = middle - 1
    return best


def _cut(text: str, cap: int) -> str:
    """Keep the head and tail of text within cap characters, marking what was cut."""
    if len(text) <= cap:
        return text
    marker_chars = len(f" …[{len(text):,} chars cut]… ")
    keep = max(cap - marker_chars, 0)
    head = keep * 2 // 3
    tail = keep - head
    removed = len(text) - head - tail
    return f"{text[:head]} …[{removed:,} chars cut]… {text[len(text) - tail:]}"


def _dump(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False, default=str)
