"""reCAPTCHA Enterprise assessment client.

Wraps the reCAPTCHA Enterprise REST API
(https://cloud.google.com/recaptcha/docs/create-assessment) using an API key
in the query string, so no google-cloud SDK / service-account plumbing is
required.

Verification semantics:

* Not configured  -> success (fail-open) so local/dev/demo work unchanged.
* Missing token   -> failure (the client should always send one when enabled).
* Transport / unexpected error -> success (fail-open) so a Google outage does
  not block real signups. The error is logged.
* Invalid token / action mismatch / score below threshold -> failure.
"""

import logging

import httpx
from pydantic import BaseModel, ConfigDict, Field

from config.recaptcha_config import RecaptchaConfig

logger = logging.getLogger(__name__)

ASSESSMENT_URL = (
    "https://recaptchaenterprise.googleapis.com/v1/projects/{project_id}/assessments"
)
DEFAULT_TIMEOUT_SECONDS = 5.0


class RecaptchaVerificationResult(BaseModel):
    """Outcome of a token assessment."""

    success: bool
    score: float | None = None
    reason: str | None = None


class _RiskAnalysis(BaseModel):
    score: float = 0.0
    reasons: list[str] = Field(default_factory=list)
    model_config = ConfigDict(extra="ignore")


class _TokenProperties(BaseModel):
    valid: bool = False
    action: str | None = None
    invalid_reason: str | None = Field(default=None, alias="invalidReason")
    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class _AssessmentResponse(BaseModel):
    token_properties: _TokenProperties = Field(
        default_factory=_TokenProperties,
        alias="tokenProperties",
    )
    risk_analysis: _RiskAnalysis = Field(
        default_factory=_RiskAnalysis,
        alias="riskAnalysis",
    )
    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class RecaptchaEnterpriseVerifier:
    def __init__(self, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS):
        self._timeout = timeout_seconds

    def verify(
        self,
        token: str | None,
        action: str | None = None,
    ) -> RecaptchaVerificationResult:
        if not RecaptchaConfig.enabled():
            return RecaptchaVerificationResult(
                success=True,
                reason="recaptcha_not_configured",
            )

        if not token:
            return RecaptchaVerificationResult(success=False, reason="missing_token")

        project_id = RecaptchaConfig.project_id()
        site_key = RecaptchaConfig.site_key()
        api_key = RecaptchaConfig.api_key()
        expected_action = action or RecaptchaConfig.expected_action()

        event: dict[str, str] = {"token": token, "siteKey": site_key or ""}
        if expected_action:
            event["expectedAction"] = expected_action

        try:
            response = httpx.post(
                ASSESSMENT_URL.format(project_id=project_id),
                params={"key": api_key},
                json={"event": event},
                timeout=self._timeout,
            )
            response.raise_for_status()
            assessment = _AssessmentResponse.model_validate(response.json())
        except Exception as e:  # noqa: BLE001 - fail-open on any transport error
            logger.error("reCAPTCHA assessment request failed: %s", e)
            return RecaptchaVerificationResult(
                success=True,
                reason="verification_error",
            )

        token_props = assessment.token_properties
        if not token_props.valid:
            logger.info(
                "reCAPTCHA token invalid: %s",
                token_props.invalid_reason or "unknown",
            )
            return RecaptchaVerificationResult(
                success=False,
                reason=f"invalid_token:{token_props.invalid_reason or 'unknown'}",
            )

        if expected_action and token_props.action != expected_action:
            logger.info(
                "reCAPTCHA action mismatch: expected %s, got %s",
                expected_action,
                token_props.action,
            )
            return RecaptchaVerificationResult(
                success=False,
                reason="action_mismatch",
            )

        score = assessment.risk_analysis.score
        threshold = RecaptchaConfig.score_threshold()
        if score < threshold:
            logger.info(
                "reCAPTCHA score %s below threshold %s",
                score,
                threshold,
            )
            return RecaptchaVerificationResult(
                success=False,
                score=score,
                reason="low_score",
            )

        return RecaptchaVerificationResult(success=True, score=score)
