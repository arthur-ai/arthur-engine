import uuid

import pytest

from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.fixture
def transform_definition() -> dict:
    return {
        "variables": [
            {
                "variable_name": "test_variable",
                "span_name": "test-span",
                "attribute_path": "attributes.test",
                "fallback": None,
            },
        ],
    }


@pytest.mark.unit_tests
def test_add_transform_to_dataset_success(
    client: GenaiEngineTestClientBase,
    transform_definition: dict,
) -> None:
    """Test adding a transform to a dataset successfully."""
    status_code, agentic_task = client.create_task(
        name="test_dataset_transforms_crud_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Create a dataset
        status_code, dataset = client.create_dataset(
            name="test_transforms_crud_dataset",
            task_id=agentic_task.id,
        )
        assert status_code == 200

        # Create a transform
        status_code, transform = client.create_transform(
            task_id=agentic_task.id,
            name="test_transforms_crud_transform",
            definition=transform_definition,
        )
        assert status_code == 200

        # Verify no transforms are associated with the dataset
        status_code, transforms = client.list_dataset_transforms(dataset_id=dataset.id)
        assert status_code == 200
        assert len(transforms.transforms) == 0

        # Add the transform to the dataset
        status_code, dataset_transform = client.add_transform_to_dataset(
            dataset_id=dataset.id,
            transform_id=transform.id,
        )
        assert status_code == 200
        assert dataset_transform.id is not None
        assert dataset_transform.dataset_id == dataset.id
        assert dataset_transform.transform_id == transform.id
        assert dataset_transform.created_at is not None

        # Verify the transform is associated with the dataset
        status_code, transforms = client.list_dataset_transforms(dataset_id=dataset.id)
        assert status_code == 200
        assert len(transforms.transforms) == 1
        assert transforms.transforms[0].id == dataset_transform.id
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_add_transform_to_dataset_failures(
    client: GenaiEngineTestClientBase,
    transform_definition: dict,
) -> None:
    """Test adding a transform to a dataset failures."""
    fake_dataset_id = str(uuid.uuid4())
    fake_transform_id = str(uuid.uuid4())

    status_code, agentic_task = client.create_task(
        name="test_dataset_transforms_crud_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Create a dataset
        status_code, dataset = client.create_dataset(
            name="test_transforms_crud_dataset",
            task_id=agentic_task.id,
        )
        assert status_code == 200

        # Create a transform
        status_code, transform = client.create_transform(
            task_id=agentic_task.id,
            name="test_transforms_crud_transform",
            definition=transform_definition,
        )
        assert status_code == 200

        # Verify no transforms are associated with the dataset
        status_code, transforms = client.list_dataset_transforms(dataset_id=dataset.id)
        assert status_code == 200
        assert len(transforms.transforms) == 0

        # Adding a transform to a nonexistent dataset returns a 404 error
        status_code, error = client.add_transform_to_dataset(
            dataset_id=fake_dataset_id,
            transform_id=transform.id,
        )
        assert status_code == 404
        assert error is not None
        assert f"dataset {fake_dataset_id} not found" in error.get("detail", "").lower()

        # Adding a non-existent transform to an existing dataset returns a 404 error
        status_code, error = client.add_transform_to_dataset(
            dataset_id=dataset.id,
            transform_id=fake_transform_id,
        )
        assert status_code == 404
        assert error is not None
        assert (
            f"transform {fake_transform_id} not found for task {agentic_task.id}"
            in error.get("detail", "").lower()
        )

        # successfully add a transform to a dataset
        status_code, error = client.add_transform_to_dataset(
            dataset_id=dataset.id,
            transform_id=transform.id,
        )
        assert status_code == 200

        # successfully adding a transform to a dataset that already has it returns a 400 error
        status_code, error = client.add_transform_to_dataset(
            dataset_id=dataset.id,
            transform_id=transform.id,
        )
        assert status_code == 400
        assert error is not None
        assert (
            f"transform {transform.id} is already associated with dataset {dataset.id}."
            in error.get("detail", "").lower()
        )
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_list_transforms_for_dataset_success(
    client: GenaiEngineTestClientBase,
    transform_definition: dict,
) -> None:
    """Test listing transforms for a dataset successfully."""
    status_code, agentic_task = client.create_task(
        name="test_dataset_transforms_crud_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Create a dataset
        status_code, dataset = client.create_dataset(
            name="test_transforms_crud_dataset",
            task_id=agentic_task.id,
        )
        assert status_code == 200

        # Create transforms
        transforms = []
        for i in range(10):
            status_code, transform = client.create_transform(
                task_id=agentic_task.id,
                name=f"test_transforms_crud_transform_{i}",
                definition=transform_definition,
            )
            assert status_code == 200
            transforms.append(transform)

        # Verify no transforms are associated with the dataset
        status_code, transforms_list = client.list_dataset_transforms(
            dataset_id=dataset.id,
        )
        assert status_code == 200
        assert len(transforms_list.transforms) == 0

        # Add the transforms to the dataset
        for transform in transforms:
            status_code, dataset_transform = client.add_transform_to_dataset(
                dataset_id=dataset.id,
                transform_id=transform.id,
            )
            assert status_code == 200
            assert dataset_transform.id is not None
            assert dataset_transform.dataset_id == dataset.id
            assert dataset_transform.transform_id == transform.id
            assert dataset_transform.created_at is not None

        # Verify the transform is associated with the dataset
        status_code, transforms_list = client.list_dataset_transforms(
            dataset_id=dataset.id,
        )
        assert status_code == 200
        assert len(transforms_list.transforms) == len(transforms)
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_get_dataset_transform_by_id_success(
    client: GenaiEngineTestClientBase,
    transform_definition: dict,
) -> None:
    """Test getting a dataset transform by id successfully."""
    status_code, agentic_task = client.create_task(
        name="test_dataset_transforms_crud_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Create a dataset
        status_code, dataset = client.create_dataset(
            name="test_transforms_crud_dataset",
            task_id=agentic_task.id,
        )
        assert status_code == 200

        # Create a transform
        status_code, transform = client.create_transform(
            task_id=agentic_task.id,
            name="test_transforms_crud_transform",
            definition=transform_definition,
        )
        assert status_code == 200

        # Add the transform to the dataset
        status_code, _ = client.add_transform_to_dataset(
            dataset_id=dataset.id,
            transform_id=transform.id,
        )
        assert status_code == 200

        # Verify you can now get the transform by id
        status_code, dataset_transform = client.get_dataset_transform_by_id(
            dataset_id=dataset.id,
            transform_id=transform.id,
        )
        assert status_code == 200
        assert dataset_transform.id is not None
        assert dataset_transform.dataset_id == dataset.id
        assert dataset_transform.transform_id == transform.id
        assert dataset_transform.created_at is not None
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_get_dataset_transform_by_id_failures(
    client: GenaiEngineTestClientBase,
    transform_definition: dict,
) -> None:
    """Test getting a dataset transform by id failures."""
    status_code, agentic_task = client.create_task(
        name="test_dataset_transforms_crud_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Create a dataset
        status_code, dataset = client.create_dataset(
            name="test_transforms_crud_dataset",
            task_id=agentic_task.id,
        )
        assert status_code == 200

        # Create a transform
        status_code, transform = client.create_transform(
            task_id=agentic_task.id,
            name="test_transforms_crud_transform",
            definition=transform_definition,
        )
        assert status_code == 200

        # Test getting a transform by id for one not associated with the dataset returns a 404 error
        status_code, error = client.get_dataset_transform_by_id(
            dataset_id=dataset.id,
            transform_id=transform.id,
        )
        assert status_code == 404
        assert error is not None
        assert (
            f"transform {transform.id} not found for dataset {dataset.id}"
            in error.get("detail", "").lower()
        )

        # Test getting a transform for a non-existent dataset returns a 404 error
        fake_dataset_id = str(uuid.uuid4())
        status_code, error = client.get_dataset_transform_by_id(
            dataset_id=fake_dataset_id,
            transform_id=transform.id,
        )
        assert status_code == 404
        assert error is not None
        assert (
            f"transform {transform.id} not found for dataset {fake_dataset_id}"
            in error.get("detail", "").lower()
        )

        # Test getting a dataset transform for a non-existent transform returns a 404 error
        fake_transform_id = str(uuid.uuid4())
        status_code, error = client.get_dataset_transform_by_id(
            dataset_id=dataset.id,
            transform_id=fake_transform_id,
        )
        assert status_code == 404
        assert error is not None
        assert (
            f"transform {fake_transform_id} not found for dataset {dataset.id}"
            in error.get("detail", "").lower()
        )

    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_remove_transform_from_dataset_success(
    client: GenaiEngineTestClientBase,
    transform_definition: dict,
) -> None:
    """Test removing a transform from a dataset successfully."""
    status_code, agentic_task = client.create_task(
        name="test_dataset_transforms_crud_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Create a dataset
        status_code, dataset = client.create_dataset(
            name="test_transforms_crud_dataset",
            task_id=agentic_task.id,
        )
        assert status_code == 200

        # Create a transform
        status_code, transform = client.create_transform(
            task_id=agentic_task.id,
            name="test_transforms_crud_transform",
            definition=transform_definition,
        )
        assert status_code == 200

        # Add the transform to the dataset
        status_code, _ = client.add_transform_to_dataset(
            dataset_id=dataset.id,
            transform_id=transform.id,
        )
        assert status_code == 200

        # Verify the transform is associated with the dataset
        status_code, retrieved_transform = client.get_dataset_transform_by_id(
            dataset_id=dataset.id,
            transform_id=transform.id,
        )
        assert status_code == 200
        assert retrieved_transform.id is not None
        assert retrieved_transform.dataset_id == dataset.id
        assert retrieved_transform.transform_id == transform.id
        assert retrieved_transform.created_at is not None

        # Remove the transform from the dataset
        status_code, _ = client.remove_transform_from_dataset(
            dataset_id=dataset.id,
            transform_id=transform.id,
        )
        assert status_code == 204

        # Verify the transform is no longer associated with the dataset
        status_code, error = client.get_dataset_transform_by_id(
            dataset_id=dataset.id,
            transform_id=transform.id,
        )
        assert status_code == 404
        assert error is not None
        assert (
            f"transform {transform.id} not found for dataset {dataset.id}"
            in error.get("detail", "").lower()
        )

        # Verify the transform still exists globally
        status_code, retrieved_transform = client.get_transform(
            task_id=agentic_task.id,
            transform_id=transform.id,
        )
        assert status_code == 200
        assert retrieved_transform.id == transform.id
        assert retrieved_transform.task_id == agentic_task.id

        # Verify the dataset still exists
        status_code, retrieved_dataset = client.get_dataset(dataset_id=dataset.id)
        assert status_code == 200
        assert retrieved_dataset.id == dataset.id
        assert retrieved_dataset.task_id == agentic_task.id

    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_get_dataset_transform_by_id_failures(
    client: GenaiEngineTestClientBase,
    transform_definition: dict,
) -> None:
    """Test getting a dataset transform by id failures."""
    status_code, agentic_task = client.create_task(
        name="test_dataset_transforms_crud_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Create a dataset
        status_code, dataset = client.create_dataset(
            name="test_transforms_crud_dataset",
            task_id=agentic_task.id,
        )
        assert status_code == 200

        # Create a transform
        status_code, transform = client.create_transform(
            task_id=agentic_task.id,
            name="test_transforms_crud_transform",
            definition=transform_definition,
        )
        assert status_code == 200

        # Test removing a transform by id for one not associated with the dataset returns a 404 error
        status_code, error = client.remove_transform_from_dataset(
            dataset_id=dataset.id,
            transform_id=transform.id,
        )
        assert status_code == 404
        assert error is not None
        assert (
            f"transform {transform.id} not found for dataset {dataset.id}"
            in error.get("detail", "").lower()
        )

        # Test removing a transform for a non-existent dataset returns a 404 error
        fake_dataset_id = str(uuid.uuid4())
        status_code, error = client.remove_transform_from_dataset(
            dataset_id=fake_dataset_id,
            transform_id=transform.id,
        )
        assert status_code == 404
        assert error is not None
        assert (
            f"transform {transform.id} not found for dataset {fake_dataset_id}"
            in error.get("detail", "").lower()
        )

        # Test removing a dataset transform for a non-existent transform returns a 404 error
        fake_transform_id = str(uuid.uuid4())
        status_code, error = client.remove_transform_from_dataset(
            dataset_id=dataset.id,
            transform_id=fake_transform_id,
        )
        assert status_code == 404
        assert error is not None
        assert (
            f"transform {fake_transform_id} not found for dataset {dataset.id}"
            in error.get("detail", "").lower()
        )

    finally:
        client.delete_task(agentic_task.id)
