"""Tests for the Retry-After header on validate routes when warmup is incomplete."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from arthur_common.models.enums import RuleResultEnum, RuleScope, RuleType
from arthur_common.models.response_schemas import ExternalRuleResult, ValidationResult
from fastapi import HTTPException, Response

from routers.v2.validate_routes import _annotate_warmup_state


def _result_with(rule_result: RuleResultEnum) -> ValidationResult:
    return ValidationResult(
        inference_id="abc",
        rule_results=[
            ExternalRuleResult(
                id="rule-1",
                name="Toxicity",
                rule_type=RuleType.TOXICITY,
                scope=RuleScope.DEFAULT,
                result=rule_result,
                latency_ms=0,
            ),
        ],
    )


@pytest.mark.unit_tests
def test_no_retry_after_when_no_rule_unavailable() -> None:
    response = Response()
    result = _result_with(RuleResultEnum.PASS)
    annotated = _annotate_warmup_state(response, result)
    assert annotated is result
    assert "Retry-After" not in response.headers


@pytest.mark.unit_tests
def test_retry_after_set_when_any_rule_unavailable() -> None:
    response = Response()
    result = _result_with(RuleResultEnum.MODEL_NOT_AVAILABLE)
    fake_warmup = MagicMock()
    fake_warmup.retry_after_seconds.return_value = 42
    with (
        patch(
            "routers.v2.validate_routes.get_model_warmup_service",
            return_value=fake_warmup,
        ),
        patch(
            "routers.v2.validate_routes.fail_fast_when_warming",
            return_value=False,
        ),
    ):
        annotated = _annotate_warmup_state(response, result)
    assert annotated is result
    assert response.headers["Retry-After"] == "42"


@pytest.mark.unit_tests
def test_fail_fast_mode_raises_503_with_retry_after() -> None:
    response = Response()
    result = _result_with(RuleResultEnum.MODEL_NOT_AVAILABLE)
    fake_warmup = MagicMock()
    fake_warmup.retry_after_seconds.return_value = 30
    with (
        patch(
            "routers.v2.validate_routes.get_model_warmup_service",
            return_value=fake_warmup,
        ),
        patch(
            "routers.v2.validate_routes.fail_fast_when_warming",
            return_value=True,
        ),
        pytest.raises(HTTPException) as exc,
    ):
        _annotate_warmup_state(response, result)
    assert exc.value.status_code == 503
    assert exc.value.headers == {"Retry-After": "30"}


@pytest.mark.unit_tests
def test_no_action_when_rule_results_empty() -> None:
    response = Response()
    result = ValidationResult(inference_id="xyz", rule_results=None)
    annotated = _annotate_warmup_state(response, result)
    assert annotated is result
    assert "Retry-After" not in response.headers
