import pytest
from arthur_common.models.enums import RuleType
from arthur_common.models.response_schemas import TaskResponse

from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.mark.integration_tests
@pytest.mark.parametrize("create_task", [False], indirect=True)
def test_archive_task(client: GenaiEngineTestClientBase, create_task: TaskResponse):
    task = create_task
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


@pytest.mark.integration_tests
@pytest.mark.parametrize("create_task", [True], indirect=True)
def test_archive_task_rule(
    client: GenaiEngineTestClientBase,
    create_task: TaskResponse,
):
    task = create_task

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
