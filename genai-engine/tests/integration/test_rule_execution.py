import pytest
from arthur_common.models.enums import PIIEntityTypes, RuleResultEnum, RuleType
from arthur_common.models.response_schemas import (
    ExternalRuleResult,
    KeywordDetailsResponse,
    RegexDetailsResponse,
)

from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.mark.parametrize(
    ("text", "expected_result", "expected_entities"),
    [
        ["This string has no PII data", RuleResultEnum.PASS, set()],
        [
            "My IP Address is 2001:0000:130F:0000:0000:09C0:876A:130B because I talked trash on Xbox Live",
            RuleResultEnum.FAIL,
            set([PIIEntityTypes.IP_ADDRESS]),
        ],
    ],
)
@pytest.mark.integration_tests
def test_pii_results(
    text: str,
    expected_result: RuleResultEnum,
    expected_entities: set[PIIEntityTypes],
    client: GenaiEngineTestClientBase,
):
    _, task = client.create_task(empty_rules=True)
    task_id = task.id

    status_code, rule = client.create_rule(
        "",
        rule_type=RuleType.PII_DATA,
        task_id=task_id,
    )
    assert status_code == 200
    _, prompt = client.create_prompt(
        text,
        task_id=task_id,
    )

    _, response = client.create_response(
        inference_id=prompt.inference_id,
        response=text,
        task_id=task_id,
    )

    assert prompt.rule_results[0].result == expected_result
    assert response.rule_results[0].result == expected_result

    if expected_result == RuleResultEnum.FAIL:
        assert (
            prompt.rule_results[0].details.pii_entities[0].entity in expected_entities
        )
        assert (
            prompt.rule_results[0].details.pii_entities[0].span
            == "2001:0000:130F:0000:0000:09C0:876A:130B"
        )
        assert (
            response.rule_results[0].details.pii_entities[0].entity in expected_entities
        )
        assert (
            response.rule_results[0].details.pii_entities[0].span
            == "2001:0000:130F:0000:0000:09C0:876A:130B"
        )
        assert response.rule_results[0].details.pii_entities[0].confidence > 0


@pytest.mark.parametrize(
    ("rule_type"),
    [
        RuleType.REGEX,
        RuleType.KEYWORD,
        RuleType.PROMPT_INJECTION,
        RuleType.MODEL_SENSITIVE_DATA,
        RuleType.MODEL_HALLUCINATION_V2,
        RuleType.PII_DATA,
        RuleType.TOXICITY,
    ],
)
@pytest.mark.integration_tests
def test_run_rule_types_check_response_model(
    rule_type: RuleType,
    client: GenaiEngineTestClientBase,
):
    _, task = client.create_task(empty_rules=True)
    task_id = task.id

    status_code, rule = client.create_rule(
        rule_type,
        rule_type=rule_type,
        task_id=task_id,
    )
    assert status_code == 200
    status_code, prompt = client.create_prompt(
        "Tell me 5 fast facts about astronomy. Limit each fact to one sentence.",
        task_id=task_id,
    )
    assert status_code == 200
    status_code, response = client.create_response(
        inference_id=prompt.inference_id,
        task_id=task_id,
        context="A light-year is the distance light travels in a year. Astronomers use this to measure distance",
    )
    assert status_code == 200

    def validate_result_model(
        rule_type: RuleType,
        prompt_rule_results: list[ExternalRuleResult],
        response_rule_results: list[ExternalRuleResult],
    ):
        match rule_type:
            case RuleType.REGEX:
                assert len(prompt_rule_results) > 0
                assert len(response_rule_results) > 0
                for prr in prompt_rule_results:
                    assert prr.result in [RuleResultEnum.PASS, RuleResultEnum.FAIL]
                    assert isinstance(prr.details, RegexDetailsResponse)
                for rrr in response_rule_results:
                    assert rrr.result in [RuleResultEnum.PASS, RuleResultEnum.FAIL]
                    assert isinstance(prr.details, RegexDetailsResponse)
            case RuleType.KEYWORD:
                assert len(prompt_rule_results) > 0
                assert len(response_rule_results) > 0
                for prr in prompt_rule_results:
                    assert prr.result in [RuleResultEnum.PASS, RuleResultEnum.FAIL]
                    assert isinstance(prr.details, KeywordDetailsResponse)
                for rrr in response_rule_results:
                    assert rrr.result in [RuleResultEnum.PASS, RuleResultEnum.FAIL]
                    assert isinstance(prr.details, KeywordDetailsResponse)
            case RuleType.PROMPT_INJECTION:
                assert len(prompt_rule_results) > 0
                assert len(response_rule_results) == 0
                for prr in prompt_rule_results:
                    assert prr.result in [RuleResultEnum.PASS, RuleResultEnum.FAIL]
                    assert prr.details is None
                for rrr in response_rule_results:
                    assert rrr.result in [RuleResultEnum.PASS, RuleResultEnum.FAIL]
                    assert rrr.details is None
            case RuleType.MODEL_SENSITIVE_DATA:
                assert len(prompt_rule_results) > 0
                assert len(response_rule_results) == 0
                for prr in prompt_rule_results:
                    assert prr.result in [RuleResultEnum.PASS, RuleResultEnum.FAIL]
                    assert prr.details is None
            case RuleType.MODEL_HALLUCINATION_V2:
                assert len(prompt_rule_results) == 0
                assert len(response_rule_results) > 0
                for rrr in response_rule_results:
                    assert rrr.result in [
                        RuleResultEnum.PASS,
                        RuleResultEnum.FAIL,
                        RuleResultEnum.PARTIALLY_UNAVAILABLE,
                        RuleResultEnum.UNAVAILABLE,
                    ]
                    # assert type(rrr.details) is HallucinationDetailsResponse
            case RuleType.PII_DATA:
                assert len(prompt_rule_results) > 0
                assert len(response_rule_results) > 0
                for prr in prompt_rule_results:
                    assert prr.result in [RuleResultEnum.PASS, RuleResultEnum.FAIL]
                    # assert type(prr.details) is PIIDetailsResponse
                for rrr in response_rule_results:
                    assert rrr.result in [RuleResultEnum.PASS, RuleResultEnum.FAIL]
                    # assert type(rrr.details) is PIIDetailsResponse
            case RuleType.TOXICITY:
                assert len(prompt_rule_results) > 0
                assert len(response_rule_results) > 0
                for prr in prompt_rule_results:
                    assert prr.result in [RuleResultEnum.PASS, RuleResultEnum.FAIL]
                    # assert type(prr.details) is ToxicityDetailsResponse
                    assert prr.details.toxicity_score is not None
                for rrr in response_rule_results:
                    assert rrr.result in [RuleResultEnum.PASS, RuleResultEnum.FAIL]
                    # assert type(rrr.details) is ToxicityDetailsResponse
                    assert rrr.details.toxicity_score is not None

            case _:
                raise ValueError(rule_type)

    validate_result_model(rule_type, prompt.rule_results, response.rule_results)
    _, inferences = client.query_inferences(task_ids=[task.id])
    # Validate query results look the same
    query_prompt_results = inferences.inferences[0].inference_prompt.prompt_rule_results
    query_response_results = inferences.inferences[
        0
    ].inference_response.response_rule_results
    validate_result_model(rule_type, query_prompt_results, query_response_results)


@pytest.mark.parametrize(
    ("prompt_str", "expected_rule_results"),
    [
        ["Hello World", [RuleResultEnum.PASS]],
        [" ".join(["Hello World" for _ in range(5000)]), [RuleResultEnum.SKIPPED]],
    ],
)
@pytest.mark.integration_tests
def test_toxicity_skipped(
    prompt_str: str,
    expected_rule_results: list[RuleResultEnum],
    client: GenaiEngineTestClientBase,
):
    _, task = client.create_task(empty_rules=True)
    task_id = task.id

    status_code, rule = client.create_rule(
        "",
        rule_type=RuleType.TOXICITY,
        task_id=task_id,
        toxicity_threshold=0.95,
    )
    assert status_code == 200

    status_code, prompt = client.create_prompt(
        prompt_str,
        task_id=task_id,
    )
    assert status_code == 200
    status_code, response = client.create_response(
        inference_id=prompt.inference_id,
        task_id=task_id,
        context=prompt_str,
    )
    assert status_code == 200

    for rr in prompt.rule_results:
        assert rr.result in expected_rule_results
        assert (
            rr.result == RuleResultEnum.SKIPPED or rr.details.toxicity_score is not None
        )

    status_code, inferences = client.query_inferences(task_ids=[task.id])
    for inference in inferences.inferences:
        for rr in inference.inference_prompt.prompt_rule_results:
            assert rr.result in expected_rule_results
            assert (
                rr.result == RuleResultEnum.SKIPPED
                or rr.details.toxicity_score is not None
            )


@pytest.mark.parametrize(
    ("threshold", "expected_rule_results"),
    [
        [None, [RuleResultEnum.PASS, RuleResultEnum.FAIL]],
        [0.99999999, [RuleResultEnum.PASS]],
        [0.00000001, [RuleResultEnum.FAIL]],
    ],
)
@pytest.mark.integration_tests
def test_toxicity_configs(
    threshold: float,
    expected_rule_results: list[RuleResultEnum],
    client: GenaiEngineTestClientBase,
):
    _, task = client.create_task(empty_rules=True)
    task_id = task.id

    status_code, rule = client.create_rule(
        "",
        rule_type=RuleType.TOXICITY,
        task_id=task_id,
        toxicity_threshold=threshold,
    )
    assert status_code == 200

    status_code, prompt = client.create_prompt(
        "Tell me 5 fast facts about astronomy. Limit each fact to one sentence.",
        task_id=task_id,
    )
    assert status_code == 200
    status_code, response = client.create_response(
        inference_id=prompt.inference_id,
        task_id=task_id,
        context="A light-year is the distance light travels in a year. Astronomers use this to measure distance",
    )
    assert status_code == 200

    for rr in prompt.rule_results:
        assert rr.result in expected_rule_results
        assert rr.details.toxicity_score is not None
    for rr in response.rule_results:
        assert rr.result in expected_rule_results
        assert rr.details.toxicity_score is not None

    status_code, inferences = client.query_inferences(task_ids=[task.id])
    for inference in inferences.inferences:
        for rr in inference.inference_prompt.prompt_rule_results:
            assert rr.result in expected_rule_results
            assert rr.details.toxicity_score is not None
        for rr in inference.inference_response.response_rule_results:
            assert rr.result in expected_rule_results
            assert rr.details.toxicity_score is not None


@pytest.mark.integration_tests
def test_rule_result_skipped(client: GenaiEngineTestClientBase):
    status_code, task = client.create_task(empty_rules=True)
    assert status_code == 200

    client.create_rule("hallv2", RuleType.MODEL_HALLUCINATION_V2)

    status_code, prompt = client.create_prompt(task_id=task.id)
    assert status_code == 200

    # Missing Context
    status_code, response = client.create_response(
        inference_id=prompt.inference_id,
        task_id=task.id,
    )
    assert status_code == 200

    assert response.rule_results[0].result == RuleResultEnum.SKIPPED


@pytest.mark.parametrize(
    ("text", "expected_result", "expected_entities"),
    [
        ["This string has no PII data", RuleResultEnum.PASS, set()],
        [
            "My IP Address is 2001:0000:130F:0000:0000:09C0:876A:130B because I talked trash on Xbox Live",
            RuleResultEnum.FAIL,
            set([PIIEntityTypes.IP_ADDRESS]),
        ],
    ],
)
@pytest.mark.integration_tests
def test_pii_results_with_model_name(
    text: str,
    expected_result: RuleResultEnum,
    expected_entities: set[PIIEntityTypes],
    client: GenaiEngineTestClientBase,
):
    _, task = client.create_task(empty_rules=True)
    task_id = task.id

    status_code, rule = client.create_rule(
        "",
        rule_type=RuleType.PII_DATA,
        task_id=task_id,
    )
    assert status_code == 200
    _, prompt = client.create_prompt(
        text,
        task_id=task_id,
    )

    _, response = client.create_response(
        inference_id=prompt.inference_id,
        response=text,
        task_id=task_id,
        model_name="gpt-4o-mini",
    )

    assert prompt.rule_results[0].result == expected_result
    assert response.rule_results[0].result == expected_result

    if expected_result == RuleResultEnum.FAIL:
        assert (
            prompt.rule_results[0].details.pii_entities[0].entity in expected_entities
        )
        assert (
            prompt.rule_results[0].details.pii_entities[0].span
            == "2001:0000:130F:0000:0000:09C0:876A:130B"
        )
        assert (
            response.rule_results[0].details.pii_entities[0].entity in expected_entities
        )
        assert response.model_name == "gpt-4o-mini"
        assert (
            response.rule_results[0].details.pii_entities[0].span
            == "2001:0000:130F:0000:0000:09C0:876A:130B"
        )
        assert response.rule_results[0].details.pii_entities[0].confidence > 0


@pytest.mark.integration_tests
def test_response_validation_with_model_name(client: GenaiEngineTestClientBase):
    """Test that model_name is properly handled in response validation."""
    _, task = client.create_task(empty_rules=True)
    task_id = task.id

    status_code, rule = client.create_rule(
        "",
        rule_type=RuleType.REGEX,
        task_id=task_id,
    )
    assert status_code == 200

    # Create prompt
    status_code, prompt = client.create_prompt(
        "Tell me about AI",
        task_id=task_id,
    )
    assert status_code == 200

    # Create response with model_name
    status_code, response = client.create_response(
        inference_id=prompt.inference_id,
        response="AI is a fascinating field of computer science.",
        task_id=task_id,
        model_name="gpt-4o-mini",
    )
    assert status_code == 200

    # Verify model_name is returned in the response validation result
    assert response.model_name == "gpt-4o-mini"
    assert len(response.rule_results) == 1
