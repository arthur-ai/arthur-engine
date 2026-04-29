"""Wire-routing tests for the PII v1 (Presidio-only) scorer.

Real-model coverage lives in
arthur-engine/models-service/tests/unit/test_pii_v1.py.
"""

import pytest
from arthur_common.models.enums import PIIEntityTypes, RuleResultEnum, RuleType

from clients.models_service_client import ModelNotAvailableError
from schemas.scorer_schemas import ScoreRequest
from scorer.checks.pii.classifier_v1 import BinaryPIIDataClassifierV1
from tests.conftest import make_pii_response


def _req(text: str, **kw) -> ScoreRequest:
    return ScoreRequest(scoring_text=text, rule_type=RuleType.PII_DATA, **kw)


@pytest.mark.unit_tests
def test_pass(fake_models_client):
    fake_models_client.pii_response = make_pii_response()
    scorer = BinaryPIIDataClassifierV1(client=fake_models_client)
    score = scorer.score(_req("This has no PII data"))
    assert score.result == RuleResultEnum.PASS


@pytest.mark.unit_tests
def test_fail(fake_models_client):
    fake_models_client.pii_response = make_pii_response(
        ("US_SSN", "133-21-6130", 0.85),
    )
    scorer = BinaryPIIDataClassifierV1(client=fake_models_client)
    score = scorer.score(_req("My SSN is 133-21-6130"))
    assert score.result == RuleResultEnum.FAIL
    assert PIIEntityTypes.US_SSN in score.details.pii_results


@pytest.mark.unit_tests
def test_use_v2_flag_is_false(fake_models_client):
    fake_models_client.pii_response = make_pii_response()
    scorer = BinaryPIIDataClassifierV1(client=fake_models_client)
    scorer.score(_req("hi"))
    assert fake_models_client.last_call[1]["use_v2"] is False


@pytest.mark.unit_tests
def test_model_not_available(fake_models_client):
    def boom(*a, **kw):
        raise ModelNotAvailableError("simulated")

    fake_models_client.pii = boom  # type: ignore[method-assign]
    scorer = BinaryPIIDataClassifierV1(client=fake_models_client)
    score = scorer.score(_req("hi"))
    assert score.result == RuleResultEnum.MODEL_NOT_AVAILABLE
