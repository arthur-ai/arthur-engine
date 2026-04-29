"""Wire schemas + vendored enums.

Pydantic request/response models for every `/v1/*` endpoint, plus copies of
the enums the engine uses so the service doesn't depend on `arthur-common`.

Vendored enums (sources):
- PIIEntityTypes, ToxicityViolationType, RuleResultEnum
  ← arthur_common.models.enums
- ClaimClassifierResultEnum
  ← genai-engine/src/schemas/enums.py
- ScorerPIIEntitySpan field shape
  ← genai-engine/src/schemas/scorer_schemas.py:20-23

Service-only additions:
- InferenceResult — tightened RuleResultEnum (drops SKIPPED/UNAVAILABLE,
  which are engine-side concerns).
- PromptInjectionLabel — string enum for the per-chunk classifier output.
"""

from enum import Enum

from pydantic import BaseModel, Field, field_validator

import config as svc_config


# ---------------------------------------------------------------------------
# Vendored enums (sources: arthur_common.models.enums, genai-engine schemas)
# ---------------------------------------------------------------------------


class PIIEntityTypes(str, Enum):
    CREDIT_CARD = "CREDIT_CARD"
    CRYPTO = "CRYPTO"
    DATE_TIME = "DATE_TIME"
    EMAIL_ADDRESS = "EMAIL_ADDRESS"
    IBAN_CODE = "IBAN_CODE"
    IP_ADDRESS = "IP_ADDRESS"
    NRP = "NRP"
    LOCATION = "LOCATION"
    PERSON = "PERSON"
    PHONE_NUMBER = "PHONE_NUMBER"
    MEDICAL_LICENSE = "MEDICAL_LICENSE"
    URL = "URL"
    US_BANK_NUMBER = "US_BANK_NUMBER"
    US_DRIVER_LICENSE = "US_DRIVER_LICENSE"
    US_ITIN = "US_ITIN"
    US_PASSPORT = "US_PASSPORT"
    US_SSN = "US_SSN"


class ToxicityViolationType(str, Enum):
    BENIGN = "benign"
    HARMFUL_REQUEST = "harmful_request"
    TOXIC_CONTENT = "toxic_content"
    PROFANITY = "profanity"
    UNKNOWN = "unknown"


class RuleResultEnum(str, Enum):
    PASS = "Pass"
    FAIL = "Fail"
    SKIPPED = "Skipped"
    UNAVAILABLE = "Unavailable"
    PARTIALLY_UNAVAILABLE = "Partially Unavailable"
    MODEL_NOT_AVAILABLE = "Model Not Available"


class ClaimClassifierResultEnum(str, Enum):
    CLAIM = "claim"
    NONCLAIM = "nonclaim"
    DIALOG = "dialog"


class PromptInjectionLabel(str, Enum):
    INJECTION = "INJECTION"
    SAFE = "SAFE"


# Reduced set used in inference responses. SKIPPED and UNAVAILABLE are
# engine-side states (returned when upstream input is malformed or rule
# evaluation can't proceed) and never originate from a service call.
class InferenceResult(str, Enum):
    PASS = "Pass"
    FAIL = "Fail"
    MODEL_NOT_AVAILABLE = "Model Not Available"


# ---------------------------------------------------------------------------
# Operational endpoint schemas — §3.1
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    status: str = "ok"


class ReadyResponse(BaseModel):
    ready: bool
    models: dict[str, str]  # model_name -> "loaded" | "loading" | "failed"


class ModelInfo(BaseModel):
    name: str
    hf_repo: str
    revision: str | None
    device: str
    loaded_at: str | None  # ISO8601, null if not yet loaded


class ModelsResponse(BaseModel):
    models: list[ModelInfo]


# ---------------------------------------------------------------------------
# Prompt injection — §3.2
# ---------------------------------------------------------------------------


class PromptInjectionRequest(BaseModel):
    text: str = Field(..., max_length=svc_config.MAX_TEXT_CHARS)


class PromptInjectionChunk(BaseModel):
    index: int
    text: str
    label: PromptInjectionLabel
    score: float


class PromptInjectionResponse(BaseModel):
    result: InferenceResult
    chunks: list[PromptInjectionChunk]


# ---------------------------------------------------------------------------
# Toxicity — §3.3
# ---------------------------------------------------------------------------


class ToxicityRequest(BaseModel):
    text: str = Field(..., max_length=svc_config.MAX_TEXT_CHARS)
    threshold: float = Field(..., ge=0.0, le=1.0)
    max_chunk_size: int | None = Field(default=None, gt=0, le=4096)
    harmful_request_max_chunk_size: int | None = Field(default=None, gt=0, le=4096)


class ToxicityResponse(BaseModel):
    result: InferenceResult
    toxicity_score: float
    violation_type: ToxicityViolationType
    profanity_detected: bool
    max_toxicity_score: float
    max_harmful_request_score: float


# ---------------------------------------------------------------------------
# PII — §3.4
# ---------------------------------------------------------------------------


class PIIRequest(BaseModel):
    text: str = Field(..., max_length=svc_config.MAX_TEXT_CHARS)
    disabled_entities: list[str] = Field(default_factory=list)
    allow_list: list[str] = Field(default_factory=list)
    confidence_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    use_v2: bool = True


class PIIEntitySpan(BaseModel):
    entity: PIIEntityTypes
    span: str
    confidence: float


class PIIResponse(BaseModel):
    result: InferenceResult
    entities: list[PIIEntitySpan]


# ---------------------------------------------------------------------------
# Hallucination claim filter — §3.5
# ---------------------------------------------------------------------------


class ClaimFilterRequest(BaseModel):
    texts: list[str] = Field(
        ...,
        max_length=svc_config.MAX_TEXTS_ITEMS,
    )

    @field_validator("texts")
    @classmethod
    def _check_item_lengths(cls, v: list[str]) -> list[str]:
        for i, item in enumerate(v):
            if len(item) > svc_config.MAX_TEXT_ITEM_CHARS:
                raise ValueError(
                    f"texts[{i}] exceeds {svc_config.MAX_TEXT_ITEM_CHARS} chars",
                )
        return v


class ClaimClassification(BaseModel):
    text: str
    label: ClaimClassifierResultEnum
    confidence: float


class ClaimFilterResponse(BaseModel):
    classifications: list[ClaimClassification]


# ---------------------------------------------------------------------------
# Errors — §3.7
# ---------------------------------------------------------------------------


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
