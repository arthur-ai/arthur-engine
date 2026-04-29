"""Prompt-injection RuleScorer.

Thin wrapper that adapts the models service's
POST /v1/inference/prompt_injection response into a RuleScore. The
in-process AutoModelForSequenceClassification + SlidingWindowChunkIterator
that used to live here moved to the models service; the engine now sends
raw text and consumes the binary verdict.

Empty `user_prompt` short-circuits to PASS without hitting the wire.
A ModelNotAvailableError from the client (5xx after retries, or
`model_not_available` body code) maps to RuleResultEnum.MODEL_NOT_AVAILABLE.
"""

import logging

from arthur_common.models.enums import RuleResultEnum

from clients.models_service_client import (
    ModelNotAvailableError,
    ModelsServiceClient,
)
from schemas.scorer_schemas import RuleScore, ScoreRequest
from scorer.scorer import RuleScorer

logger = logging.getLogger(__name__)


class BinaryPromptInjectionClassifier(RuleScorer):
    def __init__(self, client: ModelsServiceClient):
        self.client = client

    def score(self, request: ScoreRequest) -> RuleScore:
        user_prompt = request.user_prompt
        if not user_prompt:
            return RuleScore(
                result=RuleResultEnum.PASS,
                prompt_tokens=0,
                completion_tokens=0,
            )

        try:
            response = self.client.prompt_injection(user_prompt)
        except ModelNotAvailableError as e:
            logger.warning("Prompt injection model unavailable: %s", e)
            return RuleScore(
                result=RuleResultEnum.MODEL_NOT_AVAILABLE,
                prompt_tokens=0,
                completion_tokens=0,
            )

        # Wire schema: result is "Pass" | "Fail" | "Model Not Available".
        rule_result = RuleResultEnum(response.result)
        return RuleScore(
            result=rule_result,
            prompt_tokens=0,
            completion_tokens=0,
        )
