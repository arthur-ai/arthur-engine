from repositories.inference_repository import InferenceRepository
from rules_engine import RuleEngine
from schemas.internal_schemas import Rule, ValidationRequest
from schemas.request_schemas import ResponseValidationRequest
from schemas.response_schemas import ValidationResult
from scorer.score import ScorerClient
from sqlalchemy.orm import Session


def validate_response(
    inference_id: str,
    body: ResponseValidationRequest,
    db_session: Session,
    scorer_client: ScorerClient,
    rules: list[Rule],
) -> ValidationResult:
    inference_repo = InferenceRepository(db_session)

    validation_request = ValidationRequest(response=body.response, context=body.context)

    # create RuleEngine object and evaluate the rules
    rule_engine = RuleEngine(scorer_client)
    rule_results = rule_engine.evaluate(validation_request, rules)

    inference_response = inference_repo.save_response(
        inference_id,
        body.response,
        body.context,
        rule_results,
    )

    return ValidationResult(
        inference_id=inference_response.inference_id,
        rule_results=inference_response._to_response_model().response_rule_results,
    )
