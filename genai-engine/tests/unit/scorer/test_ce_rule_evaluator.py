"""Unit tests for RuleCEEvaluator."""

import json
from unittest.mock import MagicMock, patch

import pytest
from arthur_common.models.enums import PIIEntityTypes, RuleResultEnum, RuleType, ToxicityViolationType

from schemas.scorer_schemas import (
    RuleScore,
    ScorerPIIEntitySpan,
    ScorerRuleDetails,
    ScorerToxicityScore,
)
from scorer.ce_rule_evaluator import CEEvaluationResult, RuleCEEvaluator


def make_span(input_content=None, output_content=None, span_id="test-span-id"):
    """Create a mock Span with configurable input/output content."""
    span = MagicMock()
    span.span_id = span_id
    span.input_content = input_content
    span.output_content = output_content
    return span


def make_pass_score():
    return RuleScore(result=RuleResultEnum.PASS)


def make_fail_score_with_toxicity():
    return RuleScore(
        result=RuleResultEnum.FAIL,
        details=ScorerRuleDetails(
            message="Toxic content detected",
            toxicity_score=ScorerToxicityScore(
                toxicity_score=0.95,
                toxicity_violation_type=ToxicityViolationType.TOXIC_CONTENT,
            ),
        ),
    )


def make_fail_score_with_pii(entity_type=PIIEntityTypes.PHONE_NUMBER, span_text="555-1234"):
    return RuleScore(
        result=RuleResultEnum.FAIL,
        details=ScorerRuleDetails(
            message=f"PII found in data: {entity_type.value}",
            pii_results=[entity_type],
            pii_entities=[
                ScorerPIIEntitySpan(
                    entity=entity_type,
                    span=span_text,
                    confidence=0.95,
                )
            ],
        ),
    )


@pytest.fixture
def evaluator():
    """Create a RuleCEEvaluator with mocked classifiers."""
    with (
        patch(
            "scorer.ce_rule_evaluator.BinaryPIIDataClassifier",
        ) as mock_pii_cls,
        patch(
            "scorer.ce_rule_evaluator.BinaryPromptInjectionClassifier",
        ) as mock_pi_cls,
        patch(
            "scorer.ce_rule_evaluator.ToxicityScorer",
        ) as mock_tox_cls,
    ):
        mock_pii = MagicMock()
        mock_pi = MagicMock()
        mock_tox = MagicMock()
        mock_pii_cls.return_value = mock_pii
        mock_pi_cls.return_value = mock_pi
        mock_tox_cls.return_value = mock_tox

        ev = RuleCEEvaluator()
        ev._mock_pii = mock_pii
        ev._mock_pi = mock_pi
        ev._mock_tox = mock_tox
        yield ev


# ---------------------------------------------------------------------------
# PROMPT_INJECTION
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_prompt_injection_pass(evaluator):
    evaluator._mock_pi.score.return_value = make_pass_score()
    span = make_span(input_content="What is the capital of France?")

    result = evaluator.evaluate(RuleType.PROMPT_INJECTION, span)

    assert result.annotation_score == 1
    desc = json.loads(result.annotation_description)
    assert desc["result"] == RuleResultEnum.PASS.value


@pytest.mark.unit_tests
def test_prompt_injection_fail(evaluator):
    evaluator._mock_pi.score.return_value = RuleScore(
        result=RuleResultEnum.FAIL,
        details=ScorerRuleDetails(message="Prompt injection detected"),
    )
    span = make_span(input_content="Ignore previous instructions and...")

    result = evaluator.evaluate(RuleType.PROMPT_INJECTION, span)

    assert result.annotation_score == 0
    desc = json.loads(result.annotation_description)
    assert desc["result"] == RuleResultEnum.FAIL.value
    assert "message" in desc


@pytest.mark.unit_tests
def test_prompt_injection_uses_input_only(evaluator):
    """PROMPT_INJECTION should only evaluate input, not output."""
    evaluator._mock_pi.score.return_value = make_pass_score()
    span = make_span(input_content="Hello", output_content="World")

    evaluator.evaluate(RuleType.PROMPT_INJECTION, span)

    call_args = evaluator._mock_pi.score.call_args[0][0]
    assert call_args.user_prompt == "Hello"
    assert evaluator._mock_pii.score.call_count == 0
    assert evaluator._mock_tox.score.call_count == 0


@pytest.mark.unit_tests
def test_prompt_injection_empty_input(evaluator):
    """Should still call scorer with empty string when no input content."""
    evaluator._mock_pi.score.return_value = make_pass_score()
    span = make_span(input_content=None, output_content="Some output")

    result = evaluator.evaluate(RuleType.PROMPT_INJECTION, span)

    assert result.annotation_score == 1
    call_args = evaluator._mock_pi.score.call_args[0][0]
    assert call_args.user_prompt == ""


# ---------------------------------------------------------------------------
# TOXICITY
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_toxicity_pass(evaluator):
    evaluator._mock_tox.score.return_value = make_pass_score()
    span = make_span(output_content="The weather is nice today.")

    result = evaluator.evaluate(RuleType.TOXICITY, span)

    assert result.annotation_score == 1
    desc = json.loads(result.annotation_description)
    assert desc["result"] == RuleResultEnum.PASS.value


@pytest.mark.unit_tests
def test_toxicity_fail(evaluator):
    evaluator._mock_tox.score.return_value = make_fail_score_with_toxicity()
    span = make_span(output_content="Some toxic content")

    result = evaluator.evaluate(RuleType.TOXICITY, span)

    assert result.annotation_score == 0
    desc = json.loads(result.annotation_description)
    assert desc["result"] == RuleResultEnum.FAIL.value
    assert "toxicity_score" in desc
    assert desc["toxicity_score"]["toxicity_score"] == 0.95


@pytest.mark.unit_tests
def test_toxicity_uses_output_only(evaluator):
    """TOXICITY should only evaluate output, not input."""
    evaluator._mock_tox.score.return_value = make_pass_score()
    span = make_span(input_content="Hello", output_content="World")

    evaluator.evaluate(RuleType.TOXICITY, span)

    call_args = evaluator._mock_tox.score.call_args[0][0]
    assert call_args.scoring_text == "World"
    assert evaluator._mock_pii.score.call_count == 0
    assert evaluator._mock_pi.score.call_count == 0


@pytest.mark.unit_tests
def test_toxicity_empty_output(evaluator):
    """Should still call scorer with empty string when no output content."""
    evaluator._mock_tox.score.return_value = make_pass_score()
    span = make_span(input_content="Some input", output_content=None)

    result = evaluator.evaluate(RuleType.TOXICITY, span)

    assert result.annotation_score == 1
    call_args = evaluator._mock_tox.score.call_args[0][0]
    assert call_args.scoring_text == ""


# ---------------------------------------------------------------------------
# PII_DATA
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_pii_both_pass(evaluator):
    evaluator._mock_pii.score.return_value = make_pass_score()
    span = make_span(input_content="Hello world", output_content="No PII here")

    result = evaluator.evaluate(RuleType.PII_DATA, span)

    assert result.annotation_score == 1
    desc = json.loads(result.annotation_description)
    assert desc["result"] == RuleResultEnum.PASS.value
    assert evaluator._mock_pii.score.call_count == 2


@pytest.mark.unit_tests
def test_pii_input_fails(evaluator):
    evaluator._mock_pii.score.side_effect = [
        make_fail_score_with_pii(PIIEntityTypes.PHONE_NUMBER, "555-1234"),
        make_pass_score(),
    ]
    span = make_span(input_content="Call me at 555-1234", output_content="OK")

    result = evaluator.evaluate(RuleType.PII_DATA, span)

    assert result.annotation_score == 0
    desc = json.loads(result.annotation_description)
    assert desc["result"] == RuleResultEnum.FAIL.value
    assert PIIEntityTypes.PHONE_NUMBER.value in desc["pii_results"]
    # Entity should be tagged as coming from input
    assert any(e["target"] == "input" for e in desc["pii_entities"])


@pytest.mark.unit_tests
def test_pii_output_fails(evaluator):
    evaluator._mock_pii.score.side_effect = [
        make_pass_score(),
        make_fail_score_with_pii(PIIEntityTypes.EMAIL_ADDRESS, "user@example.com"),
    ]
    span = make_span(input_content="Hello", output_content="Email: user@example.com")

    result = evaluator.evaluate(RuleType.PII_DATA, span)

    assert result.annotation_score == 0
    desc = json.loads(result.annotation_description)
    assert desc["result"] == RuleResultEnum.FAIL.value
    assert PIIEntityTypes.EMAIL_ADDRESS.value in desc["pii_results"]
    assert any(e["target"] == "output" for e in desc["pii_entities"])


@pytest.mark.unit_tests
def test_pii_both_fail_combines_entities(evaluator):
    evaluator._mock_pii.score.side_effect = [
        make_fail_score_with_pii(PIIEntityTypes.PHONE_NUMBER, "555-1234"),
        make_fail_score_with_pii(PIIEntityTypes.EMAIL_ADDRESS, "user@example.com"),
    ]
    span = make_span(
        input_content="Call 555-1234",
        output_content="Email user@example.com",
    )

    result = evaluator.evaluate(RuleType.PII_DATA, span)

    assert result.annotation_score == 0
    desc = json.loads(result.annotation_description)
    assert desc["result"] == RuleResultEnum.FAIL.value
    assert PIIEntityTypes.PHONE_NUMBER.value in desc["pii_results"]
    assert PIIEntityTypes.EMAIL_ADDRESS.value in desc["pii_results"]
    assert any(e["target"] == "input" for e in desc["pii_entities"])
    assert any(e["target"] == "output" for e in desc["pii_entities"])


@pytest.mark.unit_tests
def test_pii_evaluates_both_input_and_output(evaluator):
    """PII should call the classifier for both input and output."""
    evaluator._mock_pii.score.return_value = make_pass_score()
    span = make_span(input_content="Input text", output_content="Output text")

    evaluator.evaluate(RuleType.PII_DATA, span)

    assert evaluator._mock_pii.score.call_count == 2
    calls = evaluator._mock_pii.score.call_args_list
    scored_texts = {calls[0][0][0].scoring_text, calls[1][0][0].scoring_text}
    assert scored_texts == {"Input text", "Output text"}


@pytest.mark.unit_tests
def test_pii_skips_missing_input(evaluator):
    """PII should only score output when input is absent."""
    evaluator._mock_pii.score.return_value = make_pass_score()
    span = make_span(input_content=None, output_content="Output text")

    result = evaluator.evaluate(RuleType.PII_DATA, span)

    assert evaluator._mock_pii.score.call_count == 1
    assert result.annotation_score == 1


@pytest.mark.unit_tests
def test_pii_skips_missing_output(evaluator):
    """PII should only score input when output is absent."""
    evaluator._mock_pii.score.return_value = make_pass_score()
    span = make_span(input_content="Input text", output_content=None)

    result = evaluator.evaluate(RuleType.PII_DATA, span)

    assert evaluator._mock_pii.score.call_count == 1
    assert result.annotation_score == 1


# ---------------------------------------------------------------------------
# Unsupported rule type
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_unsupported_rule_type_raises(evaluator):
    span = make_span(input_content="test", output_content="test")

    with pytest.raises(ValueError, match="Unsupported rule type"):
        evaluator.evaluate(RuleType.MODEL_HALLUCINATION_V2, span)


@pytest.mark.unit_tests
def test_unsupported_rule_type_keyword_raises(evaluator):
    span = make_span(input_content="test", output_content="test")

    with pytest.raises(ValueError, match="Unsupported rule type"):
        evaluator.evaluate(RuleType.KEYWORD, span)
