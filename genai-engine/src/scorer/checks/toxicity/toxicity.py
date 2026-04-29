"""Toxicity RuleScorer.

Thin wrapper that adapts the models service's POST /v1/inference/toxicity
response into a RuleScore + ScorerToxicityScore. The in-process RoBERTa
toxicity classifier, ONNX profanity classifier, regex profanity blacklist,
section-splitter, and chunker all moved to the models service; the engine
now sends raw text plus the policy threshold and consumes the binary
verdict + violation type.

Behavior preserved from the previous in-process scorer:
- Non-float threshold → RuleResultEnum.SKIPPED (engine-side defense; the
  Pydantic schema also rejects this at the request boundary).
- Empty scoring_text → RuleResultEnum.PASS without hitting the wire.
- ModelNotAvailableError → RuleResultEnum.MODEL_NOT_AVAILABLE.
"""

import logging

from arthur_common.models.enums import RuleResultEnum, ToxicityViolationType

from clients.models_service_client import (
    ModelNotAvailableError,
    ModelsServiceClient,
)
from schemas.scorer_schemas import (
    RuleScore,
    ScoreRequest,
    ScorerRuleDetails,
    ScorerToxicityScore,
)
from scorer.scorer import RuleScorer

logger = logging.getLogger(__name__)


class ToxicityScorer(RuleScorer):
    def __init__(self, client: ModelsServiceClient):
        self.client = client

    def score(self, request: ScoreRequest) -> RuleScore:
        # Match the legacy scorer: skip if threshold isn't a float (the route
        # layer should reject before reaching here, but defend in depth).
        if not isinstance(request.toxicity_threshold, float):
            return RuleScore(
                result=RuleResultEnum.SKIPPED,
                prompt_tokens=0,
                completion_tokens=0,
                details=ScorerRuleDetails(
                    message="Toxicity threshold must be a float. Skipping toxicity check.",
                ),
            )

        if not request.scoring_text:
            return RuleScore(
                result=RuleResultEnum.PASS,
                prompt_tokens=0,
                completion_tokens=0,
            )

        try:
            response = self.client.toxicity(
                text=request.scoring_text,
                threshold=request.toxicity_threshold,
            )
        except ModelNotAvailableError as e:
            logger.warning("Toxicity model unavailable: %s", e)
            return RuleScore(
                result=RuleResultEnum.MODEL_NOT_AVAILABLE,
                prompt_tokens=0,
                completion_tokens=0,
            )

        rule_result = RuleResultEnum(response.result)
        violation_type = ToxicityViolationType(response.violation_type)

        message = (
            "Toxicity detected"
            if rule_result == RuleResultEnum.FAIL
            else "No toxicity detected!"
        )

        return RuleScore(
            result=rule_result,
            details=ScorerRuleDetails(
                message=message,
                toxicity_score=ScorerToxicityScore(
                    toxicity_score=response.toxicity_score,
                    toxicity_violation_type=violation_type,
                ),
            ),
            prompt_tokens=0,
            completion_tokens=0,
        )
