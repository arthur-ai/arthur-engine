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
def test_create_transform_success(
    client: GenaiEngineTestClientBase,
    transform_definition: dict,
) -> None:
    """Test creating a transform successfully."""
    # Create a task
    status_code, task = client.create_task(
        name="test_transform_routes_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Create a transform
        status_code, transform = client.create_transform(
            task_id=task.id,
            name="test_transform",
            definition=transform_definition,
            description="test transform description",
        )
        assert status_code == 200
        assert transform.id is not None
        assert transform.task_id == task.id
        assert transform.name == "test_transform"
        assert transform.description == "test transform description"
        assert transform.definition.model_dump() == transform_definition
        assert transform.created_at is not None
        assert transform.updated_at is not None
    finally:
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_create_transform_nonexistent_task(
    client: GenaiEngineTestClientBase,
    transform_definition: dict,
) -> None:
    """Test creating a transform for a nonexistent task returns a 404 error."""
    task_id = str(uuid.uuid4())

    # Create a transform
    status_code, error = client.create_transform(
        task_id=task_id,
        name="test_transform",
        definition=transform_definition,
        description="test transform description",
    )
    assert status_code == 404
    assert error is not None
    assert f"task {task_id} not found" in error.get("detail", "").lower()


@pytest.mark.unit_tests
def test_get_transform_by_id_success(
    client: GenaiEngineTestClientBase,
    transform_definition: dict,
) -> None:
    """Test getting a transform by id successfully."""
    # Create a task
    status_code, task = client.create_task(
        name="test_transform_routes_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Create a transform
        status_code, transform = client.create_transform(
            task_id=task.id,
            name="test_transform",
            definition=transform_definition,
            description="test transform description",
        )
        assert status_code == 200
        assert transform.id is not None
        assert transform.task_id == task.id
        assert transform.name == "test_transform"
        assert transform.description == "test transform description"
        assert transform.definition.model_dump() == transform_definition
        assert transform.created_at is not None
        assert transform.updated_at is not None

        # Get the transform by id
        status_code, retrieved_transform = client.get_transform(
            task_id=task.id,
            transform_id=transform.id,
        )
        assert status_code == 200
        assert retrieved_transform.id == transform.id
        assert retrieved_transform.task_id == task.id
        assert retrieved_transform.name == "test_transform"
        assert retrieved_transform.description == "test transform description"
        assert retrieved_transform.definition.model_dump() == transform_definition
    finally:
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_get_transform_by_id_failures(
    client: GenaiEngineTestClientBase,
    transform_definition: dict,
) -> None:
    """Test getting a transform by id failures."""
    task_id = str(uuid.uuid4())
    transform_id = str(uuid.uuid4())

    # Create two tasks
    status_code, task = client.create_task(
        name="test_transform_routes_task",
        is_agentic=True,
    )
    assert status_code == 200

    status_code, task2 = client.create_task(
        name="test_transform_routes_task2",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Create a transform and add it to the second task
        status_code, transform = client.create_transform(
            task_id=task2.id,
            name="test_transform",
            definition=transform_definition,
            description="test transform description",
        )
        assert status_code == 200

        # Test getting a transform for a task that doesn't exist returns a 404 err
        status_code, error = client.get_transform(
            task_id=task_id,
            transform_id=transform_id,
        )
        assert status_code == 404
        assert error is not None
        assert f"task {task_id} not found" in error.get("detail", "").lower()

        # Test getting a transform that doesn't exist for a real task returns a 404 err
        status_code, error = client.get_transform(
            task_id=task.id,
            transform_id=transform_id,
        )
        assert status_code == 404
        assert error is not None
        assert (
            f"transform {transform_id} not found for task {task.id}"
            in error.get("detail", "").lower()
        )

        # Test getting the transform by id for the wrong task returns a 404 err
        status_code, error = client.get_transform(
            task_id=task.id,
            transform_id=transform.id,
        )
        assert status_code == 404
        assert error is not None
        assert (
            f"transform {transform.id} not found for task {task.id}"
            in error.get("detail", "").lower()
        )

        # Test getting the transform by id for the correct task returns a 200
        status_code, _ = client.get_transform(
            task_id=task2.id,
            transform_id=transform.id,
        )
        assert status_code == 200

    finally:
        client.delete_task(task2.id)
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_list_all_transforms_success(
    client: GenaiEngineTestClientBase,
    transform_definition: dict,
) -> None:
    """Test listing all transforms successfully."""
    # Create a task
    status_code, task = client.create_task(
        name="test_transform_routes_task",
        is_agentic=True,
    )
    assert status_code == 200

    transforms = []
    for i in range(10):
        status_code, transform = client.create_transform(
            task_id=task.id,
            name=f"test_transform_{i}",
            definition=transform_definition,
            description=f"test transform description {i}",
        )
        assert status_code == 200
        transforms.append(transform)

    # Sort descending since that's what pagination defaults to
    transforms = sorted(transforms, key=lambda x: x.created_at, reverse=True)

    try:
        # Get the transform by id
        status_code, retrieved_transforms = client.list_transforms(task_id=task.id)
        assert status_code == 200
        assert len(retrieved_transforms.transforms) == 10

        for i, transform in enumerate(retrieved_transforms.transforms):
            assert transform.id == transforms[i].id
            assert transform.task_id == task.id
            assert transform.name == transforms[i].name
            assert transform.description == transforms[i].description
            assert transform.definition.model_dump() == transform_definition
    finally:
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_list_all_transforms_pagination(
    client: GenaiEngineTestClientBase,
    transform_definition: dict,
) -> None:
    """Test listing all transforms with pagination."""
    # Create a task
    status_code, task = client.create_task(
        name="test_transform_routes_task",
        is_agentic=True,
    )
    assert status_code == 200

    transforms = []
    for i in range(10):
        status_code, transform = client.create_transform(
            task_id=task.id,
            name=f"test_transform_{i}",
            definition=transform_definition,
            description=f"test transform description {i}",
        )
        assert status_code == 200
        transforms.append(transform)

    try:
        # Sort ascending
        status_code, retrieved_transforms = client.list_transforms(
            task_id=task.id,
            search_url="sort=asc",
        )
        assert status_code == 200
        assert len(retrieved_transforms.transforms) == 10

        for i, transform in enumerate(retrieved_transforms.transforms):
            assert transform.id == transforms[i].id
            assert transform.task_id == task.id
            assert transform.name == transforms[i].name
            assert transform.description == transforms[i].description
            assert transform.definition.model_dump() == transform_definition

        # Page size is half the total number of transforms
        status_code, retrieved_transforms = client.list_transforms(
            task_id=task.id,
            search_url="page_size=5&sort=asc",
        )
        assert status_code == 200
        assert len(retrieved_transforms.transforms) == 5

        for i, transform in enumerate(retrieved_transforms.transforms):
            assert transform.id == transforms[i].id
            assert transform.task_id == task.id
            assert transform.name == transforms[i].name
            assert transform.description == transforms[i].description
            assert transform.definition.model_dump() == transform_definition

        # Page size is half the total number of transforms
        status_code, retrieved_transforms = client.list_transforms(
            task_id=task.id,
            search_url="sort=asc&page=1&page_size=5",
        )
        assert status_code == 200
        assert len(retrieved_transforms.transforms) == 5

        for i, transform in enumerate(retrieved_transforms.transforms):
            transform_idx = i + 5
            assert transform.id == transforms[transform_idx].id
            assert transform.task_id == task.id
            assert transform.name == transforms[transform_idx].name
            assert transform.description == transforms[transform_idx].description
            assert transform.definition.model_dump() == transform_definition

        # Page size is half the total number of transforms
        status_code, retrieved_transforms = client.list_transforms(
            task_id=task.id,
            search_url="sort=asc&page=2&page_size=5",
        )
        assert status_code == 200
        assert len(retrieved_transforms.transforms) == 0
    finally:
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_list_all_transforms_filtering(
    client: GenaiEngineTestClientBase,
    transform_definition: dict,
) -> None:
    """Test listing all transforms with filtering."""
    # Create a task
    status_code, task = client.create_task(
        name="test_transform_routes_task",
        is_agentic=True,
    )
    assert status_code == 200

    transforms = []
    for i in range(10):
        status_code, transform = client.create_transform(
            task_id=task.id,
            name=f"test_transform_{i}",
            definition=transform_definition,
            description=f"test transform description {i}",
        )
        assert status_code == 200
        transforms.append(transform)

    try:
        # Name like filter
        status_code, retrieved_transforms = client.list_transforms(
            task_id=task.id,
            search_url="name=test_transform_5",
        )
        assert status_code == 200
        assert len(retrieved_transforms.transforms) == 1
        assert retrieved_transforms.transforms[0].id == transforms[5].id
        assert retrieved_transforms.transforms[0].name == "test_transform_5"

        # Created after filter
        status_code, retrieved_transforms = client.list_transforms(
            task_id=task.id,
            search_url=f"created_after={transforms[5].created_at.isoformat()}",
        )
        assert status_code == 200
        assert len(retrieved_transforms.transforms) == 5

        # Created before filter
        status_code, retrieved_transforms = client.list_transforms(
            task_id=task.id,
            search_url=f"created_before={transforms[5].created_at.isoformat()}",
        )
        assert status_code == 200
        assert len(retrieved_transforms.transforms) == 5

    finally:
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_update_transform_success(
    client: GenaiEngineTestClientBase,
    transform_definition: dict,
) -> None:
    """Test updating a transform successfully."""
    # Create a task
    status_code, task = client.create_task(
        name="test_transform_routes_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Create a transform
        status_code, transform = client.create_transform(
            task_id=task.id,
            name="test_transform",
            definition=transform_definition,
            description="test transform description",
        )
        assert status_code == 200
        assert transform.id is not None
        assert transform.task_id == task.id
        assert transform.name == "test_transform"
        assert transform.description == "test transform description"
        assert transform.definition.model_dump() == transform_definition
        assert transform.created_at is not None
        assert transform.updated_at is not None

        # Update the transform
        status_code, updated_transform = client.update_transform(
            task_id=task.id,
            transform_id=transform.id,
            name="test_updated_transform",
            description="test updated transform description",
        )
        assert status_code == 200
        assert updated_transform.id == transform.id
        assert updated_transform.task_id == task.id
        assert updated_transform.name == "test_updated_transform"
        assert updated_transform.description == "test updated transform description"
        assert updated_transform.definition.model_dump() == transform_definition
        assert updated_transform.created_at == transform.created_at
        assert updated_transform.updated_at != transform.updated_at
    finally:
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_update_transform_failures(client: GenaiEngineTestClientBase) -> None:
    """Test updating a transform failures."""
    # Create a task
    status_code, task = client.create_task(
        name="test_transform_routes_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        task_id = str(uuid.uuid4())
        transform_id = str(uuid.uuid4())

        # updating a transform for a nonexistent task returns a 404 error
        status_code, error = client.update_transform(
            task_id=task_id,
            transform_id=transform_id,
            name="test_updated_transform",
            description="test updated transform description",
        )
        assert status_code == 404
        assert error is not None
        assert f"task {task_id} not found" in error.get("detail", "").lower()

        # updating a nonexistent transform returns a 404 error
        status_code, error = client.update_transform(
            task_id=task.id,
            transform_id=transform_id,
            name="test_updated_transform",
            description="test updated transform description",
        )
        assert status_code == 404
        assert error is not None
        assert (
            f"transform {transform_id} not found for task {task.id}"
            in error.get("detail", "").lower()
        )
    finally:
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_deleting_transform_success(
    client: GenaiEngineTestClientBase,
    transform_definition: dict,
) -> None:
    """Test deleting a transform successfully."""
    # Create a task
    status_code, task = client.create_task(
        name="test_transform_routes_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Create a transform
        status_code, transform = client.create_transform(
            task_id=task.id,
            name="test_transform",
            definition=transform_definition,
            description="test transform description",
        )
        assert status_code == 200
        assert transform.id is not None
        assert transform.task_id == task.id
        assert transform.name == "test_transform"
        assert transform.description == "test transform description"
        assert transform.definition.model_dump() == transform_definition
        assert transform.created_at is not None
        assert transform.updated_at is not None

        # Delete the transform
        status_code, _ = client.delete_transform(
            task_id=task.id,
            transform_id=transform.id,
        )
        assert status_code == 204
    finally:
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_deleting_transform_failures(client: GenaiEngineTestClientBase) -> None:
    """Test deleting a transform failures."""
    # Create a task
    status_code, task = client.create_task(
        name="test_transform_routes_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        task_id = str(uuid.uuid4())
        transform_id = str(uuid.uuid4())

        # deleting a transform with a nonexistent task returns a 404 error
        status_code, error = client.delete_transform(
            task_id=task_id,
            transform_id=transform_id,
        )
        assert status_code == 404
        assert error is not None
        assert f"task {task_id} not found" in error.get("detail", "").lower()

        # deleting a nonexistent transform returns a 404 error
        status_code, error = client.delete_transform(
            task_id=task.id,
            transform_id=transform_id,
        )
        assert status_code == 404
        assert error is not None
        assert (
            f"transform {transform_id} not found for task {task.id}"
            in error.get("detail", "").lower()
        )
    finally:
        client.delete_task(task.id)
