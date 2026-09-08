"""Generated fast path for call site `extract.order_id`.

Output is a verbatim substring of the input in 220/221 calls, matching order-style #NNNN. This is extraction, not judgment.

Evidence: {"holdout_calls": 96, "coverage": 1.0, "agreement_in_guard": 0.9896, "model_self_agreement": 0.9844, "model_self_agreement_n": 245, "z_vs_model": 0.366, "conditional_bits": 0.0317}
Fallback: call_model (guard returns False, script returns None, or the sampling slice is selected).
"""

import re


_RX = re.compile(r"#(\d{3,})", re.IGNORECASE)


def fast_path(text):
    """Extract the identifier the model was being asked to echo back."""
    m = _RX.search(text)
    return m.group(1).lower() if m else None




def guard(text):
    """Apply only when exactly one candidate identifier is present."""
    return len(_RX.findall(text)) == 1

