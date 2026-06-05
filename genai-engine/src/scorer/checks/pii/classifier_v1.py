import logging

from arthur_common.models.enums import PIIEntityTypes, RuleResultEnum
from presidio_analyzer import AnalyzerEngine

from schemas.scorer_schemas import (
    RuleScore,
    ScoreRequest,
    ScorerPIIEntitySpan,
    ScorerRuleDetails,
)
from scorer.checks.pii.classifier import get_gliner_model, get_gliner_tokenizer
from scorer.checks.pii.pii_utils import (
    filter_by_allow_list,
    postprocess_spans,
    process_gliner,
    process_presidio,
)
from scorer.checks.pii.presidio_gliner_map import PresidioGlinerMapper
from scorer.checks.pii.validations import is_name
from scorer.scorer import RuleScorer

logging.getLogger("presidio-analyzer").setLevel(logging.ERROR)


class BinaryPIIDataClassifierV1(RuleScorer):
    def __init__(self) -> None:
        """Initialized the binary classifier for PII Data"""
        self.analyzer: AnalyzerEngine = AnalyzerEngine()
        self.default_confidence_threshold: float = 0.5
        self.gliner_model = get_gliner_model()
        self.gliner_tokenizer = get_gliner_tokenizer()

        # Get all entity values from enum
        entities = PIIEntityTypes.values()

        self.presidio_entities = [
            entity
            for entity in entities
            if entity not in [PIIEntityTypes.US_PASSPORT.value]
        ]
        self.gliner_entity_types = [
            PresidioGlinerMapper.presidio_to_gliner(PIIEntityTypes.US_PASSPORT.value),
        ]

    def score(self, request: ScoreRequest) -> RuleScore:
        """Scores request for PII"""
        if request.pii_confidence_threshold is not None:
            confidence_threshold = request.pii_confidence_threshold
        else:
            confidence_threshold = self.default_confidence_threshold

        # Pre PII analyzer - resolve the PII entities to check for using disabled_pii_entities if present

        disabled_pii_entities = set(request.disabled_pii_entities or [])

        if not request.scoring_text:
            return RuleScore(
                result=RuleResultEnum.PASS,
                prompt_tokens=0,
                completion_tokens=0,
            )

        presidio_spans = process_presidio(
            request.scoring_text,
            self.analyzer,
            self.presidio_entities,
            disabled_pii_entities,
            request.allow_list,
        )

        # Process with GLiNER (all other entities) and combine with presidio spans
        gliner_spans = process_gliner(
            request.scoring_text,
            self.gliner_entity_types,
            disabled_pii_entities,
            self.gliner_model,
            self.gliner_tokenizer,
        )

        # Apply allow list filtering
        gliner_spans = filter_by_allow_list(gliner_spans, request.allow_list)

        # Post-process spans (sanitation and validation) before overlap removal
        gliner_spans = postprocess_spans(gliner_spans, request.scoring_text)

        # Combine presidio and gliner spans
        all_spans = presidio_spans + gliner_spans

        # Drop PERSON detections that fail name validation (e.g. contain digits) —
        # Presidio's NER tags strings like "Order 7423" or "User 4" as PERSON.
        all_spans = [
            span
            for span in all_spans
            if span["entity"] != PIIEntityTypes.PERSON.value
            or is_name(request.scoring_text[span["start"] : span["end"]])
        ]

        # Apply confidence threshold
        final_spans = [
            result
            for result in all_spans
            if result["confidence"] >= confidence_threshold
        ]

        if not final_spans:
            return RuleScore(
                result=RuleResultEnum.PASS,
                prompt_tokens=0,
                completion_tokens=0,
            )

        # Get unique entity types found
        entity_types = [span["entity"] for span in final_spans]

        # Convert spans to ScorerPIIEntitySpan objects
        pii_entity_spans = [
            ScorerPIIEntitySpan(
                entity=PIIEntityTypes(span["entity"]),
                span=span["span"],
                confidence=span["confidence"],
            )
            for span in final_spans
        ]

        return RuleScore(
            result=RuleResultEnum.FAIL,
            details=ScorerRuleDetails(
                message=f"PII found in data: {', '.join(entity_types)}",
                pii_results=[
                    PIIEntityTypes(entity_type) for entity_type in entity_types
                ],
                pii_entities=pii_entity_spans,
            ),
            prompt_tokens=0,
            completion_tokens=0,
        )
