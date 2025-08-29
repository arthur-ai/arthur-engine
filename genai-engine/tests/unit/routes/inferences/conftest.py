from typing import Generator

import pytest
from db_models.db_models import DatabaseInference
from dependencies import get_application_config
from repositories.inference_repository import InferenceRepository
from repositories.metrics_repository import MetricRepository
from repositories.rules_repository import RuleRepository
from repositories.tasks_repository import TaskRepository
from arthur_common.models.enums import RuleResultEnum, RuleScope
from schemas.internal_schemas import (
    InferencePrompt,
    InferenceResponse,
    Rule,
    RuleEngineResult,
    Task,
)
from arthur_common.models.request_schemas import NewRuleRequest, NewTaskRequest
from schemas.scorer_schemas import (
    RuleScore,
    ScorerHallucinationClaim,
    ScorerRuleDetails,
)
from tests.clients.base_test_client import override_get_db_session


@pytest.fixture
def create_task() -> Generator[Task, None, None]:
    db_session = override_get_db_session()
    application_config = get_application_config(session=db_session)
    request = NewTaskRequest(name="dummy_task_name")
    rules_repo = RuleRepository(db_session)
    metric_repo = MetricRepository(db_session)
    tasks_repo = TaskRepository(db_session, rules_repo, metric_repo, application_config)
    task = Task._from_request_model(request)
    task = tasks_repo.create_task(task)

    yield task

    if task.rule_links:
        for rule_link in task.rule_links:
            tasks_repo.delete_rule_link(task_id=task.id, rule_id=rule_link.rule_id)
    tasks_repo.delete_task(task_id=task.id)


def create_prompt_in_db(
    inference_repository: InferenceRepository,
    task_id: str | None = None,
) -> InferencePrompt:
    prompt = inference_repository.save_prompt(
        prompt=f"Is this the real life number?",
        prompt_rule_results=[],
        conversation_id=f"dummy_conversation_id",
        user_id="genai_engine_user",
        task_id=task_id,
    )

    return prompt


@pytest.fixture
def create_rule(create_task: Task) -> Generator[Rule, None, None]:
    db_session = override_get_db_session()
    application_config = get_application_config(session=db_session)
    request = NewRuleRequest(
        name="dummy_rule_name",
        type="ModelHallucinationRuleV2",
        apply_to_prompt=False,
        apply_to_response=True,
    )
    rules_repo = RuleRepository(db_session)
    metric_repo = MetricRepository(db_session)
    tasks_repo = TaskRepository(db_session, rules_repo, metric_repo, application_config)
    new_rule = rules_repo.create_rule(
        Rule._from_request_model(request, scope=RuleScope.TASK),
    )
    tasks_repo.link_rule_to_task(create_task.id, new_rule.id, new_rule.type)

    yield new_rule

    rules_repo.delete_rule(rule_id=new_rule.id)


def add_response_to_inference(
    inference_repository: InferenceRepository,
    inference_id: str,
    rule: Rule,
) -> InferenceResponse:
    response = ""
    claims = [
        ScorerHallucinationClaim(
            claim="no escape from reality",
            valid=False,
            order_number=2,
            reason="No hallucination!",
        ),
        ScorerHallucinationClaim(
            claim="Is this just fantasy?",
            valid=False,
            order_number=0,
            reason="No hallucination!",
        ),
        ScorerHallucinationClaim(
            claim="Caught in a landslide,",
            valid=False,
            order_number=1,
            reason="No hallucination!",
        ),
    ]
    details = ScorerRuleDetails(claims=claims)
    rule_score = RuleScore(
        result=RuleResultEnum.PASS,
        details=details,
        prompt_tokens=1,
        completion_tokens=1,
    )
    rule_results = [
        RuleEngineResult(rule_score_result=rule_score, rule=rule, latency_ms=42),
    ]
    inference_repository.save_response(
        inference_id=inference_id,
        response=response,
        response_context="",
        response_rule_results=rule_results,
    )


@pytest.fixture
def create_prompt_inference() -> Generator[InferencePrompt, None, None]:
    db_session = override_get_db_session()
    inference_repository = InferenceRepository(
        db_session=db_session,
    )

    prompt = create_prompt_in_db(inference_repository)

    yield prompt

    inference_repository.delete_inference(inference_id=prompt.inference_id)


@pytest.fixture
def create_prompt_inference_with_task(
    create_task: Task,
) -> Generator[tuple[Task, InferencePrompt], None, None]:
    db_session = override_get_db_session()
    inference_repository = InferenceRepository(
        db_session=db_session,
    )

    prompt = create_prompt_in_db(inference_repository, create_task.id)

    yield create_task, prompt

    inference_repository.delete_inference(inference_id=prompt.inference_id)


@pytest.fixture
def create_inference_with_prompt_and_response(
    create_task: Task,
    create_rule: Rule,
) -> Generator[DatabaseInference, None, None]:
    db_session = override_get_db_session()
    inference_repository = InferenceRepository(
        db_session=db_session,
    )

    prompt = create_prompt_in_db(inference_repository, create_task.id)
    _ = add_response_to_inference(
        inference_repository=inference_repository,
        inference_id=prompt.inference_id,
        rule=create_rule,
    )
    inference = inference_repository.get_inference(inference_id=prompt.inference_id)

    yield inference

    inference_repository.delete_inference(inference_id=prompt.inference_id)
