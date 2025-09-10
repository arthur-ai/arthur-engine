import logging

from arthur_common.models.enums import PIIEntityTypes, RuleResultEnum
from presidio_analyzer import AnalyzerEngine

from schemas.scorer_schemas import (
    RuleScore,
    ScoreRequest,
    ScorerPIIEntitySpan,
    ScorerRuleDetails,
)
from scorer.scorer import RuleScorer

logging.getLogger("presidio-analyzer").setLevel(logging.ERROR)


class BinaryPIIDataClassifierV1(RuleScorer):
    def __init__(self):
        """Initialized the binary classifier for PII Data"""
        self.analyzer = AnalyzerEngine()
        self.default_confidence_threshold = 0.5

    def score(self, request: ScoreRequest) -> RuleScore:
        """Scores request for PII"""
        if request.pii_confidence_threshold is not None:
            confidence_threshold = request.pii_confidence_threshold
        else:
            confidence_threshold = self.default_confidence_threshold

        # Pre PII analyzer - resolve the PII entities to check for using disabled_pii_entities if present
        entities_to_check = PIIEntityTypes.values()
        disabled_pii_entities = request.disabled_pii_entities
        if disabled_pii_entities:
            entities_to_check = [
                entity
                for entity in entities_to_check
                if entity not in disabled_pii_entities
            ]

        results = self.analyzer.analyze(
            text=request.scoring_text,
            entities=entities_to_check,
            allow_list=request.allow_list,
            language="en",
        )

        # Post PII analyzer - enforce our threshold on results, if there is one present
        results = [result for result in results if result.score >= confidence_threshold]

        if len(results) == 0:
            return RuleScore(
                result=RuleResultEnum.PASS,
                prompt_tokens=0,
                completion_tokens=0,
            )
        else:
            found_types = [res.entity_type for res in results]
            entity_spans = [
                ScorerPIIEntitySpan(
                    entity=res.entity_type,
                    span=request.scoring_text[res.start : res.end],
                    confidence=res.score,
                )
                for res in results
            ]
            message_string = f"PII found in data: {','.join(found_types)}"
            return RuleScore(
                result=RuleResultEnum.FAIL,
                details=ScorerRuleDetails(
                    message=message_string,
                    pii_results=found_types,
                    pii_entities=entity_spans,
                ),
                prompt_tokens=0,
                completion_tokens=0,
            )
