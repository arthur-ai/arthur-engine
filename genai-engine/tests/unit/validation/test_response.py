import pytest
from schemas.internal_schemas import InferencePrompt, Rule, Task
from arthur_common.models.request_schemas import ResponseValidationRequest
from tests.clients.base_test_client import (
    override_get_db_session,
    override_get_scorer_client,
)
from validation.response import validate_response


@pytest.mark.unit_tests
def test_validate_response(
    create_task: Task,
    create_rule_for_task_sensitive_data: Rule,
    create_rule_for_task_regex: Rule,
    create_rule_for_task_keywords: Rule,
    create_rule_for_task_prompt_injection: Rule,
    create_rule_for_task_hallucination_v2: Rule,
    create_rule_for_task_pii: Rule,
    create_rule_for_task_toxicity: Rule,
    create_prompt_inference_with_task: tuple[Task, InferencePrompt],
):
    _, inference_prompt = create_prompt_inference_with_task
    response_validation_request = ResponseValidationRequest(response="Hello, citizen!")
    db_session = override_get_db_session()
    scorer_client = override_get_scorer_client()

    validated_response = validate_response(
        inference_id=inference_prompt.inference_id,
        body=response_validation_request,
        db_session=db_session,
        scorer_client=scorer_client,
        rules=[
            create_rule_for_task_regex,
            create_rule_for_task_keywords,
            create_rule_for_task_pii,
            create_rule_for_task_toxicity,
            create_rule_for_task_hallucination_v2,
        ],
    )

    assert len(validated_response.rule_results) == 5
    assert sorted([rule.id for rule in validated_response.rule_results]) == sorted(
        [
            create_rule_for_task_regex.id,
            create_rule_for_task_keywords.id,
            create_rule_for_task_pii.id,
            create_rule_for_task_toxicity.id,
            create_rule_for_task_hallucination_v2.id,
        ],
    )
