"""Step 2 — measure tightness. Still no judge.

Tight means H(output | input) is low: the output is determined by the input.
Loose means it isn't.

The subtlety that matters: **marginal** output entropy is a bad filter. An
extraction call site emits a different order number every time — near-maximal
marginal entropy — while being perfectly tight. Only the *conditional* quantity
separates the two, and measuring it requires seeing the same input more than
once. Two sources for that:

  1. repeated inputs occurring naturally in production traffic
  2. deliberate resampling — replay recorded inputs through the same model

Sampling temperature is a confound here, not a signal. A tight function at
temperature 1.0 shows inflated conditional entropy without being loose, so it
gets *controlled for*, never ranked by. (And a caller who never set temperature
told us nothing about their intent, which is why absence is recorded as
absence rather than as a value.)
"""

import math
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from _common import spanmodel as sm  # noqa: E402

# A loose call site is one where the model does not agree with *itself*: there
# is no stable answer to reproduce. That is a statement about self-agreement,
# not about raw entropy, because sampling noise inflates entropy without making
# a function loose.
LOOSE_MAX_SELF_AGREEMENT = 0.75
LOOSE_MIN_COND_BITS = 0.50


def entropy_bits(counts) -> float:
    n = sum(counts.values())
    if n <= 1:
        return 0.0
    h = -sum((c / n) * math.log2(c / n) for c in counts.values() if c)
    return abs(h)   # a single-valued distribution yields -0.0


@dataclass
class Tightness:
    label: str
    n: int
    distinct_outputs: int
    marginal_bits: float
    conditional_bits: float | None      # None when unmeasurable
    cond_source: str                    # repeats | resamples | both | none
    repeat_groups: int
    self_agreement: float | None        # the model's agreement with itself
    self_agreement_n: int               # observations behind that estimate
    tight_mass: float | None            # share of repeated-input mass with zero variance
    verdict: str                        # CANDIDATE | LOOSE | DEGENERATE | UNKNOWN
    reason: str


def _conditional_from_groups(groups: dict[str, list[str]]) -> tuple[float, int]:
    """Size-weighted mean entropy of outputs within each identical-input group."""
    usable = {k: v for k, v in groups.items() if len(v) >= 2}
    if not usable:
        return 0.0, 0
    total = sum(len(v) for v in usable.values())
    weighted = sum(len(v) * entropy_bits(Counter(v)) for v in usable.values())
    return weighted / total, len(usable)


def _tight_mass(groups: dict[str, list[str]]) -> float | None:
    """Share of repeated-input mass whose outputs never varied.

    Reported as a diagnostic, not used for the verdict. A mean conditional
    entropy hides shape: uniform light noise and a clean-plus-arbitrary-tail
    mixture can average to the same number, and only the second one needs a
    guard that excludes part of the input space.
    """
    usable = {k: v for k, v in groups.items() if len(v) >= 2}
    if not usable:
        return None
    total = sum(len(v) for v in usable.values())
    pure = sum(len(v) for v in usable.values() if len(set(v)) == 1)
    return pure / total


def _agreement_from_groups(groups: dict[str, list[str]]) -> tuple[float | None, int]:
    """Returns (agreement, n observations) — the n matters as much as the rate.

    A self-agreement estimate from 16 repeated calls cannot adjudicate a
    one-in-a-thousand difference, so the sample size travels with the number.
    """
    usable = [v for v in groups.values() if len(v) >= 2]
    if not usable:
        return None, 0
    agree = sum(Counter(v).most_common(1)[0][1] / len(v) for v in usable) / len(usable)
    return agree, sum(len(v) for v in usable)


def measure(label: str, spans: list[dict], resamples: list[dict] | None) -> Tightness:
    outputs = [sm.canonical_output(s) for s in spans]
    marginal = entropy_bits(Counter(outputs))
    distinct = len(set(outputs))

    by_input: dict[str, list[str]] = defaultdict(list)
    for s in spans:
        by_input[sm.canonical_input(s)].append(sm.canonical_output(s))
    cond_repeats, n_groups = _conditional_from_groups(by_input)
    agree_repeats, n_agree_repeats = _agreement_from_groups(by_input)

    rs_groups: dict[str, list[str]] = {}
    if resamples:
        for row in resamples:
            rs_groups[row["input"].strip().lower()] = [
                str(o).strip().lower() for o in row["outputs"]]
    cond_resample, n_rs = _conditional_from_groups(rs_groups) if rs_groups else (0.0, 0)
    agree_resample, n_agree_rs = (_agreement_from_groups(rs_groups) if rs_groups
                                  else (None, 0))

    sources = []
    values = []
    if n_groups:
        sources.append("repeats")
        values.append(cond_repeats)
    if n_rs:
        sources.append("resamples")
        values.append(cond_resample)

    if not values:
        return Tightness(label, len(spans), distinct, marginal, None, "none", 0, None, 0, None,
                         "UNKNOWN",
                         "No repeated input observed and no resample fixture — conditional "
                         "entropy is unmeasurable. Resample before judging.")

    conditional = max(values)          # be pessimistic across sources
    agreements = [a for a in (agree_repeats, agree_resample) if a is not None]
    self_agreement = min(agreements) if agreements else None
    self_agreement_n = n_agree_repeats + n_agree_rs
    masses = [m for m in (_tight_mass(by_input), _tight_mass(rs_groups)) if m is not None]
    tight_mass = min(masses) if masses else None
    source = "both" if len(sources) == 2 else sources[0]

    if distinct == 1:
        verdict = "DEGENERATE"
        reason = (f"Every one of {len(spans)} calls returned the same value. The call adds no "
                  "information — a dead call for structural review, not a script candidate.")
    elif self_agreement is not None and self_agreement < LOOSE_MAX_SELF_AGREEMENT:
        verdict = "LOOSE"
        reason = (f"The model agrees with itself only {self_agreement:.1%} of the time on "
                  f"identical input (H(out|in) = {conditional:.2f} bits). There is no stable "
                  "answer to reproduce.")
    elif conditional >= LOOSE_MIN_COND_BITS:
        verdict = "LOOSE"
        reason = (f"H(out|in) = {conditional:.2f} bits: identical inputs diverge materially.")
    else:
        verdict = "CANDIDATE"
        reason = (f"H(out|in) = {conditional:.2f} bits over {n_groups} repeated-input groups "
                  f"and {n_rs} resample groups; the model self-agrees {self_agreement:.1%}. "
                  + (f"Marginal entropy is {marginal:.2f} bits, which is irrelevant — high "
                     "output cardinality is compatible with a tight function. "
                     if marginal > 3 else "")
                  + f"Tight over {tight_mass:.0%} of repeated-input mass; whether a guard can "
                    "isolate that region is settled by replay, not here.")

    return Tightness(label, len(spans), distinct, marginal, conditional, source,
                     n_groups, self_agreement, self_agreement_n, tight_mass, verdict, reason)


def format_table(rows: list[Tightness]) -> str:
    out = [
        f"{'call site':<19}{'n':>6}{'distinct':>9}{'H(out)':>8}{'H(out|in)':>11}"
        f"{'self-agree':>12}{'tight-mass':>12}{'verdict':>12}",
        "-" * 90,
    ]
    for r in rows:
        cond = "n/a" if r.conditional_bits is None else f"{r.conditional_bits:.3f}"
        agree = "n/a" if r.self_agreement is None else f"{r.self_agreement:.3f}"
        mass = "n/a" if r.tight_mass is None else f"{r.tight_mass:.3f}"
        out.append(f"{r.label[:18]:<19}{r.n:>6}{r.distinct_outputs:>9}{r.marginal_bits:>8.2f}"
                   f"{cond:>11}{agree:>12}{mass:>12}{r.verdict:>12}")
    return "\n".join(out)
