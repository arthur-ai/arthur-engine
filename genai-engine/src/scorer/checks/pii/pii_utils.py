import re
import unicodedata
from typing import Any, List, Optional, Set

import torch
from arthur_common.models.enums import PIIEntityTypes
from gliner import GLiNER
from presidio_analyzer import AnalyzerEngine
from transformers.tokenization_utils_base import PreTrainedTokenizerBase

from schemas.scorer_schemas import DateTimeSpan
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
    is_us_passport,
)
from utils.text_chunking import ChunkIterator

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
    PIIEntityTypes.US_PASSPORT.value: is_us_passport,
}
MAX_TOKENS_PER_CHUNK = 384

#########################
### Helper Functions ####
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


####################################
##### PII Processing Functions #####
####################################


def process_presidio(
    text: str,
    analyzer: Optional[AnalyzerEngine],
    presidio_entities: list[str],
    disabled_entities: set[str],
    allow_list: Optional[list[str]],
) -> list[DateTimeSpan]:
    """Process text using Presidio analyzer."""
    if analyzer is None:
        return []

    # Only use Presidio for entities it handles well, excluding disabled ones
    presidio_entities = [
        entity for entity in presidio_entities if entity not in disabled_entities
    ]

    if not presidio_entities:
        return []

    presidio_results = analyzer.analyze(
        text=text,
        entities=presidio_entities,
        allow_list=allow_list,
        language="en",
    )

    # Convert to span format
    return [
        DateTimeSpan(
            entity=r.entity_type,
            span=text[r.start : r.end],
            start=r.start,
            end=r.end,
            confidence=round(r.score, 4),
        )
        for r in presidio_results
    ]


def process_gliner(
    text: str,
    gliner_entity_types: List[str],
    disabled_entities: Set[str],
    model: Optional[GLiNER],
    tokenizer: Optional[PreTrainedTokenizerBase],
    max_tokens_per_chunk: int = MAX_TOKENS_PER_CHUNK,
) -> list[DateTimeSpan]:
    """Process text using GLiNER model."""
    if model is None or tokenizer is None:
        return []

    # Get GLiNER entities, excluding those that are disabled
    gliner_entities = [
        entity
        for entity in gliner_entity_types
        if PresidioGlinerMapper.gliner_to_presidio(entity) not in disabled_entities
    ]

    if not gliner_entities:
        return []

    gliner_preds: list[dict[str, Any]] = []
    current_offset: int = 0

    for chunk in ChunkIterator(text, tokenizer, max_tokens_per_chunk):
        with torch.no_grad():
            preds = model.predict_entities(chunk, labels=gliner_entities)
        for pred in preds:
            # Adjust offsets for chunk position
            pred["start"] += current_offset
            pred["end"] += current_offset
            gliner_preds.append(pred)

        # Update offset for next chunk
        current_offset += len(chunk)

    # Convert to span format
    return [
        DateTimeSpan(
            entity=PresidioGlinerMapper.gliner_to_presidio(pred["label"]),
            span=text[pred["start"] : pred["end"]],
            start=pred["start"],
            end=pred["end"],
            confidence=round(pred.get("score", 1.0), 4),
        )
        for pred in gliner_preds
    ]


####################################
### PII Postprocessing Functions ###
####################################


def remove_overlapping_spans(
    spans: list[DateTimeSpan],
) -> list[DateTimeSpan]:
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


def postprocess_spans(
    spans: list[DateTimeSpan],
    text: str,
    min_len: int = 2,
    merge_distance: int = 2,
) -> list[DateTimeSpan]:
    """Post-process spans by filtering, merging, and validating."""
    # Filter by minimum length
    spans = [s for s in spans if (s["end"] - s["start"]) >= min_len]
    spans.sort(key=lambda s: s["start"])

    # Merge adjacent spans of same entity type
    merged: list[DateTimeSpan] = []
    for span in spans:
        if (
            merged
            and span["entity"] == merged[-1]["entity"]
            and span["start"] - merged[-1]["end"] <= merge_distance
        ):

            last = merged[-1]
            merged[-1] = DateTimeSpan(
                entity=last["entity"],
                start=last["start"],
                end=span["end"],
                span=text[last["start"] : span["end"]],
                confidence=max(last["confidence"], span["confidence"]),
            )
        else:
            merged.append(span)

    # Validate and clean spans
    validated: list[DateTimeSpan] = []
    for span in merged:
        clean_value = sanitize_span_text(span["span"])

        # Skip if cleaned value is too short
        if not clean_value or len(clean_value) < min_len:
            continue

        # Validate specific entity types using mapping
        entity_type = span["entity"]
        if entity_type in ENTITY_VALIDATORS:
            validator = ENTITY_VALIDATORS[entity_type]
            if not validator(clean_value):
                continue

        span["span"] = clean_value
        validated.append(span)

    return validated


def filter_by_allow_list(
    spans: list[DateTimeSpan],
    allow_list: Optional[list[str]],
) -> list[DateTimeSpan]:
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
