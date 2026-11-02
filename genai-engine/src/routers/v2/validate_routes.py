from uuid import UUID

from arthur_common.models.enums import RuleResultEnum, RuleScope
from arthur_common.models.request_schemas import (
    PromptValidationRequest,
    ResponseValidationRequest,
)
from arthur_common.models.response_schemas import HTTPError, ValidationResult
from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from config.cache_config import cache_config
from dependencies import get_db_session, get_org_scope, get_scorer_client
from repositories.inference_repository import InferenceRepository
from repositories.rules_repository import RuleRepository
from repositories.tasks_rules_repository import TasksRulesRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from rules_engine import RuleEngine
from schemas.builtin_validate_schemas import (
    BuiltinValidationRequest,
    BuiltinValidationResponse,
)
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import (
    PromptRuleResult,
    Rule,
    RuleEngineResult,
    User,
    ValidationRequest,
)
from scorer.score import ScorerClient
from services.trace.guardrail_span_emitter import parse_traceparent
from utils.users import enforce_org_scope, permission_checker
from validation.prompt import validate_prompt
from validation.response import validate_response

validate_routes = APIRouter(
    prefix="/api/v2",
    route_class=GenaiEngineRoute,
)


@validate_routes.post(
    "/validate_prompt",
    description="[Deprecated] Validate a non-task related prompt based on the configured default rules.",
    response_model=ValidationResult,
    response_model_exclude_none=True,
    tags=["Default Validation"],
    deprecated=True,
)
@permission_checker(permissions=PermissionLevelsEnum.DEFAULT_VALIDATION_RUN.value)
def default_validate_prompt(
    body: PromptValidationRequest,
    db_session: Session = Depends(get_db_session),
    scorer_client: ScorerClient = Depends(get_scorer_client),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> ValidationResult:
    try:
        rules_repo = RuleRepository(db_session)
        default_rules, _ = rules_repo.query_rules(
            prompt_enabled=True,
            rule_scopes=[RuleScope.DEFAULT],
        )
        if not body.user_id and current_user:
            body.user_id = current_user.id
        return validate_prompt(
            body=body,
            db_session=db_session,
            scorer_client=scorer_client,
            rules=default_rules,
        )
    finally:
        db_session.close()


@validate_routes.post(
    "/validate_response/{inference_id}",
    description="[Deprecated] Validate a non-task related generated response based on the configured default rules. "
    "Inference ID corresponds to the previously validated associated prompt’s inference ID. Must provide "
    "context if a Hallucination Rule is an enabled default rule.",
    response_model=ValidationResult,
    response_model_exclude_none=True,
    tags=["Default Validation"],
    deprecated=True,
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_WRITE.value)
def default_validate_response(
    inference_id: UUID,
    body: ResponseValidationRequest,
    db_session: Session = Depends(get_db_session),
    scorer_client: ScorerClient = Depends(get_scorer_client),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    org_scope: UUID | None = Depends(get_org_scope),
) -> ValidationResult:
    try:
        # Validate inference ownership for tenants before running rules / writes.
        if org_scope is not None:
            InferenceRepository(db_session).get_inference(
                str(inference_id), org_scope=org_scope
            )

        rules_repo = RuleRepository(db_session)

        default_rules, _ = rules_repo.query_rules(
            response_enabled=True,
            rule_scopes=[RuleScope.DEFAULT],
        )

        return validate_response(
            inference_id=str(inference_id),
            body=body,
            db_session=db_session,
            scorer_client=scorer_client,
            rules=default_rules,
        )
    finally:
        db_session.close()


@validate_routes.post(
    "/tasks/{task_id}/validate_prompt",
    description="Validate a prompt based on the configured rules for this task. "
    "Note: Rules related to specific tasks are cached for {} seconds. ".format(
        cache_config.TASK_RULES_CACHE_TTL,
    ),
    responses={200: {"model": ValidationResult}, 400: {"model": HTTPError}},
    response_model_exclude_none=True,
    tags=["Task Based Validation"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_WRITE.value)
@enforce_org_scope()
def validate_prompt_endpoint(
    body: PromptValidationRequest,
    task_id: UUID,
    traceparent: str | None = Header(
        default=None,
        description="Optional W3C traceparent header. When supplied, the emitted "
        "guardrail span joins that trace, nested under its parent span; otherwise "
        "a trace is derived from the inference ID. OpenTelemetry-instrumented "
        "callers send this automatically.",
    ),
    db_session: Session = Depends(get_db_session),
    scorer_client: ScorerClient = Depends(get_scorer_client),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> ValidationResult:
    try:
        trace_id, parent_span_id = parse_traceparent(traceparent)
        tasks_rules_repo = TasksRulesRepository(db_session)
        task_rules = tasks_rules_repo.get_task_rules_ids_cached(str(task_id))
        rules_repo = RuleRepository(db_session)
        rules, _ = rules_repo.query_rules(
            rule_ids=task_rules,
            prompt_enabled=True,
        )
        return validate_prompt(
            body=body,
            task_id=str(task_id),
            db_session=db_session,
            scorer_client=scorer_client,
            rules=rules,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
        )
    finally:
        db_session.close()


@validate_routes.post(
    "/tasks/{task_id}/validate_response/{inference_id}",
    description="Validate a response based on the configured rules for this task. Inference ID corresponds "
    "to the previously validated associated prompt’s inference id. Must provide "
    "context if a Hallucination Rule is an enabled task rule. "
    "Note: Rules related to specific tasks are cached for {} seconds. ".format(
        cache_config.TASK_RULES_CACHE_TTL,
    ),
    responses={200: {"model": ValidationResult}, 400: {"model": HTTPError}},
    response_model_exclude_none=True,
    tags=["Task Based Validation"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_WRITE.value)
@enforce_org_scope()
def validate_response_endpoint(
    inference_id: UUID,
    body: ResponseValidationRequest,
    task_id: UUID,
    traceparent: str | None = Header(
        default=None,
        description="Optional W3C traceparent header. When supplied, the emitted "
        "guardrail span joins that trace, nested under its parent span; otherwise "
        "it joins the trace derived from the inference ID, under its prompt span. "
        "OpenTelemetry-instrumented callers send this automatically.",
    ),
    db_session: Session = Depends(get_db_session),
    scorer_client: ScorerClient = Depends(get_scorer_client),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    org_scope: UUID | None = Depends(get_org_scope),
) -> ValidationResult:
    try:
        trace_id, parent_span_id = parse_traceparent(traceparent)
        # @enforce_org_scope above validated the task_id; also validate the
        # inference belongs to a task in the caller's org so a tenant can't
        # bind a foreign inference to their own task.
        if org_scope is not None:
            InferenceRepository(db_session).get_inference(
                str(inference_id), org_scope=org_scope
            )
        tasks_rules_repo = TasksRulesRepository(db_session)
        task_rules = tasks_rules_repo.get_task_rules_ids_cached(str(task_id))
        rules_repo = RuleRepository(db_session)
        rules, _ = rules_repo.query_rules(
            rule_ids=task_rules,
            response_enabled=True,
        )
        return validate_response(
            inference_id=str(inference_id),
            body=body,
            db_session=db_session,
            scorer_client=scorer_client,
            rules=rules,
            task_id=str(task_id),
            trace_id=trace_id,
            parent_span_id=parent_span_id,
        )
    finally:
        db_session.close()


@validate_routes.post(
    "/validate",
    description=(
        "Stateless validation of arbitrary input against inline rule specs. Does NOT "
        "persist results, does NOT create an inference, and is task-less. Intended for "
        "ad-hoc checks such as validating tool-call output before passing it back to an "
        "LLM.\n\n"
        "Each entry in `checks` is a `NewRuleRequest` — the same shape accepted by the "
        "rule-management API. `type` is a `RuleType` enum value: `PromptInjectionRule`, "
        "`ToxicityRule`, `PIIDataRule`, `ModelHallucinationRuleV2`, `RegexRule`, "
        "`KeywordRule`, `ModelSensitiveDataRule`.\n\n"
        "`apply_to_prompt` and `apply_to_response` decide which of `prompt` and "
        "`response` a check scores; a check that applies to both fails if either "
        "one violates it.\n\n"
        "Hallucination requires `response` + `context`; if `context` is missing the rule "
        "engine returns a `Skipped` result. A check may return result=`Model Not "
        "Available` if its underlying model has not finished loading; callers should "
        "treat this as transient and retry."
    ),
    response_model=BuiltinValidationResponse,
    response_model_exclude_none=True,
    tags=["Stateless Validation"],
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_WRITE.value)
def stateless_validate(
    body: BuiltinValidationRequest,
    scorer_client: ScorerClient = Depends(get_scorer_client),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> BuiltinValidationResponse:
    rules = [Rule._from_request_model(c, RuleScope.DEFAULT) for c in body.checks]
    engine_results = _evaluate_prompt_and_response(
        RuleEngine(scorer_client),
        body,
        rules,
    )
    results = [
        PromptRuleResult._from_rule_engine_model(r)._to_response_model()
        for r in engine_results
    ]
    return BuiltinValidationResponse(results=results)


# When one side fails and the other passes, the rule fails. A side the rule
# could not score (model unavailable) outranks a pass, and a pass outranks a
# side that skipped the rule because it had nothing to score.
_RESULT_PRECEDENCE = [
    RuleResultEnum.FAIL,
    RuleResultEnum.UNAVAILABLE,
    RuleResultEnum.MODEL_NOT_AVAILABLE,
    RuleResultEnum.PARTIALLY_UNAVAILABLE,
    RuleResultEnum.PASS,
    RuleResultEnum.SKIPPED,
]

_MERGED_DETAIL_LISTS = [
    "keywords",
    "regex_matches",
    "pii_entities",
    "pii_results",
    "claims",
]


def _evaluate_prompt_and_response(
    engine: RuleEngine,
    body: BuiltinValidationRequest,
    rules: list[Rule],
) -> list[RuleEngineResult]:
    """Scores the prompt and the response separately, like validate_prompt and
    validate_response do for a task, then merges each rule's results.

    The rule engine scores one text per request (the response when present,
    otherwise the prompt), so a single combined request would never look at
    the prompt once a response is given.
    """
    side_requests: list[tuple[ValidationRequest, list[Rule]]] = []
    if body.prompt:
        side_requests.append(
            (
                ValidationRequest(prompt=body.prompt, context=body.context),
                [r for r in rules if r.prompt_enabled],
            ),
        )
    if body.response:
        side_requests.append(
            (
                ValidationRequest(
                    prompt=body.prompt,
                    response=body.response,
                    context=body.context,
                ),
                [r for r in rules if r.response_enabled],
            ),
        )

    results_by_rule: dict[str, list[RuleEngineResult]] = {r.id: [] for r in rules}
    for request, side_rules in side_requests:
        for result in engine.evaluate(request, side_rules):
            results_by_rule[result.rule.id].append(result)

    # A rule scoped only to a side that was not provided keeps the previous
    # behavior: it is scored against the request as given.
    unscored = [r for r in rules if not results_by_rule[r.id]]
    if unscored:
        request = ValidationRequest(
            prompt=body.prompt,
            response=body.response,
            context=body.context,
        )
        for result in engine.evaluate(request, unscored):
            results_by_rule[result.rule.id].append(result)

    return [_merge_side_results(results_by_rule[r.id]) for r in rules]


def _merge_side_results(results: list[RuleEngineResult]) -> RuleEngineResult:
    if len(results) == 1:
        return results[0]

    deciding = min(
        results,
        key=lambda r: _RESULT_PRECEDENCE.index(r.rule_score_result.result),
    )
    score = deciding.rule_score_result.model_copy(deep=True)
    same_result = [
        r.rule_score_result
        for r in results
        if r.rule_score_result.result == score.result
    ]
    if score.details is not None and len(same_result) > 1:
        for field in _MERGED_DETAIL_LISTS:
            merged = []
            for other in same_result:
                for item in getattr(other.details, field, None) or []:
                    if item not in merged:
                        merged.append(item)
            if getattr(score.details, field) is not None or merged:
                setattr(score.details, field, merged)
    score.prompt_tokens = sum(r.rule_score_result.prompt_tokens for r in results)
    score.completion_tokens = sum(
        r.rule_score_result.completion_tokens for r in results
    )
    return RuleEngineResult(
        rule_score_result=score,
        rule=deciding.rule,
        latency_ms=sum(r.latency_ms for r in results),
    )
