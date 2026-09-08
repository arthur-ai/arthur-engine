"""Step 1 — profile arithmetically. No model calls.

You would never profile a program by asking an LLM to read every instruction.
Same here: aggregate by call site, rank by cumulative cost, and only hand the
top few to a judge. Every input to this ranking is already a column on `spans`
or derivable from the span attributes.
"""

import os
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from _common import spanmodel as sm  # noqa: E402


@dataclass
class CallSiteProfile:
    key: str
    label: str
    model: str
    temperature: float | None
    temperature_specified: bool
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    durations: list[float] = field(default_factory=list)
    span_ids: list[str] = field(default_factory=list)

    @property
    def cost_per_call(self) -> float:
        return self.cost_usd / self.calls if self.calls else 0.0

    @property
    def p50_ms(self) -> float:
        return statistics.median(self.durations) if self.durations else 0.0

    @property
    def p95_ms(self) -> float:
        if not self.durations:
            return 0.0
        s = sorted(self.durations)
        return s[min(len(s) - 1, int(0.95 * len(s)))]

    @property
    def total_ms(self) -> float:
        return sum(self.durations)


def profile_corpus(traces: list[dict]) -> list[CallSiteProfile]:
    profiles: dict[str, CallSiteProfile] = {}
    for _tr, span in sm.iter_llm_spans(traces):
        key = sm.call_site_key(span)
        p = profiles.get(key)
        if p is None:
            temp = sm.temperature(span)
            p = profiles[key] = CallSiteProfile(
                key=key,
                label=sm.call_site_label(span),
                model=sm.model_name(span) or "?",
                temperature=temp,
                temperature_specified=temp is not None,
            )
        ptok, ctok = sm.tokens(span)
        p.calls += 1
        p.prompt_tokens += ptok
        p.completion_tokens += ctok
        p.cost_usd += sm.cost_usd(span)
        p.durations.append(sm.duration_ms(span))
        p.span_ids.append(span["spanId"])
    return sorted(profiles.values(), key=lambda p: -p.cost_usd)


def format_table(profiles: list[CallSiteProfile], total_cost: float) -> str:
    lines = [
        f"{'call site':<19}{'model':<16}{'calls':>7}{'cost $':>9}{'%':>6}"
        f"{'$/call':>10}{'p50ms':>8}{'p95ms':>8}{'temp':>7}",
        "-" * 96,
    ]
    for p in profiles:
        share = 100 * p.cost_usd / total_cost if total_cost else 0
        temp = "unset" if not p.temperature_specified else f"{p.temperature:g}"
        lines.append(
            f"{p.label[:18]:<19}{p.model:<16}{p.calls:>7}{p.cost_usd:>9.3f}{share:>6.1f}"
            f"{p.cost_per_call:>10.5f}{p.p50_ms:>8.0f}{p.p95_ms:>8.0f}{temp:>7}")
    return "\n".join(lines)


def hot_spots(profiles: list[CallSiteProfile], top_n: int = 5,
              max_sites: int = 12) -> list[tuple[CallSiteProfile, list[str]]]:
    """Union of the top call sites by cost, by cumulative latency, and by volume.

    Cost alone is the wrong lens: the press release promises lower bills *and*
    faster responses *and* consistency. A cheap call site made 400 times a day
    on the critical path is a latency and consistency target even when it
    rounds to zero dollars, and ranking on spend alone never surfaces it.
    """
    rankings = {
        "cost": sorted(profiles, key=lambda p: -p.cost_usd)[:top_n],
        "latency": sorted(profiles, key=lambda p: -p.total_ms)[:top_n],
        "volume": sorted(profiles, key=lambda p: -p.calls)[:top_n],
    }
    reasons: dict[str, list[str]] = {}
    for why, group in rankings.items():
        for p in group:
            reasons.setdefault(p.key, []).append(why)
    picked = [p for p in profiles if p.key in reasons][:max_sites]
    return [(p, reasons[p.key]) for p in picked]
