"""Generated fast path for call site `route.team`.

4 distinct outputs; 24 tokens predict a single label, chosen by greedy cover over 4 labels. Purity bar calibrated to observed self-agreement 0.946 (bar 0.886). Training inputs left uncovered per label: {'billing': 13, 'onboarding': 9, 'security': 10, 'platform': 14}.

Evidence: {"holdout_calls": 132, "coverage": 0.8409, "agreement_in_guard": 0.982, "model_self_agreement": 0.9473, "model_self_agreement_n": 550, "z_vs_model": 1.577, "conditional_bits": 0.2889}
Fallback: call_model (guard returns False, script returns None, or the sampling slice is selected).
"""

import re


_RULES = {
    "billing": [
        "invoice",
        "receipt",
        "proration",
        "refund",
        "chargeback",
        "vat"
    ],
    "onboarding": [
        "trial",
        "sandbox",
        "sso",
        "provisioning",
        "migration",
        "kickoff"
    ],
    "security": [
        "soc2",
        "phishing",
        "pentest",
        "breach",
        "mfa",
        "credential"
    ],
    "platform": [
        "cluster",
        "throughput",
        "latency",
        "quota",
        "deploy",
        "timeout"
    ]
}
_FALLBACK = 'billing'


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

