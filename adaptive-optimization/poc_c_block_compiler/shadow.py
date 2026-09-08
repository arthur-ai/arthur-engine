"""Shadow mode: deploy in parallel, discard the output, watch the evidence.

This is the honest answer to cold start and the mechanism behind "Arthur tells
you before your customers notice". Two independent monitors, because they see
different failures:

  coverage monitor  the guard's accept rate. Catches the input distribution
                    moving — new intake channel, new phrasing, new locale. The
                    fast path degrades safely here: rejected traffic just goes
                    to the model, so the bill rises but quality does not move.

  sampling monitor  agreement on the slice of *guarded* traffic that keeps
                    going to the model anyway. Catches the case the guard is
                    blind to by construction: input still looks familiar, but
                    the right answer changed underneath. Nothing else can see
                    this, which is why the sampling slice is a permanent cost
                    of running a fast path rather than a rollout phase.
"""

import os
import statistics
import sys
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from _common import spanmodel as sm  # noqa: E402


@dataclass
class Window:
    day: int
    phase: str
    seen: int = 0
    admitted: int = 0
    sampled: int = 0
    sampled_agree: int = 0

    @property
    def coverage(self) -> float:
        return self.admitted / self.seen if self.seen else 0.0

    @property
    def sampled_agreement(self) -> float | None:
        return self.sampled_agree / self.sampled if self.sampled else None


@dataclass
class Alert:
    day: int
    kind: str
    message: str
    action: str


class ShadowRun:
    """Rolling monitors with a baseline learned from the first `warmup` days."""

    def __init__(self, compiled, sample_rate: float = 0.20, warmup_days: int = 8,
                 coverage_drop: float = 0.15, agreement_drop: float = 0.05):
        self.compiled = compiled
        self.sample_rate = sample_rate
        self.warmup_days = warmup_days
        self.coverage_drop = coverage_drop
        self.agreement_drop = agreement_drop
        self.windows: dict[int, Window] = {}
        self.alerts: list[Alert] = []
        self.baseline_coverage: float | None = None
        self.baseline_agreement: float | None = None
        self.state = "SHADOW"
        self._rng = 0

    def _sample(self) -> bool:
        """Deterministic 1-in-k sampling so runs are reproducible."""
        self._rng += 1
        return self._rng % max(1, round(1 / self.sample_rate)) == 0

    def observe(self, day: int, phase: str, text: str, tool_result: dict,
                recorded_final: str) -> None:
        w = self.windows.setdefault(day, Window(day=day, phase=phase))
        w.seen += 1
        if not self.compiled["guard_fn"](text):
            return
        w.admitted += 1
        if self._sample():
            produced = self.compiled["block_fn"](text, lambda _n, _a: tool_result)
            w.sampled += 1
            w.sampled_agree += int(produced == recorded_final)

    def close_day(self, day: int) -> None:
        days = sorted(self.windows)
        if day < self.warmup_days:
            return
        if self.baseline_coverage is None:
            warm = [self.windows[d] for d in days if d < self.warmup_days]
            self.baseline_coverage = statistics.mean(w.coverage for w in warm)
            agrees = [w.sampled_agreement for w in warm if w.sampled_agreement is not None]
            self.baseline_agreement = statistics.mean(agrees) if agrees else None
            self.state = "PROMOTED"
            self.alerts.append(Alert(
                day, "promote",
                f"baseline established over {self.warmup_days} days: coverage "
                f"{self.baseline_coverage:.1%}, sampled agreement "
                f"{self.baseline_agreement:.1%}",
                "fast path serves guarded traffic; sampling continues at "
                f"{self.sample_rate:.0%}"))
            return

        w = self.windows[day]
        if self.baseline_coverage - w.coverage > self.coverage_drop:
            self.alerts.append(Alert(
                day, "coverage",
                f"guard coverage {w.coverage:.1%} vs baseline "
                f"{self.baseline_coverage:.1%} — the input distribution moved",
                "no quality risk: rejected traffic already falls back to the model. "
                "Savings shrink until the guard is re-fit."))
        agree = w.sampled_agreement
        if (agree is not None and self.baseline_agreement is not None
                and self.baseline_agreement - agree > self.agreement_drop):
            self.state = "DEMOTED"
            self.alerts.append(Alert(
                day, "agreement",
                f"sampled agreement {agree:.1%} vs baseline "
                f"{self.baseline_agreement:.1%} on traffic the guard still accepts — "
                "the correct answer changed, not the input",
                "DEMOTE the fast path now. The guard cannot detect this class of "
                "failure; only the sampling slice can."))

    def timeline(self) -> str:
        lines = [f"{'day':>4}{'phase':>14}{'seen':>7}{'coverage':>10}"
                 f"{'sampled':>9}{'agreement':>11}  state", "-" * 74]
        state = "SHADOW"
        for day in sorted(self.windows):
            w = self.windows[day]
            for a in self.alerts:
                if a.day == day and a.kind == "promote":
                    state = "PROMOTED"
                if a.day == day and a.kind == "agreement":
                    state = "DEMOTED"
            agree = w.sampled_agreement
            agree_s = "n/a" if agree is None else f"{agree:.1%}"
            flag = ""
            for a in self.alerts:
                if a.day == day and a.kind == "coverage":
                    flag = "  <- coverage alert"
                if a.day == day and a.kind == "agreement":
                    flag = "  <- AGREEMENT ALERT"
            lines.append(f"{day:>4}{w.phase:>14}{w.seen:>7}{w.coverage:>10.1%}"
                         f"{w.sampled:>9}{agree_s:>11}  {state}{flag}")
        return "\n".join(lines)
