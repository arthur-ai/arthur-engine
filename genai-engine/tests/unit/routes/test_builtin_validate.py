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
        prompt="Tell me a joke about astronauts.",
        checks=[{"type": "prompt_injection"}],
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
        prompt="My SSN is 123-45-6789",
        checks=[{"type": "pii"}, {"type": "toxicity"}],
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
def test_builtin_validate_unknown_check_returns_400(
    client: GenaiEngineTestClientBase,
):
    status_code, _ = client.builtin_validate(
        prompt="hello",
        checks=[{"type": "not_a_real_check"}],
    )
    assert status_code == 400


@pytest.mark.unit_tests
def test_builtin_validate_empty_checks_returns_400(
    client: GenaiEngineTestClientBase,
):
    status_code, _ = client.builtin_validate(prompt="hello", checks=[])
    assert status_code == 400


@pytest.mark.unit_tests
def test_builtin_validate_no_text_fields_returns_400(
    client: GenaiEngineTestClientBase,
):
    status_code, _ = client.builtin_validate(
        checks=[{"type": "prompt_injection"}],
    )
    assert status_code == 400


@pytest.mark.unit_tests
def test_builtin_validate_prompt_injection_requires_prompt_returns_400(
    client: GenaiEngineTestClientBase,
):
    status_code, body = client.builtin_validate(
        response="some response text",
        checks=[{"type": "prompt_injection"}],
    )
    assert status_code == 400
    assert "prompt_injection" in body["detail"]
    assert "prompt" in body["detail"]


@pytest.mark.unit_tests
def test_builtin_validate_hallucination_requires_response_returns_400(
    client: GenaiEngineTestClientBase,
):
    status_code, body = client.builtin_validate(
        prompt="some prompt text",
        context="some grounding context",
        checks=[{"type": "hallucination"}],
    )
    assert status_code == 400
    assert "hallucination" in body["detail"]
    assert "response" in body["detail"]


@pytest.mark.unit_tests
def test_builtin_validate_hallucination_requires_context_returns_400(
    client: GenaiEngineTestClientBase,
):
    status_code, body = client.builtin_validate(
        response="The Eiffel Tower is in Berlin.",
        checks=[{"type": "hallucination"}],
    )
    assert status_code == 400
    assert "hallucination" in body["detail"]
    assert "context" in body["detail"]


@pytest.mark.unit_tests
def test_builtin_validate_hallucination_runs_with_response_and_context(
    client: GenaiEngineTestClientBase,
):
    status_code, body = client.builtin_validate(
        response="The Eiffel Tower is located in Paris and is 330 meters tall.",
        context="The Eiffel Tower is a wrought-iron lattice tower in Paris, France. "
        "It is 330 metres tall.",
        checks=[{"type": "hallucination"}],
    )
    assert status_code == 200
    assert len(body["results"]) == 1
    assert body["results"][0]["name"] == "hallucination"
    assert body["results"][0]["rule_type"] == RuleType.MODEL_HALLUCINATION_V2.value


@pytest.mark.unit_tests
def test_builtin_validate_regex_with_inline_config(
    client: GenaiEngineTestClientBase,
):
    status_code, body = client.builtin_validate(
        prompt="My account number is 12345",
        checks=[
            {"type": "regex", "config": {"regex_patterns": ["\\d{5}"]}},
        ],
    )
    assert status_code == 200
    assert len(body["results"]) == 1
    assert body["results"][0]["name"] == "regex"
    assert body["results"][0]["rule_type"] == RuleType.REGEX.value
    assert body["results"][0]["result"] == RuleResultEnum.FAIL.value


@pytest.mark.unit_tests
def test_builtin_validate_regex_requires_config_returns_400(
    client: GenaiEngineTestClientBase,
):
    status_code, _ = client.builtin_validate(
        prompt="hello",
        checks=[{"type": "regex"}],
    )
    assert status_code == 400


@pytest.mark.unit_tests
def test_builtin_validate_keyword_with_inline_config(
    client: GenaiEngineTestClientBase,
):
    status_code, body = client.builtin_validate(
        prompt="The forbidden word is bananafish.",
        checks=[
            {"type": "keyword", "config": {"keywords": ["bananafish"]}},
        ],
    )
    assert status_code == 200
    assert len(body["results"]) == 1
    assert body["results"][0]["name"] == "keyword"
    assert body["results"][0]["rule_type"] == RuleType.KEYWORD.value
    assert body["results"][0]["result"] == RuleResultEnum.FAIL.value


@pytest.mark.unit_tests
def test_builtin_validate_keyword_requires_config_returns_400(
    client: GenaiEngineTestClientBase,
):
    status_code, _ = client.builtin_validate(
        prompt="hello",
        checks=[{"type": "keyword"}],
    )
    assert status_code == 400


@pytest.mark.unit_tests
def test_builtin_validate_sensitive_data_requires_config_returns_400(
    client: GenaiEngineTestClientBase,
):
    status_code, _ = client.builtin_validate(
        prompt="hello",
        checks=[{"type": "sensitive_data"}],
    )
    assert status_code == 400


@pytest.mark.unit_tests
def test_builtin_validate_toxicity_with_inline_config(
    client: GenaiEngineTestClientBase,
):
    status_code, body = client.builtin_validate(
        prompt="A perfectly benign message.",
        checks=[{"type": "toxicity", "config": {"threshold": 0.9}}],
    )
    assert status_code == 200
    assert len(body["results"]) == 1
    assert body["results"][0]["name"] == "toxicity"


@pytest.mark.unit_tests
def test_builtin_validate_pii_with_inline_config(
    client: GenaiEngineTestClientBase,
):
    status_code, body = client.builtin_validate(
        prompt="My email is alice@example.com",
        checks=[
            {
                "type": "pii",
                "config": {"allow_list": ["alice@example.com"]},
            },
        ],
    )
    assert status_code == 200
    assert len(body["results"]) == 1
    assert body["results"][0]["name"] == "pii"


@pytest.mark.unit_tests
def test_builtin_validate_runs_on_response_when_only_response_provided(
    client: GenaiEngineTestClientBase,
):
    status_code, body = client.builtin_validate(
        response="My SSN is 123-45-6789",
        checks=[{"type": "pii"}],
    )
    assert status_code == 200
    assert len(body["results"]) == 1
    assert body["results"][0]["name"] == "pii"


@pytest.mark.unit_tests
def test_builtin_validate_does_not_persist_rows(
    client: GenaiEngineTestClientBase,
):
    inferences_before = _count_rows(DatabaseInference)
    prompt_rule_results_before = _count_rows(DatabasePromptRuleResult)
    response_rule_results_before = _count_rows(DatabaseResponseRuleResult)

    status_code, _ = client.builtin_validate(
        prompt="Validate this text statelessly please.",
        checks=[
            {"type": "prompt_injection"},
            {"type": "toxicity"},
            {"type": "pii"},
        ],
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
        prompt="Some arbitrary tool-call output.",
        checks=[
            {"type": "toxicity"},
            {"type": "prompt_injection"},
            {"type": "pii"},
        ],
    )
    assert status_code == 200
    names = [r["name"] for r in body["results"]]
    assert names == ["toxicity", "prompt_injection", "pii"]
