"""PII inference (v1 + v2).

Migrated from genai-engine/src/scorer/checks/pii/classifier.py (v2) and
classifier_v1.py. The two implementations share a wire schema; the request's
`use_v2` flag picks which path runs server-side.

v1 (Presidio only, no torch): rule-based analyze across all PIIEntityTypes,
filter by confidence threshold, return spans.

v2 (Presidio + GLiNER + spaCy): Presidio handles the entities it does best
(EMAIL_ADDRESS, IP_ADDRESS, IBAN_CODE, US_SSN); GLiNER handles everything
else; spaCy en_core_web_lg + date_spacy detect DATE_TIME. Spans go through
allow-list filtering, entity-type validators, sanitization, and overlap
removal before being returned.

API contract:
    POST /v1/inference/pii
    Request:
        {
            "text": str,
            "disabled_entities": [PIIEntityTypes],   # default []
            "allow_list": [str],                     # default []
            "confidence_threshold": float | null,    # default 0.5
            "use_v2": bool                           # required
        }
    Response:
        {
            "result": "Pass" | "Fail" | "Model Not Available",
            "entities": [
                {
                    "entity": PIIEntityTypes,        # enum value as string
                    "span": str,
                    "confidence": float
                }
            ]
        }
    Behavior:
        - Empty text → result=Pass, entities=[].
        - result=Fail iff at least one entity survives all filters.
        - For v2, GLiNER weights are required — service returns
          Model Not Available if they failed to load.
        - Unique entity types are derivable client-side from `entities`;
          they are not duplicated on the wire.
"""

import logging
import re
import unicodedata
from typing import TypedDict

import torch

from inference.pii.presidio_gliner_map import PresidioGlinerMapper
from inference.pii.validations import (
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
from inference.text_chunking import ChunkIterator
from model_registry import loader
from schemas import (
    InferenceResult,
    PIIEntitySpan,
    PIIEntityTypes,
    PIIRequest,
    PIIResponse,
)

logger = logging.getLogger(__name__)
logging.getLogger("presidio-analyzer").setLevel(logging.ERROR)


MAX_TOKENS_PER_CHUNK = 384
DEFAULT_CONFIDENCE_THRESHOLD = 0.5

# Entities Presidio handles better than GLiNER (regex+context-driven).
PRESIDIO_SUPPORTED = {
    PIIEntityTypes.EMAIL_ADDRESS.value,
    PIIEntityTypes.IBAN_CODE.value,
    PIIEntityTypes.IP_ADDRESS.value,
    PIIEntityTypes.US_SSN.value,
}

# Entity → custom validator (drops descriptive text that looked like PII).
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


class _Span(TypedDict):
    entity: str
    span: str
    start: int
    end: int
    confidence: float


# ---------------------------------------------------------------------------
# Sanitation — lifted from classifier.py:475-518
# ---------------------------------------------------------------------------


def _sanitize(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("|", "\n")
    text = re.sub(r"[\x00-\x09\x0b\x0c\x0e-\x1f\x7f]", " ", text)
    text = text.replace("\\n", " ").replace("\\t", " ").replace("\\r", " ")
    text = re.sub(r"\\x[0-9a-fA-F]{2}", " ", text)
    text = text.replace("\r", " ").replace("\t", " ")
    text = re.sub(r"[ ]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()


def _sanitize_span(text: str) -> str:
    text = text.replace("\\", " ")
    text = re.sub(r"[\n\r\t]", " ", text)
    text = text.replace(",", " ")
    text = re.sub(r"[^\w@.:/#&+-]", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Entity providers
# ---------------------------------------------------------------------------


def _process_presidio(
    text: str,
    presidio_entities: list[str],
    disabled: set[str],
    allow_list: list[str],
) -> list[_Span]:
    enabled = [e for e in presidio_entities if e not in disabled]
    if not enabled:
        return []
    analyzer = loader.get_presidio_analyzer()
    if analyzer is None:
        return []
    results = analyzer.analyze(
        text=text,
        entities=enabled,
        allow_list=allow_list,
        language="en",
    )
    return [
        _Span(
            entity=r.entity_type,
            span=text[r.start : r.end],
            start=r.start,
            end=r.end,
            confidence=round(r.score, 4),
        )
        for r in results
    ]


def _process_gliner(
    text: str,
    gliner_entity_types: list[str],
    disabled: set[str],
) -> list[_Span]:
    model = loader.get_gliner_model()
    tokenizer = loader.get_gliner_tokenizer()
    if model is None or tokenizer is None:
        return []

    enabled = [
        e
        for e in gliner_entity_types
        if PresidioGlinerMapper.gliner_to_presidio(e) not in disabled
    ]
    if not enabled:
        return []

    spans: list[_Span] = []
    offset = 0
    for chunk in ChunkIterator(text, tokenizer, MAX_TOKENS_PER_CHUNK):
        with torch.no_grad():
            preds = model.predict_entities(chunk, labels=enabled)
        for pred in preds:
            spans.append(
                _Span(
                    entity=PresidioGlinerMapper.gliner_to_presidio(pred["label"]),
                    span=text[pred["start"] + offset : pred["end"] + offset],
                    start=pred["start"] + offset,
                    end=pred["end"] + offset,
                    confidence=round(pred.get("score", 1.0), 4),
                ),
            )
        offset += len(chunk)
    return spans


# Datetime patterns lifted from classifier.py:412-440.
_DATETIME_PATTERNS = [
    r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b",
    r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b",
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b",
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{2,4}\b",
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{2,4}\b",
    r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)(?:,?\s*\d{2,4})?\b",
    r"\b(19|20)\d{2}\b",
    r"\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:am|pm|AM|PM|a\.m\.|p\.m\.)\b",
    r"\b\d{1,2}\s*(?:am|pm|AM|PM|a\.m\.|p\.m\.)\b",
    r"\b\d{1,2}\s*o'?clock\b",
    r"\b(?:noon|midnight)\b",
    r"\bquarter\s+past\b",
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b",
    r"\b\d+\s*(?:seconds?|minutes?|hours?|days?|weeks?|months?|years?)\b",
    r"\b\d+\s*(?:secs?|mins?|hrs?|wks?|yrs?)\b",
    r"\bQ[1-4]\s*\d{4}\b",
    r"\b(?:Christmas|Xmas|Easter|Halloween|Valentine|Thanksgiving|New\s+Year)\b",
]


def _process_date_spacy(text: str, disabled: set[str]) -> list[_Span]:
    if PIIEntityTypes.DATE_TIME.value in disabled:
        return []

    spans: list[_Span] = []

    nlp = loader.get_spacy_date_nlp()
    if nlp is not None:
        doc = nlp(text)
        for ent in doc.ents:
            if ent.label_ != "DATE":
                continue
            parsed_date = ent._.date if hasattr(ent._, "date") else None
            if parsed_date is None:
                continue
            spans.append(
                _Span(
                    entity=PIIEntityTypes.DATE_TIME.value,
                    span=ent.text,
                    start=ent.start_char,
                    end=ent.end_char,
                    confidence=0.95,
                ),
            )

    # Pattern supplementation for cases spaCy misses.
    for pattern in _DATETIME_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            span_text = match.group().strip()
            start = match.start()
            end = match.end()
            overlaps = any(
                s["start"] <= start < s["end"]
                or s["start"] < end <= s["end"]
                or start <= s["start"] < end
                for s in spans
            )
            if not overlaps and span_text:
                spans.append(
                    _Span(
                        entity=PIIEntityTypes.DATE_TIME.value,
                        span=span_text,
                        start=start,
                        end=end,
                        confidence=0.9,
                    ),
                )

    return spans


# ---------------------------------------------------------------------------
# Post-processing: filter, validate, merge, dedupe
# ---------------------------------------------------------------------------


def _filter_by_allow_list(spans: list[_Span], allow_list: list[str]) -> list[_Span]:
    if not allow_list:
        return spans
    out: list[_Span] = []
    for span in spans:
        s = span["span"].lower()
        if any(allowed.lower() in s for allowed in allow_list):
            continue
        out.append(span)
    return out


def _postprocess(
    spans: list[_Span],
    text: str,
    min_len: int = 2,
    merge_distance: int = 2,
) -> list[_Span]:
    spans = [s for s in spans if (s["end"] - s["start"]) >= min_len]
    spans.sort(key=lambda s: s["start"])

    # Merge adjacent same-entity spans.
    merged: list[_Span] = []
    for span in spans:
        if (
            merged
            and span["entity"] == merged[-1]["entity"]
            and span["start"] - merged[-1]["end"] <= merge_distance
        ):
            last = merged[-1]
            merged[-1] = _Span(
                entity=last["entity"],
                start=last["start"],
                end=span["end"],
                span=text[last["start"] : span["end"]],
                confidence=max(last["confidence"], span["confidence"]),
            )
        else:
            merged.append(span)

    # Validate + sanitize.
    out: list[_Span] = []
    for span in merged:
        clean = _sanitize_span(span["span"])
        if not clean or len(clean) < min_len:
            continue
        validator = ENTITY_VALIDATORS.get(span["entity"])
        if validator and not validator(clean):
            continue
        span["span"] = clean
        out.append(span)
    return out


def _remove_overlapping(spans: list[_Span]) -> list[_Span]:
    if not spans:
        return []
    sorted_spans = sorted(
        spans,
        key=lambda s: (s["start"], -s["confidence"], -(s["end"] - s["start"])),
    )
    max_end = max(s["end"] for s in spans)
    occupied = [False] * (max_end + 1)
    out: list[_Span] = []
    for span in sorted_spans:
        if not any(occupied[p] for p in range(span["start"], span["end"])):
            out.append(span)
            for p in range(span["start"], span["end"]):
                occupied[p] = True
    return out


# ---------------------------------------------------------------------------
# v1 (Presidio only) and v2 (full pipeline) entry points
# ---------------------------------------------------------------------------


def _classify_v1(req: PIIRequest) -> PIIResponse:
    analyzer = loader.get_presidio_analyzer()
    if analyzer is None:
        return PIIResponse(result=InferenceResult.MODEL_NOT_AVAILABLE, entities=[])

    if not req.text:
        return PIIResponse(result=InferenceResult.PASS, entities=[])

    threshold = req.confidence_threshold or DEFAULT_CONFIDENCE_THRESHOLD
    disabled = set(req.disabled_entities)
    entities = [e.value for e in PIIEntityTypes if e.value not in disabled]

    results = analyzer.analyze(
        text=req.text,
        entities=entities,
        allow_list=req.allow_list,
        language="en",
    )
    results = [r for r in results if r.score >= threshold]
    if not results:
        return PIIResponse(result=InferenceResult.PASS, entities=[])

    return PIIResponse(
        result=InferenceResult.FAIL,
        entities=[
            PIIEntitySpan(
                entity=PIIEntityTypes(r.entity_type),
                span=req.text[r.start : r.end],
                confidence=r.score,
            )
            for r in results
        ],
    )


def _classify_v2(req: PIIRequest) -> PIIResponse:
    if loader.get_gliner_model() is None:
        # GLiNER unavailable — the engine should have used v1 instead. Surface
        # MODEL_NOT_AVAILABLE rather than silently degrade.
        return PIIResponse(result=InferenceResult.MODEL_NOT_AVAILABLE, entities=[])

    text = _sanitize(req.text)
    if not text:
        return PIIResponse(result=InferenceResult.PASS, entities=[])

    threshold = req.confidence_threshold or DEFAULT_CONFIDENCE_THRESHOLD
    disabled = set(req.disabled_entities)
    all_entities = [e.value for e in PIIEntityTypes]

    presidio_entities = [e for e in all_entities if e in PRESIDIO_SUPPORTED]
    gliner_entities = [
        e
        for e in all_entities
        if e not in PRESIDIO_SUPPORTED and e != PIIEntityTypes.DATE_TIME.value
    ]
    gliner_entity_types = [
        PresidioGlinerMapper.presidio_to_gliner(e) for e in gliner_entities
    ]

    spans: list[_Span] = []
    spans.extend(_process_presidio(text, presidio_entities, disabled, req.allow_list))
    spans.extend(_process_gliner(text, gliner_entity_types, disabled))
    spans.extend(_process_date_spacy(text, disabled))

    # Confidence threshold.
    spans = [s for s in spans if s["confidence"] >= threshold]
    spans = _filter_by_allow_list(spans, req.allow_list)
    spans = _postprocess(spans, text)
    spans = _remove_overlapping(spans)

    if not spans:
        return PIIResponse(result=InferenceResult.PASS, entities=[])

    return PIIResponse(
        result=InferenceResult.FAIL,
        entities=[
            PIIEntitySpan(
                entity=PIIEntityTypes(s["entity"]),
                span=s["span"],
                confidence=s["confidence"],
            )
            for s in spans
        ],
    )


def classify(req: PIIRequest) -> PIIResponse:
    return _classify_v2(req) if req.use_v2 else _classify_v1(req)
