import uuid
from datetime import datetime

from arthur_common.models.common_schemas import PIIConfig, ToxicityConfig
from arthur_common.models.enums import RuleScope, RuleType
from fastapi import APIRouter, Depends

from dependencies import get_scorer_client
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from rules_engine import RuleEngine
from schemas.builtin_validate_schemas import (
    BUILTIN_CHECK_TO_RULE_TYPE,
    BuiltinCheckName,
    BuiltinValidationRequest,
    BuiltinValidationResponse,
)
from schemas.enums import PermissionLevelsEnum, RuleScoringMethod
from schemas.internal_schemas import (
    PromptRuleResult,
    Rule,
    User,
    ValidationRequest,
)
from schemas.rules_schema_utils import get_pii_data_config, get_toxicity_config
from scorer.score import ScorerClient
from utils.users import permission_checker

builtin_validate_routes = APIRouter(
    prefix="/api/v2",
    route_class=GenaiEngineRoute,
)


def _build_synthetic_rule(check: BuiltinCheckName) -> Rule:
    rule_type = BUILTIN_CHECK_TO_RULE_TYPE[check]
    if rule_type == RuleType.TOXICITY:
        rule_data = get_toxicity_config(ToxicityConfig())
    elif rule_type == RuleType.PII_DATA:
        rule_data = get_pii_data_config(PIIConfig())
    else:
        rule_data = []
    now = datetime.now()
    return Rule(
        id=str(uuid.uuid4()),
        name=check.value,
        type=rule_type,
        prompt_enabled=True,
        response_enabled=False,
        scoring_method=RuleScoringMethod.BINARY,
        created_at=now,
        updated_at=now,
        rule_data=rule_data,
        scope=RuleScope.DEFAULT,
        archived=False,
    )


@builtin_validate_routes.post(
    "/validate",
    description=(
        "Stateless validation of arbitrary text against Arthur's built-in checks "
        "(prompt_injection, toxicity, pii). Does NOT persist results, does NOT "
        "create an inference, and is task-less. Intended for ad-hoc checks such as "
        "validating tool-call output for prompt injection.\n\n"
        "Notes:\n"
        "- Configurable checks (regex, keyword, sensitive_data, hallucination) are "
        "not supported here; use the rule-management API for those.\n"
        "- A check may return result=`Model Not Available` if its underlying model "
        "has not finished loading. Callers should treat this as a transient state "
        "and retry."
    ),
    response_model=BuiltinValidationResponse,
    response_model_exclude_none=True,
    tags=["Stateless Validation"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_WRITE.value)
def builtin_validate(
    body: BuiltinValidationRequest,
    scorer_client: ScorerClient = Depends(get_scorer_client),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> BuiltinValidationResponse:
    rules = [_build_synthetic_rule(check) for check in body.checks]
    request = ValidationRequest(prompt=body.text)
    rule_engine_results = RuleEngine(scorer_client).evaluate(request, rules)
    results = [
        PromptRuleResult._from_rule_engine_model(r)._to_response_model()
        for r in rule_engine_results
    ]
    return BuiltinValidationResponse(results=results)
