import pytest
from schemas.enums import RuleType
from schemas.response_schemas import TokenUsageCount, TokenUsageResponse
from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.mark.parametrize(
    ("rule_type"),
    [
        RuleType.REGEX,
        RuleType.KEYWORD,
        RuleType.MODEL_SENSITIVE_DATA,
        RuleType.MODEL_HALLUCINATION_V2,
    ],
)
@pytest.mark.integration_tests
def test_get_token_usage_by_rule_type_incrementing(
    rule_type: RuleType,
    client: GenaiEngineTestClientBase,
):
    def get_count_by_rule(
        rule_type: RuleType,
        counts: list[TokenUsageResponse],
    ) -> TokenUsageResponse:
        for count in counts:
            if count.rule_type == rule_type:
                return count

    _, old_token_counts = client.get_token_usage(
        headers=client.authorized_org_admin_api_key_headers,
    )
    _, task = client.create_task(empty_rules=True)
    task_id = task.id

    prompt_text, prompt_text_tokens = (
        "This prompt is 10 tokens with this extra text",
        10,
    )
    response_text, response_text_tokens = (
        "This response is 20 tokens with this extra text. Extra text is good for padding token counts.",
        20,
    )
    context_text, context_text_tokens = (
        "This context is 17 tokens with this extra text. Extra text for giggles.",
        17,
    )

    client.create_rule("", rule_type=rule_type, task_id=task_id)
    _, prompt_result = client.create_prompt(prompt_text, task_id=task_id)
    client.create_response(
        inference_id=prompt_result.inference_id,
        response=response_text,
        task_id=task_id,
        context=context_text,
    )

    sc, new_token_counts = client.get_token_usage(
        headers=client.authorized_org_admin_api_key_headers,
    )
    print(new_token_counts)
    assert sc == 200

    old_count = get_count_by_rule(rule_type, old_token_counts) or TokenUsageResponse(
        rule_type=rule_type,
        count=TokenUsageCount(prompt=0, completion=0),
    )
    new_count = get_count_by_rule(rule_type, new_token_counts)

    match rule_type:
        case RuleType.REGEX:
            assert new_count.count.prompt - old_count.count.prompt == 0
            assert new_count.count.completion - old_count.count.completion == 0
        case RuleType.KEYWORD:
            assert new_count.count.prompt - old_count.count.prompt == 0
            assert new_count.count.completion - old_count.count.completion == 0
        case RuleType.PROMPT_INJECTION:
            assert new_count.count.prompt - old_count.count.prompt == 0
            assert new_count.count.completion - old_count.count.completion == 0
        case RuleType.MODEL_SENSITIVE_DATA:
            assert new_count.count.prompt - old_count.count.prompt > prompt_text_tokens
            assert new_count.count.completion - old_count.count.completion > 0
        case RuleType.MODEL_HALLUCINATION:
            assert new_count.count.prompt - old_count.count.prompt > 4 * (
                response_text_tokens + context_text_tokens
            )
            assert new_count.count.completion - old_count.count.completion > 0
        case RuleType.MODEL_HALLUCINATION_V2:
            # These thresholds are difficult to predict as claim parsing is not deterministic. 4x seems fine but may need to be adjusted.
            assert new_count.count.prompt - old_count.count.prompt > 4 * (
                response_text_tokens + context_text_tokens
            )
            assert new_count.count.completion - old_count.count.completion > 0
        case _:
            raise ValueError(rule_type)
