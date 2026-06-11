import uuid

from arthur_common.models.request_schemas import PromptValidationRequest
from arthur_common.models.response_schemas import ValidationResult
from sqlalchemy.orm import Session

from repositories.inference_repository import InferenceRepository
from rules_engine import RuleEngine
from schemas.internal_schemas import Rule, ValidationRequest
from scorer.score import ScorerClient
from services.trace.guardrail_span_emitter import guardrail_span


def validate_prompt(
    body: PromptValidationRequest,
    db_session: Session,
    scorer_client: ScorerClient,
    rules: list[Rule],
    task_id: str | None = None,
    trace_id: str | None = None,
    parent_span_id: str | None = None,
    emit_guardrail_trace: bool = True,
) -> ValidationResult:
    inference_repo = InferenceRepository(db_session)
    # Pre-generated so the guardrail span's derived trace can start before
    # evaluation; save_prompt persists the same id.
    inference_id = str(uuid.uuid4())
    validation_request = ValidationRequest(prompt=body.prompt)

    with guardrail_span(
        db_session,
        enabled=emit_guardrail_trace and bool(rules),
        task_id=task_id,
        inference_id=inference_id,
        input_payload={"prompt": body.prompt},
        is_response=False,
        trace_id=trace_id,
        parent_span_id=parent_span_id,
        user_id=body.user_id,
        session_id=body.conversation_id,
    ) as gspan:
        rule_results = RuleEngine(scorer_client).evaluate(validation_request, rules)
        gspan.set_rule_results(rule_results)

    inference_prompt = inference_repo.save_prompt(
        body.prompt,
        rule_results,
        task_id=task_id,
        conversation_id=body.conversation_id,
        user_id=body.user_id,
        inference_id=inference_id,
    )
    # Flushed only now, after the inference committed.
    gspan.persist()

    return ValidationResult(
        inference_id=inference_prompt.inference_id,
        rule_results=inference_prompt._to_response_model().prompt_rule_results,
        user_id=body.user_id,
    )
