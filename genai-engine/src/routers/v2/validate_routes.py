from uuid import UUID

from arthur_common.models.enums import RuleScope
from arthur_common.models.request_schemas import (
    PromptValidationRequest,
    ResponseValidationRequest,
)
from arthur_common.models.response_schemas import HTTPError, ValidationResult
from fastapi import APIRouter, Depends
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
from utils.users import permission_checker
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
@permission_checker(permissions=PermissionLevelsEnum.INFERENCE_WRITE.value)
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
    except Exception as e:
        raise e
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
) -> ValidationResult:
    try:
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

    except:
        raise
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
        )
    except Exception as err:
        raise
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
        return validate_response(
            inference_id=str(inference_id),
            body=body,
            db_session=db_session,
            scorer_client=scorer_client,
            rules=rules,
        )
    except Exception as err:
        raise err
    finally:
        db_session.close()
