"""
PII (Personally Identifiable Information) Detection Module.

This module provides utilities and classifiers for detecting PII in text data
using both Presidio and GLiNER models.
"""

import logging
import re

import spacy
from arthur_common.models.enums import PIIEntityTypes, RuleResultEnum
from date_spacy import find_dates  # noqa: F401 - Import registers the component

from schemas.scorer_schemas import (
    DateTimeSpan,
    RuleScore,
    ScoreRequest,
    ScorerPIIEntitySpan,
    ScorerRuleDetails,
)
from scorer.checks.pii.pii_utils import (
    MAX_TOKENS_PER_CHUNK,
    filter_by_allow_list,
    postprocess_spans,
    process_gliner,
    process_presidio,
    remove_overlapping_spans,
    sanitize,
)
from scorer.checks.pii.presidio_gliner_map import PresidioGlinerMapper
from utils.model_load import (
    get_gliner_model,
    get_gliner_tokenizer,
    get_presidio_analyzer,
)

logging.getLogger("presidio-analyzer").setLevel(logging.ERROR)


class BinaryPIIDataClassifier:
    """Binary PII classifier using both Presidio and GLiNER models."""

    # Entities that are better handled by Presidio (more accurate/reliable)
    PRESIDIO_SUPPORTED = {
        PIIEntityTypes.EMAIL_ADDRESS.value,
        PIIEntityTypes.IBAN_CODE.value,
        PIIEntityTypes.IP_ADDRESS.value,
        PIIEntityTypes.US_SSN.value,
    }

    # All other entities from PIIEntityTypes will be handled by GLiNER
    DEFAULT_CONFIDENCE_THRESHOLD = 0.5

    def __init__(self) -> None:
        """Initialize the PII classifier as a per-process singleton."""
        self.model = get_gliner_model()
        self.tokenizer = get_gliner_tokenizer()
        self.max_tokens_per_chunk = MAX_TOKENS_PER_CHUNK
        self.analyzer = get_presidio_analyzer()

        # Initialize spaCy with date_spacy for datetime detection
        # Create a minimal pipeline without NER to avoid entity conflicts
        self.date_nlp = spacy.load("en_core_web_lg", exclude=["ner"])
        self.date_nlp.add_pipe("find_dates")

        # Get all entity values from enum
        entities = PIIEntityTypes.values()

        # Separate entities for Presidio, date_spacy, and GLiNER
        self.presidio_entities = [
            entity for entity in entities if entity in self.PRESIDIO_SUPPORTED
        ]
        # Exclude DATE_TIME from GLiNER - it will be handled by date_spacy
        self.gliner_entities = [
            entity
            for entity in entities
            if entity not in self.PRESIDIO_SUPPORTED
            and entity != PIIEntityTypes.DATE_TIME.value
        ]

        # Convert GLiNER entities to GLiNER format
        self.gliner_entity_types = [
            PresidioGlinerMapper.presidio_to_gliner(entity)
            for entity in self.gliner_entities
        ]

    def score(self, request: ScoreRequest) -> RuleScore:
        """Score text for PII detection using Presidio, GLiNER, and date_spacy."""
        text = sanitize(request.scoring_text or "")
        disabled_entities = set(request.disabled_pii_entities or [])
        allow_list = request.allow_list or []
        confidence_threshold = (
            request.pii_confidence_threshold or self.DEFAULT_CONFIDENCE_THRESHOLD
        )

        # Process with Presidio
        all_spans = process_presidio(
            text,
            self.analyzer,
            self.presidio_entities,
            disabled_entities,
            allow_list,
        )

        # Process with GLiNER (all other entities except DATE_TIME)
        all_spans = all_spans + process_gliner(
            text,
            self.gliner_entity_types,
            disabled_entities,
            self.model,
            self.tokenizer,
            self.max_tokens_per_chunk,
        )

        # Process with date_spacy for DATE_TIME entities
        all_spans = all_spans + self._process_date_spacy(text, disabled_entities)

        # Apply confidence threshold
        if confidence_threshold > 0:
            all_spans = [
                span for span in all_spans if span["confidence"] >= confidence_threshold
            ]

        # Apply allow list filtering
        all_spans = filter_by_allow_list(all_spans, allow_list)

        # Post-process spans (sanitation and validation) before overlap removal
        processed_spans = postprocess_spans(all_spans, text)

        # Remove overlaps after postprocessing
        final_spans = remove_overlapping_spans(processed_spans)

        if not final_spans:
            return RuleScore(
                result=RuleResultEnum.PASS,
                prompt_tokens=0,
                completion_tokens=0,
            )

        # Get unique entity types found
        entity_types = sorted(set(span["entity"] for span in final_spans))

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

    def _process_date_spacy(
        self,
        text: str,
        disabled_entities: set[str],
    ) -> list[DateTimeSpan]:
        """
        Process text using date_spacy NER + pattern-based supplementation.

        Strategy:
        1. Run spaCy NER first (intelligent, context-aware)
        2. Supplement with pattern matching for specific cases spaCy misses
        3. Generic filtering happens in postprocessing via is_datetime()
        """
        if PIIEntityTypes.DATE_TIME.value in disabled_entities:
            return []

        datetime_spans: list[DateTimeSpan] = []

        # Phase 1: spaCy NER (intelligent, context-aware detection)
        doc = self.date_nlp(text)
        for ent in doc.ents:
            if ent.label_ == "DATE":
                # Check if the entity has a parsed date
                parsed_date = ent._.date if hasattr(ent._, "date") else None

                if parsed_date is not None:
                    datetime_spans.append(
                        DateTimeSpan(
                            entity=PIIEntityTypes.DATE_TIME.value,
                            span=ent.text,
                            start=ent.start_char,
                            end=ent.end_char,
                            confidence=0.95,  # High confidence for spaCy NER
                        ),
                    )

        # Phase 2: Pattern-based supplementation for specific patterns spaCy misses
        datetime_patterns = [
            # Day names
            r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b",
            r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b",
            # Month + Year combinations
            r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b",
            r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{2,4}\b",
            # Full date patterns
            r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{2,4}\b",
            r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)(?:,?\s*\d{2,4})?\b",
            # Year patterns
            r"\b(19|20)\d{2}\b",
            # Time patterns
            r"\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:am|pm|AM|PM|a\.m\.|p\.m\.)\b",
            r"\b\d{1,2}\s*(?:am|pm|AM|PM|a\.m\.|p\.m\.)\b",
            r"\b\d{1,2}\s*o'?clock\b",
            r"\b(?:noon|midnight)\b",
            r"\bquarter\s+past\b",
            # Date formats
            r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
            r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b",
            # Quantified time units (specific durations)
            r"\b\d+\s*(?:seconds?|minutes?|hours?|days?|weeks?|months?|years?)\b",
            r"\b\d+\s*(?:secs?|mins?|hrs?|wks?|yrs?)\b",
            # Quarters
            r"\bQ[1-4]\s*\d{4}\b",
            # Holidays
            r"\b(?:Christmas|Xmas|Easter|Halloween|Valentine|Thanksgiving|New\s+Year)\b",
        ]

        for pattern in datetime_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                span_text = match.group().strip()
                start_pos = match.start()
                end_pos = match.end()

                # Avoid duplicates - check if overlaps with spaCy detections
                overlaps = any(
                    span["start"] <= start_pos < span["end"]
                    or span["start"] < end_pos <= span["end"]
                    or start_pos <= span["start"] < end_pos
                    for span in datetime_spans
                )

                if not overlaps and span_text:
                    datetime_spans.append(
                        {
                            "entity": PIIEntityTypes.DATE_TIME.value,
                            "span": span_text,
                            "start": start_pos,
                            "end": end_pos,
                            "confidence": 0.9,  # Slightly lower for pattern matches
                        },
                    )

        return datetime_spans
