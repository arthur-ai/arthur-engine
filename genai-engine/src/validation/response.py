from arthur_common.models.request_schemas import ResponseValidationRequest
from arthur_common.models.response_schemas import ValidationResult
from sqlalchemy.orm import Session

from repositories.inference_repository import InferenceRepository
from rules_engine import RuleEngine
from schemas.internal_schemas import Rule, ValidationRequest
from scorer.score import ScorerClient
from services.trace.guardrail_span_emitter import emit_guardrail_span


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

    validation_request = ValidationRequest(
        response=body.response,
        context=body.context,
        model_name=body.model_name,
    )

    # create RuleEngine object and evaluate the rules
    rule_engine = RuleEngine(scorer_client)
    rule_results = rule_engine.evaluate(validation_request, rules)

    inference_response = inference_repo.save_response(
        inference_id,
        body.response,
        body.context or "",
        rule_results,
        model_name=body.model_name,
    )

    result = ValidationResult(
        inference_id=inference_response.inference_id,
        rule_results=inference_response._to_response_model().response_rule_results,
        model_name=body.model_name,
    )

    # Best-effort: surface this guardrail invocation in the trace viewer. The
    # response span nests under the prompt span of the same inference (derived case).
    # Skipped for callers that emit their own trace (e.g. the chatbot), which
    # would otherwise get a disconnected standalone guardrail trace per turn.
    if emit_guardrail_trace:
        input_payload: dict[str, str] = {"response": body.response}
        if body.context:
            input_payload["context"] = body.context
        emit_guardrail_span(
            db_session,
            task_id=task_id,
            inference_id=result.inference_id,
            rule_results=result.rule_results,
            input_payload=input_payload,
            is_response=True,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
        )

    return result
