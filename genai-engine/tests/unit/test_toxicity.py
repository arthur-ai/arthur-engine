"""Wire-routing tests for the toxicity scorer.

The actual model behaviour now lives in the models service — see
arthur-engine/models-service/tests/unit/test_toxicity.py.
"""

import pytest
from arthur_common.models.enums import RuleResultEnum, RuleType, ToxicityViolationType

from clients.models_service_client import ModelNotAvailableError
from schemas.scorer_schemas import ScoreRequest
from scorer.checks.toxicity.toxicity import ToxicityScorer
from tests.conftest import make_toxicity_response


def _req(text: str, threshold: float = 0.5) -> ScoreRequest:
    return ScoreRequest(
        scoring_text=text,
        rule_type=RuleType.TOXICITY,
        toxicity_threshold=threshold,
    )


@pytest.mark.unit_tests
def test_pass(fake_models_client):
    fake_models_client.toxicity_response = make_toxicity_response()
    scorer = ToxicityScorer(client=fake_models_client)
    score = scorer.score(_req("hello"))
    assert score.result == RuleResultEnum.PASS
    assert score.details.toxicity_score.toxicity_violation_type == ToxicityViolationType.BENIGN


@pytest.mark.unit_tests
def test_fail_toxic_content(fake_models_client):
    fake_models_client.toxicity_response = make_toxicity_response(
        result="Fail",
        toxicity_score=0.9,
        violation_type="toxic_content",
    )
    scorer = ToxicityScorer(client=fake_models_client)
    score = scorer.score(_req("nasty thing"))
    assert score.result == RuleResultEnum.FAIL
    assert score.details.toxicity_score.toxicity_score == 0.9
    assert score.details.toxicity_score.toxicity_violation_type == ToxicityViolationType.TOXIC_CONTENT


@pytest.mark.unit_tests
def test_fail_profanity(fake_models_client):
    fake_models_client.toxicity_response = make_toxicity_response(
        result="Fail",
        toxicity_score=0.99,
        violation_type="profanity",
        profanity_detected=True,
    )
    scorer = ToxicityScorer(client=fake_models_client)
    score = scorer.score(_req("dirty word"))
    assert score.result == RuleResultEnum.FAIL
    assert score.details.toxicity_score.toxicity_violation_type == ToxicityViolationType.PROFANITY


@pytest.mark.unit_tests
def test_skipped_when_threshold_not_float(fake_models_client):
    """Defense-in-depth: if some upstream caller constructs a ScoreRequest
    without going through Pydantic validation (e.g. via `model_construct`)
    and passes a non-float threshold, the scorer returns SKIPPED locally."""
    scorer = ToxicityScorer(client=fake_models_client)
    request = ScoreRequest.model_construct(
        scoring_text="hi",
        rule_type=RuleType.TOXICITY,
        toxicity_threshold="not-a-float",
    )
    score = scorer.score(request)
    assert score.result == RuleResultEnum.SKIPPED
    assert fake_models_client.last_call is None


@pytest.mark.unit_tests
def test_empty_text_passes(fake_models_client):
    scorer = ToxicityScorer(client=fake_models_client)
    score = scorer.score(_req(""))
    assert score.result == RuleResultEnum.PASS
    assert fake_models_client.last_call is None


@pytest.mark.unit_tests
def test_model_not_available(fake_models_client):
    def boom(text, threshold):
        raise ModelNotAvailableError("simulated")

    fake_models_client.toxicity = boom  # type: ignore[method-assign]
    scorer = ToxicityScorer(client=fake_models_client)
    score = scorer.score(_req("hi"))
    assert score.result == RuleResultEnum.MODEL_NOT_AVAILABLE
