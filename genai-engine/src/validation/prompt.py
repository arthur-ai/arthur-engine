from arthur_common.models.request_schemas import PromptValidationRequest
from arthur_common.models.response_schemas import ValidationResult
from sqlalchemy.orm import Session

from repositories.inference_repository import InferenceRepository
from rules_engine import RuleEngine
from schemas.internal_schemas import Rule, ValidationRequest
from scorer.score import ScorerClient
from services.trace.guardrail_span_emitter import emit_guardrail_span


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

    validation_request = ValidationRequest(prompt=body.prompt)
    rule_results = RuleEngine(scorer_client).evaluate(
        validation_request,
        rules,
    )
    inference_prompt = inference_repo.save_prompt(
        body.prompt,
        rule_results,
        task_id=task_id,
        conversation_id=body.conversation_id,
        user_id=body.user_id,
    )

    result = ValidationResult(
        inference_id=inference_prompt.inference_id,
        rule_results=inference_prompt._to_response_model().prompt_rule_results,
        user_id=body.user_id,
    )

    # Best-effort: surface this guardrail invocation in the trace viewer.
    # Skipped for callers that emit their own trace (e.g. the chatbot), which
    # would otherwise get a disconnected standalone guardrail trace per turn.
    if emit_guardrail_trace:
        emit_guardrail_span(
            db_session,
            task_id=task_id,
            inference_id=result.inference_id,
            rule_results=result.rule_results,
            input_payload={"prompt": body.prompt},
            is_response=False,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            user_id=body.user_id,
            session_id=body.conversation_id,
        )

    return result
