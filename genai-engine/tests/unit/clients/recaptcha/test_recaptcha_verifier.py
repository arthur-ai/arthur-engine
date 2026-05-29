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
