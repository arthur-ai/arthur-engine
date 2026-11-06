import hashlib
from unittest.mock import patch

import pytest
from arthur_common.models.request_schemas import PromptValidationRequest

from db_models import DatabaseSpan
from repositories.inference_repository import InferenceRepository
from schemas.internal_schemas import Rule, Task
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


@pytest.mark.unit_tests
def test_validate_prompt_emits_guardrail_span(
    create_task: Task,
    create_rule_for_task_keywords: Rule,
):
    """End-to-end: validate_prompt writes a GUARDRAIL span into a trace derived
    from the inference id, carrying the rule outcomes in output.value and scoped to
    the route's task."""
    db_session = override_get_db_session()
    result = validate_prompt(
        PromptValidationRequest(prompt="Hello, world!"),
        task_id=create_task.id,
        db_session=db_session,
        scorer_client=override_get_scorer_client(),
        rules=[create_rule_for_task_keywords],
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
    span = spans[0]
    # Org/task stamping comes from the route task, not any caller-supplied trace.
    assert span.task_id == create_task.id
    # The span brackets the evaluation, so it has a real, non-inverted duration.
    assert span.start_time is not None and span.end_time is not None
    assert span.end_time >= span.start_time
    # Ingestion unflattens dot-notation attributes and JSON-parses output.value.
    output_value = span.raw_data["attributes"]["output"]["value"]
    assert output_value["inference_id"] == result.inference_id
    assert len(output_value["rule_results"]) == 1
    assert output_value["rule_results"][0]["id"] == create_rule_for_task_keywords.id


@pytest.mark.unit_tests
def test_validate_prompt_skips_guardrail_span_when_disabled(
    create_task: Task,
    create_rule_for_task_keywords: Rule,
):
    """Callers that emit their own trace (emit_guardrail_trace=False, e.g. the
    chatbot) must not produce a standalone guardrail span."""
    db_session = override_get_db_session()
    result = validate_prompt(
        PromptValidationRequest(prompt="Hello, world!"),
        task_id=create_task.id,
        db_session=db_session,
        scorer_client=override_get_scorer_client(),
        rules=[create_rule_for_task_keywords],
        emit_guardrail_trace=False,
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
    assert spans == []


@pytest.mark.unit_tests
def test_validate_prompt_save_failure_persists_no_span(
    create_task: Task,
    create_rule_for_task_keywords: Rule,
):
    """A failed inference save must leave no guardrail span behind."""
    db_session = override_get_db_session()
    with patch.object(
        InferenceRepository,
        "save_prompt",
        side_effect=RuntimeError("save blew up"),
    ):
        with pytest.raises(RuntimeError, match="save blew up"):
            validate_prompt(
                PromptValidationRequest(prompt="Hello, world!"),
                task_id=create_task.id,
                db_session=db_session,
                scorer_client=override_get_scorer_client(),
                rules=[create_rule_for_task_keywords],
            )

    # The inference id is generated inside validate_prompt, so scope by task.
    spans = (
        db_session.query(DatabaseSpan)
        .filter(
            DatabaseSpan.task_id == create_task.id,
            DatabaseSpan.span_kind == "GUARDRAIL",
        )
        .all()
    )
    assert spans == []
