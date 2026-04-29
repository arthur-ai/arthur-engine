"""Prompt-injection inference.

Migrated from genai-engine/src/scorer/checks/prompt_injection/classifier.py:66-114.
The sliding-window chunker (512 tokens, 50% stride) used to live in the
engine; it now runs server-side and the engine sends raw text.

API contract:
    POST /v1/inference/prompt_injection
    Request:
        { "text": str }
    Response:
        {
            "result": "Pass" | "Fail" | "Model Not Available",
            "chunks": [
                {
                    "index": int,
                    "text": str,
                    "label": "INJECTION" | "SAFE",
                    "score": float    # softmax probability for predicted label
                }
            ]
        }
    Behavior:
        - Empty text → result=Pass, chunks=[].
        - Scoring stops at the first chunk classified as INJECTION; the flagged
          chunk is the last entry of `chunks` when result=Fail.
        - For Pass, all chunks are returned with their label/score.
"""

import logging
from typing import Any

import torch
import torch.nn.functional as F
from opentelemetry import trace

from inference.text_chunking import SlidingWindowChunkIterator
from models import loader
from schemas import (
    InferenceResult,
    PromptInjectionChunk,
    PromptInjectionLabel,
    PromptInjectionRequest,
    PromptInjectionResponse,
)

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

CHUNK_SIZE = 512
STRIDE = CHUNK_SIZE // 2  # 50% overlap, matches genai-engine
INJECTION_LABEL = "INJECTION"


def classify(req: PromptInjectionRequest) -> PromptInjectionResponse:
    """Run the prompt-injection classifier; stop at the first INJECTION chunk."""
    pipeline = loader.get_prompt_injection_classifier()
    tokenizer = loader.get_prompt_injection_tokenizer()
    if pipeline is None or tokenizer is None:
        return PromptInjectionResponse(result=InferenceResult.MODEL_NOT_AVAILABLE, chunks=[])

    text = req.text
    if not text:
        return PromptInjectionResponse(result=InferenceResult.PASS, chunks=[])

    chunks: list[PromptInjectionChunk] = []
    flagged = False

    with tracer.start_as_current_span("prompt_injection: chunk + classify"):
        chunk_iter = SlidingWindowChunkIterator(
            text=text,
            tokenizer=tokenizer,
            chunk_size=CHUNK_SIZE,
            stride=STRIDE,
        )

        for idx, chunk_text in enumerate(chunk_iter):
            with torch.no_grad():
                raw_scores: list[dict[str, Any]] = pipeline(chunk_text)
            # The pipeline returns one dict per label (top_k = num labels).
            # Softmax across labels, argmax to pick predicted label.
            scores = torch.tensor([item["score"] for item in raw_scores])
            probs = F.softmax(scores, dim=0)
            max_idx = int(torch.argmax(probs).item())
            label_str = raw_scores[max_idx]["label"]
            chunks.append(
                PromptInjectionChunk(
                    index=idx,
                    text=chunk_text,
                    label=PromptInjectionLabel(label_str.upper()),
                    score=float(probs[max_idx].item()),
                ),
            )
            if label_str == INJECTION_LABEL:
                flagged = True
                break

    return PromptInjectionResponse(
        result=InferenceResult.FAIL if flagged else InferenceResult.PASS,
        chunks=chunks,
    )
