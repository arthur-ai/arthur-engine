from typing import Generator

import pytest
from dependencies import get_application_config
from repositories.metrics_repository import MetricRepository
from repositories.rules_repository import RuleRepository
from repositories.tasks_repository import TaskRepository
from schemas.enums import RuleScope
from schemas.internal_schemas import Rule
from schemas.request_schemas import NewRuleRequest
from tests.clients.base_test_client import override_get_db_session


@pytest.fixture
def create_experimental_hallucination_rule():
    db_session = override_get_db_session()
    application_config = get_application_config(session=db_session)
    request = NewRuleRequest(
        name="dummy_rule_name",
        type="ModelHallucinationRuleExperimental",
        apply_to_prompt=False,
        apply_to_response=True,
    )
    rules_repo = RuleRepository(db_session)
    metric_repo = MetricRepository(db_session)
    tasks_repo = TaskRepository(db_session, rules_repo, metric_repo, application_config)
    rule = Rule._from_request_model(request, scope=RuleScope.DEFAULT)
    rule = rules_repo.create_rule(rule)
    tasks_repo.update_all_tasks_add_default_rule(rule)

    yield rule

    rules_repo.archive_rule(rule_id=rule.id)
    tasks_repo.update_all_tasks_remove_default_rule(rule.id)


@pytest.fixture
def create_default_rule() -> Generator[Rule, None, None]:
    db_session = override_get_db_session()
    application_config = get_application_config(session=db_session)
    request = NewRuleRequest(
        name="dummy_default_rule_name",
        type="ModelHallucinationRuleV2",
        apply_to_prompt=False,
        apply_to_response=True,
    )
    rules_repo = RuleRepository(db_session)
    metric_repo = MetricRepository(db_session)
    tasks_repo = TaskRepository(db_session, rules_repo, metric_repo, application_config)
    rule = Rule._from_request_model(request, scope=RuleScope.DEFAULT)
    rule = rules_repo.create_rule(rule)
    tasks_repo.update_all_tasks_add_default_rule(rule)

    yield rule

    rules_repo.archive_rule(rule_id=rule.id)
    tasks_repo.update_all_tasks_remove_default_rule(rule.id)
