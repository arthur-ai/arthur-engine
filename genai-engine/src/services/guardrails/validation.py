from uuid import UUID

from rules_engine import RuleEngine
from schemas.internal_schemas import Rule, RuleEngineResult, ValidationRequest
from scorer.score import ScorerClient
from services.guardrails.llm_configuration_service import capture_judge_context


def evaluate_guardrails(
    request: ValidationRequest,
    rules: list[Rule],
    scorer: ScorerClient,
    org_id: UUID,
) -> list[RuleEngineResult]:
    engine = RuleEngine(scorer)
    if not engine.needs_judge(request, rules):
        return engine.evaluate(request, rules)
    context = capture_judge_context(org_id)
    try:
        return RuleEngine(scorer, judge_context=context).evaluate(request, rules)
    finally:
        context.close()
