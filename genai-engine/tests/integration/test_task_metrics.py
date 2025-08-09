import random

import pytest

from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.mark.integration_tests
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


@pytest.mark.integration_tests
def test_create_metric_on_non_agentic_task_fails(client: GenaiEngineTestClientBase):
    """Test that metrics cannot be created on non-agentic tasks."""
    task_name = str(random.random())
    status_code, task_response = client.create_task(task_name, is_agentic=False)
    assert status_code == 200
    assert task_response.is_agentic == False

    # Try to create a metric on the non-agentic task - should fail
    status_code, metric_response = client.create_task_metric(
        task_id=task_response.id,
        metric_type="QueryRelevance",
        metric_name="Test Query Relevance",
        metric_metadata="Test metric for non-agentic task",
    )
    assert status_code == 400
    assert metric_response is None


@pytest.mark.integration_tests
def test_create_metric_on_default_task_fails(client: GenaiEngineTestClientBase):
    """Test that metrics cannot be created on tasks with default is_agentic=False."""
    task_name = str(random.random())
    # Create task without specifying is_agentic (defaults to False)
    status_code, task_response = client.create_task(task_name)
    assert status_code == 200
    assert task_response.is_agentic == False

    # Try to create a metric on the task - should fail
    status_code, metric_response = client.create_task_metric(
        task_id=task_response.id,
        metric_type="QueryRelevance",
        metric_name="Test Query Relevance",
        metric_metadata="Test metric for default task",
    )
    assert status_code == 400
    assert metric_response is None
