import uuid

import pytest

from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.mark.unit_tests
def test_user_story_datasets_crud(client: GenaiEngineTestClientBase) -> None:
    """Test the basic happy path for dataset CRUD operations: create, get, patch, delete."""
    # test dataset creation
    dataset_name = f"My Test Dataset"
    dataset_description = "Test dataset for CRUD operations"
    dataset_metadata = {"test_key": "test_value", "version": 1.0}

    status_code, agentic_task = client.create_task(name="test_user_story_datasets_crud_task", is_agentic=True)
    assert status_code == 200

    status_code, created_dataset = client.create_dataset(
        name=dataset_name,
        task_id=agentic_task.id,
        description=dataset_description,
        metadata=dataset_metadata,
    )
    assert status_code == 200
    assert created_dataset.name == dataset_name
    assert created_dataset.task_id == agentic_task.id
    assert created_dataset.description == dataset_description
    assert created_dataset.metadata == dataset_metadata
    assert created_dataset.id is not None
    assert created_dataset.created_at is not None
    assert created_dataset.updated_at is not None
    assert created_dataset.latest_version_number is None

    # test dataset fetch
    status_code, retrieved_dataset = client.get_dataset(created_dataset.id)
    assert status_code == 200
    assert retrieved_dataset.id == created_dataset.id
    assert retrieved_dataset.task_id == created_dataset.task_id
    assert retrieved_dataset.name == dataset_name
    assert retrieved_dataset.description == dataset_description
    assert retrieved_dataset.metadata == dataset_metadata

    # test dataset update
    updated_name = f"Updated test dataset"
    updated_description = "Updated test dataset description"
    updated_metadata = {"version": 2, "new_field": "new_value"}

    status_code, updated_dataset = client.update_dataset(
        dataset_id=created_dataset.id,
        name=updated_name,
        description=updated_description,
        metadata=updated_metadata,
    )
    assert status_code == 200
    assert updated_dataset.id == created_dataset.id
    assert updated_dataset.name == updated_name
    assert updated_dataset.description == updated_description
    assert updated_dataset.metadata == updated_metadata
    assert updated_dataset.updated_at > updated_dataset.created_at

    # validate updates persisted on fetch
    status_code, final_dataset = client.get_dataset(created_dataset.id)
    assert status_code == 200
    assert final_dataset.name == updated_name
    assert final_dataset.description == updated_description
    assert final_dataset.metadata == updated_metadata

    # test list dataset versions for dataset with no versions
    status_code, versions_response = client.get_dataset_versions(created_dataset.id)
    assert status_code == 200
    assert versions_response.total_count == 0
    assert len(versions_response.versions) == 0

    # delete dataset
    status_code = client.delete_dataset(created_dataset.id)
    assert status_code == 204

    # fail to fetch dataset because it was deleted
    status_code, _ = client.get_dataset(created_dataset.id)
    assert status_code == 404

    # fail to patch dataset that doesn't exist
    status_code, _ = client.update_dataset(
        dataset_id=created_dataset.id,
        name=updated_name,
        description=updated_description,
        metadata=updated_metadata,
    )
    assert status_code == 404

    # fail to delete dataset that doesn't exist
    status_code = client.delete_dataset(created_dataset.id)
    assert status_code == 404

    status_code = client.delete_task(agentic_task.id)
    assert status_code == 204


def test_create_dataset_with_task_errors(client: GenaiEngineTestClientBase) -> None:
    """Test dataset creation with task errors."""
    # test dataset creation with task errors
    dataset_name = f"My Test Dataset"
    dataset_description = "Test dataset for CRUD operations"
    dataset_metadata = {"test_key": "test_value", "version": 1.0}

    # create a dataset with a non-existent task
    status_code, _ = client.create_dataset(
        name=dataset_name,
        task_id=str(uuid.uuid4()),
        description=dataset_description,
        metadata=dataset_metadata,
    )
    assert status_code == 404

    # create a non-agentic task
    task_name = "non-agentic-dataset-task"
    status_code, non_agentic_task = client.create_task(task_name, is_agentic=False)
    assert status_code == 200

    # create a dataset with a non-agentic task
    status_code, _ = client.create_dataset(
        name=dataset_name,
        task_id=non_agentic_task.id,
        description=dataset_description,
        metadata=dataset_metadata,
    )
    assert status_code == 400

    status_code = client.delete_task(non_agentic_task.id)
    assert status_code == 204


def test_search_datasets_with_task_errors(client: GenaiEngineTestClientBase) -> None:
    """Test dataset creation with task errors."""
    # search datasets with a non-existent task
    status_code, _ = client.search_datasets(task_id=str(uuid.uuid4()))
    assert status_code == 404

    # search datasets with a non-agentic task
    task_name = "non-agentic-dataset-task"
    status_code, non_agentic_task = client.create_task(task_name, is_agentic=False)
    assert status_code == 200

    # search datasets with a non-agentic task
    status_code, _ = client.search_datasets(task_id=non_agentic_task.id)
    assert status_code == 400

    status_code = client.delete_task(non_agentic_task.id)
    assert status_code == 204
