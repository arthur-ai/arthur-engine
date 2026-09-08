"""Mine recurring span blocks, then compile one into code around its real work.

A single span replaced by a script saves one call. The prize the press release
describes — eleven steps, two doing real work — needs whole *blocks* to
collapse, which means reasoning about a subgraph rather than an I/O mapping.

The block that matters here is the commonest agent idiom there is:

    LLM(pick a tool)  ->  TOOL(do the thing)  ->  LLM(phrase the result)

The tool call is real work and is preserved. Both LLM calls are deterministic:
the first extracts arguments, the second renders a template. So the compiled
artifact is not a pure function — it is code wrapped around a retained
side-effecting call, which is also why its guard has to cover the argument
extraction rather than the whole block.
"""

import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from _common import spanmodel as sm  # noqa: E402


@dataclass
class BlockPattern:
    signature: tuple[str, ...]
    labels: tuple[str, ...]
    kinds: tuple[str, ...]
    occurrences: int
    llm_calls: int
    cost_usd: float
    latency_ms: float
    examples: list[list[dict]] = field(default_factory=list)

    @property
    def cost_per_occurrence(self) -> float:
        return self.cost_usd / self.occurrences if self.occurrences else 0.0


def mine(traces: list[dict], min_len: int = 2, max_len: int = 4,
         min_occurrences: int = 20) -> list[BlockPattern]:
    """Every contiguous sibling window, keyed by its call-site signature."""
    agg: dict[tuple, BlockPattern] = {}
    for trace in traces:
        by_parent: dict[str, list[dict]] = defaultdict(list)
        for span in sm.spans_in_start_order(trace):
            if span.get("parentSpanId"):
                by_parent[span["parentSpanId"]].append(span)
        for siblings in by_parent.values():
            for size in range(min_len, max_len + 1):
                for i in range(len(siblings) - size + 1):
                    window = siblings[i:i + size]
                    sig = tuple(sm.call_site_key(s) for s in window)
                    bp = agg.get(sig)
                    if bp is None:
                        bp = agg[sig] = BlockPattern(
                            signature=sig,
                            labels=tuple(sm.call_site_label(s) for s in window),
                            kinds=tuple(sm.span_kind(s) or "?" for s in window),
                            occurrences=0, llm_calls=0, cost_usd=0.0, latency_ms=0.0)
                    bp.occurrences += 1
                    bp.llm_calls = sum(1 for k in bp.kinds if k == "LLM")
                    bp.cost_usd += sum(sm.cost_usd(s) for s in window
                                       if sm.span_kind(s) == "LLM")
                    bp.latency_ms += sum(sm.duration_ms(s) for s in window)
                    if len(bp.examples) < 400:
                        bp.examples.append(window)
    keep = [b for b in agg.values()
            if b.occurrences >= min_occurrences and b.llm_calls >= 1]
    return sorted(keep, key=lambda b: -b.cost_usd)


def format_table(blocks: list[BlockPattern], limit: int = 8) -> str:
    lines = [f"{'block (call sites in order)':<52}{'kinds':<18}{'n':>5}{'LLM':>5}"
             f"{'cost $':>9}{'$/occ':>9}", "-" * 98]
    for b in blocks[:limit]:
        chain = " -> ".join(l[:14] for l in b.labels)
        kinds = "/".join(k[0] for k in b.kinds)
        lines.append(f"{chain[:51]:<52}{kinds:<18}{b.occurrences:>5}{b.llm_calls:>5}"
                     f"{b.cost_usd:>9.3f}{b.cost_per_occurrence:>9.5f}")
    return "\n".join(lines)


# ── compiling the dispatch -> tool -> render block ───────────────────────────

# Field transforms the render call was observed to apply. Recording *which*
# transform matched is not a nicety: inferring only the field name produces a
# template that looks right and is wrong on every value containing an
# underscore, which is precisely the failure replay is there to catch.
TRANSFORMS = {
    "identity": lambda v: str(v),
    "spaces": lambda v: str(v).replace("_", " "),
    "title": lambda v: str(v).replace("_", " ").title(),
    "upper": lambda v: str(v).upper(),
}

BLOCK_TEMPLATE = '''_ARG_RX = re.compile(r"@@PATTERN@@")
_TEMPLATE = @@TEMPLATE@@
_TOOL = @@TOOL@@
_FIELDS = @@FIELDS@@
_TRANSFORMS = {
    "identity": lambda v: str(v),
    "spaces": lambda v: str(v).replace("_", " "),
    "title": lambda v: str(v).replace("_", " ").title(),
    "upper": lambda v: str(v).upper(),
}


def guard(text):
    """Admit only inputs the argument extractor can actually read.

    The guard covers the *extraction*, not the whole block: the tool call in the
    middle is preserved, so what has to be safe is deriving its arguments.
    """
    return len(_ARG_RX.findall(text)) == 1


def block(text, call_tool):
    """Collapsed form of @@CHAIN@@.

    Two model calls become an extraction and a template render. The tool call
    between them is real work and is kept, which is why `call_tool` is injected
    rather than reimplemented.
    """
    m = _ARG_RX.search(text)
    if m is None:
        return None
    result = call_tool(_TOOL, {"order_id": m.group(1)})
    try:
        values = {k: _TRANSFORMS[t](result[k]) for k, t in _FIELDS.items()}
    except KeyError:
        return None
    return _TEMPLATE.format(**values)
'''


def infer_template(windows: list[list[dict]]) -> tuple[str, dict, str] | None:
    """Recover the render template *and* the per-field transform it applied.

    If every recorded final message is reproduced by one format string over the
    tool result's own fields, the second model call was a template render.
    """
    candidates: Counter = Counter()
    # Transform choice is voted across every window, not taken from the first
    # one that happens to parse. A value with no underscore matches `identity`
    # and `spaces` alike, so a single observation cannot distinguish them; the
    # discriminating values are the ones that must decide.
    votes: dict[str, Counter] = defaultdict(Counter)
    for window in windows:
        tool_span = next((s for s in window if sm.span_kind(s) == "TOOL"), None)
        render = [s for s in window if sm.span_kind(s) == "LLM"]
        if tool_span is None or not render:
            continue
        result = sm.get(sm.attrs(tool_span), "output.value")
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except (json.JSONDecodeError, TypeError):
                continue
        if not isinstance(result, dict):
            continue
        final = str(sm.output_payload(render[-1]) or "")
        if not final:
            continue
        tmpl = final
        # longest raw values first so a substring never masks its container
        for key in sorted(result, key=lambda k: -len(str(result[k]))):
            matched_any = False
            for tname, fn in TRANSFORMS.items():
                rendered = fn(result[key])
                if not rendered or rendered not in final:
                    continue
                votes[key][tname] += 1
                if not matched_any:
                    tmpl = tmpl.replace(rendered, "{" + key + "}")
                    matched_any = True
        if "{" in tmpl:
            candidates[tmpl] += 1

    if not candidates:
        return None
    best, n = candidates.most_common(1)[0]
    # argmax over votes; TRANSFORMS is ordered simplest-first so ties resolve to
    # `identity` rather than to an incidentally-equivalent transform
    fields = {key: max(TRANSFORMS, key=lambda t: counter.get(t, 0))
              for key, counter in votes.items() if "{" + key + "}" in best}
    note = (f"{n}/{len(windows)} recorded renders match one format string; field "
            f"transforms voted across all {len(windows)} windows")
    return best, fields, note


def compile_block(block: BlockPattern) -> dict | None:
    inferred = infer_template(block.examples)
    if inferred is None:
        return None
    template, fields, note = inferred
    tool_span = next((s for s in block.examples[0] if sm.span_kind(s) == "TOOL"), None)
    if tool_span is None:
        return None
    tool_name = sm.get(sm.attrs(tool_span), "tool.name")
    source = (BLOCK_TEMPLATE
              .replace("@@PATTERN@@", r"#(\d{3,})")
              .replace("@@TEMPLATE@@", repr(template))
              .replace("@@FIELDS@@", json.dumps(fields))
              .replace("@@TOOL@@", repr(tool_name))
              .replace("@@CHAIN@@", " -> ".join(block.labels)))
    ns: dict = {"re": re}
    exec(compile(source, "<block>", "exec"), ns)
    return {"source": source, "template": template, "fields": fields,
            "tool": tool_name, "note": note, "block_fn": ns["block"],
            "guard_fn": ns["guard"], "llm_calls_removed": block.llm_calls}


def replay_block(block: BlockPattern, compiled: dict,
                 windows: list[list[dict]]) -> dict:
    """Score the compiled block against the recorded final message."""
    admitted = correct = 0
    misses = []
    for window in windows:
        tool_span = next((s for s in window if sm.span_kind(s) == "TOOL"), None)
        render = [s for s in window if sm.span_kind(s) == "LLM"]
        if tool_span is None or not render:
            continue
        dispatch = render[0]
        text = sm.input_text(dispatch)
        if not compiled["guard_fn"](text):
            continue
        admitted += 1
        recorded_result = sm.get(sm.attrs(tool_span), "output.value")
        if isinstance(recorded_result, str):
            recorded_result = json.loads(recorded_result)
        produced = compiled["block_fn"](text, lambda _n, _a: recorded_result)
        expected = str(sm.output_payload(render[-1]) or "")
        if produced == expected:
            correct += 1
        elif len(misses) < 5:
            misses.append({"produced": produced, "expected": expected})
    n = sum(1 for w in windows
            if any(sm.span_kind(s) == "TOOL" for s in w))
    return {"windows": n, "admitted": admitted,
            "coverage": admitted / n if n else 0.0,
            "agreement": correct / admitted if admitted else 0.0,
            "misses": misses}
