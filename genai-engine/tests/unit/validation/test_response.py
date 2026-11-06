import hashlib

import pytest
from arthur_common.models.request_schemas import ResponseValidationRequest

from db_models import DatabaseSpan
from repositories.inference_repository import InferenceRepository
from schemas.internal_schemas import InferencePrompt, Rule, Task
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


@pytest.mark.unit_tests
def test_validate_response_with_model_name(
    create_task: Task,
    create_rule_for_task_regex: Rule,
    create_rule_for_task_keywords: Rule,
    create_rule_for_task_pii: Rule,
    create_rule_for_task_toxicity: Rule,
    create_rule_for_task_hallucination_v2: Rule,
    create_prompt_inference_with_task: tuple[Task, InferencePrompt],
):
    """Test that model_name is properly handled in response validation."""
    _, inference_prompt = create_prompt_inference_with_task
    model_name = "gpt-4o-mini"
    response_validation_request = ResponseValidationRequest(
        response="Hello, citizen!",
        model_name=model_name,
    )
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

    # Verify model_name is returned in the validation result
    assert validated_response.model_name == model_name
    assert len(validated_response.rule_results) == 5

    # Verify model_name is stored in the database objects
    inference_repository = InferenceRepository(db_session=db_session)
    stored_inference = inference_repository.get_inference(
        inference_id=inference_prompt.inference_id,
    )

    # Check model_name in Inference object
    assert stored_inference.model_name == model_name

    # Check model_name in InferenceResponse object
    assert stored_inference.inference_response is not None
    assert stored_inference.inference_response.model_name == model_name


@pytest.mark.unit_tests
def test_validate_response_guardrail_span_carries_user_and_session(
    create_rule_for_task_keywords: Rule,
    create_prompt_inference_with_task: tuple[Task, InferencePrompt],
):
    """The response GUARDRAIL span sources user/session from the persisted
    inference — the response request body carries neither."""
    task, inference_prompt = create_prompt_inference_with_task
    db_session = override_get_db_session()

    result = validate_response(
        inference_id=inference_prompt.inference_id,
        body=ResponseValidationRequest(response="Hello, citizen!"),
        db_session=db_session,
        scorer_client=override_get_scorer_client(),
        rules=[create_rule_for_task_keywords],
        task_id=task.id,
    )

    derived_trace_id = hashlib.sha256(result.inference_id.encode()).hexdigest()[:32]
    spans = (
        db_session.query(DatabaseSpan)
        .filter(
            DatabaseSpan.trace_id == derived_trace_id,
            DatabaseSpan.span_kind == "GUARDRAIL",
        )
        .all()
    )

    assert len(spans) == 1
    # Fixture-written values, extracted by ingestion from user.id/session.id.
    assert spans[0].user_id == "genai_engine_user"
    assert spans[0].session_id == "dummy_conversation_id"
