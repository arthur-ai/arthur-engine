import logging
import threading

import torch
from arthur_common.models.enums import RuleResultEnum
from schemas.scorer_schemas import RuleScore, ScoreRequest
from scorer.scorer import RuleScorer
from transformers import TextClassificationPipeline
from transformers.modeling_utils import PreTrainedModel
from transformers.tokenization_utils import PreTrainedTokenizerBase
from utils.classifiers import get_device
from utils.model_load import get_prompt_injection_model, get_prompt_injection_tokenizer

logger = logging.getLogger()
MAX_LENGTH = 512


def get_prompt_injection_classifier(
    model: PreTrainedModel | None,
    tokenizer: PreTrainedTokenizerBase | None,
) -> TextClassificationPipeline | None:
    """Loads in the prompt injection binary classifier"""
    if model is None:
        model = get_prompt_injection_model()
    if tokenizer is None:
        tokenizer = get_prompt_injection_tokenizer()
    return TextClassificationPipeline(
        model=model,
        tokenizer=tokenizer,
        max_length=MAX_LENGTH,
        truncation=True,
        device=torch.device(get_device()),
    )


class BinaryPromptInjectionClassifier(RuleScorer):
    LABEL = "INJECTION"

    def __init__(self, model: PreTrainedModel, tokenizer: PreTrainedTokenizerBase):
        """Initialized the binary classifier for prompt injection"""
        self.model = get_prompt_injection_classifier(model, tokenizer)

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
        if len(request) > 2000:
            shortened = request[:1000] + request[-1000:]
            request = shortened

        label = self.model(request)[0]["label"]

        if label != self.LABEL:
            return RuleScore(
                result=RuleResultEnum.PASS,
                prompt_tokens=0,
                completion_tokens=0,
            )
        else:
            return RuleScore(
                result=RuleResultEnum.FAIL,
                prompt_tokens=0,
                completion_tokens=0,
            )
