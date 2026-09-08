"""Read/query helpers over spans in the engine's `arthur_span_v1` shape.

Every POC consumes the same span dicts the GenAI Engine stores in
DatabaseSpan.raw_data: nested OpenInference attributes, flat span list per
trace, tree rebuilt from parentSpanId.
"""

import hashlib
import json
import re
from typing import Any, Iterable, Optional

# Illustrative per-million-token prices for the POCs only. NOT authoritative
# pricing — swap in the customer's real rate card before quoting savings.
ILLUSTRATIVE_PRICES_USD_PER_MTOK = {
    "small":  {"prompt": 0.15, "completion": 0.60},
    "medium": {"prompt": 2.50, "completion": 10.00},
    "large":  {"prompt": 15.00, "completion": 75.00},
}
MODEL_TIER = {
    "gpt-4o-mini": "small",
    "claude-haiku-4-5": "small",
    "gpt-4o": "medium",
    "claude-sonnet-5": "medium",
    "claude-opus-5": "large",
}


def get(obj: Any, dotted: str, default: Any = None) -> Any:
    """Fetch a dotted path out of a nested dict, tolerating missing levels."""
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return default
    return cur


def attrs(span: dict) -> dict:
    return span.get("attributes", {}) or {}


def span_kind(span: dict) -> Optional[str]:
    return get(attrs(span), "openinference.span.kind")


def duration_ms(span: dict) -> float:
    return (int(span["endTimeUnixNano"]) - int(span["startTimeUnixNano"])) / 1e6


def model_name(span: dict) -> Optional[str]:
    return get(attrs(span), "llm.model_name")


def tokens(span: dict) -> tuple[int, int]:
    a = attrs(span)
    return (get(a, "llm.token_count.prompt", 0) or 0,
            get(a, "llm.token_count.completion", 0) or 0)


def cost_usd(span: dict) -> float:
    """Cost of one LLM span from the illustrative rate card."""
    tier = MODEL_TIER.get(model_name(span) or "", "medium")
    p = ILLUSTRATIVE_PRICES_USD_PER_MTOK[tier]
    ptok, ctok = tokens(span)
    return (ptok * p["prompt"] + ctok * p["completion"]) / 1_000_000


def temperature(span: dict) -> Optional[float]:
    """Temperature as *sent*. None means the caller never passed one.

    Absence is more informative than the value: it means no decision was made.
    """
    return get(attrs(span), "llm.invocation_parameters.temperature")


def messages(span: dict, direction: str = "input") -> list[dict]:
    raw = get(attrs(span), f"llm.{direction}_messages", []) or []
    out = []
    for item in raw:
        m = item.get("message", {}) if isinstance(item, dict) else {}
        out.append(m)
    return out


def system_prompt(span: dict) -> str:
    """The invariant prefix — every leading system message, concatenated."""
    parts = []
    for m in messages(span, "input"):
        if m.get("role") == "system":
            parts.append(m.get("content", ""))
        else:
            break
    return "\n".join(parts)


_NUM = re.compile(r"\d+")


def call_site_key(span: dict) -> str:
    """Identity of the *code location* that produced this span.

    span_name is useless on its own — every OpenAI span is "ChatCompletion".
    The stable identity is the invariant prompt prefix, plus graph.node.id when
    the framework sets one. Digits in the system prompt are masked so an
    embedded date or ID doesn't split one call site into thousands.
    """
    a = attrs(span)
    sys_norm = _NUM.sub("#", system_prompt(span).strip().lower())
    parts = [
        span_kind(span) or "",
        get(a, "graph.node.id") or "",
        get(a, "tool.name") or "",
        sys_norm,
    ]
    digest = hashlib.sha1("\x1f".join(parts).encode()).hexdigest()[:12]
    return digest


def call_site_label(span: dict) -> str:
    """Human-readable name for a call site, for reports."""
    a = attrs(span)
    node = get(a, "graph.node.id")
    if node:
        return node
    tool = get(a, "tool.name")
    if tool:
        return f"tool:{tool}"
    sysp = system_prompt(span).strip().splitlines()
    head = sysp[0] if sysp else (span.get("name") or "?")
    return head[:58]


# ── the variable part of a call: what a replacement script would receive ──────

def input_payload(span: dict) -> dict:
    """Everything that varies between invocations of the same call site."""
    non_system = [m for m in messages(span, "input") if m.get("role") != "system"]
    payload = {"messages": non_system}
    tmpl_vars = get(attrs(span), "llm.prompt_template.variables")
    if tmpl_vars:
        payload["variables"] = tmpl_vars
    return payload


def input_text(span: dict) -> str:
    """Flattened user-side text — the practical input to a synthesized script."""
    return "\n".join(
        m.get("content", "") or ""
        for m in messages(span, "input")
        if m.get("role") != "system"
    ).strip()


def output_payload(span: dict) -> Any:
    """Canonical output: a tool call if there is one, else the text."""
    for m in messages(span, "output"):
        calls = m.get("tool_calls") or []
        if calls:
            norm = []
            for c in calls:
                tc = c.get("tool_call", {}) if isinstance(c, dict) else {}
                args = get(tc, "function.arguments")
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except (json.JSONDecodeError, TypeError):
                        pass
                norm.append({"name": get(tc, "function.name"), "arguments": args})
            return {"tool_calls": norm}
        if "content" in m:
            return m["content"]
    return get(attrs(span), "output.value")


def canonical_output(span: dict) -> str:
    """Stable string form of the output, for equality and entropy work.

    Canonicalization is doing real work here: it strips formatting jitter
    (case, whitespace, key order, JSON-vs-dict) that would otherwise read as
    non-determinism.
    """
    val = output_payload(span)
    if isinstance(val, (dict, list)):
        return json.dumps(val, sort_keys=True, separators=(",", ":"))
    return re.sub(r"\s+", " ", str(val)).strip().lower()


def canonical_input(span: dict) -> str:
    return re.sub(r"\s+", " ", input_text(span)).strip().lower()


# ── trace / corpus loading ────────────────────────────────────────────────────

def load_corpus(path: str) -> list[dict]:
    with open(path) as fh:
        return json.load(fh)


def iter_llm_spans(traces: Iterable[dict]):
    for tr in traces:
        for s in tr["spans"]:
            if span_kind(s) == "LLM":
                yield tr, s


def children_of(trace: dict, span_id: str) -> list[dict]:
    return [s for s in trace["spans"] if s.get("parentSpanId") == span_id]


def by_id(trace: dict) -> dict[str, dict]:
    return {s["spanId"]: s for s in trace["spans"]}


def spans_in_start_order(trace: dict) -> list[dict]:
    return sorted(trace["spans"], key=lambda s: int(s["startTimeUnixNano"]))
