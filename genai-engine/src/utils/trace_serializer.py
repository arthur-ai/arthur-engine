"""One trace as text for an LLM judge: the whole run in one prompt, within a size budget.

serialize_trace(spans, max_chars) turns a trace's spans, given as a flat list, into
indented text: one head line per span in tree order (utils.span_tree, the order every
transform uses), then that span's fields. It is a pure function of its input: the
same spans give the same bytes, whatever order the rows arrive in.

What each span shows:
- LLM: the tools the model could call (`tools:`), its input messages, its output
  messages and tool calls. Input messages before the last user message are earlier
  turns of the conversation and are labelled `history.<role>`, so a judge can tell
  context from this turn's work.
- TOOL: args and result. RETRIEVER: query and documents. Other kinds: input and output.
- Any span with an error status or exception events: the error text.
Exact repeats of a long value become `(same as [n] label)`.

When the text is over budget it is cut in a fixed order, and a footer says what was cut:
1. shorten fields, least important class first (history, tool results, LLM inputs,
   documents, tool args, LLM outputs, other input/output), each cut keeping head and tail;
2. omit span bodies from the middle of the trace outwards (error spans last, the root never);
3. collapse runs of same-named siblings whose bodies are omitted;
4. cut the span list itself, keeping head and tail.

FORMAT_VERSION changes whenever field choice, order or cutting changes, because a
stored hash of the text only proves two runs saw the same text under one version.
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Optional, Protocol, Sequence

from pydantic import BaseModel

from utils.span_tree import tree_order

FORMAT_VERSION = 1
DEFAULT_MAX_CHARS = 48_000
MIN_MAX_CHARS = 2_000

FIELD_CAP_LADDER = [2000, 1000, 500, 250, 120]  # per-field caps tried in order
PROTECTED_CAP = 4000  # root input/output, error text, tools
DEDUPE_MIN_CHARS = 80
TOOLS_FIELD_CAP = 1000
FOOTER_RESERVE = 160

# Field classes, in the order they are shortened (first to last).
(
    C_HISTORY,
    C_TOOL_RESULT,
    C_LLM_IN,
    C_DOC,
    C_TOOL_ARGS,
    C_LLM_OUT,
    C_IO,
    C_PROTECTED,
) = range(8)
N_CLASSES = 8

Field = tuple[str, Any, int]  # (label, value, field class)


class TraceSerializationStats(BaseModel):
    """What serialize_trace kept and cut."""

    spans: int
    chars: int
    full_chars: int  # size with nothing cut
    fields_shortened: int = 0
    chars_cut: int = 0
    bodies_omitted: int = 0
    hard_cut: int = 0
    collapsed: bool = False
    detached: int = 0  # placed at top level because the parent link is cyclic
    orphans: int = 0  # parent not in the trace
    duplicate_chars_replaced: int = 0
    truncated: bool = False
    format_version: int = FORMAT_VERSION


class SerializableSpan(Protocol):
    """A span the serializer can read: DB rows and API responses both fit."""

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


def _seconds(value: Any) -> float:
    if isinstance(value, datetime):
        return value.timestamp()
    if isinstance(value, (int, float)):
        return float(value)
    return datetime.fromisoformat(str(value)).timestamp()


def _unwrap(value: Any) -> Any:
    """Parse JSON-looking strings; turn a list of {text: ...} parts into its text."""
    if isinstance(value, str):
        stripped = value.strip()
        if stripped[:1] in ("[", "{"):
            try:
                return _unwrap(json.loads(stripped))
            except ValueError:
                return stripped
        return stripped
    if (
        isinstance(value, list)
        and value
        and all(isinstance(p, dict) and isinstance(p.get("text"), str) for p in value)
    ):
        return "\n".join(_text(p["text"]) for p in value)
    return value


def _text(value: Any) -> str:
    value = _unwrap(value)
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _get(data: Any, path: str) -> Any:
    for part in path.split("."):
        if not isinstance(data, dict) or part not in data:
            return None
        data = data[part]
    return data


def _cut(text: str, cap: int) -> tuple[str, int]:
    """Keep the head (two thirds) and tail of text; returns (text, chars removed)."""
    if len(text) <= cap + cap // 4:
        return text, 0
    head = (cap * 2) // 3
    tail = cap - head
    removed = len(text) - cap
    return f"{text[:head]} …[{removed:,} chars cut]… {text[-tail:]}", removed


def _message_content(message: dict[str, Any]) -> Any:
    content = message.get("content")
    if content is None and message.get("contents") is not None:
        content = message.get("contents")
    return content


def _message_fields(messages: Any, direction: str) -> list[Field]:
    field_class = C_LLM_IN if direction == "in" else C_LLM_OUT
    unwrapped = [
        (m.get("message", m) if isinstance(m, dict) else {}) for m in (messages or [])
    ]
    # Input messages before the last user message are earlier turns: context only.
    last_user = -1
    if direction == "in":
        last_user = max(
            (i for i, m in enumerate(unwrapped) if m.get("role") == "user"),
            default=-1,
        )
    fields: list[Field] = []
    for i, message in enumerate(unwrapped):
        role = message.get("role", "?")
        content = _message_content(message)
        if i < last_user and role != "system":
            if content not in (None, "", []):
                fields.append((f"history.{role}", content, C_HISTORY))
            continue
        if content not in (None, "", []):
            fields.append((f"{direction}.{role}", content, field_class))
        for tool_call in message.get("tool_calls") or []:
            tool_call = tool_call.get("tool_call", tool_call)
            function = tool_call.get("function", {})
            fields.append(
                (
                    f"{direction}.call {function.get('name', '?')}",
                    function.get("arguments"),
                    field_class,
                ),
            )
    return fields


def _tool_params(function: dict[str, Any]) -> list[str]:
    params = function.get("parameters") or function.get("input_schema") or {}
    if not isinstance(params, dict):
        return []
    if isinstance(params.get("properties"), dict):
        return sorted(params["properties"])
    if params and "type" not in params:  # a flat {name: type} map
        return sorted(params)
    return []


def _tools_field(tools: Any) -> str:
    """The tools an LLM call could use, one line each: `name(param, ...): description`.

    Names always survive: descriptions shorten first (160, 80, 0 chars), then
    parameter names go."""
    parsed = []
    for tool in tools or []:
        tool = tool.get("tool", tool) if isinstance(tool, dict) else {}
        schema = _unwrap(tool.get("json_schema", tool))
        if not isinstance(schema, dict):
            continue
        function = schema.get(
            "function", schema
        )  # nested in OpenAI's shape, flat otherwise
        name = function.get("name")
        if not name:
            continue
        description = " ".join(str(function.get("description") or "").split())
        parsed.append((str(name), _tool_params(function), description))
    if not parsed:
        return ""
    parsed.sort()
    text = ""
    for description_cap, with_params in (
        (160, True),
        (80, True),
        (0, True),
        (0, False),
    ):
        lines = []
        for name, params, description in parsed:
            line = f"{name}({', '.join(params)})" if with_params else name
            if description_cap and description:
                if len(description) > description_cap:
                    description = description[: description_cap - 1] + "…"
                line += ": " + description
            lines.append(line)
        text = "\n".join(lines)
        if len(text) <= TOOLS_FIELD_CAP:
            return text
    return _cut(text, TOOLS_FIELD_CAP)[0]


def _error_text(span: SerializableSpan) -> Optional[str]:
    raw = span.raw_data if isinstance(span.raw_data, dict) else {}
    status = raw.get("status")
    errors = []
    if isinstance(status, dict) and status.get("message"):
        errors.append(str(status["message"]))
    for event in raw.get("events") or []:
        attributes = event.get("attributes") or {}
        if event.get("name") == "exception" or "exception" in attributes:
            exception = attributes.get("exception", attributes)
            errors.append(
                f"{exception.get('type', 'exception')}: {exception.get('message', '')}".strip(),
            )
    if errors:
        return " | ".join(errors)
    if span.status_code == "Error":
        return "status=Error (no message recorded)"
    return None


def _span_fields(span: SerializableSpan, is_root: bool) -> list[Field]:
    raw = span.raw_data if isinstance(span.raw_data, dict) else {}
    attributes = raw.get("attributes") or {}
    kind = (span.span_kind or "").upper()
    fields: list[Field]
    if kind == "LLM":
        inputs = _message_fields(_get(attributes, "llm.input_messages"), "in")
        outputs = _message_fields(_get(attributes, "llm.output_messages"), "out")
        if not inputs and _get(attributes, "input.value") is not None:
            inputs = [("in", _get(attributes, "input.value"), C_LLM_IN)]
        if not outputs and _get(attributes, "llm.output_messages") is not None:
            outputs = [("out", "(no tool calls, no text)", C_PROTECTED)]
        elif not outputs and _get(attributes, "output.value") is not None:
            outputs = [("out", _get(attributes, "output.value"), C_LLM_OUT)]
        tools = _tools_field(_get(attributes, "llm.tools"))
        fields = ([("tools", tools, C_PROTECTED)] if tools else []) + inputs + outputs
    elif kind == "TOOL":
        fields = [
            ("args", _get(attributes, "input.value"), C_TOOL_ARGS),
            ("result", _get(attributes, "output.value"), C_TOOL_RESULT),
        ]
    elif kind == "RETRIEVER":
        fields = [("query", _get(attributes, "input.value"), C_IO)]
        documents = _get(attributes, "retrieval.documents") or []
        for i, document in enumerate(documents):
            document = (
                document.get("document", document) if isinstance(document, dict) else {}
            )
            fields.append((f"doc{i + 1}", document.get("content"), C_DOC))
        if not documents:
            fields.append(("result", _get(attributes, "output.value"), C_TOOL_RESULT))
    else:
        io_class = C_PROTECTED if is_root else C_IO
        fields = [
            ("input", _get(attributes, "input.value"), io_class),
            ("output", _get(attributes, "output.value"), io_class),
        ]
    error = _error_text(span)
    if error:
        fields.append(("error", error, C_PROTECTED))
    return [field for field in fields if field[1] not in (None, "", [], {})]


def _head_line(span: SerializableSpan, number: int, trace_start: float) -> str:
    raw = span.raw_data if isinstance(span.raw_data, dict) else {}
    attributes = raw.get("attributes") or {}
    start, end = _seconds(span.start_time), _seconds(span.end_time)
    kind = (span.span_kind or "SPAN").upper()
    name = span.span_name or "?"
    parts = [
        f"[{number}]",
        kind,
        name,
        f"+{start - trace_start:.1f}s",
        f"dur={end - start:.1f}s",
    ]
    if kind == "LLM":
        model = _get(attributes, "llm.model_name")
        if model and model not in name:
            parts.append(f"model={model}")
        prompt_tokens = _get(attributes, "llm.token_count.prompt")
        completion_tokens = _get(attributes, "llm.token_count.completion")
        if prompt_tokens is not None or completion_tokens is not None:
            parts.append(f"tokens_in={prompt_tokens} tokens_out={completion_tokens}")
        if _get(attributes, "llm.finish_reason"):
            parts.append(f"finish={_get(attributes, 'llm.finish_reason')}")
    if span.status_code == "Error":
        parts.append("ERROR")
    return " ".join(parts)


class _Row:
    __slots__ = (
        "number",
        "depth",
        "head",
        "fields",
        "is_error",
        "is_root",
        "signature",
    )

    def __init__(
        self,
        number: int,
        depth: int,
        head: str,
        fields: list[tuple[str, str, int]],
        is_error: bool,
        is_root: bool,
        signature: tuple[str, str],
    ) -> None:
        self.number = number
        self.depth = depth
        self.head = head
        self.fields = fields
        self.is_error = is_error
        self.is_root = is_root
        self.signature = signature


def _render(
    header: str,
    rows: list[_Row],
    caps: dict[int, int],
    bodiless: set[int],
    collapse: bool = False,
) -> tuple[str, int, int]:
    """Returns (text, fields shortened, chars cut)."""
    lines, fields_cut, chars_cut = [header], 0, 0
    i = 0
    while i < len(rows):
        row = rows[i]
        pad = "  " * row.depth
        if collapse and row.number in bodiless and not row.is_error:
            j = i
            while (
                j + 1 < len(rows)
                and rows[j + 1].number in bodiless
                and not rows[j + 1].is_error
                and rows[j + 1].depth == row.depth
                and rows[j + 1].signature == row.signature
            ):
                j += 1
            if j - i >= 2:
                kind, name = row.signature
                lines.append(
                    f"{pad}[{row.number}-{rows[j].number}] {kind} {name} x{j - i + 1} (bodies omitted)",
                )
                i = j + 1
                continue
        lines.append(pad + row.head)
        if row.number not in bodiless:
            for label, text, field_class in row.fields:
                shown, removed = _cut(text, caps[field_class])
                if removed:
                    fields_cut += 1
                    chars_cut += removed
                shown = shown.replace("\n", "\n" + pad + "    ")
                lines.append(f"{pad}  {label}: {shown}")
        i += 1
    return "\n".join(lines), fields_cut, chars_cut


def serialize_trace(
    spans: Sequence[SerializableSpan],
    max_chars: int = DEFAULT_MAX_CHARS,
    dedupe: bool = True,
) -> tuple[str, TraceSerializationStats]:
    """The trace as judge-ready text of at most max_chars, and what was cut."""
    if max_chars < MIN_MAX_CHARS:
        raise ValueError(f"max_chars must be at least {MIN_MAX_CHARS}")
    if not spans:
        text = f"TRACE v{FORMAT_VERSION} spans=0"
        return text, TraceSerializationStats(
            spans=0, chars=len(text), full_chars=len(text)
        )

    # 1. Tree order (shared with transforms). Depth follows real parent links only:
    #    a span whose parent is not in the trace, or whose parent comes after it
    #    (a cycle that tree_order broke), sits at top level.
    ordered = tree_order(spans)
    span_ids = {span.span_id for span in spans}
    position = {span.span_id: i for i, span in enumerate(ordered)}
    depth: dict[str, int] = {}
    orphans = detached = 0
    placed: list[tuple[SerializableSpan, int, bool]] = []
    for i, span in enumerate(ordered):
        parent = span.parent_span_id
        is_detached = False
        if parent is not None and parent not in span_ids:
            orphans += 1
            level = 0
        elif parent is not None and parent != span.span_id and position[parent] < i:
            level = depth[parent] + 1
        elif parent is not None:
            is_detached = True
            detached += 1
            level = 0
        else:
            level = 0
        depth[span.span_id] = level
        placed.append((span, level, is_detached))

    trace_start = min(_seconds(span.start_time) for span in spans)
    trace_end = max(_seconds(span.end_time) for span in spans)

    # 2. Fields per span, with back-references for exact repeats of long values.
    seen: dict[str, str] = {}
    rows: list[_Row] = []
    duplicate_chars = 0
    for number, (span, level, is_detached) in enumerate(placed, 1):
        is_root = span.parent_span_id is None
        fields: list[tuple[str, str, int]] = []
        for label, value, field_class in _span_fields(span, is_root=is_root):
            text = _text(value)
            if dedupe and len(text) >= DEDUPE_MIN_CHARS:
                digest = hashlib.sha256(text.encode()).hexdigest()
                if digest in seen:
                    duplicate_chars += len(text)
                    fields.append((label, f"(same as {seen[digest]})", C_PROTECTED))
                    continue
                seen[digest] = f"[{number}] {label}"
            fields.append((label, text, field_class))
        head = _head_line(span, number, trace_start)
        if is_detached:
            head += " (detached: parent link is cyclic)"
        rows.append(
            _Row(
                number=number,
                depth=level,
                head=head,
                fields=fields,
                is_error=span.status_code == "Error",
                is_root=is_root,
                signature=((span.span_kind or "SPAN").upper(), span.span_name or "?"),
            ),
        )

    kinds: dict[str, int] = {}
    for span in spans:
        kind = (span.span_kind or "SPAN").upper()
        kinds[kind] = kinds.get(kind, 0) + 1
    header = (
        f"TRACE v{FORMAT_VERSION} spans={len(spans)} "
        + " ".join(f"{kind.lower()}={count}" for kind, count in sorted(kinds.items()))
        + f" errors={sum(1 for row in rows if row.is_error)}"
        + f" duration={trace_end - trace_start:.1f}s"
        + (f" parent_missing={orphans}" if orphans else "")
        + (f" detached_groups={detached}" if detached else "")
        + "\n([n] = span number in tree order, children indented;"
        + " +Xs = start offset from trace start)"
    )

    # 3. Cut to budget, in a fixed order.
    caps = {field_class: FIELD_CAP_LADDER[0] for field_class in range(N_CLASSES)}
    caps[C_PROTECTED] = min(PROTECTED_CAP, max(200, max_chars // 4))
    full_size = len(
        _render(header, rows, {c: 10**9 for c in range(N_CLASSES)}, set())[0]
    )
    bodiless: set[int] = set()
    text, fields_cut, chars_cut = _render(header, rows, caps, bodiless)
    ladder_steps = 0
    # 3a. Step each field class down the ladder, least important class first.
    schedule = [
        (level, field_class)
        for level in range(1, len(FIELD_CAP_LADDER))
        for field_class in range(C_PROTECTED)
    ]
    while len(text) + FOOTER_RESERVE > max_chars and ladder_steps < len(schedule):
        level, field_class = schedule[ladder_steps]
        caps[field_class] = FIELD_CAP_LADDER[level]
        text, fields_cut, chars_cut = _render(header, rows, caps, bodiless)
        ladder_steps += 1
    # 3b. Omit span bodies from the middle outwards; error spans last, the root never.
    if len(text) + FOOTER_RESERVE > max_chars:
        middle = (len(rows) + 1) / 2
        droppable = [
            row.number
            for row in sorted(
                (row for row in rows if not row.is_root),
                key=lambda row: (row.is_error, abs(row.number - middle), row.number),
            )
        ]
        low, high = 1, len(droppable)
        while low < high:
            k = (low + high) // 2
            if (
                len(_render(header, rows, caps, set(droppable[:k]))[0]) + FOOTER_RESERVE
                <= max_chars
            ):
                high = k
            else:
                low = k + 1
        bodiless = set(droppable[:low])
        text, fields_cut, chars_cut = _render(header, rows, caps, bodiless)
    # 3c. Collapse runs of same-named siblings whose bodies are omitted.
    collapsed = False
    if len(text) + FOOTER_RESERVE > max_chars:
        collapsed = True
        text, fields_cut, chars_cut = _render(
            header, rows, caps, bodiless, collapse=True
        )
    # 3d. Last resort: cut the span list itself, keeping head and tail.
    hard_cut = 0
    if len(text) + FOOTER_RESERVE > max_chars:
        text, hard_cut = _cut(text, max(0, (max_chars - FOOTER_RESERVE) * 4 // 5))

    truncated = bool(fields_cut or bodiless or hard_cut)
    if truncated:
        text += (
            f"\n[TRUNCATED view of {len(spans)} spans, {full_size:,} chars in full: "
            f"{fields_cut} fields shortened, {len(bodiless)} span bodies omitted"
            + (f", {hard_cut:,} chars of span list cut" if hard_cut else "")
            + "]"
        )
    stats = TraceSerializationStats(
        spans=len(spans),
        chars=len(text),
        full_chars=full_size,
        fields_shortened=fields_cut,
        chars_cut=chars_cut,
        bodies_omitted=len(bodiless),
        hard_cut=hard_cut,
        collapsed=collapsed,
        detached=detached,
        orphans=orphans,
        duplicate_chars_replaced=duplicate_chars,
        truncated=truncated,
    )
    return text, stats
