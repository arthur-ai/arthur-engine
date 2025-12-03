import uuid

import pytest

from schemas.internal_schemas import TraceTransform
from schemas.llm_eval_schemas import LLMEval
from tests.clients.base_test_client import GenaiEngineTestClientBase


def create_test_transform(
    client: GenaiEngineTestClientBase,
    task_id: str,
) -> tuple[int, TraceTransform]:
    transform_definition = {
        "variables": [
            {
                "variable_name": "test_variable",
                "span_name": "test_span",
                "attribute_path": "test_attribute",
            },
        ],
    }
    return client.create_transform(
        task_id=task_id,
        name="test_transform",
        description="Test transform description",
        definition=transform_definition,
    )


def create_test_llm_eval(
    client: GenaiEngineTestClientBase,
    task_id: str,
    llm_eval_name: str = "test_llm_eval",
) -> tuple[int, LLMEval]:
    llm_eval_data = {
        "model_name": "gpt-4o",
        "model_provider": "openai",
        "instructions": "Test instructions",
    }
    return client.save_llm_eval(
        task_id=task_id,
        llm_eval_name=llm_eval_name,
        llm_eval_data=llm_eval_data,
    )


@pytest.mark.unit_tests
def test_add_transform_to_llm_eval_success(client: GenaiEngineTestClientBase):
    """Test adding an llm eval transform successfully."""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_execute_transform_missing_trace_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Save an llm eval
        status_code, llm_eval = create_test_llm_eval(client, agentic_task.id)
        assert status_code == 200

        # Create a transform
        status_code, transform = create_test_transform(client, agentic_task.id)
        assert status_code == 200

        # Add the transform to the llm eval
        status_code, llm_eval_transform = client.add_transform_to_llm_eval(
            task_id=agentic_task.id,
            llm_eval_name=llm_eval.name,
            llm_eval_version=llm_eval.version,
            transform_id=transform.id,
        )
        assert status_code == 200
        assert llm_eval_transform.id is not None
        assert llm_eval_transform.task_id == agentic_task.id
        assert llm_eval_transform.llm_eval_name == llm_eval.name
        assert llm_eval_transform.llm_eval_version == llm_eval.version
        assert llm_eval_transform.transform_id == transform.id
        assert llm_eval_transform.created_at is not None
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_add_transform_to_llm_eval_failures(client: GenaiEngineTestClientBase):
    """Test adding a transform to an llm eval failures."""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_execute_transform_missing_trace_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Save an llm eval
        status_code, llm_eval = create_test_llm_eval(client, agentic_task.id)
        assert status_code == 200

        # Create a transform
        status_code, transform = create_test_transform(client, agentic_task.id)
        assert status_code == 200

        # Add a transform to a non-existent task
        fake_task_id = str(uuid.uuid4())
        status_code, error = client.add_transform_to_llm_eval(
            task_id=fake_task_id,
            llm_eval_name=llm_eval.name,
            llm_eval_version=llm_eval.version,
            transform_id=transform.id,
        )
        assert status_code == 404
        assert error is not None
        assert f"task {fake_task_id} not found" in error.get("detail", "").lower()

        # Add a transform to a non-existent llm eval
        status_code, error = client.add_transform_to_llm_eval(
            task_id=agentic_task.id,
            llm_eval_name="fake_llm_eval_name",
            llm_eval_version="latest",
            transform_id=transform.id,
        )
        assert status_code == 404
        assert error is not None
        assert (
            f"'fake_llm_eval_name' (version 'latest') not found for task '{agentic_task.id}'"
            in error.get("detail", "").lower()
        )
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_get_llm_eval_transform_by_id_success(client: GenaiEngineTestClientBase):
    """Test getting an llm eval transform by id successfully."""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_execute_transform_missing_trace_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Save an llm eval
        status_code, llm_eval = create_test_llm_eval(client, agentic_task.id)
        assert status_code == 200

        # Create a transform
        status_code, transform = create_test_transform(client, agentic_task.id)
        assert status_code == 200

        # Add the transform to the llm eval
        status_code, llm_eval_transform = client.add_transform_to_llm_eval(
            task_id=agentic_task.id,
            llm_eval_name=llm_eval.name,
            llm_eval_version=llm_eval.version,
            transform_id=transform.id,
        )
        assert status_code == 200

        status_code, retrieved_llm_eval_transform = client.get_llm_eval_transform_by_id(
            task_id=agentic_task.id,
            llm_eval_name=llm_eval.name,
            llm_eval_version=llm_eval.version,
            transform_id=transform.id,
        )
        assert status_code == 200
        assert retrieved_llm_eval_transform.id == llm_eval_transform.id
        assert retrieved_llm_eval_transform.task_id == agentic_task.id
        assert retrieved_llm_eval_transform.llm_eval_name == llm_eval.name
        assert retrieved_llm_eval_transform.llm_eval_version == llm_eval.version
        assert retrieved_llm_eval_transform.transform_id == transform.id
        assert retrieved_llm_eval_transform.created_at is not None
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_get_llm_eval_transform_by_id_failures(client: GenaiEngineTestClientBase):
    """Test getting an llm eval transform by id failures."""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_execute_transform_missing_trace_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Save an llm eval
        status_code, llm_eval = create_test_llm_eval(client, agentic_task.id)
        assert status_code == 200

        # Create a transform
        status_code, transform = create_test_transform(client, agentic_task.id)
        assert status_code == 200

        # attempt to get a transform for a non-existent task
        fake_task_id = str(uuid.uuid4())
        status_code, error = client.get_llm_eval_transform_by_id(
            task_id=fake_task_id,
            llm_eval_name=llm_eval.name,
            llm_eval_version=llm_eval.version,
            transform_id=transform.id,
        )
        assert status_code == 404
        assert error is not None
        assert f"task {fake_task_id} not found" in error.get("detail", "").lower()

        # attempt to get a transform for a non-existent llm eval
        status_code, error = client.get_llm_eval_transform_by_id(
            task_id=agentic_task.id,
            llm_eval_name="fake_llm_eval_name",
            llm_eval_version="latest",
            transform_id=transform.id,
        )
        assert status_code == 404
        assert error is not None
        assert (
            f"'fake_llm_eval_name' (version 'latest') not found for task '{agentic_task.id}'"
            in error.get("detail", "").lower()
        )

        # attempt to get a non-existent transform
        fake_transform_id = str(uuid.uuid4())
        status_code, error = client.get_llm_eval_transform_by_id(
            task_id=agentic_task.id,
            llm_eval_name=llm_eval.name,
            llm_eval_version=llm_eval.version,
            transform_id=fake_transform_id,
        )
        assert status_code == 404
        assert error is not None
        assert (
            f"transform {fake_transform_id} not found for eval {llm_eval.name} (version {llm_eval.version})"
            in error.get("detail", "").lower()
        )

        # attempt to get a transform that hasn't been added to the llm eval
        status_code, error = client.get_llm_eval_transform_by_id(
            task_id=agentic_task.id,
            llm_eval_name=llm_eval.name,
            llm_eval_version=llm_eval.version,
            transform_id=transform.id,
        )
        assert status_code == 404
        assert error is not None
        assert (
            f"transform {transform.id} not found for eval {llm_eval.name} (version {llm_eval.version})"
            in error.get("detail", "").lower()
        )
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_list_llm_eval_transforms_success(client: GenaiEngineTestClientBase):
    """Test listing llm eval transforms successfully."""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_execute_transform_missing_trace_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Save an llm eval
        status_code, llm_eval = create_test_llm_eval(client, agentic_task.id)
        assert status_code == 200

        # Create transforms
        transforms = {}
        for i in range(3):
            status_code, transform = create_test_transform(client, agentic_task.id)
            assert status_code == 200
            transforms[transform.id] = transform

        # Add the transforms to the llm eval
        llm_eval_transforms = []
        for transform in transforms.values():
            status_code, llm_eval_transform = client.add_transform_to_llm_eval(
                task_id=agentic_task.id,
                llm_eval_name=llm_eval.name,
                llm_eval_version=llm_eval.version,
                transform_id=transform.id,
            )
            assert status_code == 200
            llm_eval_transforms.append(llm_eval_transform)

        # Sort the transforms by created_at in descending order since that's what pagination defaults to
        llm_eval_transforms = sorted(
            llm_eval_transforms,
            key=lambda x: x.created_at,
            reverse=True,
        )
        sorted_transforms = []
        for transform in llm_eval_transforms:
            sorted_transforms.append(transforms[transform.transform_id])

        # List the transforms
        status_code, received_llm_eval_transforms = client.list_llm_eval_transforms(
            task_id=agentic_task.id,
        )
        assert status_code == 200
        assert len(received_llm_eval_transforms.transforms) == len(transforms)
        assert received_llm_eval_transforms.count == len(transforms)

        for i in range(len(transforms)):
            assert (
                received_llm_eval_transforms.transforms[i].id
                == llm_eval_transforms[i].id
            )
            assert received_llm_eval_transforms.transforms[i].task_id == agentic_task.id
            assert (
                received_llm_eval_transforms.transforms[i].llm_eval_name
                == llm_eval.name
            )
            assert (
                received_llm_eval_transforms.transforms[i].llm_eval_version
                == llm_eval.version
            )
            assert (
                received_llm_eval_transforms.transforms[i].transform_id
                == sorted_transforms[i].id
            )
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_list_llm_eval_transforms_pagination(client: GenaiEngineTestClientBase):
    """Test listing llm eval transforms with pagination"""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_execute_transform_missing_trace_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Save an llm eval
        status_code, llm_eval = create_test_llm_eval(client, agentic_task.id)
        assert status_code == 200

        # Create transforms
        transforms = {}
        for i in range(10):
            status_code, transform = create_test_transform(client, agentic_task.id)
            assert status_code == 200
            transforms[transform.id] = transform

        # Add the transforms to the llm eval
        llm_eval_transforms = []
        for transform in transforms.values():
            status_code, llm_eval_transform = client.add_transform_to_llm_eval(
                task_id=agentic_task.id,
                llm_eval_name=llm_eval.name,
                llm_eval_version=llm_eval.version,
                transform_id=transform.id,
            )
            assert status_code == 200
            llm_eval_transforms.append(llm_eval_transform)

        # Test sort ascending
        llm_eval_transforms = sorted(llm_eval_transforms, key=lambda x: x.created_at)
        status_code, received_llm_eval_transforms = client.list_llm_eval_transforms(
            task_id=agentic_task.id,
            search_url="sort=asc",
        )
        assert status_code == 200
        assert len(received_llm_eval_transforms.transforms) == len(transforms)
        assert received_llm_eval_transforms.count == len(transforms)

        for i in range(len(transforms)):
            assert (
                received_llm_eval_transforms.transforms[i].id
                == llm_eval_transforms[i].id
            )
            assert (
                received_llm_eval_transforms.transforms[i].task_id
                == llm_eval_transforms[i].task_id
            )
            assert (
                received_llm_eval_transforms.transforms[i].llm_eval_name
                == llm_eval_transforms[i].llm_eval_name
            )
            assert (
                received_llm_eval_transforms.transforms[i].llm_eval_version
                == llm_eval_transforms[i].llm_eval_version
            )
            assert (
                received_llm_eval_transforms.transforms[i].transform_id
                == llm_eval_transforms[i].transform_id
            )

        # Test page size = 5
        status_code, received_llm_eval_transforms = client.list_llm_eval_transforms(
            task_id=agentic_task.id,
            search_url="sort=asc&page=0&page_size=5",
        )
        assert status_code == 200
        assert len(received_llm_eval_transforms.transforms) == len(transforms) // 2
        assert received_llm_eval_transforms.count == len(transforms) // 2
        for i in range(len(received_llm_eval_transforms.transforms) // 2):
            assert (
                received_llm_eval_transforms.transforms[i].id
                == llm_eval_transforms[i].id
            )
            assert (
                received_llm_eval_transforms.transforms[i].task_id
                == llm_eval_transforms[i].task_id
            )
            assert (
                received_llm_eval_transforms.transforms[i].llm_eval_name
                == llm_eval_transforms[i].llm_eval_name
            )
            assert (
                received_llm_eval_transforms.transforms[i].llm_eval_version
                == llm_eval_transforms[i].llm_eval_version
            )
            assert (
                received_llm_eval_transforms.transforms[i].transform_id
                == llm_eval_transforms[i].transform_id
            )

        # Test page size = 5 and page = 2 (over the number of items)
        status_code, received_llm_eval_transforms = client.list_llm_eval_transforms(
            task_id=agentic_task.id,
            search_url="sort=asc&page=2&page_size=5",
        )
        assert status_code == 200
        assert len(received_llm_eval_transforms.transforms) == 0
        assert received_llm_eval_transforms.count == 0
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_list_llm_eval_transforms_filtering(client: GenaiEngineTestClientBase):
    """Test listing llm eval transforms with filtering"""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_execute_transform_missing_trace_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Save an llm eval
        llm_evals = []
        for i in range(2):
            status_code, llm_eval = create_test_llm_eval(
                client,
                agentic_task.id,
                f"test_llm_eval_{i}",
            )
            assert status_code == 200
            llm_evals.append(llm_eval)

        # Create transforms
        transforms = []
        for i in range(4):
            status_code, transform = create_test_transform(client, agentic_task.id)
            assert status_code == 200
            transforms.append(transform)

        # Add the transforms to the llm evals
        llm_eval_transforms = []
        for i in range(4):
            status_code, llm_eval_transform = client.add_transform_to_llm_eval(
                task_id=agentic_task.id,
                llm_eval_name=llm_evals[i % 2].name,
                llm_eval_version=llm_evals[i % 2].version,
                transform_id=transforms[i].id,
            )
            assert status_code == 200
            llm_eval_transforms.append(llm_eval_transform)

        # Test filtering by llm eval name
        status_code, received_llm_eval_transforms = client.list_llm_eval_transforms(
            task_id=agentic_task.id,
            search_url="llm_eval_name=test_llm_eval_0",
        )
        assert status_code == 200
        assert len(received_llm_eval_transforms.transforms) == len(transforms) // 2
        assert received_llm_eval_transforms.count == len(transforms) // 2

        llm_eval_transforms = sorted(llm_eval_transforms, key=lambda x: x.created_at)

        # Test filtering by created after
        status_code, received_llm_eval_transforms = client.list_llm_eval_transforms(
            task_id=agentic_task.id,
            search_url=f"created_after={llm_eval_transforms[-1].created_at.isoformat()}",
        )
        assert status_code == 200
        assert len(received_llm_eval_transforms.transforms) == 1
        assert received_llm_eval_transforms.count == 1

        # Test filtering by created before
        status_code, received_llm_eval_transforms = client.list_llm_eval_transforms(
            task_id=agentic_task.id,
            search_url=f"created_before={llm_eval_transforms[-1].created_at.isoformat()}",
        )
        assert status_code == 200
        assert len(received_llm_eval_transforms.transforms) == 3
        assert received_llm_eval_transforms.count == 3
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_remove_transform_from_llm_eval_success(client: GenaiEngineTestClientBase):
    """Test removing an llm eval transform successfully."""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_execute_transform_missing_trace_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Save an llm eval
        status_code, llm_eval = create_test_llm_eval(client, agentic_task.id)
        assert status_code == 200

        # Create a transform
        status_code, transform = create_test_transform(client, agentic_task.id)
        assert status_code == 200

        # Add the transform to the llm eval
        status_code, _ = client.add_transform_to_llm_eval(
            task_id=agentic_task.id,
            llm_eval_name=llm_eval.name,
            llm_eval_version=llm_eval.version,
            transform_id=transform.id,
        )
        assert status_code == 200

        # Get the transform from the llm eval
        status_code, retrieved_llm_eval_transform = client.get_llm_eval_transform_by_id(
            task_id=agentic_task.id,
            llm_eval_name=llm_eval.name,
            llm_eval_version=llm_eval.version,
            transform_id=transform.id,
        )
        assert status_code == 200
        assert retrieved_llm_eval_transform.transform_id == transform.id

        # Remove the transform from the llm eval
        status_code, _ = client.remove_transform_from_llm_eval(
            task_id=agentic_task.id,
            llm_eval_name=llm_eval.name,
            llm_eval_version=llm_eval.version,
            transform_id=transform.id,
        )
        assert status_code == 204

        # Verify the transform was removed
        status_code, error = client.get_llm_eval_transform_by_id(
            task_id=agentic_task.id,
            llm_eval_name=llm_eval.name,
            llm_eval_version=llm_eval.version,
            transform_id=transform.id,
        )
        assert status_code == 404
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_remove_transform_from_llm_eval_failures(client: GenaiEngineTestClientBase):
    """Test removing an llm eval transform failures."""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_execute_transform_missing_trace_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        # Save an llm eval
        status_code, llm_eval = create_test_llm_eval(client, agentic_task.id)
        assert status_code == 200

        # Create a transform
        status_code, transform = create_test_transform(client, agentic_task.id)
        assert status_code == 200

        # Remove a transform from a non-existent task
        fake_task_id = str(uuid.uuid4())
        status_code, error = client.remove_transform_from_llm_eval(
            task_id=fake_task_id,
            llm_eval_name=llm_eval.name,
            llm_eval_version=llm_eval.version,
            transform_id=transform.id,
        )
        assert status_code == 404
        assert error is not None
        assert f"task {fake_task_id} not found" in error.get("detail", "").lower()

        # Remove a transform from a non-existent llm eval
        status_code, error = client.remove_transform_from_llm_eval(
            task_id=agentic_task.id,
            llm_eval_name="fake_llm_eval_name",
            llm_eval_version="latest",
            transform_id=transform.id,
        )
        assert status_code == 404
        assert error is not None
        assert (
            f"'fake_llm_eval_name' (version 'latest') not found for task '{agentic_task.id}'"
            in error.get("detail", "").lower()
        )

        # Remove a non-existent transform
        fake_transform_id = str(uuid.uuid4())
        status_code, error = client.remove_transform_from_llm_eval(
            task_id=agentic_task.id,
            llm_eval_name=llm_eval.name,
            llm_eval_version=llm_eval.version,
            transform_id=fake_transform_id,
        )
        assert status_code == 404
        assert error is not None
        assert (
            f"transform {fake_transform_id} not found for eval {llm_eval.name} (version '{llm_eval.version}')"
            in error.get("detail", "").lower()
        )
    finally:
        client.delete_task(agentic_task.id)
