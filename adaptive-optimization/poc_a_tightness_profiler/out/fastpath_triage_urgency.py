"""Generated fast path for call site `triage.urgency`.

3 distinct outputs; 13 tokens predict a single label, chosen by greedy cover over 3 labels. Purity bar calibrated to observed self-agreement 0.974 (bar 0.914). Training inputs left uncovered per label: {'p1': 4, 'p2': 4, 'p3': 4}.

Evidence: {"holdout_calls": 147, "coverage": 1.0, "agreement_in_guard": 0.9728, "model_self_agreement": 0.974, "model_self_agreement_n": 537, "z_vs_model": -0.084, "conditional_bits": 0.196}
Fallback: call_model (guard returns False, script returns None, or the sampling slice is selected).
"""

import re


_RULES = {
    "p1": [
        "down",
        "dashboard",
        "migration",
        "total",
        "suspect"
    ],
    "p2": [
        "are",
        "export"
    ],
    "p3": [
        "next",
        "change",
        "last",
        "mode",
        "find",
        "address"
    ]
}
_FALLBACK = 'p3'


def fast_path(text):
    """Score the input against per-label keyword sets."""
    toks = set(re.findall(r"[a-z0-9_#]+", text.lower()))
    best, best_hits = None, 0
    for label, keywords in _RULES.items():
        hits = len(toks & set(keywords))
        if hits > best_hits:
            best, best_hits = label, hits
    return best if best_hits else _FALLBACK




def guard(text):
    """Apply only when at least one known keyword is present.

    Inputs carrying no recognised keyword are exactly the unfamiliar ones the
    fallback exists for, so rejecting them is correct behaviour, not a miss.
    """
    toks = set(re.findall(r"[a-z0-9_#]+", text.lower()))
    return any(toks & set(kw) for kw in _RULES.values())

