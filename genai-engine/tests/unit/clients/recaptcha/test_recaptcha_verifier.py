"""Unit tests for the reCAPTCHA Enterprise assessment client."""

import os
from unittest.mock import MagicMock, patch

import httpx
import pytest

from clients.recaptcha.recaptcha_verifier import RecaptchaEnterpriseVerifier

CONFIGURED_ENV = {
    "RECAPTCHA_ENTERPRISE_PROJECT_ID": "demo-project",
    "RECAPTCHA_ENTERPRISE_SITE_KEY": "site-key",
    "RECAPTCHA_ENTERPRISE_API_KEY": "api-key",
}


def _mock_post(payload: dict) -> MagicMock:
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status = lambda: None
    return response


@pytest.mark.unit_tests
def test_verify_skips_when_not_configured():
    with patch.dict(os.environ, {}, clear=False):
        for key in CONFIGURED_ENV:
            os.environ.pop(key, None)
        result = RecaptchaEnterpriseVerifier().verify("any-token")

    assert result.success is True
    assert result.reason == "recaptcha_not_configured"


@pytest.mark.unit_tests
def test_verify_missing_token_fails_when_configured():
    with patch.dict(os.environ, CONFIGURED_ENV):
        result = RecaptchaEnterpriseVerifier().verify(None)

    assert result.success is False
    assert result.reason == "missing_token"


@pytest.mark.unit_tests
def test_verify_valid_token_above_threshold_succeeds():
    payload = {
        "tokenProperties": {"valid": True, "action": "onboarding_signup"},
        "riskAnalysis": {"score": 0.9, "reasons": []},
    }
    with patch.dict(os.environ, CONFIGURED_ENV):
        with patch(
            "clients.recaptcha.recaptcha_verifier.httpx.post",
            return_value=_mock_post(payload),
        ) as mock_post:
            result = RecaptchaEnterpriseVerifier().verify(
                "tok",
                action="onboarding_signup",
            )

    assert result.success is True
    assert result.score == 0.9
    # API key is passed as a query param, token + siteKey + action in the body.
    _, kwargs = mock_post.call_args
    assert kwargs["params"] == {"key": "api-key"}
    assert kwargs["json"]["event"]["token"] == "tok"
    assert kwargs["json"]["event"]["siteKey"] == "site-key"
    assert kwargs["json"]["event"]["expectedAction"] == "onboarding_signup"


@pytest.mark.unit_tests
def test_verify_invalid_token_fails():
    payload = {
        "tokenProperties": {"valid": False, "invalidReason": "EXPIRED"},
        "riskAnalysis": {"score": 0.9},
    }
    with patch.dict(os.environ, CONFIGURED_ENV):
        with patch(
            "clients.recaptcha.recaptcha_verifier.httpx.post",
            return_value=_mock_post(payload),
        ):
            result = RecaptchaEnterpriseVerifier().verify("tok")

    assert result.success is False
    assert result.reason == "invalid_token:EXPIRED"


@pytest.mark.unit_tests
def test_verify_action_mismatch_fails():
    payload = {
        "tokenProperties": {"valid": True, "action": "some_other_action"},
        "riskAnalysis": {"score": 0.9},
    }
    with patch.dict(os.environ, CONFIGURED_ENV):
        with patch(
            "clients.recaptcha.recaptcha_verifier.httpx.post",
            return_value=_mock_post(payload),
        ):
            result = RecaptchaEnterpriseVerifier().verify(
                "tok",
                action="onboarding_signup",
            )

    assert result.success is False
    assert result.reason == "action_mismatch"


@pytest.mark.unit_tests
def test_verify_low_score_fails():
    payload = {
        "tokenProperties": {"valid": True, "action": "onboarding_signup"},
        "riskAnalysis": {"score": 0.1},
    }
    with patch.dict(
        os.environ,
        {**CONFIGURED_ENV, "RECAPTCHA_ENTERPRISE_SCORE_THRESHOLD": "0.5"},
    ):
        with patch(
            "clients.recaptcha.recaptcha_verifier.httpx.post",
            return_value=_mock_post(payload),
        ):
            result = RecaptchaEnterpriseVerifier().verify(
                "tok",
                action="onboarding_signup",
            )

    assert result.success is False
    assert result.reason == "low_score"
    assert result.score == 0.1


@pytest.mark.unit_tests
def test_verify_transport_error_fails_open():
    with patch.dict(os.environ, CONFIGURED_ENV):
        with patch(
            "clients.recaptcha.recaptcha_verifier.httpx.post",
            side_effect=httpx.TimeoutException("timeout"),
        ):
            result = RecaptchaEnterpriseVerifier().verify("tok")

    assert result.success is True
    assert result.reason == "verification_error"


@pytest.mark.unit_tests
def test_verify_error_handling_fail_open_vs_closed():
    """Consolidated coverage of fail-OPEN vs fail-CLOSED error paths.

    Pins the intent of the post-PR-1693 split: only true network failures
    are allowed to bypass reCAPTCHA; every other failure (HTTP 4xx, malformed
    body, unexpected schema) must fail CLOSED. Each sub-case asserts both
    ``success`` and ``reason``; the case name is included in assert messages
    so failures still identify the offending case.
    """

    def _http_status_response() -> MagicMock:
        response = MagicMock()
        response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Bad Request",
                request=MagicMock(),
                response=MagicMock(status_code=400),
            ),
        )
        return response

    def _malformed_json_response() -> MagicMock:
        response = MagicMock()
        response.raise_for_status = lambda: None
        response.json = MagicMock(side_effect=ValueError("not json"))
        return response

    # Each sub-case: (case_name, patch kwargs for httpx.post, expected_success).
    # _RiskAnalysis.score is typed as float; a list cannot be coerced and
    # will raise a pydantic ValidationError during model_validate -> fail CLOSED.
    unexpected_schema_payload = {
        "tokenProperties": {"valid": True, "action": "signup"},
        "riskAnalysis": {"score": ["not", "a", "float"], "reasons": []},
    }

    cases = [
        (
            "generic_transport_error_fails_open",
            {"side_effect": httpx.TransportError("connection reset")},
            True,
        ),
        (
            "http_4xx_fails_closed",
            {"return_value": _http_status_response()},
            False,
        ),
        (
            "malformed_json_body_fails_closed",
            {"return_value": _malformed_json_response()},
            False,
        ),
        (
            "unexpected_schema_fails_closed",
            {"return_value": _mock_post(unexpected_schema_payload)},
            False,
        ),
    ]

    for case_name, post_patch_kwargs, expected_success in cases:
        with patch.dict(os.environ, CONFIGURED_ENV):
            with patch(
                "clients.recaptcha.recaptcha_verifier.httpx.post",
                **post_patch_kwargs,
            ):
                result = RecaptchaEnterpriseVerifier().verify(
                    "tok",
                    action="signup",
                )

        assert result.success is expected_success, case_name
        assert result.reason == "verification_error", case_name
