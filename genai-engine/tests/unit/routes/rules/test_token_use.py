from datetime import datetime, timedelta

import pytest
from arthur_common.models.enums import RuleResultEnum, RuleType, TokenUsageScope
from tests.clients.base_test_client import GenaiEngineTestClientBase
from tests.mocks.mock_scorer_client import (
    MOCK_KEYWORD_PASSING_TEXT,
    MOCK_REGEX_PASSING_TEXT,
)
from utils import constants


@pytest.mark.parametrize(
    ("start_time", "end_time"),
    [
        [None, None],
        [datetime.now() + timedelta(days=1), None],
        [None, datetime.now() - timedelta(days=1)],
    ],
)
@pytest.mark.unit_tests
def test_get_token_usage_by_rule_type(
    start_time: datetime,
    end_time: datetime,
    client: GenaiEngineTestClientBase,
):
    status_code, tokens_response = client.get_token_usage(
        start_time=start_time,
        end_time=end_time,
        headers={"Authorization": "Bearer auditor_0"},
    )
    assert status_code == 200

    for token_count in tokens_response:
        assert token_count.rule_type in [e.value for e in RuleType]
        if start_time:
            assert token_count.count.prompt == 0
            assert token_count.count.completion == 0
        if end_time:
            assert token_count.count.prompt == 0
            assert token_count.count.completion == 0


@pytest.mark.unit_tests
def test_get_token_usage_by_task(client: GenaiEngineTestClientBase):
    _, task1 = client.create_task(empty_rules=True)
    _, task2 = client.create_task(empty_rules=True)
    client.create_rule("", rule_type=RuleType.REGEX, task_id=task1.id)
    client.create_rule("", rule_type=RuleType.REGEX, task_id=task2.id)

    client.create_prompt(MOCK_REGEX_PASSING_TEXT, task1.id)

    status_code, tokens_response = client.get_token_usage(
        group_by=[TokenUsageScope.TASK],
        headers={"Authorization": "Bearer auditor_0"},
    )

    assert status_code == 200

    for usage in tokens_response:
        if usage.task_id == task2.id:
            raise ValueError("task2 should not be present")
        assert usage.rule_type is None


@pytest.mark.unit_tests
def test_get_token_usage_by_task_and_rules(client: GenaiEngineTestClientBase):
    _, task1 = client.create_task(empty_rules=True)
    _, task2 = client.create_task(empty_rules=True)
    client.create_rule("", rule_type=RuleType.REGEX, task_id=task1.id)
    client.create_rule("", rule_type=RuleType.KEYWORD, task_id=task2.id)

    client.create_prompt(MOCK_REGEX_PASSING_TEXT, task1.id)
    client.create_prompt(MOCK_KEYWORD_PASSING_TEXT, task2.id)

    status_code, tokens_response = client.get_token_usage(
        group_by=[TokenUsageScope.TASK, TokenUsageScope.RULE_TYPE],
        headers={"Authorization": "Bearer auditor_0"},
    )

    assert status_code == 200
    groups = [(usage.rule_type, usage.task_id) for usage in tokens_response]

    assert (RuleType.REGEX, task1.id) in groups
    assert (RuleType.KEYWORD, task2.id) in groups

    assert (RuleType.KEYWORD, task1.id) not in groups
    assert (RuleType.REGEX, task2.id) not in groups


@pytest.mark.parametrize(
    ("rule_type"),
    [
        RuleType.MODEL_SENSITIVE_DATA,
        RuleType.MODEL_HALLUCINATION_V2,
    ],
)
@pytest.mark.unit_tests
def test_rate_limit_handled(rule_type: RuleType, client: GenaiEngineTestClientBase):
    _, task = client.create_task(empty_rules=True)
    task_id = task.id

    _, rule = client.create_rule("", rule_type=rule_type, task_id=task_id)
    status_code, prompt_result = client.create_prompt(
        "RateLimitException",
        task_id=task_id,
    )
    status_code, response_result = client.create_response(
        inference_id=prompt_result.inference_id,
        response="RateLimitException",
        task_id=task_id,
        context="Context for this response",
    )

    match rule_type:
        case RuleType.MODEL_SENSITIVE_DATA:
            for rr in prompt_result.rule_results:
                assert rr.result == RuleResultEnum.UNAVAILABLE
                assert (
                    rr.details.message
                    == constants.ERROR_GENAI_ENGINE_RATE_LIMIT_EXCEEDED
                )
        case RuleType.MODEL_HALLUCINATION_V2:
            for rr in response_result.rule_results:
                assert rr.result == RuleResultEnum.UNAVAILABLE
                assert (
                    rr.details.message
                    == constants.ERROR_GENAI_ENGINE_RATE_LIMIT_EXCEEDED
                )
        case _:
            raise ValueError(rule_type)


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "expected_status_code, user_role",
    [
        (200, "admin_0"),
        (200, "auditor_0"),
        (403, "genai_engine_user_0"),
        (403, "no_name_0"),
    ],
)
def test_get_token_usage_by_user(
    expected_status_code: int,
    user_role: str,
    changed_user_client: GenaiEngineTestClientBase,
):
    client = changed_user_client
    status_code, _ = client.get_token_usage(
        start_time=None,
        end_time=None,
        headers={"Authorization": f"Bearer {user_role}"},
    )
    assert status_code == expected_status_code
