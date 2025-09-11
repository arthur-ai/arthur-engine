import random

import pytest
from arthur_common.models.enums import RuleType
from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.mark.unit_tests
def test_archive_default_rule_applies_to_all_tasks(client: GenaiEngineTestClientBase):
    i = 0
    num_tasks = 44
    while i <= num_tasks:
        task_name = f"test_task{i}"
        status_code, task_response = client.create_task(task_name)
        assert status_code == 200
        assert len(task_response.id) != 0
        assert task_response.name == task_name
        assert task_response.created_at
        assert task_response.updated_at
        assert task_response.created_at != 0
        assert task_response.updated_at != 0
        i += 1

    status_code, all_tasks = client.search_tasks(page_size=num_tasks)
    all_tasks = all_tasks.tasks

    assert status_code == 200

    assert task_response.id in [task.id for task in all_tasks]

    # Create a default rule - this should be applied to ALL tasks
    unique_keyword = "{}{}".format("keyword", random.random())
    status_code, resp = client.create_rule(
        unique_keyword,
        RuleType.KEYWORD,
        keywords=[unique_keyword],
    )

    assert status_code == 200
    default_rule_id = resp.id

    status_code, post_rule_creation_tasks = client.search_tasks(page_size=num_tasks)
    post_rule_creation_tasks = post_rule_creation_tasks.tasks

    assert status_code == 200
    for post_rule_creation_task in post_rule_creation_tasks:
        for task in all_tasks:
            if task.id == post_rule_creation_task.id:
                assert len(post_rule_creation_task.rules) == len(task.rules) + 1

    # Delete the default rule across all tasks

    resp = client.delete_default_rule(default_rule_id)
    assert resp == 200
    status_code, post_rule_deletion_tasks = client.search_tasks(page_size=num_tasks)
    post_rule_deletion_tasks = post_rule_deletion_tasks.tasks
    assert status_code == 200
    assert len(post_rule_deletion_tasks) == num_tasks

    for post_rule_deletion_task in post_rule_deletion_tasks:
        for task in all_tasks:
            if task.id == post_rule_deletion_task.id:
                if (
                    len(post_rule_deletion_task.rules) > 0
                ):  # Make sure number of rules is the same as before creation
                    assert len(post_rule_deletion_task.rules) == len(task.rules)
