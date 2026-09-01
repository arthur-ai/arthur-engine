import random

import pytest

from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.mark.unit_tests
def test_create_metric_on_agentic_task_success(client: GenaiEngineTestClientBase):
    """Test that metrics can be created on agentic tasks."""
    task_name = str(random.random())
    status_code, task_response = client.create_task(task_name, is_agentic=True)
    assert status_code == 200
    assert task_response.is_agentic == True

    # Create a metric on the agentic task - should succeed
    status_code, metric_response = client.create_task_metric(
        task_id=task_response.id,
        metric_type="QueryRelevance",
        metric_name="Test Query Relevance",
        metric_metadata="Test metric for agentic task",
    )
    assert status_code == 201
    assert metric_response is not None
    assert metric_response["type"] == "QueryRelevance"
    assert metric_response["name"] == "Test Query Relevance"


@pytest.mark.unit_tests
def test_create_metric_on_legacy_flagged_task_succeeds(
    client: GenaiEngineTestClientBase,
):
    """The agentic-only metric gate is removed: metrics can be
    created on any task, even when the caller sends the legacy
    is_agentic=False flag."""
    task_name = str(random.random())
    status_code, task_response = client.create_task(task_name, is_agentic=False)
    assert status_code == 200
    assert task_response.is_agentic == True

    status_code, metric_response = client.create_task_metric(
        task_id=task_response.id,
        metric_type="QueryRelevance",
        metric_name="Test Query Relevance",
        metric_metadata="Test metric for legacy-flagged task",
    )
    assert status_code == 201
    assert metric_response is not None


@pytest.mark.unit_tests
def test_create_metric_on_default_task_succeeds(client: GenaiEngineTestClientBase):
    """Every task is agentic post-consolidation, so metric creation
    succeeds on a task created without any legacy flag."""
    task_name = str(random.random())
    status_code, task_response = client.create_task(task_name)
    assert status_code == 200
    assert task_response.is_agentic == True

    status_code, metric_response = client.create_task_metric(
        task_id=task_response.id,
        metric_type="QueryRelevance",
        metric_name="Test Query Relevance",
        metric_metadata="Test metric for default task",
    )
    assert status_code == 201
    assert metric_response is not None


@pytest.mark.unit_tests
def test_enable_metric_on_legacy_flagged_task_succeeds(
    client: GenaiEngineTestClientBase,
):
    """The agentic-only gate on enabling metrics is removed: a task
    created with the legacy is_agentic=False flag can have its metric
    toggled like any other task."""
    status_code, task = client.create_task(
        str(random.random()),
        is_agentic=False,
    )
    assert status_code == 200

    status_code, metric_response = client.create_task_metric(
        task_id=task.id,
        metric_type="QueryRelevance",
        metric_name="Test Query Relevance",
        metric_metadata="Test metric",
    )
    assert status_code == 201
    metric_id = metric_response["id"]

    status_code, response = client.update_task_metric(
        task_id=task.id,
        metric_id=metric_id,
        enabled=True,
    )
    assert status_code == 200
