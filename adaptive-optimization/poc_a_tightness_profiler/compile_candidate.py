"""Step 3 — judge proposes, replay disposes.

The judge writes a candidate fast path. Its confidence is discarded. The number
that decides promotion comes from replaying the generated function against the
recorded (input, output) pairs, scored *inside the guard*, against the model's
own self-agreement rate as the baseline.

The deliverable is a (script, guard, fallback) tuple, because that is what the
product ships. A script without a coverage predicate is not deployable.
"""

import math
import os
import sys
from collections import Counter
from dataclasses import dataclass, field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from _common import spanmodel as sm  # noqa: E402
from _common.judge import Example, Proposal  # noqa: E402

HOLDOUT_FRACTION = 0.30
MIN_COVERAGE = 0.50
Z_ONE_SIDED_95 = 1.645


def significantly_worse(p_fast: float, n_fast: int,
                        p_model: float, n_model: int) -> tuple[bool, float]:
    """One-sided two-proportion test: is the fast path *materially* less consistent?

    A bare `p_fast < p_model` inequality makes the promotion decision a coin
    flip whenever the two are within sampling error — 0.973 against 0.974 is
    noise, not evidence, and which side of the line it lands on depends on how
    many calls happened to be in the holdout. The rule that survives contact
    with real data is "reject only if significantly worse", which keeps the
    precision-first posture without manufacturing verdicts out of noise.
    """
    if n_fast == 0 or n_model == 0:
        return False, 0.0
    pooled = ((p_fast * n_fast) + (p_model * n_model)) / (n_fast + n_model)
    se = math.sqrt(max(pooled * (1 - pooled) * (1 / n_fast + 1 / n_model), 1e-12))
    z = (p_fast - p_model) / se
    return z < -Z_ONE_SIDED_95, z


@dataclass
class ReplayResult:
    label: str
    strategy: str
    n_train: int
    n_holdout: int
    coverage: float              # share of holdout the guard admits
    agreement_in_guard: float    # agreement on admitted inputs
    agreement_overall: float     # agreement if the guard were ignored
    self_agreement: float | None
    self_agreement_n: int
    z_vs_model: float
    promoted: bool
    decision_reason: str
    mismatches: list[dict] = field(default_factory=list)
    proposal: Proposal | None = field(default=None, repr=False)

    @property
    def consistency_delta(self) -> float | None:
        if self.self_agreement is None:
            return None
        return self.agreement_in_guard - self.self_agreement


def split(spans: list[dict]) -> tuple[list[dict], list[dict]]:
    """Chronological split — train on the past, replay against the future.

    A random split would leak: repeated inputs would land on both sides and the
    guard would look better than it is.
    """
    ordered = sorted(spans, key=lambda s: int(s["startTimeUnixNano"]))
    cut = int(len(ordered) * (1 - HOLDOUT_FRACTION))
    return ordered[:cut], ordered[cut:]


def to_examples(spans: list[dict]) -> list[Example]:
    return [Example(input_text=sm.canonical_input(s),
                    output=sm.canonical_output(s),
                    span_id=s["spanId"]) for s in spans]


def compile_and_replay(label: str, spans: list[dict], judge,
                       self_agreement: float | None,
                       self_agreement_n: int = 0) -> ReplayResult:
    train_spans, hold_spans = split(spans)
    train, hold = to_examples(train_spans), to_examples(hold_spans)

    proposal = judge.propose(label, train)
    if proposal.declined or proposal.fn is None:
        return ReplayResult(label, "decline", len(train), len(hold), 0.0, 0.0, 0.0,
                            self_agreement, self_agreement_n, 0.0, False,
                            f"Judge declined: {proposal.rationale}", proposal=proposal)

    admitted = correct_in = correct_all = 0
    mismatches: list[dict] = []
    for ex in hold:
        try:
            predicted = proposal.fn(ex.input_text)
            allowed = bool(proposal.guard_fn(ex.input_text)) if proposal.guard_fn else True
        except Exception as exc:                      # a crashing script is a rejected script
            mismatches.append({"input": ex.input_text[:120], "expected": ex.output,
                               "got": f"<error: {exc}>", "in_guard": True})
            admitted += 1
            continue
        hit = (predicted is not None
               and str(predicted).strip().lower() == ex.output.strip().lower())
        correct_all += int(hit)
        if allowed:
            admitted += 1
            correct_in += int(hit)
            if not hit and len(mismatches) < 12:
                mismatches.append({"input": ex.input_text[:120], "expected": ex.output,
                                   "got": str(predicted)[:80], "in_guard": True})

    coverage = admitted / len(hold) if hold else 0.0
    agree_in = correct_in / admitted if admitted else 0.0
    agree_all = correct_all / len(hold) if hold else 0.0

    # Promotion is precision-first: the fast path must not be measurably less
    # consistent than the model it replaces, over enough traffic to matter.
    worse, z = (significantly_worse(agree_in, admitted, self_agreement, self_agreement_n)
                if self_agreement is not None else (False, 0.0))
    if worse:
        promoted, why = False, (
            f"Agreement inside guard ({agree_in:.3f}) is significantly below the model's own "
            f"self-agreement ({self_agreement:.3f}), z={z:.2f}.")
    elif coverage < MIN_COVERAGE:
        promoted, why = False, (
            f"Guard admits only {coverage:.1%} of traffic (< {MIN_COVERAGE:.0%}); the "
            "remaining calls still pay full price, so the saving does not justify the risk.")
    else:
        if self_agreement is None:
            why = f"Agreement inside guard {agree_in:.3f}"
        elif agree_in >= self_agreement:
            why = (f"Agreement inside guard {agree_in:.3f} >= model self-agreement "
                   f"{self_agreement:.3f}")
        else:
            why = (f"Agreement inside guard {agree_in:.3f} is statistically indistinguishable "
                   f"from model self-agreement {self_agreement:.3f} (z={z:.2f})")
        promoted = True
        why += f", covering {coverage:.1%} of holdout traffic."

    return ReplayResult(label, proposal.strategy, len(train), len(hold), coverage,
                        agree_in, agree_all, self_agreement, self_agreement_n, z,
                        promoted, why, mismatches, proposal)


def projected_savings(result: ReplayResult, cost_per_call: float, calls: int,
                      days_in_corpus: int = 1, days_projected: int = 30,
                      sample_rate: float = 0.05) -> dict:
    """Savings must be discounted by coverage and by continued sampling.

    The guard catches unfamiliar inputs. It does not catch familiar-looking
    inputs where the script is quietly wrong, so a slice of guarded traffic
    keeps going to the model for comparison. That slice is a real cost.
    """
    scale = days_projected / days_in_corpus
    monthly_calls = calls * scale
    replaced = monthly_calls * result.coverage * (1 - sample_rate)
    gross = replaced * cost_per_call
    return {
        "monthly_calls": round(monthly_calls),
        "calls_replaced": round(replaced),
        "sampling_rate": sample_rate,
        "gross_saving_usd": round(gross, 2),
        "residual_model_spend_usd": round((monthly_calls - replaced) * cost_per_call, 2),
        "note": "Illustrative rate card; sampling keeps 5% of guarded traffic on the model.",
    }


TIGHT_MIN_COVERAGE = 0.90


def refine_verdict(result: ReplayResult) -> str:
    """Settle TIGHT vs PARTIAL from the guard's reach.

    Step 2 can only say "there is a stable answer here" (CANDIDATE). How much of
    the input space that stability covers is a property of the guard, so it is
    measured, not guessed: a call site whose guard admits nearly everything is
    tight; one whose guard has to exclude a slice is partial.
    """
    if result.strategy == "decline":
        return "LOOSE"
    if not result.promoted:
        return "REJECTED"
    return "TIGHT" if result.coverage >= TIGHT_MIN_COVERAGE else "PARTIAL"
