"""Hallucination claim-filter inference tests — needs real models.

The filter is a small sentence-transformer + logreg head, much lighter than
the other model-backed checks. Tests check label routing and confidence
shape.
"""

import pytest

from inference.claim_filter import classify
from schemas import ClaimClassifierResultEnum, ClaimFilterRequest

pytestmark = pytest.mark.real_models


def test_empty_input_returns_empty():
    result = classify(ClaimFilterRequest(texts=[]))
    assert result.classifications == []


def test_factual_claim_routes_to_claim():
    result = classify(ClaimFilterRequest(texts=[
        "Isaac Newton built on the principles put forth by Galileo.",
    ]))
    assert len(result.classifications) == 1
    assert result.classifications[0].label == ClaimClassifierResultEnum.CLAIM
    assert 0.0 <= result.classifications[0].confidence <= 1.0


def test_dialog_routes_to_dialog():
    result = classify(ClaimFilterRequest(texts=["Hi! Any other questions?"]))
    assert len(result.classifications) == 1
    # The classifier should label small-talk as DIALOG, not CLAIM.
    assert result.classifications[0].label != ClaimClassifierResultEnum.CLAIM


def test_order_preserved():
    texts = ["Newton invented calculus.", "Hi there!", "Water boils at 100C."]
    result = classify(ClaimFilterRequest(texts=texts))
    assert [c.text for c in result.classifications] == texts
