import logging
import threading

import torch
import torch.nn.functional as F
from transformers.modeling_utils import PreTrainedModel
from transformers.tokenization_utils import PreTrainedTokenizerBase

from schemas.enums import RuleResultEnum
from schemas.scorer_schemas import RuleScore, ScoreRequest
from scorer.scorer import RuleScorer
from utils.model_load import (
    get_prompt_injection_classifier,
    get_prompt_injection_model,
    get_prompt_injection_tokenizer,
)
from utils.text_chunking import SlidingWindowChunkIterator

logger = logging.getLogger()
MAX_LENGTH = 512


class BinaryPromptInjectionClassifier(RuleScorer):
    def __init__(self, model: PreTrainedModel, tokenizer: PreTrainedTokenizerBase):
        """Initialized the binary classifier for prompt injection"""
        self.model = get_prompt_injection_classifier(model, tokenizer)
        self.tokenizer = (
            tokenizer if tokenizer is not None else get_prompt_injection_tokenizer()
        )
        self.injection_label = "INJECTION"

    def chunk_text(self, text: str) -> list[str]:
        chunk_iterator = SlidingWindowChunkIterator(
            text=text,
            tokenizer=self.tokenizer,
            chunk_size=MAX_LENGTH,
            stride=MAX_LENGTH // 2,
        )

        return [chunk for chunk in chunk_iterator]

    def _download_model_and_tokenizer(self):
        global PROMPT_INJECTION_MODEL
        global PROMPT_INJECTION_TOKENIZER
        if PROMPT_INJECTION_MODEL is None:
            PROMPT_INJECTION_MODEL = get_prompt_injection_model()
        if PROMPT_INJECTION_TOKENIZER is None:
            PROMPT_INJECTION_TOKENIZER = get_prompt_injection_tokenizer()
        self.model = get_prompt_injection_classifier(
            PROMPT_INJECTION_MODEL,
            PROMPT_INJECTION_TOKENIZER,
        )

    def score(self, request: ScoreRequest) -> RuleScore:
        """Scores prompt for how likely they are to be a prompt injection attack
        Requests greater than 2000 characters are truncated from the middle"""
        if self.model is None:
            threading.Thread(
                target=self._download_model_and_tokenizer,
                daemon=True,
            ).start()
            logger.warning(
                "Prompt injection classifier is not available.",
            )
            return RuleScore(
                result=RuleResultEnum.MODEL_NOT_AVAILABLE,
                prompt_tokens=0,
                completion_tokens=0,
            )
        request = request.user_prompt
        text_chunks = self.chunk_text(request)

        for chunk in text_chunks:
            # Get raw scores from model
            with torch.no_grad():
                raw_scores = self.model(chunk)

            scores = torch.tensor([item["score"] for item in raw_scores])

            probs = F.softmax(scores, dim=0)

            max_prob_idx = torch.argmax(probs).item()
            label = raw_scores[max_prob_idx]["label"]

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
