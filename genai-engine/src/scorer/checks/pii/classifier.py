"""PII v2 RuleScorer.

Thin wrapper that adapts the models service's POST /v1/inference/pii
response (with use_v2=True) into a RuleScore + ScorerRuleDetails. The
in-process GLiNER + Presidio + spaCy pipeline moved to the models service;
the engine forwards `disabled_pii_entities`, `allow_list`, and
`pii_confidence_threshold` from the request and translates the resulting
spans back into the engine's RuleScore shape.
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


class BinaryPIIDataClassifier(RuleScorer):
    """PII v2 — uses the full GLiNER+Presidio+spaCy pipeline server-side."""

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
                use_v2=True,
            )
        except ModelNotAvailableError as e:
            logger.warning("PII v2 model unavailable: %s", e)
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
                message=f"PII found in data: {', '.join(unique_types)}",
                pii_results=[PIIEntityTypes(t) for t in unique_types],
                pii_entities=spans,
            ),
            prompt_tokens=0,
            completion_tokens=0,
        )
