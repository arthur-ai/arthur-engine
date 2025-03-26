import logging
import time
from unittest.mock import patch

import pytest
from cachetools import TTLCache
from repositories.tasks_rules_repository import TasksRulesRepository
from schemas.internal_schemas import Rule, Task
from tests.clients.base_test_client import override_get_db_session

LOGGER = logging.getLogger(__name__)


@pytest.mark.unit_tests
def test_get_task_rules_ids(
    create_task: Task,
    create_rule_for_task_sensitive_data: Rule,
    create_rule_for_task_regex: Rule,
    create_rule_for_task_keywords: Rule,
    create_rule_for_task_prompt_injection: Rule,
    create_rule_for_task_hallucination_v2: Rule,
    create_rule_for_task_pii: Rule,
    create_rule_for_task_toxicity: Rule,
):
    db_session = override_get_db_session()
    task_rules_repo = TasksRulesRepository(db_session)
    task_id = create_task.id
    rules = task_rules_repo.get_task_rules_ids_cached(task_id)
    assert len(rules) == 7


@pytest.mark.unit_tests
@patch("config.cache_config.cache_config.TASK_RULES_CACHE_ENABLED", True)
def test_get_task_rules_ids_cache(
    caplog: pytest.LogCaptureFixture,
    create_task: Task,
    create_rule_for_task_sensitive_data: Rule,
    create_rule_for_task_regex: Rule,
    create_rule_for_task_keywords: Rule,
    create_rule_for_task_prompt_injection: Rule,
    create_rule_for_task_hallucination_v2: Rule,
    create_rule_for_task_pii: Rule,
    create_rule_for_task_toxicity: Rule,
):
    db_session = override_get_db_session()
    task_rules_repo = TasksRulesRepository(db_session)
    task_id = create_task.id

    # Measure DB query time
    with caplog.at_level(logging.DEBUG):
        start_time = time.perf_counter()
        task_rules_repo.get_task_rules_ids_cached(task_id)
        db_query_time = time.perf_counter() - start_time
    assert f"Querying DB for rules for task {task_id}" in caplog.text

    # Measure cache retrieval time
    with caplog.at_level(logging.DEBUG):
        start_time = time.perf_counter()
        task_rules_repo.get_task_rules_ids_cached(task_id)
        cache_time = time.perf_counter() - start_time
    assert f"Returning cached rules for task {task_id}" in caplog.text
    assert cache_time < db_query_time


@patch("config.cache_config.cache_config.TASK_RULES_CACHE_ENABLED", True)
@patch(
    "repositories.tasks_rules_repository.CACHED_TASK_RULES",
    TTLCache(maxsize=1000, ttl=3),
)
@pytest.mark.unit_tests
def test_get_task_rules_ids_cache_ttl(
    caplog: pytest.LogCaptureFixture,
    create_task: Task,
):
    db_session = override_get_db_session()
    task_rules_repo = TasksRulesRepository(db_session)
    task_id = create_task.id
    with caplog.at_level(logging.DEBUG):
        task_rules_repo.get_task_rules_ids_cached(task_id)
        assert f"Querying DB for rules for task {task_id}" in caplog.text
        time.sleep(4)
        task_rules_repo.get_task_rules_ids_cached(task_id)
        assert f"Returning cached rules for task {task_id}" not in caplog.text
        task_rules_repo.get_task_rules_ids_cached(task_id)
        assert f"Returning cached rules for task {task_id}" in caplog.text


@patch("config.cache_config.cache_config.TASK_RULES_CACHE_ENABLED", True)
@pytest.mark.unit_tests
def test_clear_cache(
    caplog: pytest.LogCaptureFixture,
    create_task: Task,
):
    db_session = override_get_db_session()
    task_rules_repo = TasksRulesRepository(db_session)
    task_id = create_task.id
    with caplog.at_level(logging.DEBUG):
        task_rules_repo.get_task_rules_ids_cached(task_id)
        assert f"Querying DB for rules for task {task_id}" in caplog.text
        task_rules_repo.clear_cache()
        task_rules_repo.get_task_rules_ids_cached(task_id)
        assert f"Returning cached rules for task {task_id}" not in caplog.text
