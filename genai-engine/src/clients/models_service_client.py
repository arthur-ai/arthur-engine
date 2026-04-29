"""HTTP client for the sideloaded models service.

Behavior:
- Bearer header from MODEL_REGISTRY_SECRET; base URL from MODELS_SERVICE_URL.
  Both are required at construction; the constructor raises if either is
  unset.
- Tenacity retries (3 attempts, exponential backoff) on transport errors
  and 5xx responses.
- After retries exhaust: 5xx and `model_not_available` body codes are
  translated into ModelNotAvailableError. Each scorer catches that and
  returns RuleResultEnum.MODEL_NOT_AVAILABLE, preserving the engine's
  legacy "model not loaded" behavior.
- 4xx other than `model_not_available` (validation_failed, payload_too_large)
  raise ModelsServiceClientError — these are caller bugs, not transient
  service issues, and should surface to the developer.
- W3C traceparent header is auto-injected by HTTPXClientInstrumentor so
  service-side spans nest under the engine's request span.

Public surface (signatures match the wire schemas exactly):
    prompt_injection(text: str) -> PromptInjectionResponse
    toxicity(text: str, threshold: float) -> ToxicityResponse
    pii(
        text: str,
        disabled_entities: list[str] | None = None,
        allow_list: list[str] | None = None,
        confidence_threshold: float | None = None,
        use_v2: bool = True,
    ) -> PIIResponse
    claim_filter(texts: list[str]) -> ClaimFilterResponse
"""

import logging
import os
from typing import Any

import httpx
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from pydantic import BaseModel
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# Default timeout: connect + read. Inference can be slow on first hit so
# we leave generous read timeout but tighten connect.
DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=10.0)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ModelsServiceError(Exception):
    """Generic transport / protocol error."""


class ModelNotAvailableError(ModelsServiceError):
    """Either the service returned `model_not_available` or a 5xx exhausted retries.

    The scorer-side wrapper translates this to RuleResultEnum.MODEL_NOT_AVAILABLE.
    """


class ModelsServiceClientError(ModelsServiceError):
    """4xx that isn't `model_not_available` — programmer error, surface to caller."""


# ---------------------------------------------------------------------------
# Response DTOs — must match models-service/src/schemas.py wire shapes
# ---------------------------------------------------------------------------


class _PromptInjectionChunk(BaseModel):
    index: int
    text: str
    label: str
    score: float


class PromptInjectionResponse(BaseModel):
    result: str  # "Pass" | "Fail" | "Model Not Available"
    chunks: list[_PromptInjectionChunk]


class ToxicityResponse(BaseModel):
    result: str
    toxicity_score: float
    violation_type: str
    profanity_detected: bool
    max_toxicity_score: float
    max_harmful_request_score: float


class _PIIEntitySpan(BaseModel):
    entity: str
    span: str
    confidence: float


class PIIResponse(BaseModel):
    result: str
    entities: list[_PIIEntitySpan]


class _ClaimClassification(BaseModel):
    text: str
    label: str
    confidence: float


class ClaimFilterResponse(BaseModel):
    classifications: list[_ClaimClassification]


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

# Apply httpx auto-instrumentation once at import time. Subsequent client
# instances pick it up automatically.
HTTPXClientInstrumentor().instrument()


class ModelsServiceClient:
    """Thin synchronous HTTP client for the models service."""

    def __init__(
        self,
        base_url: str | None = None,
        secret: str | None = None,
        timeout: httpx.Timeout | None = None,
    ) -> None:
        self._base_url = (base_url or os.environ.get("MODELS_SERVICE_URL", "")).rstrip("/")
        self._secret = secret or os.environ.get("MODEL_REGISTRY_SECRET", "")
        if not self._base_url:
            raise ValueError("MODELS_SERVICE_URL is not set")
        if not self._secret:
            raise ValueError("MODEL_REGISTRY_SECRET is not set")
        self._client = httpx.Client(
            base_url=self._base_url,
            timeout=timeout or DEFAULT_TIMEOUT,
            headers={"Authorization": f"Bearer {self._secret}"},
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ModelsServiceClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # -----------------------------------------------------------------------
    # Internal request loop with retries on 5xx
    # -----------------------------------------------------------------------

    @retry(
        retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4.0),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._client.post(path, json=body)
        except httpx.TransportError as e:
            logger.warning("Transport error to models service: %s", e)
            raise

        if response.status_code >= 500:
            # Tenacity will retry — raise to trigger.
            raise httpx.HTTPStatusError(
                f"5xx from models service: {response.status_code}",
                request=response.request,
                response=response,
            )

        if response.status_code >= 400:
            self._raise_4xx(response)

        return response.json()

    @staticmethod
    def _raise_4xx(response: httpx.Response) -> None:
        try:
            payload = response.json()
            err = payload.get("error", {}) or {}
            code = err.get("code", "")
            message = err.get("message", response.text)
        except Exception:
            code = ""
            message = response.text

        if code == "model_not_available":
            raise ModelNotAvailableError(message)

        raise ModelsServiceClientError(
            f"{response.status_code} {code or 'client_error'}: {message}",
        )

    def _safe_post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        """Wrap _post and translate exhausted-retry 5xx + transport errors
        into ModelNotAvailableError."""
        try:
            return self._post(path, body)
        except httpx.HTTPStatusError as e:
            # All retries used and last response was 5xx.
            logger.warning("Models service 5xx after retries: %s", e)
            raise ModelNotAvailableError(str(e)) from e
        except httpx.TransportError as e:
            logger.warning("Models service unreachable after retries: %s", e)
            raise ModelNotAvailableError(str(e)) from e

    # -----------------------------------------------------------------------
    # Public methods — one per /v1/inference/* endpoint
    # -----------------------------------------------------------------------

    def prompt_injection(self, text: str) -> PromptInjectionResponse:
        body = self._safe_post("/v1/inference/prompt_injection", {"text": text})
        return PromptInjectionResponse.model_validate(body)

    def toxicity(self, text: str, threshold: float) -> ToxicityResponse:
        body = self._safe_post(
            "/v1/inference/toxicity",
            {"text": text, "threshold": threshold},
        )
        return ToxicityResponse.model_validate(body)

    def pii(
        self,
        text: str,
        disabled_entities: list[str] | None = None,
        allow_list: list[str] | None = None,
        confidence_threshold: float | None = None,
        use_v2: bool = True,
    ) -> PIIResponse:
        body = self._safe_post(
            "/v1/inference/pii",
            {
                "text": text,
                "disabled_entities": disabled_entities or [],
                "allow_list": allow_list or [],
                "confidence_threshold": confidence_threshold,
                "use_v2": use_v2,
            },
        )
        return PIIResponse.model_validate(body)

    def claim_filter(self, texts: list[str]) -> ClaimFilterResponse:
        body = self._safe_post("/v1/inference/claim_filter", {"texts": texts})
        return ClaimFilterResponse.model_validate(body)


# ---------------------------------------------------------------------------
# Singleton helper
# ---------------------------------------------------------------------------

_SINGLETON: ModelsServiceClient | None = None


def get_models_service_client() -> ModelsServiceClient:
    """Used by dependencies.py to share one client across all scorer instances."""
    global _SINGLETON
    if _SINGLETON is None:
        _SINGLETON = ModelsServiceClient()
    return _SINGLETON
