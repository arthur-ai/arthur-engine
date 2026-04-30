from uuid import UUID

from arthur_common.models.enums import RuleResultEnum, RuleScope
from arthur_common.models.request_schemas import (
    PromptValidationRequest,
    ResponseValidationRequest,
)
from arthur_common.models.response_schemas import HTTPError, ValidationResult
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from config.cache_config import cache_config
from dependencies import get_db_session, get_scorer_client
from repositories.rules_repository import RuleRepository
from repositories.tasks_rules_repository import TasksRulesRepository
from routers.route_handler import GenaiEngineRoute
from routers.v2 import multi_validator
from schemas.enums import PermissionLevelsEnum
from schemas.internal_schemas import User
from scorer.score import ScorerClient
from services.model_warmup_service import (
    fail_fast_when_warming,
    get_model_warmup_service,
)
from utils import constants
from utils.users import permission_checker
from validation.prompt import validate_prompt
from validation.response import validate_response

validate_routes = APIRouter(
    prefix="/api/v2",
    route_class=GenaiEngineRoute,
)


def _annotate_warmup_state(
    response: Response,
    result: ValidationResult,
) -> ValidationResult:
    """Attach a ``Retry-After`` header (or 503) when warmup blocked any rule.

    Implements the agreed signaling for the engine: 200 OK with per-rule
    ``MODEL_NOT_AVAILABLE`` and a ``Retry-After`` header. If
    ``GENAI_ENGINE_FAIL_FAST_WHEN_WARMING=true`` is set, the engine instead
    raises 503 so callers see a hard failure they can retry on.
    """
    rule_results = result.rule_results or []
    if not any(r.result == RuleResultEnum.MODEL_NOT_AVAILABLE for r in rule_results):
        return result
    retry_after = get_model_warmup_service().retry_after_seconds()
    if fail_fast_when_warming():
        raise HTTPException(
            status_code=503,
            detail="One or more models are still warming up. Retry shortly.",
            headers={constants.RETRY_AFTER_HEADER: str(retry_after)},
        )
    response.headers[constants.RETRY_AFTER_HEADER] = str(retry_after)
    return result


@validate_routes.post(
    "/validate_prompt",
    description="[Deprecated] Validate a non-task related prompt based on the configured default rules.",
    response_model=ValidationResult,
    response_model_exclude_none=True,
    tags=["Default Validation"],
    deprecated=True,
)
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_WRITE.value)
def default_validate_prompt(
    body: PromptValidationRequest,
    response: Response,
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
        result = validate_prompt(
            body=body,
            db_session=db_session,
            scorer_client=scorer_client,
            rules=default_rules,
        )
        return _annotate_warmup_state(response, result)
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
    response: Response,
    db_session: Session = Depends(get_db_session),
    scorer_client: ScorerClient = Depends(get_scorer_client),
    current_user: User | None = Depends(multi_validator.validate_api_multi_auth),
) -> ValidationResult:
    try:
        rules_repo = RuleRepository(db_session)

        default_rules, _ = rules_repo.query_rules(
            response_enabled=True,
            rule_scopes=[RuleScope.DEFAULT],
        )

        result = validate_response(
            inference_id=str(inference_id),
            body=body,
            db_session=db_session,
            scorer_client=scorer_client,
            rules=default_rules,
        )
        return _annotate_warmup_state(response, result)
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
def validate_prompt_endpoint(
    body: PromptValidationRequest,
    task_id: UUID,
    response: Response,
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
        result = validate_prompt(
            body=body,
            task_id=str(task_id),
            db_session=db_session,
            scorer_client=scorer_client,
            rules=rules,
        )
        return _annotate_warmup_state(response, result)
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
def validate_response_endpoint(
    inference_id: UUID,
    body: ResponseValidationRequest,
    task_id: UUID,
    response: Response,
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
            response_enabled=True,
        )
        result = validate_response(
            inference_id=str(inference_id),
            body=body,
            db_session=db_session,
            scorer_client=scorer_client,
            rules=rules,
        )
        return _annotate_warmup_state(response, result)
    finally:
        db_session.close()
