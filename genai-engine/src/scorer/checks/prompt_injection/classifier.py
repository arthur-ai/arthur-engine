import logging
import threading

import torch
from schemas.enums import RuleResultEnum
from schemas.scorer_schemas import RuleScore, ScoreRequest
from scorer.scorer import RuleScorer
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    TextClassificationPipeline,
)
from transformers.modeling_utils import PreTrainedModel
from transformers.tokenization_utils import PreTrainedTokenizerBase
from utils.classifiers import get_device
from utils.decorators import reset_on_failure, with_lock

logger = logging.getLogger()
MAX_LENGTH = 512
PROMPT_INJECTION_MODEL = None
PROMPT_INJECTION_TOKENIZER = None


@reset_on_failure("PROMPT_INJECTION_MODEL")
@with_lock("/tmp/prompt_injection_model.lock")
def get_prompt_injection_model():
    global PROMPT_INJECTION_MODEL
    if not PROMPT_INJECTION_MODEL:
        PROMPT_INJECTION_MODEL = AutoModelForSequenceClassification.from_pretrained(
            "ProtectAI/deberta-v3-base-prompt-injection-v2",
        )
    return PROMPT_INJECTION_MODEL


@reset_on_failure("PROMPT_INJECTION_TOKENIZER")
@with_lock("/tmp/prompt_injection_tokenizer.lock")
def get_prompt_injection_tokenizer():
    global PROMPT_INJECTION_TOKENIZER
    if not PROMPT_INJECTION_TOKENIZER:
        PROMPT_INJECTION_TOKENIZER = AutoTokenizer.from_pretrained(
            "ProtectAI/deberta-v3-base-prompt-injection-v2",
        )
    return PROMPT_INJECTION_TOKENIZER


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
        if PROMPT_INJECTION_MODEL is None:
            get_prompt_injection_model()
        if PROMPT_INJECTION_TOKENIZER is None:
            get_prompt_injection_tokenizer()
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
