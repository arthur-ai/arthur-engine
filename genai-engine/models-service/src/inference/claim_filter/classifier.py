"""Hallucination claim-filter inference.

Migrated from genai-engine/src/scorer/checks/hallucination/v2.py:50-91, 178-187.

Embedding + logistic-regression head only — this is the cheap filter that
decides which sentences are actual claims versus dialog/non-claims, so the
expensive LLM judge only sees real claims. The LLM judge itself stays in
genai-engine because it shares scorer/llm_client.py with non-scorer code.

API contract:
    POST /v1/inference/claim_filter
    Request:
        { "texts": [str] }                # pre-parsed sentences/list-items
    Response:
        {
            "classifications": [
                {
                    "text": str,
                    "label": "claim" | "nonclaim" | "dialog",
                    "confidence": float    # max softmax probability
                }
            ]
        }
    Behavior:
        - Order preserved: classifications[i] corresponds to texts[i].
        - Empty input → classifications=[].
        - Engine forwards `claim`-labeled items to its local LLM judge;
          `nonclaim`/`dialog` items skip the judge.
"""

import logging

import numpy as np
from opentelemetry import trace

from model_registry import loader
from schemas import (
    ClaimClassification,
    ClaimClassifierResultEnum,
    ClaimFilterRequest,
    ClaimFilterResponse,
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


def classify(req: ClaimFilterRequest) -> ClaimFilterResponse:
    classifier = loader.get_claim_classifier()
    if classifier is None or not req.texts:
        return ClaimFilterResponse(classifications=[])

    with tracer.start_as_current_span("claim_filter: classify"):
        result = classifier(req.texts)

    # `result` from Classifier.forward (see model_registry/classifier_arch.py): a dict
    # with keys "label" (np int array), "logit", "prob" (softmax distribution),
    # "pred_label_str" (list[str] from inv_label_map).
    labels: list[str] = result["pred_label_str"]
    probs = np.asarray(result["prob"])  # (N, 3)

    classifications: list[ClaimClassification] = []
    for text, label_str, prob_row in zip(req.texts, labels, probs):
        classifications.append(
            ClaimClassification(
                text=text,
                label=ClaimClassifierResultEnum(label_str),
                confidence=float(np.max(prob_row)),
            ),
        )
    return ClaimFilterResponse(classifications=classifications)
