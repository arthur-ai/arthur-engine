from unittest.mock import Mock, patch

import pytest
from arthur_common.models.enums import RuleResultEnum
from schemas.scorer_schemas import RuleScore
from scorer.checks.prompt_injection.classifier import (
    BinaryPromptInjectionClassifier,
    get_prompt_injection_model,
    get_prompt_injection_tokenizer,
)

PROMPT_INJECTION_MODEL = get_prompt_injection_model()
PROMPT_INJECTION_TOKENIZER = get_prompt_injection_tokenizer()


@patch("scorer.checks.prompt_injection.classifier.get_prompt_injection_classifier")
@pytest.mark.unit_tests
def test_binary_prompt_injection_classifier_init(
    mock_pi_classifier,
):
    classifier = BinaryPromptInjectionClassifier(
        model=PROMPT_INJECTION_MODEL,
        tokenizer=PROMPT_INJECTION_TOKENIZER,
    )
    assert mock_pi_classifier.call_count == 1
    assert classifier.model is mock_pi_classifier.return_value


@patch("scorer.checks.prompt_injection.classifier.get_prompt_injection_classifier")
@pytest.mark.unit_tests
def test_score_above_threshold(mock_classifier):
    classifier = BinaryPromptInjectionClassifier(
        model=PROMPT_INJECTION_MODEL,
        tokenizer=PROMPT_INJECTION_TOKENIZER,
    )

    # Create a mock ScoreRequest object
    mock_request = Mock()
    mock_request.user_prompt = "Test prompt"

    # Set the mock model's return value
    mock_classifier.return_value.return_value = [{"label": "INJECTION", "score": 0.99}]

    # Test score method
    score = classifier.score(mock_request)
    assert isinstance(score, RuleScore)
    assert score.result is RuleResultEnum.FAIL
    assert score.details is None


@patch("scorer.checks.prompt_injection.classifier.get_prompt_injection_classifier")
@pytest.mark.unit_tests
def test_score_below_threshold(mock_classifier):
    classifier = BinaryPromptInjectionClassifier(
        model=PROMPT_INJECTION_MODEL,
        tokenizer=PROMPT_INJECTION_TOKENIZER,
    )

    # Create a mock ScoreRequest object
    mock_request = Mock()
    mock_request.user_prompt = "Test prompt"

    # Set the mock model's return value
    mock_classifier.return_value.return_value = [{"label": "SAFE", "score": 0.01}]

    # Test score method
    score = classifier.score(mock_request)
    assert isinstance(score, RuleScore)
    assert score.result is RuleResultEnum.PASS
    assert score.details is None
