import pytest
from arthur_common.models.enums import RuleScope, RuleType
from tests.clients.base_test_client import GenaiEngineTestClientBase


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
    _, old_default_rules = client.search_rules(rule_scopes=[RuleScope.DEFAULT])
    old_default_rules = old_default_rules.rules

    _, prompt = client.create_prompt(task_id=task.id, conversation_id=task.id)
    _, _ = client.create_response(inference_id=prompt.inference_id, task_id=task.id)

    status_code = client.delete_task(task.id)
    assert status_code == 204

    # Task should return 404
    status_code, _ = client.get_task(task.id)
    assert status_code == 404

    # Default rules should be unaffected
    _, new_default_rules = client.search_rules(rule_scopes=[RuleScope.DEFAULT])
    new_default_rules = new_default_rules.rules

    assert set([rule.id for rule in old_default_rules]) == set(
        [rule.id for rule in new_default_rules],
    )

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

    _, default_rule = client.create_rule("", rule_type=RuleType.KEYWORD)

    _, task = client.get_task(task.id)
    _, old_default_rules = client.search_rules(rule_scopes=[RuleScope.DEFAULT])
    old_default_rules = old_default_rules.rules

    _, prompt = client.create_prompt(task_id=task.id, conversation_id=task.id)
    _, _ = client.create_response(inference_id=prompt.inference_id, task_id=task.id)

    status_code = client.delete_task_rule(task.id, regex_rule.id)
    assert status_code == 204

    status_code = client.delete_task_rule(task.id, default_rule.id)
    assert status_code == 400

    status_code, _ = client.patch_rule(task.id, default_rule.id, enabled=False)
    assert status_code == 200

    # Task should return 200
    status_code, task = client.get_task(task.id)
    assert status_code == 200

    # Default rules should be unaffected
    _, new_default_rules = client.search_rules(rule_scopes=[RuleScope.DEFAULT])
    new_default_rules = new_default_rules.rules
    assert set([rule.id for rule in old_default_rules]) == set(
        [rule.id for rule in new_default_rules],
    )

    # Unarchived task rule should be unaffected
    assert keyword_rule.id in [rule.id for rule in task.rules]
    # Archived task rule should not be present
    assert regex_rule.id not in [rule.id for rule in task.rules]
    # Archived defualt rule should be present but disabled
    assert default_rule.id not in [rule.id for rule in task.rules if rule.enabled]
    assert default_rule.id in [rule.id for rule in task.rules if not rule.enabled]

    # Inferences should be unaffected
    _, query_resp = client.query_inferences(conversation_id=task.id)
    assert query_resp.count > 0
    assert all([i.task_id == task.id for i in query_resp.inferences])


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
