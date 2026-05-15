import uuid
from datetime import datetime

from arthur_common.models.common_schemas import (
    ExamplesConfig,
    KeywordsConfig,
    PIIConfig,
    RegexConfig,
    ToxicityConfig,
)
from arthur_common.models.enums import RuleScope
from fastapi import APIRouter, Depends, HTTPException

from dependencies import get_scorer_client
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from rules_engine import RuleEngine
from schemas.builtin_validate_schemas import (
    BUILTIN_CHECK_TO_RULE_TYPE,
    BuiltinCheck,
    BuiltinCheckName,
    BuiltinValidationRequest,
    BuiltinValidationResponse,
    KeywordCheck,
    PIICheck,
    RegexCheck,
    SensitiveDataCheck,
    ToxicityCheck,
)
from schemas.enums import PermissionLevelsEnum, RuleScoringMethod
from schemas.internal_schemas import (
    PromptRuleResult,
    Rule,
    User,
    ValidationRequest,
)
from schemas.rules_schema_utils import CONFIG_CHECKERS
from scorer.score import ScorerClient
from utils.users import permission_checker

builtin_validate_routes = APIRouter(
    prefix="/api/v2",
    route_class=GenaiEngineRoute,
)


_PROMPT_ONLY_CHECKS = {BuiltinCheckName.PROMPT_INJECTION}
_RESPONSE_ONLY_CHECKS = {BuiltinCheckName.HALLUCINATION}


def _validate_prerequisites(
    check_name: BuiltinCheckName,
    request: BuiltinValidationRequest,
) -> None:
    if check_name == BuiltinCheckName.PROMPT_INJECTION and not request.prompt:
        raise HTTPException(
            status_code=400,
            detail="Check 'prompt_injection' requires `prompt` to be provided.",
        )
    if check_name == BuiltinCheckName.HALLUCINATION:
        if not request.response:
            raise HTTPException(
                status_code=400,
                detail="Check 'hallucination' requires `response` to be provided.",
            )
        if not request.context:
            raise HTTPException(
                status_code=400,
                detail="Check 'hallucination' requires `context` to be provided.",
            )


def _build_synthetic_rule(
    check: BuiltinCheck,
    request: BuiltinValidationRequest,
) -> Rule:
    check_name = check.type
    rule_type = BUILTIN_CHECK_TO_RULE_TYPE[check_name]

    config: (
        ToxicityConfig
        | PIIConfig
        | RegexConfig
        | KeywordsConfig
        | ExamplesConfig
        | None
    )
    if isinstance(check, ToxicityCheck):
        config = check.config or ToxicityConfig()
    elif isinstance(check, PIICheck):
        config = check.config or PIIConfig()
    elif isinstance(
        check,
        (RegexCheck, KeywordCheck, SensitiveDataCheck),
    ):
        config = check.config
    else:
        config = None

    rule_data = CONFIG_CHECKERS[rule_type.value](config)

    if check_name in _PROMPT_ONLY_CHECKS:
        prompt_enabled, response_enabled = True, False
    elif check_name in _RESPONSE_ONLY_CHECKS:
        prompt_enabled, response_enabled = False, True
    else:
        prompt_enabled = bool(request.prompt)
        response_enabled = bool(request.response)

    now = datetime.now()
    return Rule(
        id=str(uuid.uuid4()),
        name=check_name.value,
        type=rule_type,
        prompt_enabled=prompt_enabled,
        response_enabled=response_enabled,
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
        "Stateless validation of arbitrary input against Arthur's built-in checks. "
        "Does NOT persist results, does NOT create an inference, and is task-less. "
        "Intended for ad-hoc checks such as validating tool-call output before passing "
        "it back to an LLM.\n\n"
        "Supported checks: prompt_injection, toxicity, pii, hallucination, regex, "
        "keyword, sensitive_data. Each check declares its type and (where applicable) "
        "an inline config. Hallucination requires both `response` and `context`; "
        "prompt_injection requires `prompt`; the rest run against whichever of "
        "`prompt`/`response` you populate.\n\n"
        "A check may return result=`Model Not Available` if its underlying model has "
        "not finished loading. Callers should treat this as transient and retry."
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
    for check in body.checks:
        _validate_prerequisites(check.type, body)

    rules = [_build_synthetic_rule(check, body) for check in body.checks]
    request = ValidationRequest(
        prompt=body.prompt,
        response=body.response,
        context=body.context,
    )
    rule_engine_results = RuleEngine(scorer_client).evaluate(request, rules)
    results = [
        PromptRuleResult._from_rule_engine_model(r)._to_response_model()
        for r in rule_engine_results
    ]
    return BuiltinValidationResponse(results=results)
