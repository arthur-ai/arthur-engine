import pytest
from arthur_common.models.enums import RuleResultEnum, RuleType
from sqlalchemy import func, select

from db_models import (
    DatabaseInference,
    DatabasePromptRuleResult,
    DatabaseResponseRuleResult,
)
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)


def _count_rows(model) -> int:
    db = override_get_db_session()
    try:
        return db.execute(select(func.count()).select_from(model)).scalar_one()
    finally:
        db.close()


@pytest.mark.unit_tests
def test_builtin_validate_single_check_shape(client: GenaiEngineTestClientBase):
    status_code, body = client.builtin_validate(
        text="Tell me a joke about astronauts.",
        checks=["prompt_injection"],
    )
    assert status_code == 200
    results = body["results"]
    assert len(results) == 1
    only = results[0]
    assert only["name"] == "prompt_injection"
    assert only["rule_type"] == RuleType.PROMPT_INJECTION.value
    assert only["scope"] == "default"
    assert only["result"] in [r.value for r in RuleResultEnum]
    assert isinstance(only["latency_ms"], int)
    assert only["latency_ms"] >= 0


@pytest.mark.unit_tests
def test_builtin_validate_multiple_checks(client: GenaiEngineTestClientBase):
    status_code, body = client.builtin_validate(
        text="My SSN is 123-45-6789",
        checks=["pii", "toxicity"],
    )
    assert status_code == 200
    results = body["results"]
    assert len(results) == 2

    by_name = {r["name"]: r for r in results}
    assert set(by_name.keys()) == {"pii", "toxicity"}
    assert by_name["pii"]["rule_type"] == RuleType.PII_DATA.value
    assert by_name["toxicity"]["rule_type"] == RuleType.TOXICITY.value
    assert by_name["pii"]["id"] != by_name["toxicity"]["id"]


@pytest.mark.unit_tests
def test_builtin_validate_unknown_check_returns_422(
    client: GenaiEngineTestClientBase,
):
    status_code, _ = client.builtin_validate(
        text="hello",
        checks=["not_a_real_check"],
    )
    assert status_code == 422


@pytest.mark.unit_tests
def test_builtin_validate_empty_checks_returns_422(
    client: GenaiEngineTestClientBase,
):
    status_code, _ = client.builtin_validate(text="hello", checks=[])
    assert status_code == 422


@pytest.mark.unit_tests
def test_builtin_validate_empty_text_returns_422(
    client: GenaiEngineTestClientBase,
):
    status_code, _ = client.builtin_validate(text="", checks=["prompt_injection"])
    assert status_code == 422


@pytest.mark.unit_tests
def test_builtin_validate_does_not_persist_rows(
    client: GenaiEngineTestClientBase,
):
    inferences_before = _count_rows(DatabaseInference)
    prompt_rule_results_before = _count_rows(DatabasePromptRuleResult)
    response_rule_results_before = _count_rows(DatabaseResponseRuleResult)

    status_code, _ = client.builtin_validate(
        text="Validate this text statelessly please.",
        checks=["prompt_injection", "toxicity", "pii"],
    )
    assert status_code == 200

    assert _count_rows(DatabaseInference) == inferences_before
    assert _count_rows(DatabasePromptRuleResult) == prompt_rule_results_before
    assert _count_rows(DatabaseResponseRuleResult) == response_rule_results_before


@pytest.mark.unit_tests
def test_builtin_validate_preserves_check_order_in_results(
    client: GenaiEngineTestClientBase,
):
    status_code, body = client.builtin_validate(
        text="Some arbitrary tool-call output.",
        checks=["toxicity", "prompt_injection", "pii"],
    )
    assert status_code == 200
    names = [r["name"] for r in body["results"]]
    assert names == ["toxicity", "prompt_injection", "pii"]
