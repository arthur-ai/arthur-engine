import uuid

import pytest
from arthur_common.models.common_schemas import RegexConfig
from arthur_common.models.enums import RuleScope, RuleType
from arthur_common.models.request_schemas import NewRuleRequest

from dependencies import get_application_config
from repositories.metrics_repository import MetricRepository
from repositories.rules_repository import RuleRepository
from repositories.tasks_repository import TaskRepository
from schemas.internal_schemas import Rule
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)


@pytest.mark.unit_tests
def test_archive_task(client: GenaiEngineTestClientBase):
    status_code, task = client.create_task()
    assert status_code == 200

    _, regex_rule = client.create_rule("", rule_type=RuleType.REGEX, task_id=task.id)
    _, keyword_rule = client.create_rule(
        "",
        rule_type=RuleType.KEYWORD,
        task_id=task.id,
    )

    _, task = client.get_task(task.id)

    _, prompt = client.create_prompt(task_id=task.id, conversation_id=task.id)
    _, _ = client.create_response(inference_id=prompt.inference_id, task_id=task.id)

    status_code = client.delete_task(task.id)
    assert status_code == 204

    # Task should return 404
    status_code, _ = client.get_task(task.id)
    assert status_code == 404

    # Inferences should be unaffected
    _, query_resp = client.query_inferences(conversation_id=task.id)
    assert query_resp.count > 0
    assert all([i.task_id == task.id for i in query_resp.inferences])


@pytest.mark.unit_tests
def test_archive_task_rule(client: GenaiEngineTestClientBase):
    status_code, task = client.create_task()
    assert status_code == 200

    _, regex_rule = client.create_rule("", rule_type=RuleType.REGEX, task_id=task.id)
    _, keyword_rule = client.create_rule(
        "",
        rule_type=RuleType.KEYWORD,
        task_id=task.id,
    )

    _, disabled_rule = client.create_rule(
        "",
        rule_type=RuleType.KEYWORD,
        task_id=task.id,
    )

    _, task = client.get_task(task.id)

    _, prompt = client.create_prompt(task_id=task.id, conversation_id=task.id)
    _, _ = client.create_response(inference_id=prompt.inference_id, task_id=task.id)

    status_code = client.delete_task_rule(task.id, regex_rule.id)
    assert status_code == 204

    status_code, _ = client.patch_rule(task.id, disabled_rule.id, enabled=False)
    assert status_code == 200

    # Task should return 200
    status_code, task = client.get_task(task.id)
    assert status_code == 200

    # Unarchived task rule should be unaffected
    assert keyword_rule.id in [rule.id for rule in task.rules]
    # Archived task rule should not be present
    assert regex_rule.id not in [rule.id for rule in task.rules]
    # Disabled task rule should be present but disabled
    assert disabled_rule.id not in [rule.id for rule in task.rules if rule.enabled]
    assert disabled_rule.id in [rule.id for rule in task.rules if not rule.enabled]

    # Inferences should be unaffected
    _, query_resp = client.query_inferences(conversation_id=task.id)
    assert query_resp.count > 0
    assert all([i.task_id == task.id for i in query_resp.inferences])


@pytest.mark.unit_tests
def test_unarchive_task(client: GenaiEngineTestClientBase):
    status_code, task = client.create_task()
    assert status_code == 200

    _, task_rule = client.create_rule("", rule_type=RuleType.REGEX, task_id=task.id)

    # Archive the task
    status_code = client.delete_task(task.id)
    assert status_code == 204

    # Task should be inaccessible after archiving
    status_code, _ = client.get_task(task.id)
    assert status_code == 404

    # Unarchive the task
    status_code = client.unarchive_task(task.id)
    assert status_code == 204

    # Task should be accessible again
    status_code, restored_task = client.get_task(task.id)
    assert status_code == 200
    assert restored_task.id == task.id

    # Task-scoped rule should be restored
    assert task_rule.id in [rule.id for rule in restored_task.rules]


@pytest.mark.unit_tests
def test_unarchive_task_not_archived(client: GenaiEngineTestClientBase):
    status_code, task = client.create_task()
    assert status_code == 200

    # Unarchiving an active task should return 400
    status_code = client.unarchive_task(task.id)
    assert status_code == 400

    # Clean up
    client.delete_task(task.id)


@pytest.mark.unit_tests
def test_unarchive_task_not_found(client: GenaiEngineTestClientBase):
    status_code = client.unarchive_task(str(uuid.uuid4()))
    assert status_code == 404


@pytest.mark.unit_tests
@pytest.mark.integration_tests
def test_archive_task_rule_which_is_disabled(client: GenaiEngineTestClientBase):
    status_code, task = client.create_task()
    assert status_code == 200

    _, regex_rule = client.create_rule("", rule_type=RuleType.REGEX, task_id=task.id)
    _, _ = client.patch_rule(task.id, regex_rule.id, enabled=False)

    status_code = client.delete_task_rule(task.id, regex_rule.id)
    assert status_code == 204

    _, task = client.get_task(task.id)
    assert regex_rule.id not in [rule.id for rule in task.rules]

    # Clean up
    status_code = client.delete_task(task.id)
    assert status_code == 204

    status_code, _ = client.get_task(task.id)
    assert status_code == 404


@pytest.mark.unit_tests
def test_delete_legacy_shared_rule_archives_once_unlinked_everywhere(
    client: GenaiEngineTestClientBase,
):
    """A rule row from before default rules were removed is linked to several
    tasks. Deleting it from one task only unlinks it there; it is archived once
    no task links to it anymore."""
    _, task_a = client.create_task()
    _, task_b = client.create_task()

    db_session = override_get_db_session()
    rules_repo = RuleRepository(db_session)
    tasks_repo = TaskRepository(
        db_session,
        rules_repo,
        MetricRepository(db_session),
        get_application_config(session=db_session),
    )
    rule = rules_repo.create_rule(
        Rule._from_request_model(
            NewRuleRequest(
                name="legacy default rule",
                type=RuleType.REGEX,
                apply_to_prompt=True,
                apply_to_response=False,
                config=RegexConfig(regex_patterns=["legacy"]),
            ),
            scope=RuleScope.DEFAULT,
        ),
    )
    for task in (task_a, task_b):
        tasks_repo.link_rule_to_task(task.id, rule.id, rule.type)
    db_session.close()

    assert client.delete_task_rule(task_a.id, rule.id) == 204
    _, task_b_after = client.get_task(task_b.id)
    assert rule.id in [r.id for r in task_b_after.rules]
    _, search = client.search_rules(rule_ids=[rule.id])
    assert [r.id for r in search.rules] == [rule.id]

    assert client.delete_task_rule(task_b.id, rule.id) == 204
    _, search = client.search_rules(rule_ids=[rule.id])
    assert search.rules == []
