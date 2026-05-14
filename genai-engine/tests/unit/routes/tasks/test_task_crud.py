import os
import random
from unittest.mock import patch

import pytest
from arthur_common.models.enums import RegisteredAgentProvider, RuleScope, RuleType
from arthur_common.models.request_schemas import AgentMetadata, GCPAgentMetadata
from fastapi import HTTPException

from db_models import DatabaseTask
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)


@pytest.mark.unit_tests
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


@pytest.mark.unit_tests
def test_create_non_agentic_task_explicit(client: GenaiEngineTestClientBase):
    """Test creating a task with is_agentic=False explicitly"""
    task_name = str(random.random())
    status_code, task_response = client.create_task(task_name, is_agentic=False)
    assert status_code == 200

    assert task_response.name == task_name
    assert task_response.is_agentic == False

    # Verify by getting the task
    status_code, task = client.get_task(task_response.id)
    assert status_code == 200
    assert task.is_agentic == False


@pytest.mark.unit_tests
def test_search_tasks_by_agentic_status(client: GenaiEngineTestClientBase):
    """Test filtering tasks by agentic status"""
    # Create some agentic and non-agentic tasks
    agentic_task_ids = []
    non_agentic_task_ids = []

    for i in range(3):
        # Create agentic tasks
        status_code, task = client.create_task(f"agentic_task_{i}", is_agentic=True)
        assert status_code == 200
        agentic_task_ids.append(task.id)

        # Create non-agentic tasks
        status_code, task = client.create_task(
            f"non_agentic_task_{i}",
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
    assert len(agentic_results) == 3
    for task in agentic_results:
        assert task.is_agentic == True

    # Search for non-agentic tasks only
    status_code, search_response = client.search_tasks(is_agentic=False, page_size=50)
    assert status_code == 200

    non_agentic_results = [
        task for task in search_response.tasks if task.id in non_agentic_task_ids
    ]
    assert len(non_agentic_results) == 3
    for task in non_agentic_results:
        assert task.is_agentic == False

    # Search without filter should return both types
    status_code, search_response = client.search_tasks(page_size=50)
    assert status_code == 200

    all_test_tasks = [
        task
        for task in search_response.tasks
        if task.id in agentic_task_ids + non_agentic_task_ids
    ]
    assert len(all_test_tasks) == 6


@pytest.mark.unit_tests
def test_create_task_with_agent_metadata_stores_creation_source(
    client: GenaiEngineTestClientBase,
):
    """Test that creating a task with agent metadata stores GCP creation_source in task_metadata."""
    task_name = str(random.random())
    status_code, task_response = client.create_task(
        task_name,
        is_agentic=True,
        agent_metadata=AgentMetadata(
            provider=RegisteredAgentProvider.GCP,
            gcp_metadata=GCPAgentMetadata(
                project_id="test-project",
                region="test-region",
                resource_id="test-resource",
            ),
        ),
    )
    assert status_code == 200

    # Verify the response has agent_metadata (backward-compatible format)
    assert task_response.agent_metadata.provider == RegisteredAgentProvider.GCP.value
    assert task_response.agent_metadata.gcp_metadata.project_id == "test-project"
    assert task_response.agent_metadata.gcp_metadata.region == "test-region"
    assert task_response.agent_metadata.gcp_metadata.resource_id == "test-resource"

    # Verify task_metadata in DB has new creation_source format
    db_session = override_get_db_session()
    db_task = (
        db_session.query(DatabaseTask)
        .filter(DatabaseTask.id == task_response.id)
        .first()
    )
    assert db_task is not None
    assert db_task.task_metadata is not None
    creation_source = db_task.task_metadata.get("creation_source", {})
    assert creation_source.get("type") == "GCP"
    assert creation_source.get("gcp_project_id") == "test-project"
    assert creation_source.get("gcp_region") == "test-region"
    assert creation_source.get("gcp_reasoning_engine_id") == "test-resource"

    # Clean up
    status_code = client.delete_task(task_response.id)
    assert status_code == 204


@pytest.mark.unit_tests
def test_create_demo_task_returns_400_when_demo_mode_disabled(
    client: GenaiEngineTestClientBase,
):
    """Demo task creation is rejected when demo mode is not enabled."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("GENAI_ENGINE_DEMO_MODE", None)
        status_code, task = client.create_demo_task()

    assert status_code == 400
    assert task is None


@pytest.mark.unit_tests
def test_create_demo_task_succeeds_when_demo_mode_enabled(
    client: GenaiEngineTestClientBase,
):
    """Demo task is created (agentic) when demo mode is enabled and demo item creation succeeds."""
    with (
        patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "enabled"}),
        patch(
            "routers.v2.task_management_routes.DemoTaskRepository.create_demo_items_for_task",
            return_value=None,
        ),
    ):
        status_code, task = client.create_demo_task()

    assert status_code == 200
    assert task is not None
    assert task.name == "Demo Task"
    assert task.is_agentic is True

    status_code, fetched_task = client.get_task(task.id)
    assert status_code == 200
    assert fetched_task.id == task.id

    # Clean up
    status_code = client.delete_task(task.id)
    assert status_code == 204


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "raised_exception,expected_status",
    [
        (ValueError("no model provider"), 400),
        (HTTPException(status_code=422, detail="bad demo data"), 422),
        (RuntimeError("kaboom"), 500),
    ],
    ids=["value_error", "http_exception", "unexpected_exception"],
)
def test_create_demo_task_archives_task_when_demo_items_raise(
    client: GenaiEngineTestClientBase,
    raised_exception: Exception,
    expected_status: int,
):
    """If demo item creation raises, route returns mapped status and archives the partial task."""
    captured_task_ids: list[str] = []

    def raise_on_create_items(self, task_id: str) -> None:
        captured_task_ids.append(task_id)
        raise raised_exception

    with (
        patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "enabled"}),
        patch(
            "routers.v2.task_management_routes.DemoTaskRepository.create_demo_items_for_task",
            new=raise_on_create_items,
        ),
    ):
        status_code, task = client.create_demo_task()

    assert status_code == expected_status
    assert task is None
    assert len(captured_task_ids) == 1

    # The partial task should be archived, so get_task returns 404
    status_code, _ = client.get_task(captured_task_ids[0])
    assert status_code == 404
