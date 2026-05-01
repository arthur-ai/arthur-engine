from unittest.mock import Mock, patch

import pytest
from arthur_common.models.enums import RuleResultEnum

from schemas.scorer_schemas import RuleScore
from scorer.checks.prompt_injection.classifier import BinaryPromptInjectionClassifier
from services.model_warmup_service import ModelKey
from utils.model_load import (
    get_prompt_injection_model,
    get_prompt_injection_tokenizer,
)

PROMPT_INJECTION_MODEL = get_prompt_injection_model()
PROMPT_INJECTION_TOKENIZER = get_prompt_injection_tokenizer()


def _ready_warmup() -> Mock:
    """Return a fake warmup service that always reports the model ready."""
    fake = Mock()
    fake.is_ready.return_value = True
    return fake


@pytest.mark.unit_tests
def test_binary_prompt_injection_classifier_init_is_lazy():
    """Construction should not load the classifier; that happens on demand."""
    with patch(
        "scorer.checks.prompt_injection.classifier.get_prompt_injection_classifier",
    ) as mock_pi_classifier:
        classifier = BinaryPromptInjectionClassifier(
            model=PROMPT_INJECTION_MODEL,
            tokenizer=PROMPT_INJECTION_TOKENIZER,
        )
    assert mock_pi_classifier.call_count == 0
    assert classifier.is_loaded() is False


@pytest.mark.unit_tests
@patch("scorer.checks.prompt_injection.classifier.get_prompt_injection_classifier")
@patch(
    "scorer.checks.prompt_injection.classifier.get_model_warmup_service",
    new=_ready_warmup,
)
def test_score_above_threshold(mock_classifier):
    classifier = BinaryPromptInjectionClassifier(
        model=PROMPT_INJECTION_MODEL,
        tokenizer=PROMPT_INJECTION_TOKENIZER,
    )

    mock_request = Mock()
    mock_request.user_prompt = "Test prompt"
    mock_classifier.return_value.return_value = [{"label": "INJECTION", "score": 0.99}]

    score = classifier.score(mock_request)
    assert isinstance(score, RuleScore)
    assert score.result is RuleResultEnum.FAIL
    assert score.details is None


@pytest.mark.unit_tests
@patch("scorer.checks.prompt_injection.classifier.get_prompt_injection_classifier")
@patch(
    "scorer.checks.prompt_injection.classifier.get_model_warmup_service",
    new=_ready_warmup,
)
def test_score_below_threshold(mock_classifier):
    classifier = BinaryPromptInjectionClassifier(
        model=PROMPT_INJECTION_MODEL,
        tokenizer=PROMPT_INJECTION_TOKENIZER,
    )

    mock_request = Mock()
    mock_request.user_prompt = "Test prompt"
    mock_classifier.return_value.return_value = [{"label": "SAFE", "score": 0.01}]

    score = classifier.score(mock_request)
    assert isinstance(score, RuleScore)
    assert score.result is RuleResultEnum.PASS
    assert score.details is None


@pytest.mark.unit_tests
def test_score_returns_model_not_available_when_warming():
    """When the warmup service hasn't loaded the model, score() short-circuits."""
    fake_warmup = Mock()
    fake_warmup.is_ready.return_value = False
    # Both the scorer's _ensure_loaded and the shared model_not_available
    # helper read the singleton. Patching at the source of truth covers
    # both call sites.
    with (
        patch(
            "services.model_warmup_service.get_model_warmup_service",
            return_value=fake_warmup,
        ),
        patch(
            "scorer.checks.prompt_injection.classifier.get_model_warmup_service",
            return_value=fake_warmup,
        ),
    ):
        classifier = BinaryPromptInjectionClassifier(
            model=None,
            tokenizer=None,
        )
        mock_request = Mock()
        mock_request.user_prompt = "Test prompt"
        score = classifier.score(mock_request)

    assert score.result is RuleResultEnum.MODEL_NOT_AVAILABLE
    fake_warmup.ensure_warmup_started.assert_called()
    fake_warmup.is_ready.assert_called_with(ModelKey.PROMPT_INJECTION)
