"""The "judge proposes" half of judge-proposes-replay-disposes.

Two interchangeable implementations behind one interface:

  OfflineSynthesizer  — deterministic program synthesis over the observed
                        (input, output) pairs. Default, no network, no key.
  ModelJudge          — hands the same examples to a Claude model and asks it
                        to write the function. Used when ANTHROPIC_API_KEY is
                        set and `--judge model` is passed.

Both return the same Proposal, and *neither is trusted*: the score that decides
promotion comes from replay against recorded outputs, never from the judge's
own confidence. Swapping implementations must not change the verdict machinery.
"""

import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Callable, Optional

MODEL_JUDGE_DEFAULT = "claude-sonnet-5"


@dataclass
class Example:
    input_text: str
    output: str          # canonical output
    span_id: str


@dataclass
class Proposal:
    """A candidate fast path: the script, when it applies, and what it replaces."""
    strategy: str                       # keyword_rules | extraction | constant | decline
    source: str                         # the generated Python
    guard_source: str                   # the coverage predicate
    rationale: str
    declined: bool = False
    fn: Optional[Callable[[str], Optional[str]]] = field(default=None, repr=False)
    guard_fn: Optional[Callable[[str], bool]] = field(default=None, repr=False)


# ── helpers ───────────────────────────────────────────────────────────────────

WORD = re.compile(r"[a-z0-9_#]+")


def tokenize(text: str) -> list[str]:
    return WORD.findall(text.lower())


def observed_self_agreement(examples: list[Example]) -> float | None:
    """Agreement rate among repeated identical inputs, from the examples alone."""
    by_input = defaultdict(list)
    for e in examples:
        by_input[e.input_text].append(e.output)
    groups = [v for v in by_input.values() if len(v) >= 2]
    if not groups:
        return None
    return sum(Counter(v).most_common(1)[0][1] / len(v) for v in groups) / len(groups)


def purity_threshold(examples: list[Example]) -> tuple[float, str]:
    """Calibrate the keyword-purity bar to the call site's own noise floor.

    A fixed cutoff is wrong in both directions. At a call site whose model
    self-agrees 99% of the time, a genuinely perfect keyword can still show
    93% observed purity because a couple of sampled labels flipped — and a hard
    0.95 bar discards it, starving that label and collapsing guard coverage.
    Conversely, at a noisy call site a 0.95 bar is too generous.

    Loosening this is safe precisely because the judge's output is not trusted:
    an over-eager keyword shows up as reduced agreement during replay, and the
    promotion gate rejects it there.
    """
    agree = observed_self_agreement(examples)
    if agree is None:
        return 0.95, "no repeated inputs; defaulting to 0.95"
    thresh = max(0.70, min(0.95, agree - 0.06))
    return thresh, f"calibrated to observed self-agreement {agree:.3f} (bar {thresh:.3f})"


def compile_proposal(prop: Proposal) -> Proposal:
    """Exec the generated source and bind the callables.

    The POC execs generated code in a bare namespace. A production version must
    not: it would ship the source to the customer for review, or run it in a
    sandbox with no imports, no filesystem and a wall-clock budget.
    """
    ns: dict = {"re": re}
    exec(compile(prop.source + "\n" + prop.guard_source, "<proposal>", "exec"), ns)
    prop.fn = ns.get("fast_path")
    prop.guard_fn = ns.get("guard")
    return prop



# ── generated-source templates ────────────────────────────────────────────────
# Kept as module-level, already-dedented strings: interpolating a multi-line
# JSON table into an indented triple-quoted block silently breaks dedent.

EXTRACT_TEMPLATE = '''_RX = re.compile(r"@@PATTERN@@", re.IGNORECASE)


def fast_path(text):
    """Extract the identifier the model was being asked to echo back."""
    m = _RX.search(text)
    return m.group(1).lower() if m else None
'''

EXTRACT_GUARD = '''

def guard(text):
    """Apply only when exactly one candidate identifier is present."""
    return len(_RX.findall(text)) == 1
'''

RULES_TEMPLATE = '''_RULES = @@TABLE@@
_FALLBACK = @@FALLBACK@@


def fast_path(text):
    """Score the input against per-label keyword sets."""
    toks = set(re.findall(r"[a-z0-9_#]+", text.lower()))
    best, best_hits = None, 0
    for label, keywords in _RULES.items():
        hits = len(toks & set(keywords))
        if hits > best_hits:
            best, best_hits = label, hits
    return best if best_hits else _FALLBACK
'''

RULES_GUARD = '''

def guard(text):
    """Apply only when at least one known keyword is present.

    Inputs carrying no recognised keyword are exactly the unfamiliar ones the
    fallback exists for, so rejecting them is correct behaviour, not a miss.
    """
    toks = set(re.findall(r"[a-z0-9_#]+", text.lower()))
    return any(toks & set(kw) for kw in _RULES.values())
'''


# ── offline synthesizer ───────────────────────────────────────────────────────

class OfflineSynthesizer:
    """Deterministic stand-in for an LLM judge.

    It writes real, readable Python for the three shapes that actually recur in
    agent traces, and declines otherwise. It exists so the POC's measurement
    machinery can be exercised with no API dependency; the interface is
    identical to ModelJudge so the comparison is apples-to-apples.
    """

    name = "offline-synthesizer"

    def propose(self, label: str, examples: list[Example]) -> Proposal:
        outputs = Counter(e.output for e in examples)

        if len(outputs) == 1:
            only = next(iter(outputs))
            return compile_proposal(Proposal(
                strategy="constant",
                source=f"def fast_path(text):\n    return {only!r}\n",
                guard_source="def guard(text):\n    return True\n",
                rationale=(f"All {len(examples)} observed outputs are identical ({only!r}). "
                           "A constant call site is a dead call, not a script candidate — "
                           "escalate to structural review rather than substituting."),
            ))

        extraction = self._try_extraction(examples)
        if extraction:
            return extraction

        rules = self._try_keyword_rules(examples, outputs)
        if rules:
            return rules

        return Proposal(
            strategy="decline", source="", guard_source="", declined=True,
            rationale=(f"{len(outputs)} distinct outputs over {len(examples)} calls with no "
                       "extractable span and no separating keyword. Output is not a tight "
                       "function of the input at this call site."),
        )

    # output appears verbatim inside the input -> write an extractor
    def _try_extraction(self, examples: list[Example]) -> Optional[Proposal]:
        hits = [e for e in examples if e.output and e.output in e.input_text.lower()]
        if len(hits) < max(8, int(0.85 * len(examples))):
            return None

        patterns = [
            (r"#(\d{3,})", "order-style #NNNN"),
            (r"\b([A-Z]{2,4}-\d{3,})\b", "ticket-style ABC-123"),
            (r"\b(\d{4,})\b", "bare digit run"),
        ]
        for pat, desc in patterns:
            rx = re.compile(pat, re.IGNORECASE)
            ok = sum(1 for e in examples
                     if (m := rx.search(e.input_text)) and m.group(1).lower() == e.output)
            if ok >= 0.9 * len(examples):
                src = EXTRACT_TEMPLATE.replace("@@PATTERN@@", pat)
                guard = EXTRACT_GUARD
                return compile_proposal(Proposal(
                    strategy="extraction", source=src, guard_source=guard,
                    rationale=(f"Output is a verbatim substring of the input in "
                               f"{len(hits)}/{len(examples)} calls, matching {desc}. "
                               "This is extraction, not judgment."),
                ))
        return None

    # small output space with separating keywords -> write a rule table
    def _try_keyword_rules(self, examples: list[Example], outputs: Counter) -> Optional[Proposal]:
        if len(outputs) > 12:
            return None

        # how sharply does each token predict a single label?
        tok_label = defaultdict(Counter)
        tok_total = Counter()
        for e in examples:
            for t in set(tokenize(e.input_text)):
                tok_label[t][e.output] += 1
                tok_total[t] += 1

        min_support = max(4, int(0.01 * len(examples)))
        bar, bar_note = purity_threshold(examples)
        pure_by_label: dict[str, list[str]] = defaultdict(list)
        for tok, labels in tok_label.items():
            if tok_total[tok] < min_support or len(tok) <= 2:
                continue
            label, n = labels.most_common(1)[0]
            if n / tok_total[tok] >= bar:
                pure_by_label[label].append(tok)

        # Greedy set cover per label, not a global purity ranking.
        #
        # Ranking every candidate token by purity and truncating starves whole
        # labels: a label whose vocabulary is merely less frequent loses its
        # keywords entirely, and the guard then rejects 100% of that label's
        # traffic. Covering each label's own training inputs keeps the guard's
        # reach proportional to the input space instead of to token frequency.
        by_label: dict[str, list[str]] = {}
        uncovered_report: dict[str, int] = {}
        for label in outputs:
            targets = [e for e in examples if e.output == label]
            candidates = set(pure_by_label.get(label, []))
            chosen: list[str] = []
            remaining = [set(tokenize(e.input_text)) for e in targets]
            while candidates and remaining and len(chosen) < 24:
                best_tok, best_gain = None, 0
                for tok in candidates:
                    gain = sum(1 for toks in remaining if tok in toks)
                    if gain > best_gain:
                        best_tok, best_gain = tok, gain
                if not best_tok or best_gain == 0:
                    break
                chosen.append(best_tok)
                candidates.discard(best_tok)
                remaining = [toks for toks in remaining if best_tok not in toks]
            if chosen:
                by_label[label] = chosen
            uncovered_report[label] = len(remaining)

        if len(by_label) < 2:
            return None

        fallback = outputs.most_common(1)[0][0]
        table = json.dumps(by_label, indent=4)
        src = (RULES_TEMPLATE
               .replace("@@TABLE@@", table)
               .replace("@@FALLBACK@@", repr(fallback)))
        guard = RULES_GUARD

        starved = [lbl for lbl in outputs if lbl not in by_label]
        n_kw = sum(len(v) for v in by_label.values())
        rationale = (f"{len(outputs)} distinct outputs; {n_kw} tokens predict a single label, "
                     f"chosen by greedy cover over {len(by_label)} labels. Purity bar "
                     f"{bar_note}.")
        if starved:
            rationale += (f" No separating token found for {starved} — the guard will reject "
                          "that traffic to the model, which is correct but caps coverage.")
        left = {k: v for k, v in uncovered_report.items() if v}
        if left:
            rationale += f" Training inputs left uncovered per label: {left}."
        return compile_proposal(Proposal(
            strategy="keyword_rules", source=src, guard_source=guard, rationale=rationale))


# ── real model judge ──────────────────────────────────────────────────────────

PROMPT = """You are optimizing an AI agent. Below are recorded (input, output) pairs from a \
single LLM call site named "{label}".

Write a Python function `fast_path(text) -> str | None` that reproduces the outputs \
deterministically, and a function `guard(text) -> bool` that returns True only for inputs \
your function is likely to handle correctly.

Rules:
- stdlib only; `re` is already imported.
- No network, no file access, no imports of your own.
- If the output is NOT a tight function of the input, return exactly: DECLINE
- Prefer being narrow. A guard that rejects unfamiliar input is correct behaviour.

Return only a JSON object: {{"strategy": "...", "rationale": "...", "code": "...", "guard": "..."}}

Examples:
{examples}
"""


class ModelJudge:
    """Asks a Claude model to write the fast path. Opt-in; requires a key."""

    name = "model-judge"

    def __init__(self, model: str = MODEL_JUDGE_DEFAULT, max_examples: int = 60):
        self.model = model
        self.max_examples = max_examples

    def propose(self, label: str, examples: list[Example]) -> Proposal:
        try:
            import anthropic
        except ImportError:
            raise SystemExit(
                "ModelJudge needs the anthropic SDK: pip install anthropic\n"
                "(or run with --judge offline, the default)"
            )
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise SystemExit("ModelJudge needs ANTHROPIC_API_KEY set.")

        shown = examples[: self.max_examples]
        rendered = "\n".join(
            f"- input: {e.input_text[:300]!r}\n  output: {e.output[:200]!r}" for e in shown
        )
        client = anthropic.Anthropic(api_key=key)
        resp = client.messages.create(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user",
                       "content": PROMPT.format(label=label, examples=rendered)}],
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
        if "DECLINE" in text[:400] and "{" not in text[:400]:
            return Proposal(strategy="decline", source="", guard_source="", declined=True,
                            rationale="Model judge declined.")
        payload = json.loads(text[text.index("{"): text.rindex("}") + 1])
        prop = Proposal(
            strategy=payload.get("strategy", "model"),
            source=payload["code"],
            guard_source=payload["guard"],
            rationale=payload.get("rationale", ""),
        )
        return compile_proposal(prop)


def get_judge(kind: str):
    return ModelJudge() if kind == "model" else OfflineSynthesizer()
