from arthur_common.models.request_schemas import ResponseValidationRequest
from arthur_common.models.response_schemas import ValidationResult
from sqlalchemy.orm import Session

from repositories.inference_repository import InferenceRepository
from rules_engine import RuleEngine
from schemas.internal_schemas import Rule, ValidationRequest
from scorer.score import ScorerClient
from services.trace.guardrail_span_emitter import guardrail_span


def validate_response(
    inference_id: str,
    body: ResponseValidationRequest,
    db_session: Session,
    scorer_client: ScorerClient,
    rules: list[Rule],
    task_id: str | None = None,
    trace_id: str | None = None,
    parent_span_id: str | None = None,
    emit_guardrail_trace: bool = True,
) -> ValidationResult:
    inference_repo = InferenceRepository(db_session)
    # Loaded up front: 404s on unknown ids before rules run, and supplies the
    # span's user/session (the response body carries neither).
    inference = inference_repo.get_inference(inference_id)

    validation_request = ValidationRequest(
        response=body.response,
        context=body.context,
        model_name=body.model_name,
    )

    input_payload: dict[str, str] = {"response": body.response}
    if body.context:
        input_payload["context"] = body.context

    with guardrail_span(
        db_session,
        enabled=emit_guardrail_trace and bool(rules),
        task_id=task_id,
        inference_id=inference_id,
        input_payload=input_payload,
        is_response=True,
        trace_id=trace_id,
        parent_span_id=parent_span_id,
        user_id=inference.user_id,
        session_id=inference.conversation_id,
    ) as gspan:
        rule_results = RuleEngine(scorer_client).evaluate(validation_request, rules)
        gspan.set_rule_results(rule_results)

    inference_response = inference_repo.save_response(
        inference_id,
        body.response,
        body.context or "",
        rule_results,
        model_name=body.model_name,
    )
    # Flushed only now, after the response committed.
    gspan.persist()

    return ValidationResult(
        inference_id=inference_response.inference_id,
        rule_results=inference_response._to_response_model().response_rule_results,
        model_name=body.model_name,
    )
