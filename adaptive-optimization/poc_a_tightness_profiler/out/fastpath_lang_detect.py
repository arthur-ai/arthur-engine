"""Generated fast path for call site `lang.detect`.

5 distinct outputs; 9 tokens predict a single label, chosen by greedy cover over 5 labels. Purity bar calibrated to observed self-agreement 0.984 (bar 0.924). Training inputs left uncovered per label: {'es': 1, 'pt': 1, 'en': 2}.

Evidence: {"holdout_calls": 106, "coverage": 1.0, "agreement_in_guard": 1.0, "model_self_agreement": 0.9896, "model_self_agreement_n": 383, "z_vs_model": 1.052, "conditional_bits": 0.0758}
Fallback: call_model (guard returns False, script returns None, or the sampling slice is selected).
"""

import re


_RULES = {
    "es": [
        "una",
        "acceder"
    ],
    "pt": [
        "conta",
        "uma"
    ],
    "de": [
        "ich"
    ],
    "en": [
        "account",
        "wrong"
    ],
    "fr": [
        "connecter",
        "incorrecte"
    ]
}
_FALLBACK = 'en'


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

