"""Wire-routing tests for the PII v2 scorer.

Real-model coverage (entity validators, GLiNER + Presidio + spaCy interplay)
lives in arthur-engine/models-service/tests/unit/test_pii.py.
"""

import pytest
from arthur_common.models.enums import PIIEntityTypes, RuleResultEnum, RuleType

from clients.models_service_client import ModelNotAvailableError
from schemas.scorer_schemas import ScoreRequest
from scorer.checks.pii.classifier import BinaryPIIDataClassifier
from tests.conftest import make_pii_response


def _req(text: str, **kw) -> ScoreRequest:
    return ScoreRequest(scoring_text=text, rule_type=RuleType.PII_DATA, **kw)


@pytest.mark.unit_tests
def test_pass(fake_models_client):
    fake_models_client.pii_response = make_pii_response()
    scorer = BinaryPIIDataClassifier(client=fake_models_client)
    score = scorer.score(_req("This has no PII data"))
    assert score.result == RuleResultEnum.PASS


@pytest.mark.unit_tests
def test_fail(fake_models_client):
    fake_models_client.pii_response = make_pii_response(
        ("PHONE_NUMBER", "914-714-1729", 0.95),
    )
    scorer = BinaryPIIDataClassifier(client=fake_models_client)
    score = scorer.score(_req("call me at 914-714-1729"))
    assert score.result == RuleResultEnum.FAIL
    assert PIIEntityTypes.PHONE_NUMBER in score.details.pii_results
    assert score.details.pii_entities[0].span == "914-714-1729"


@pytest.mark.unit_tests
def test_passes_disabled_entities_through(fake_models_client):
    fake_models_client.pii_response = make_pii_response()
    scorer = BinaryPIIDataClassifier(client=fake_models_client)
    scorer.score(_req(
        "hi",
        disabled_pii_entities=[PIIEntityTypes.EMAIL_ADDRESS, PIIEntityTypes.PHONE_NUMBER],
    ))
    assert fake_models_client.last_call[0] == "pii"
    assert fake_models_client.last_call[1]["use_v2"] is True
    assert "EMAIL_ADDRESS" in fake_models_client.last_call[1]["disabled_entities"]


@pytest.mark.unit_tests
def test_empty_text_passes(fake_models_client):
    scorer = BinaryPIIDataClassifier(client=fake_models_client)
    score = scorer.score(_req(""))
    assert score.result == RuleResultEnum.PASS
    assert fake_models_client.last_call is None


@pytest.mark.unit_tests
def test_model_not_available(fake_models_client):
    def boom(*a, **kw):
        raise ModelNotAvailableError("simulated")

    fake_models_client.pii = boom  # type: ignore[method-assign]
    scorer = BinaryPIIDataClassifier(client=fake_models_client)
    score = scorer.score(_req("hi"))
    assert score.result == RuleResultEnum.MODEL_NOT_AVAILABLE
