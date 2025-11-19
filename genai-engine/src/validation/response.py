from arthur_common.models.request_schemas import ResponseValidationRequest
from arthur_common.models.response_schemas import ValidationResult
from sqlalchemy.orm import Session

from repositories.inference_repository import InferenceRepository
from rules_engine import RuleEngine
from schemas.internal_schemas import Rule, ValidationRequest
from scorer.score import ScorerClient


def validate_response(
    inference_id: str,
    body: ResponseValidationRequest,
    db_session: Session,
    scorer_client: ScorerClient,
    rules: list[Rule],
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

    return ValidationResult(
        inference_id=inference_response.inference_id,
        rule_results=inference_response._to_response_model().response_rule_results,
        model_name=body.model_name,
    )
