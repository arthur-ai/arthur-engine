import logging
from typing import Any

import torch
import torch.nn.functional as F
from arthur_common.models.enums import RuleResultEnum
from transformers.modeling_utils import PreTrainedModel
from transformers.tokenization_utils import PreTrainedTokenizerBase

from schemas.scorer_schemas import RuleScore, ScoreRequest
from scorer.scorer import RuleScorer
from services.model_warmup_service import ModelKey, get_model_warmup_service
from utils.model_load import (
    get_prompt_injection_classifier,
    get_prompt_injection_tokenizer,
)
from utils.text_chunking import SlidingWindowChunkIterator

logger = logging.getLogger()
MAX_LENGTH = 512


class BinaryPromptInjectionClassifier(RuleScorer):
    def __init__(
        self,
        model: PreTrainedModel | None,
        tokenizer: PreTrainedTokenizerBase | None,
    ):
        """Initialized the binary classifier for prompt injection.

        Constructed before models finish warming up, so it does not eagerly
        load the classifier; it consults the warmup service per ``score``
        call and lazily fetches the loaded handles only once they're ready.
        """
        self._init_model = model
        self._init_tokenizer = tokenizer
        self._classifier: Any | None = None
        self._tokenizer: PreTrainedTokenizerBase | None = None
        self.injection_label = "INJECTION"

    def _ensure_loaded(self) -> bool:
        """Resolve cached classifier+tokenizer once the model is ready.

        If the constructor was given concrete ``model``/``tokenizer`` objects
        (e.g. by a caller that pre-loaded them), use them immediately rather
        than waiting on the global warmup service: that caller has already
        proven the model is loaded.
        """
        if self._classifier is not None and self._tokenizer is not None:
            return True
        if self._init_model is not None and self._init_tokenizer is not None:
            self._classifier = get_prompt_injection_classifier(
                self._init_model,
                self._init_tokenizer,
            )
            self._tokenizer = self._init_tokenizer
            return self._classifier is not None and self._tokenizer is not None
        if not get_model_warmup_service().is_ready(ModelKey.PROMPT_INJECTION):
            return False
        self._classifier = get_prompt_injection_classifier(
            self._init_model,
            self._init_tokenizer,
        )
        self._tokenizer = self._init_tokenizer or get_prompt_injection_tokenizer()
        return self._classifier is not None and self._tokenizer is not None

    def is_loaded(self) -> bool:
        """Public read-only view of whether the classifier is wired up."""
        return self._classifier is not None and self._tokenizer is not None

    def chunk_text(self, text: str) -> list[str]:
        # Callers must run after ``_ensure_loaded()`` returns True; the
        # tokenizer is guaranteed non-None here.
        assert self._tokenizer is not None, "_ensure_loaded must run first"
        chunk_iterator = SlidingWindowChunkIterator(
            text=text,
            tokenizer=self._tokenizer,
            chunk_size=MAX_LENGTH,
            stride=MAX_LENGTH // 2,
        )

        return [chunk for chunk in chunk_iterator]

    def score(self, request: ScoreRequest) -> RuleScore:
        """Scores prompt for how likely they are to be a prompt injection attack
        Requests greater than 2000 characters are truncated from the middle"""
        if not self._ensure_loaded():
            return self._model_not_available(
                ModelKey.PROMPT_INJECTION,
                "Prompt injection classifier is not available yet (warming up).",
            )
        user_prompt = request.user_prompt
        if not user_prompt:
            return RuleScore(
                result=RuleResultEnum.PASS,
                prompt_tokens=0,
                completion_tokens=0,
            )
        text_chunks = self.chunk_text(user_prompt)

        for chunk in text_chunks:
            # Get raw scores from model
            with torch.no_grad():
                raw_scores: list[dict[str, Any]] = self._classifier(chunk)  # type: ignore[misc]

            scores = torch.tensor([item["score"] for item in raw_scores])

            probs = F.softmax(scores, dim=0)

            max_prob_idx: int | float = torch.argmax(probs).item()
            label: str = raw_scores[int(max_prob_idx)]["label"]

            if label == self.injection_label:
                return RuleScore(
                    result=RuleResultEnum.FAIL,
                    prompt_tokens=0,
                    completion_tokens=0,
                )

        return RuleScore(
            result=RuleResultEnum.PASS,
            prompt_tokens=0,
            completion_tokens=0,
        )
