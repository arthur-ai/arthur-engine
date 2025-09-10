import pytest
from schemas.internal_schemas import Rule, Task
from arthur_common.models.request_schemas import PromptValidationRequest
from tests.clients.base_test_client import (
    override_get_db_session,
    override_get_scorer_client,
)
from validation.prompt import validate_prompt


@pytest.mark.unit_tests
def test_validate_prompt(
    create_task: Task,
    create_rule_for_task_sensitive_data: Rule,
    create_rule_for_task_regex: Rule,
    create_rule_for_task_keywords: Rule,
    create_rule_for_task_prompt_injection: Rule,
    create_rule_for_task_pii: Rule,
    create_rule_for_task_toxicity: Rule,
):
    prompt_validation_request = PromptValidationRequest(prompt="Hello, world!")
    db_session = override_get_db_session()
    scorer_client = override_get_scorer_client()

    validated_prompt = validate_prompt(
        prompt_validation_request,
        task_id=create_task.id,
        db_session=db_session,
        scorer_client=scorer_client,
        rules=[
            create_rule_for_task_sensitive_data,
            create_rule_for_task_regex,
            create_rule_for_task_keywords,
            create_rule_for_task_prompt_injection,
            create_rule_for_task_pii,
            create_rule_for_task_toxicity,
        ],
    )

    assert len(validated_prompt.rule_results) == 6
    assert [rule.id for rule in validated_prompt.rule_results] == [
        create_rule_for_task_sensitive_data.id,
        create_rule_for_task_regex.id,
        create_rule_for_task_keywords.id,
        create_rule_for_task_prompt_injection.id,
        create_rule_for_task_pii.id,
        create_rule_for_task_toxicity.id,
    ]
