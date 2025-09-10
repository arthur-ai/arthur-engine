import random

import pytest

from arthur_common.models.enums import RuleScope, RuleType
from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.mark.integration_tests
def test_user_story_create_task_get_task(client: GenaiEngineTestClientBase):
    task_name = str(random.random())
    client.create_rule("", rule_type=RuleType.REGEX)
    status_code, task_response = client.create_task(task_name)
    assert status_code == 200

    assert task_response.name == task_name
    assert task_response.is_agentic == False  # Default should be False

    status_code, task = client.get_task(task_response.id)

    assert len(task.rules) > 0
    assert task.is_agentic == False


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


@pytest.mark.integration_tests
def test_create_agentic_task(client: GenaiEngineTestClientBase):
    """Test creating a task with is_agentic=True"""
    task_name = str(random.random())
    status_code, task_response = client.create_task(task_name, is_agentic=True)
    assert status_code == 200

    assert task_response.name == task_name
    assert task_response.is_agentic == True

    # Verify by getting the task
    status_code, task = client.get_task(task_response.id)
    assert status_code == 200
    assert task.is_agentic == True


@pytest.mark.integration_tests
def test_search_tasks_by_agentic_status(client: GenaiEngineTestClientBase):
    """Test filtering tasks by agentic status"""
    # Create some agentic and non-agentic tasks
    agentic_task_ids = []
    non_agentic_task_ids = []

    for i in range(2):  # Fewer tasks for integration tests to be faster
        # Create agentic tasks
        status_code, task = client.create_task(
            f"integration_agentic_{i}",
            is_agentic=True,
        )
        assert status_code == 200
        agentic_task_ids.append(task.id)

        # Create non-agentic tasks
        status_code, task = client.create_task(
            f"integration_non_agentic_{i}",
            is_agentic=False,
        )
        assert status_code == 200
        non_agentic_task_ids.append(task.id)

    # Search for agentic tasks only
    status_code, search_response = client.search_tasks(is_agentic=True, page_size=50)
    assert status_code == 200

    agentic_results = [
        task for task in search_response.tasks if task.id in agentic_task_ids
    ]
    assert len(agentic_results) == 2
    for task in agentic_results:
        assert task.is_agentic == True

    # Search for non-agentic tasks only
    status_code, search_response = client.search_tasks(is_agentic=False, page_size=50)
    assert status_code == 200

    non_agentic_results = [
        task for task in search_response.tasks if task.id in non_agentic_task_ids
    ]
    assert len(non_agentic_results) == 2
    for task in non_agentic_results:
        assert task.is_agentic == False
