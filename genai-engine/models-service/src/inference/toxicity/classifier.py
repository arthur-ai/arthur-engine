"""Toxicity inference.

Migrated from genai-engine/src/scorer/checks/toxicity/toxicity.py:251-369.
Combines four signals — regex profanity blacklist, profanity classifier,
RoBERTa toxicity classifier, optional harmful-request classifier — into a
single aggregate score. Section-splitting and chunking run server-side.
The harmful-request classifier is a no-op today (mirroring the engine's
`harmful_request_model=None` default); the slot is kept so wiring it up
later doesn't change the wire shape.

API contract:
    POST /v1/inference/toxicity
    Request:
        {
            "text": str,
            "threshold": float,                       # 0..1, required
            "max_chunk_size": int | null,             # default 32
            "harmful_request_max_chunk_size": int | null  # default 512
        }
    Response:
        {
            "result": "Pass" | "Fail" | "Model Not Available",
            "toxicity_score": float,                  # max across classifiers
            "violation_type":
                "benign" | "profanity" | "toxic_content" | "harmful_request",
            "profanity_detected": bool,
            "max_toxicity_score": float,
            "max_harmful_request_score": float
        }
    Behavior:
        - Empty text → result=Pass, violation_type=benign.
        - Profanity-regex hit short-circuits: toxicity_score is set to
          nextafter(1.0, 0.0) and violation_type=profanity (no model run).
        - Otherwise final_score = max(max_toxicity_score, max_harmful_request_score),
          violation_type names the classifier that produced the max.
        - result=Fail iff final_score > threshold.
"""

import logging
import re
from typing import Any

import numpy as np
import torch
from opentelemetry import trace

from inference.text_chunking import ChunkIterator
from inference.toxicity.profanity import detect_profanity
from inference.toxicity.text_utils import list_indicator_regex, pad_text
from model_registry import loader
from schemas import (
    InferenceResult,
    ToxicityRequest,
    ToxicityResponse,
    ToxicityViolationType,
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

DEFAULT_TOXICITY_CHUNK_SIZE = 32
DEFAULT_HARMFUL_REQUEST_CHUNK_SIZE = 512
TOXICITY_MODEL_BATCH_SIZE = 64
TOXIC_LABEL = "TOXIC"
PROFANITY_OFFENSIVE_LABEL = "OFFENSIVE"

# Patterns lifted verbatim from toxicity.py:123-134.
_SENTENCE_BOUNDARY = re.compile(r"(?:\.|\?)(?=\s+[A-Za-z])")
_SPECIAL_CHAR = re.compile(r"(?<![a-zA-Z])([^\w\s])\1{2,}(?![a-zA-Z])")


def _replace_special_chars(match: re.Match[str]) -> str:
    return match.group(1)


def _split_sections(text: str) -> list[str]:
    """Sentence/list-item splitter. Treats list items as a single section."""
    lines = text.split("\n")
    sections: list[str] = []
    for line in lines:
        line = line.strip()
        line = _SPECIAL_CHAR.sub(_replace_special_chars, line)
        if list_indicator_regex.match(line):
            sections.append(line)
        else:
            parts = _SENTENCE_BOUNDARY.split(line)
            sections.extend(p.strip() for p in parts if p)
    return sections


def _chunk(text: str, tokenizer: Any, chunk_size: int) -> list[str]:
    return list(ChunkIterator(text, tokenizer, chunk_size))


def _profanity_pass(
    chunks: list[str],
    threshold: float,
) -> bool:
    """Two-stage profanity check: regex blacklist then classifier fallback.
    Returns True on any hit."""
    profanity_pipeline = loader.get_profanity_classifier()
    if profanity_pipeline is None:
        # Without the classifier we can still do regex.
        for chunk in chunks:
            if detect_profanity(chunk):
                return True
        return False

    with tracer.start_as_current_span("toxicity: profanity detection"):
        for chunk in chunks:
            if detect_profanity(chunk):
                return True

        # transformers `pipeline()` overload returns Any at the type level when
        # called with a list+top_k; the runtime shape is list[list[dict]].
        results: list[list[dict[str, str | float]]] = profanity_pipeline(  # type: ignore[assignment]
            chunks,
            batch_size=TOXICITY_MODEL_BATCH_SIZE,
        )
        for per_chunk in results:
            if any(
                float(label["score"]) > threshold
                for label in per_chunk
                if str(label["label"]) == PROFANITY_OFFENSIVE_LABEL
            ):
                return True
    return False


def _score_toxicity(chunks: list[str]) -> list[float]:
    """Run the deberta toxicity classifier on chunks; return per-chunk scores
    for the TOXIC label."""
    pipeline = loader.get_toxicity_classifier()
    if pipeline is None:
        return []

    with tracer.start_as_current_span("toxicity: run deberta classifier"):
        with torch.no_grad():
            results: list[list[dict[str, str | float]]] = pipeline(  # type: ignore[assignment]
                pad_text(chunks, pad_type="repetition"),
                batch_size=TOXICITY_MODEL_BATCH_SIZE,
            )
    scores: list[float] = []
    for per_chunk in results:
        for label in per_chunk:
            if str(label["label"]).upper() == TOXIC_LABEL:
                scores.append(float(label["score"]))
    return scores


def _score_harmful_request(chunks: list[str]) -> list[float]:
    """genai-engine ships harmful_request_classifier=None, so this returns
    zeros. Kept as a function so the wire shape stays stable when the model
    is later wired up."""
    return [0.0] * len(chunks)


def classify(req: ToxicityRequest) -> ToxicityResponse:
    pipeline = loader.get_toxicity_classifier()
    tokenizer = loader.get_toxicity_tokenizer()
    if pipeline is None or tokenizer is None:
        return ToxicityResponse(
            result=InferenceResult.MODEL_NOT_AVAILABLE,
            toxicity_score=0.0,
            violation_type=ToxicityViolationType.UNKNOWN,
            profanity_detected=False,
            max_toxicity_score=0.0,
            max_harmful_request_score=0.0,
        )

    if not req.text:
        return ToxicityResponse(
            result=InferenceResult.PASS,
            toxicity_score=0.0,
            violation_type=ToxicityViolationType.BENIGN,
            profanity_detected=False,
            max_toxicity_score=0.0,
            max_harmful_request_score=0.0,
        )

    tox_chunk_size = req.max_chunk_size or DEFAULT_TOXICITY_CHUNK_SIZE
    harm_chunk_size = (
        req.harmful_request_max_chunk_size or DEFAULT_HARMFUL_REQUEST_CHUNK_SIZE
    )

    text_chunks = _chunk(req.text, tokenizer, tox_chunk_size)
    harm_chunks = _chunk(req.text, tokenizer, harm_chunk_size)

    profanity_detected = _profanity_pass(text_chunks, req.threshold)

    if profanity_detected:
        # Match genai-engine: nextafter(1, 0) == "just below 1".
        final_score = float(np.nextafter(1.0, 0.0))
        violation = ToxicityViolationType.PROFANITY
        result = InferenceResult.FAIL
        return ToxicityResponse(
            result=result,
            toxicity_score=final_score,
            violation_type=violation,
            profanity_detected=True,
            max_toxicity_score=0.0,
            max_harmful_request_score=0.0,
        )

    harm_scores = _score_harmful_request(harm_chunks)
    tox_scores = _score_toxicity(text_chunks)

    max_harm = max(harm_scores) if harm_scores else 0.0
    max_tox = max(tox_scores) if tox_scores else 0.0

    if max_harm > max_tox:
        final_score = max_harm
        violation = ToxicityViolationType.HARMFUL_REQUEST
    else:
        final_score = max_tox
        violation = ToxicityViolationType.TOXIC_CONTENT

    failed = final_score > req.threshold
    if not failed:
        violation = ToxicityViolationType.BENIGN

    return ToxicityResponse(
        result=InferenceResult.FAIL if failed else InferenceResult.PASS,
        toxicity_score=final_score,
        violation_type=violation,
        profanity_detected=False,
        max_toxicity_score=float(max_tox),
        max_harmful_request_score=float(max_harm),
    )
