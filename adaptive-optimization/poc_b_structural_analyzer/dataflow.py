"""Structural analyses over a single trace. No corpus, no model, no statistics.

Each detector answers a question a compiler would ask, not a question a
statistician would: is this value ever read, is this argument derived or copied,
does this call add information, is this work repeated, is this context re-sent.

The findings are ranked by how much evidence they need before acting:

  PROVABLE   the value is never read. Deleting it is safe the way dead-code
             elimination is safe — no guard, no replay, no eval.
  LOCAL      provable within the trace, but the safe replacement still depends
             on the call site behaving this way in general, so it needs corpus
             confirmation (POC A) before it ships.
  ADVISORY   a config or caching change, not a substitution.
"""

import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from _common import spanmodel as sm  # noqa: E402

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "of", "to", "for", "in", "on",
    "and", "or", "with", "your", "you", "it", "this", "that", "at", "by", "as",
    "be", "has", "have", "will", "we", "i", "my", "our", "from", "order", "status",
}
TOKEN = re.compile(r"[a-z0-9#\.]+")


def toks(text: str) -> set[str]:
    return {t for t in TOKEN.findall((text or "").lower()) if t not in STOPWORDS}


@dataclass
class Finding:
    trace_id: str
    span_id: str
    call_site: str
    pattern: str
    confidence: str          # PROVABLE | LOCAL | ADVISORY
    saving_usd: float
    saving_ms: float
    detail: str
    evidence: dict = field(default_factory=dict)


def _serialized_downstream(trace: dict, span: dict) -> str:
    """Everything any later-starting span could have read, as one blob."""
    t_end = int(span["endTimeUnixNano"])
    parts = []
    for other in trace["spans"]:
        if other["spanId"] == span["spanId"]:
            continue
        if int(other["startTimeUnixNano"]) >= t_end - 1_000_000:   # 1ms slack
            parts.append(json.dumps(other.get("attributes", {})))
    root = next((s for s in trace["spans"] if not s.get("parentSpanId")), None)
    if root is not None and root["spanId"] != span["spanId"]:
        parts.append(json.dumps(root.get("attributes", {})))
    return " ".join(parts).lower()


def find_dead_calls(trace: dict) -> list[Finding]:
    """An LLM call whose output no later span and not the trace answer reads."""
    out = []
    for span in trace["spans"]:
        if sm.span_kind(span) != "LLM":
            continue
        payload = sm.output_payload(span)
        if isinstance(payload, dict) and payload.get("tool_calls"):
            # a tool call is "read" if a matching TOOL span actually ran
            names = {c["name"] for c in payload["tool_calls"]}
            ran = {sm.get(sm.attrs(s), "tool.name") for s in trace["spans"]
                   if sm.span_kind(s) == "TOOL"}
            if names & ran:
                continue
            detail = f"tool call {sorted(names)} was emitted but no matching TOOL span ran"
        else:
            content = str(payload or "")
            wanted = toks(content)
            if len(wanted) < 2:
                continue
            downstream = _serialized_downstream(trace, span)
            seen = sum(1 for t in wanted if t in downstream)
            if seen / len(wanted) >= 0.5:
                continue
            detail = (f"{len(wanted) - seen} of {len(wanted)} content tokens from this "
                      "output appear nowhere downstream or in the trace answer")
        out.append(Finding(
            trace["trace_id"], span["spanId"], sm.call_site_label(span),
            "dead_llm_call", "PROVABLE", sm.cost_usd(span), sm.duration_ms(span),
            detail + " — the call can be deleted outright, no fast path needed",
            {"model": sm.model_name(span), "tokens": sum(sm.tokens(span))}))
    return out


def find_verbatim_dispatch(trace: dict) -> list[Finding]:
    """Tool-call arguments lifted straight out of the input text."""
    out = []
    for span in trace["spans"]:
        if sm.span_kind(span) != "LLM":
            continue
        payload = sm.output_payload(span)
        if not (isinstance(payload, dict) and payload.get("tool_calls")):
            continue
        haystack = sm.input_text(span).lower()
        values, copied = [], []
        for call in payload["tool_calls"]:
            args = call.get("arguments")
            if not isinstance(args, dict):
                continue
            for k, v in args.items():
                if isinstance(v, (str, int, float)) and len(str(v)) >= 3:
                    values.append((k, str(v)))
                    if str(v).lower() in haystack:
                        copied.append((k, str(v)))
        if not values or len(copied) != len(values):
            continue
        out.append(Finding(
            trace["trace_id"], span["spanId"], sm.call_site_label(span),
            "verbatim_dispatch", "LOCAL", sm.cost_usd(span), sm.duration_ms(span),
            f"every argument ({', '.join(k for k, _ in copied)}) appears verbatim in the "
            "input; the model is doing string extraction, not tool selection. Tool-name "
            "determinism still needs corpus confirmation before substitution",
            {"arguments": dict(copied), "tool": payload["tool_calls"][0]["name"]}))
    return out


def find_passthrough(trace: dict) -> list[Finding]:
    """An LLM call that restates the tool result immediately before it."""
    out = []
    ordered = sm.spans_in_start_order(trace)
    for prev, span in zip(ordered, ordered[1:]):
        if sm.span_kind(span) != "LLM" or sm.span_kind(prev) != "TOOL":
            continue
        produced = toks(str(sm.output_payload(span) or ""))
        available = toks(json.dumps(sm.get(sm.attrs(prev), "output.value")))
        available |= toks(sm.input_text(span))
        if not produced:
            continue
        novel = produced - available
        if len(novel) / len(produced) > 0.15:
            continue
        out.append(Finding(
            trace["trace_id"], span["spanId"], sm.call_site_label(span),
            "passthrough_reformat", "LOCAL", sm.cost_usd(span), sm.duration_ms(span),
            f"output introduces {len(novel)} new content tokens out of {len(produced)}; "
            f"it restates `{sm.get(sm.attrs(prev), 'tool.name')}` output and can be a "
            "template render",
            {"novel_tokens": sorted(novel)[:6],
             "preceding_tool": sm.get(sm.attrs(prev), "tool.name")}))
    return out


def find_redundant_calls(trace: dict) -> list[Finding]:
    """The same call site invoked twice on identical input inside one trace."""
    seen: dict[tuple[str, str], dict] = {}
    out = []
    for span in sm.spans_in_start_order(trace):
        if sm.span_kind(span) != "LLM":
            continue
        key = (sm.call_site_key(span), sm.canonical_input(span))
        first = seen.get(key)
        if first is None:
            seen[key] = span
            continue
        out.append(Finding(
            trace["trace_id"], span["spanId"], sm.call_site_label(span),
            "redundant_call", "PROVABLE", sm.cost_usd(span), sm.duration_ms(span),
            f"identical input already sent to this call site as span "
            f"{first['spanId'][:8]} in the same trace — memoize within the trace",
            {"first_span": first["spanId"]}))
    return out


def find_rebuilt_prefix(trace: dict, min_chars: int = 400) -> list[Finding]:
    """A large prompt prefix re-sent on every call in the trace."""
    llm = [s for s in sm.spans_in_start_order(trace) if sm.span_kind(s) == "LLM"]
    if len(llm) < 2:
        return []
    groups: dict[str, list[dict]] = defaultdict(list)
    for span in llm:
        sysp = sm.system_prompt(span)
        if len(sysp) >= min_chars:
            groups[sysp[:min_chars]].append(span)
    out = []
    for prefix, spans in groups.items():
        if len(spans) < 2:
            continue
        approx_tokens = len(prefix) // 4
        repeated = len(spans) - 1
        # charge the repeat at the prompt-token rate of the model in use
        tier = sm.MODEL_TIER.get(sm.model_name(spans[0]) or "", "medium")
        rate = sm.ILLUSTRATIVE_PRICES_USD_PER_MTOK[tier]["prompt"]
        out.append(Finding(
            trace["trace_id"], spans[1]["spanId"], sm.call_site_label(spans[1]),
            "rebuilt_prefix", "ADVISORY",
            approx_tokens * repeated * rate / 1_000_000, 0.0,
            f"~{approx_tokens} tokens of identical context re-sent across "
            f"{len(spans)} calls in one trace — a caching change, not a script",
            {"calls_sharing_prefix": len(spans), "approx_prefix_tokens": approx_tokens}))
    return out


DETECTORS = {
    "dead_llm_call": find_dead_calls,
    "verbatim_dispatch": find_verbatim_dispatch,
    "passthrough_reformat": find_passthrough,
    "redundant_call": find_redundant_calls,
    "rebuilt_prefix": find_rebuilt_prefix,
}


def analyze(trace: dict) -> list[Finding]:
    found: list[Finding] = []
    for fn in DETECTORS.values():
        found.extend(fn(trace))
    return found
