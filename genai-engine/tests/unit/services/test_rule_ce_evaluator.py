"""Unit tests for RuleCEEvaluator and ContinuousEvalQueueService rule dispatch."""

import uuid
from datetime import datetime
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from arthur_common.models.enums import RuleResultEnum, RuleType

from schemas.internal_schemas import ValidationRequest
from schemas.scorer_schemas import RuleScore, ScorerRuleDetails, ScorerPIIEntitySpan
from services.continuous_eval.rule_ce_evaluator import RuleCEEvaluator, SUPPORTED_RULE_TYPES


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _mock_scorer_client(result: RuleResultEnum = RuleResultEnum.PASS) -> MagicMock:
    """Return a ScorerClient mock whose .score() returns the given result."""
    mock_client = MagicMock()
    mock_score = RuleScore(result=result, details=None)
    mock_client.score.return_value = mock_score
    return mock_client


# ---------------------------------------------------------------------------
# RuleCEEvaluator._build_rule tests
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
class TestRuleCEEvaluatorBuildRule:
    def test_prompt_injection_builds_empty_rule_data(self):
        evaluator = RuleCEEvaluator(scorer_client=MagicMock())
        rule = evaluator._build_rule(RuleType.PROMPT_INJECTION, {})
        assert rule.type == RuleType.PROMPT_INJECTION
        assert rule.rule_data == []

    def test_toxicity_uses_config_threshold(self):
        evaluator = RuleCEEvaluator(scorer_client=MagicMock())
        rule = evaluator._build_rule(RuleType.TOXICITY, {"threshold": 0.8})
        threshold_data = [rd for rd in rule.rule_data if rd.data_type.value == "toxicity_threshold"]
        assert len(threshold_data) == 1
        assert float(threshold_data[0].data) == pytest.approx(0.8)

    def test_toxicity_uses_default_threshold_when_not_in_config(self):
        from utils import constants
        evaluator = RuleCEEvaluator(scorer_client=MagicMock())
        rule = evaluator._build_rule(RuleType.TOXICITY, {})
        threshold_data = [rd for rd in rule.rule_data if rd.data_type.value == "toxicity_threshold"]
        assert len(threshold_data) == 1
        assert float(threshold_data[0].data) == pytest.approx(
            constants.DEFAULT_TOXICITY_RULE_THRESHOLD
        )

    def test_pii_includes_disabled_entities(self):
        evaluator = RuleCEEvaluator(scorer_client=MagicMock())
        config = {"disabled_pii_entities": ["EMAIL_ADDRESS", "PHONE_NUMBER"]}
        rule = evaluator._build_rule(RuleType.PII_DATA, config)
        disabled_data = [rd for rd in rule.rule_data if rd.data_type.value == "disabled_pii_entities"]
        assert len(disabled_data) == 1
        assert "EMAIL_ADDRESS" in disabled_data[0].data

    def test_pii_empty_config_produces_no_rule_data(self):
        evaluator = RuleCEEvaluator(scorer_client=MagicMock())
        rule = evaluator._build_rule(RuleType.PII_DATA, {})
        assert rule.rule_data == []

    def test_unsupported_rule_type_raises(self):
        evaluator = RuleCEEvaluator(scorer_client=MagicMock())
        with pytest.raises(ValueError, match="Unsupported rule type"):
            evaluator._build_rule(RuleType.REGEX, {})


# ---------------------------------------------------------------------------
# RuleCEEvaluator.evaluate tests
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
class TestRuleCEEvaluatorEvaluate:
    def test_evaluate_prompt_injection_pass(self):
        mock_client = MagicMock()
        mock_client.score.return_value = RuleScore(result=RuleResultEnum.PASS)
        evaluator = RuleCEEvaluator(scorer_client=mock_client)

        result = evaluator.evaluate(
            rule_type=RuleType.PROMPT_INJECTION,
            rule_config=None,
            validation_request=ValidationRequest(prompt="Hello"),
        )

        assert result.result == RuleResultEnum.PASS
        mock_client.score.assert_called_once()

    def test_evaluate_toxicity_fail(self):
        mock_client = MagicMock()
        mock_client.score.return_value = RuleScore(
            result=RuleResultEnum.FAIL,
            details=ScorerRuleDetails(message="toxic"),
        )
        evaluator = RuleCEEvaluator(scorer_client=mock_client)

        result = evaluator.evaluate(
            rule_type=RuleType.TOXICITY,
            rule_config={"threshold": 0.5},
            validation_request=ValidationRequest(response="bad text"),
        )

        assert result.result == RuleResultEnum.FAIL

    def test_evaluate_unsupported_rule_type_raises(self):
        evaluator = RuleCEEvaluator(scorer_client=MagicMock())
        with pytest.raises(ValueError, match="Unsupported rule type"):
            evaluator.evaluate(
                rule_type=RuleType.MODEL_HALLUCINATION_V2,
                rule_config=None,
                validation_request=ValidationRequest(prompt="x"),
            )

    def test_all_supported_rule_types_do_not_raise(self):
        mock_client = MagicMock()
        mock_client.score.return_value = RuleScore(result=RuleResultEnum.PASS)
        evaluator = RuleCEEvaluator(scorer_client=mock_client)

        for rule_type in SUPPORTED_RULE_TYPES:
            result = evaluator.evaluate(
                rule_type=rule_type,
                rule_config={},
                validation_request=ValidationRequest(prompt="test"),
            )
            assert result.result == RuleResultEnum.PASS


# ---------------------------------------------------------------------------
# ContinuousEvalQueueService._map_rule_result_to_status tests
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
class TestMapRuleResultToStatus:
    def setup_method(self):
        from services.continuous_eval.continuous_eval_queue_service import (
            ContinuousEvalQueueService,
        )
        self.map_fn = ContinuousEvalQueueService._map_rule_result_to_status

    def test_pass_maps_to_passed_score_1(self):
        status, score = self.map_fn(RuleResultEnum.PASS)
        assert score == 1
        assert "passed" in status.lower()

    def test_fail_maps_to_failed_score_0(self):
        status, score = self.map_fn(RuleResultEnum.FAIL)
        assert score == 0
        assert "failed" in status.lower()

    def test_skipped_maps_to_skipped_no_score(self):
        status, score = self.map_fn(RuleResultEnum.SKIPPED)
        assert score is None
        assert "skipped" in status.lower()

    def test_unavailable_maps_to_error_no_score(self):
        status, score = self.map_fn(RuleResultEnum.UNAVAILABLE)
        assert score is None
        assert "error" in status.lower()
