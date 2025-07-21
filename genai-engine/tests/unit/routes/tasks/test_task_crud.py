import random

import pytest

from schemas.enums import RuleScope, RuleType, TaskType
from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.mark.unit_tests
def test_user_story_create_task_get_task(client: GenaiEngineTestClientBase):
    task_name = str(random.random())
    client.create_rule("", rule_type=RuleType.REGEX)
    status_code, task_response = client.create_task(task_name)
    assert status_code == 200

    assert task_response.name == task_name
    assert task_response.task_type == TaskType.LLM  # Default should be LLM

    status_code, task = client.get_task(task_response.id)

    assert len(task.rules) > 0
    assert task.task_type == TaskType.LLM


@pytest.mark.unit_tests
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


@pytest.mark.unit_tests
def test_create_agent_task(client: GenaiEngineTestClientBase):
    """Test creating a task with task_type=Agent"""
    task_name = str(random.random())
    status_code, task_response = client.create_task(task_name, task_type=TaskType.AGENT)
    assert status_code == 200

    assert task_response.name == task_name
    assert task_response.task_type == TaskType.AGENT

    # Verify by getting the task
    status_code, task = client.get_task(task_response.id)
    assert status_code == 200
    assert task.task_type == TaskType.AGENT


@pytest.mark.unit_tests
def test_create_llm_task_explicit(client: GenaiEngineTestClientBase):
    """Test creating a task with task_type=LLM explicitly"""
    task_name = str(random.random())
    status_code, task_response = client.create_task(task_name, task_type=TaskType.LLM)
    assert status_code == 200

    assert task_response.name == task_name
    assert task_response.task_type == TaskType.LLM

    # Verify by getting the task
    status_code, task = client.get_task(task_response.id)
    assert status_code == 200
    assert task.task_type == TaskType.LLM


@pytest.mark.unit_tests
def test_search_tasks_by_task_type(client: GenaiEngineTestClientBase):
    """Test filtering tasks by task type"""
    # Create some Agent and LLM tasks
    agent_task_ids = []
    llm_task_ids = []

    for i in range(3):
        # Create Agent tasks
        status_code, task = client.create_task(
            f"agent_task_{i}",
            task_type=TaskType.AGENT,
        )
        assert status_code == 200
        agent_task_ids.append(task.id)

        # Create LLM tasks
        status_code, task = client.create_task(f"llm_task_{i}", task_type=TaskType.LLM)
        assert status_code == 200
        llm_task_ids.append(task.id)

    # Search for Agent tasks only
    status_code, search_response = client.search_tasks(
        task_type=TaskType.AGENT,
        page_size=50,
    )
    assert status_code == 200

    agent_results = [
        task for task in search_response.tasks if task.id in agent_task_ids
    ]
    assert len(agent_results) == 3
    for task in agent_results:
        assert task.task_type == TaskType.AGENT

    # Search for LLM tasks only
    status_code, search_response = client.search_tasks(
        task_type=TaskType.LLM,
        page_size=50,
    )
    assert status_code == 200

    llm_results = [task for task in search_response.tasks if task.id in llm_task_ids]
    assert len(llm_results) == 3
    for task in llm_results:
        assert task.task_type == TaskType.LLM

    # Search without filter should return both types
    status_code, search_response = client.search_tasks(page_size=50)
    assert status_code == 200

    all_test_tasks = [
        task
        for task in search_response.tasks
        if task.id in agent_task_ids + llm_task_ids
    ]
    assert len(all_test_tasks) == 6
