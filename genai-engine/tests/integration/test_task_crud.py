import random

import pytest
from schemas.enums import RuleScope, RuleType
from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.mark.integration_tests
def test_user_story_create_task_get_task(client: GenaiEngineTestClientBase):
    task_name = str(random.random())
    client.create_rule("", rule_type=RuleType.REGEX)
    status_code, task_response = client.create_task(task_name)
    assert status_code == 200

    assert task_response.name == task_name

    status_code, task = client.get_task(task_response.id)

    assert len(task.rules) > 0


@pytest.mark.integration_tests
def test_user_story_create_task_rule_update_rule(client: GenaiEngineTestClientBase):
    task_name = str(random.random())
    status_code, task_response = client.create_task(task_name, empty_rules=True)
    assert status_code == 200

    assert task_response.name == task_name

    custom_keyword = str(random.random())
    rule_name = str(random.random())
    status_code, task_scoped_keyword_rule = client.create_rule(
        rule_name,
        rule_type=RuleType.KEYWORD,
        keywords=[custom_keyword],
        task_id=task_response.id,
    )

    assert status_code == 200
    assert task_scoped_keyword_rule.scope == RuleScope.TASK

    status_code, _ = client.patch_rule(
        task_response.id,
        task_scoped_keyword_rule.id,
        False,
    )
    assert status_code == 200

    status_code, task = client.get_task(task_response.id)
    get_task_rules = task.rules
    assert len(get_task_rules) > 0
    # Assert patched rule is disabled
    patched_rule = [r for r in get_task_rules if r.id == task_scoped_keyword_rule.id][0]
    assert patched_rule.enabled == False
