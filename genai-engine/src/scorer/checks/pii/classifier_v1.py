"""PII v1 RuleScorer (Presidio-only).

Thin wrapper that adapts the models service's POST /v1/inference/pii
response (with use_v2=False) into a RuleScore + ScorerRuleDetails. v1 still
runs Presidio server-side; it just doesn't engage GLiNER or spaCy.

Construct with the same ModelsServiceClient as the v2 scorer — the engine
chooses between v1 and v2 in dependencies.py based on
GENAI_ENGINE_USE_PII_MODEL_V2 and forwards the choice via the `use_v2`
flag on each call.
"""

import logging

from arthur_common.models.enums import PIIEntityTypes, RuleResultEnum

from clients.models_service_client import (
    ModelNotAvailableError,
    ModelsServiceClient,
)
from schemas.scorer_schemas import (
    RuleScore,
    ScoreRequest,
    ScorerPIIEntitySpan,
    ScorerRuleDetails,
)
from scorer.scorer import RuleScorer

logger = logging.getLogger(__name__)


class BinaryPIIDataClassifierV1(RuleScorer):
    def __init__(self, client: ModelsServiceClient):
        self.client = client

    def score(self, request: ScoreRequest) -> RuleScore:
        if not request.scoring_text:
            return RuleScore(
                result=RuleResultEnum.PASS,
                prompt_tokens=0,
                completion_tokens=0,
            )

        try:
            response = self.client.pii(
                text=request.scoring_text,
                disabled_entities=list(request.disabled_pii_entities or []),
                allow_list=list(request.allow_list or []),
                confidence_threshold=request.pii_confidence_threshold,
                use_v2=False,
            )
        except ModelNotAvailableError as e:
            logger.warning("PII v1 model unavailable: %s", e)
            return RuleScore(
                result=RuleResultEnum.MODEL_NOT_AVAILABLE,
                prompt_tokens=0,
                completion_tokens=0,
            )

        rule_result = RuleResultEnum(response.result)
        if rule_result == RuleResultEnum.PASS:
            return RuleScore(
                result=rule_result,
                prompt_tokens=0,
                completion_tokens=0,
            )

        entity_types: list[PIIEntityTypes] = []
        spans: list[ScorerPIIEntitySpan] = []
        for entity in response.entities:
            etype = PIIEntityTypes(entity.entity)
            entity_types.append(etype)
            spans.append(
                ScorerPIIEntitySpan(
                    entity=etype,
                    span=entity.span,
                    confidence=entity.confidence,
                ),
            )

        unique_types = sorted({e.value for e in entity_types})
        return RuleScore(
            result=rule_result,
            details=ScorerRuleDetails(
                message=f"PII found in data: {','.join(unique_types)}",
                pii_results=[PIIEntityTypes(t) for t in unique_types],
                pii_entities=spans,
            ),
            prompt_tokens=0,
            completion_tokens=0,
        )
