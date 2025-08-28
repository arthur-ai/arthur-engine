"""
PII (Personally Identifiable Information) Detection Module.

This module provides utilities and classifiers for detecting PII in text data
using both Presidio and GLiNER models.
"""

import logging
import re
import unicodedata
from typing import Any, Dict, List, Set

import torch

from arthur_common.models.enums import PIIEntityTypes, RuleResultEnum
from schemas.scorer_schemas import RuleScore, ScorerPIIEntitySpan, ScorerRuleDetails
from scorer.checks.pii.presidio_gliner_map import PresidioGlinerMapper
from scorer.checks.pii.validations import (
    is_bank_account_number,
    is_credit_card,
    is_crypto,
    is_email_address,
    is_ip,
    is_location,
    is_name,
    is_phone_number,
    is_ssn,
    is_url,
)
from utils.model_load import (
    USE_PII_MODEL_V2,
    get_gliner_model,
    get_gliner_tokenizer,
    get_presidio_analyzer,
)
from utils.text_chunking import ChunkIterator

logging.getLogger("presidio-analyzer").setLevel(logging.ERROR)

MAX_TOKENS_PER_CHUNK = 384


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

    # Entity validation mapping
    ENTITY_VALIDATORS = {
        PIIEntityTypes.IP_ADDRESS.value: is_ip,
        PIIEntityTypes.US_SSN.value: is_ssn,
        PIIEntityTypes.URL.value: is_url,
        PIIEntityTypes.PERSON.value: is_name,
        PIIEntityTypes.CRYPTO.value: is_crypto,
        PIIEntityTypes.US_BANK_NUMBER.value: is_bank_account_number,
        PIIEntityTypes.PHONE_NUMBER.value: is_phone_number,
        PIIEntityTypes.LOCATION.value: is_location,
        PIIEntityTypes.EMAIL_ADDRESS.value: is_email_address,
        PIIEntityTypes.CREDIT_CARD.value: is_credit_card,
    }

    def __init__(self):
        """Initialize the PII classifier as a per-process singleton."""
        self.model = get_gliner_model()
        self.tokenizer = get_gliner_tokenizer()
        self.max_tokens_per_chunk = MAX_TOKENS_PER_CHUNK
        self.analyzer = get_presidio_analyzer()

        # Get all entity values from enum
        entities = PIIEntityTypes.values()

        # Separate entities for Presidio and GLiNER
        if USE_PII_MODEL_V2:
            self.presidio_entities = [
                entity for entity in entities if entity in self.PRESIDIO_SUPPORTED
            ]
            self.gliner_entities = [
                entity for entity in entities if entity not in self.PRESIDIO_SUPPORTED
            ]

            # Convert GLiNER entities to GLiNER format
            self.gliner_entity_types = [
                PresidioGlinerMapper.presidio_to_gliner(entity)
                for entity in self.gliner_entities
            ]
        else:
            self.presidio_entities = entities

    def _remove_overlapping_spans(
        self,
        spans: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Remove overlapping spans using a greedy approach with confidence and length prioritization."""
        if not spans:
            return []

        # Sort by start position, then by confidence (desc), then by length (desc)
        sorted_spans = sorted(
            spans,
            key=lambda s: (s["start"], -s["confidence"], -(s["end"] - s["start"])),
        )

        result = []
        max_end = max((s["end"] for s in spans), default=0)
        occupied = [False] * (max_end + 1)

        for span in sorted_spans:
            # Check if span overlaps with any occupied positions
            if not any(occupied[pos] for pos in range(span["start"], span["end"])):
                result.append(span)
                # Mark positions as occupied
                for pos in range(span["start"], span["end"]):
                    occupied[pos] = True

        return result

    def _postprocess_spans(
        self,
        spans: List[Dict[str, Any]],
        text: str,
        min_len: int = 2,
        merge_distance: int = 2,
    ) -> List[Dict[str, Any]]:
        """Post-process spans by filtering, merging, and validating."""
        # Filter by minimum length
        spans = [s for s in spans if (s["end"] - s["start"]) >= min_len]
        spans.sort(key=lambda s: s["start"])

        # Merge adjacent spans of same entity type
        merged = []
        for span in spans:
            if (
                merged
                and span["entity"] == merged[-1]["entity"]
                and span["start"] - merged[-1]["end"] <= merge_distance
            ):

                last = merged[-1]
                merged[-1] = {
                    "entity": last["entity"],
                    "start": last["start"],
                    "end": span["end"],
                    "span": text[last["start"] : span["end"]],
                    "confidence": max(last["confidence"], span["confidence"]),
                }
            else:
                merged.append(span)

        # Validate and clean spans
        validated = []
        for span in merged:
            clean_value = sanitize_span_text(span["span"])

            # Skip if cleaned value is too short
            if not clean_value or len(clean_value) < min_len:
                continue

            # Validate specific entity types using mapping
            entity_type = span["entity"]
            if entity_type in self.ENTITY_VALIDATORS:
                validator = self.ENTITY_VALIDATORS[entity_type]
                if not validator(clean_value):
                    continue

            span["span"] = clean_value
            validated.append(span)

        return validated

    def _filter_by_allow_list(
        self,
        spans: List[Dict[str, Any]],
        allow_list: List[str],
    ) -> List[Dict[str, Any]]:
        """Filter spans by allow list - remove spans that match allowed patterns."""
        if not allow_list:
            return spans

        filtered_spans = []
        for span in spans:
            span_text = span["span"].lower()
            is_allowed = False

            for allowed_pattern in allow_list:
                if allowed_pattern.lower() in span_text:
                    is_allowed = True
                    break

            if not is_allowed:
                filtered_spans.append(span)

        return filtered_spans

    def score(self, request) -> RuleScore:
        """Score text for PII detection using both Presidio and GLiNER."""
        text = sanitize(request.scoring_text)
        disabled_entities = set(request.disabled_pii_entities or [])
        allow_list = request.allow_list or []
        confidence_threshold = (
            request.pii_confidence_threshold or self.DEFAULT_CONFIDENCE_THRESHOLD
        )

        # Process with Presidio
        # Note: if USE_PII_MODEL_V2 == True then we only process entities that are better handled by Presidio
        all_spans = self._process_presidio(text, disabled_entities, allow_list)

        if USE_PII_MODEL_V2:
            # Process with GLiNER (all other entities) and combine with presidio spans
            all_spans = all_spans + self._process_gliner(text, disabled_entities)

        # Apply confidence threshold
        if confidence_threshold > 0:
            all_spans = [
                span for span in all_spans if span["confidence"] >= confidence_threshold
            ]

        # Apply allow list filtering
        all_spans = self._filter_by_allow_list(all_spans, allow_list)

        # Post-process spans (sanitation and validation) before overlap removal
        processed_spans = self._postprocess_spans(all_spans, text)

        # Remove overlaps after postprocessing
        final_spans = self._remove_overlapping_spans(processed_spans)

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

    def _process_presidio(
        self,
        text: str,
        disabled_entities: Set[str],
        allow_list: List[str],
    ) -> List[Dict[str, Any]]:
        """Process text using Presidio analyzer."""
        # Only use Presidio for entities it handles well, excluding disabled ones
        presidio_entities = [
            entity
            for entity in self.presidio_entities
            if entity not in disabled_entities
        ]

        if not presidio_entities:
            return []

        presidio_results = self.analyzer.analyze(
            text=text,
            entities=presidio_entities,
            allow_list=allow_list,
            language="en",
        )

        # Convert to span format
        return [
            {
                "entity": r.entity_type,
                "span": text[r.start : r.end],
                "start": r.start,
                "end": r.end,
                "confidence": round(r.score, 4),
            }
            for r in presidio_results
        ]

    def _process_gliner(
        self,
        text: str,
        disabled_entities: Set[str],
    ) -> List[Dict[str, Any]]:
        """Process text using GLiNER model."""
        # Get GLiNER entities, excluding those that are disabled
        gliner_entities = [
            entity
            for entity in self.gliner_entity_types
            if PresidioGlinerMapper.gliner_to_presidio(entity) not in disabled_entities
        ]

        if not gliner_entities:
            return []

        gliner_preds = []
        current_offset = 0

        for chunk in ChunkIterator(text, self.tokenizer, self.max_tokens_per_chunk):
            with torch.no_grad():
                preds = self.model.predict_entities(chunk, labels=gliner_entities)
            for pred in preds:
                # Adjust offsets for chunk position
                pred["start"] += current_offset
                pred["end"] += current_offset
                gliner_preds.append(pred)

            # Update offset for next chunk
            current_offset += len(chunk)

        # Convert to span format
        return [
            {
                "entity": PresidioGlinerMapper.gliner_to_presidio(pred["label"]),
                "span": text[pred["start"] : pred["end"]],
                "start": pred["start"],
                "end": pred["end"],
                "confidence": round(pred.get("score", 1.0), 4),
            }
            for pred in gliner_preds
        ]


#########################
### Utility Functions ###
#########################


def sanitize(text: str) -> str:
    """Sanitize text by normalizing unicode, removing control characters, and cleaning whitespace."""
    if not isinstance(text, str):
        return ""

    # Normalize unicode characters
    text = unicodedata.normalize("NFKC", text)

    # Replace pipe with newline for better tokenization
    text = text.replace("|", "\n")

    # Remove control characters except newline and tab
    text = re.sub(r"[\x00-\x09\x0b\x0c\x0e-\x1f\x7f]", " ", text)

    # Replace escaped characters with spaces
    text = text.replace("\\n", " ").replace("\\t", " ").replace("\\r", " ")
    text = re.sub(r"\\x[0-9a-fA-F]{2}", " ", text)

    # Replace actual control characters
    text = text.replace("\r", " ").replace("\t", " ")

    # Clean up whitespace
    text = re.sub(r"[ ]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)

    return text.strip()


def sanitize_span_text(text: str) -> str:
    """Sanitize span text for entity extraction by removing problematic characters."""
    # Replace backslashes and control characters
    text = text.replace("\\", " ")
    text = re.sub(r"[\n\r\t]", " ", text)

    # Replace commas with spaces
    text = text.replace(",", " ")

    # Keep only word characters, @, ., :, /, #, &, +, -
    text = re.sub(r"[^\w@.:/#&+-]", " ", text)

    # Clean up multiple spaces
    text = re.sub(r"\s{2,}", " ", text)

    return text.strip()
