from uuid import UUID

from arthur_common.models.enums import RuleScope
from arthur_common.models.request_schemas import (
    PromptValidationRequest,
    ResponseValidationRequest,
)
from arthur_common.models.response_schemas import HTTPError, ValidationResult
from fastapi import APIRouter, Depends, Query
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
    User,
    ValidationRequest,
)
from scorer.score import ScorerClient
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
    trace_id: str | None = Query(
        default=None,
        description="Optional trace ID (32-hex) to attach the emitted guardrail span "
        "to an existing trace. If omitted, a trace is derived from the inference ID.",
    ),
    parent_span_id: str | None = Query(
        default=None,
        description="Optional parent span ID (16-hex) to nest the guardrail span "
        "under within the trace. Ignored when trace_id is absent.",
    ),
    db_session: Session = Depends(get_db_session),
    scorer_client: ScorerClient = Depends(get_scorer_client),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> ValidationResult:
    try:
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
    trace_id: str | None = Query(
        default=None,
        description="Optional trace ID (32-hex) to attach the emitted guardrail span "
        "to an existing trace. If omitted, the trace derived from the inference ID is "
        "reused so the response span joins its prompt span.",
    ),
    parent_span_id: str | None = Query(
        default=None,
        description="Optional parent span ID (16-hex) to nest the guardrail span "
        "under within the trace. Ignored when trace_id is absent.",
    ),
    db_session: Session = Depends(get_db_session),
    scorer_client: ScorerClient = Depends(get_scorer_client),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
    org_scope: UUID | None = Depends(get_org_scope),
) -> ValidationResult:
    try:
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
    request = ValidationRequest(
        prompt=body.prompt,
        response=body.response,
        context=body.context,
    )
    engine_results = RuleEngine(scorer_client).evaluate(request, rules)
    results = [
        PromptRuleResult._from_rule_engine_model(r)._to_response_model()
        for r in engine_results
    ]
    return BuiltinValidationResponse(results=results)
