from repositories.inference_repository import InferenceRepository
from rules_engine import RuleEngine
from schemas.internal_schemas import Rule, ValidationRequest
from schemas.request_schemas import PromptValidationRequest
from schemas.response_schemas import ValidationResult
from scorer.score import ScorerClient
from sqlalchemy.orm import Session


def validate_prompt(
    body: PromptValidationRequest,
    db_session: Session,
    scorer_client: ScorerClient,
    rules: list[Rule],
    task_id: str | None = None,
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

    return ValidationResult(
        inference_id=inference_prompt.inference_id,
        rule_results=inference_prompt._to_response_model().prompt_rule_results,
        user_id=body.user_id,
    )
