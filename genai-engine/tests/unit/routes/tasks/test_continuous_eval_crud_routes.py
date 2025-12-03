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
def test_create_continuous_eval_success(client: GenaiEngineTestClientBase):
    """Test creating a continuous eval successfully."""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_create_continuous_eval_success",
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

        # Create a continuous eval
        status_code, continuous_eval = client.save_continuous_eval(
            task_id=agentic_task.id,
            continuous_eval_data={
                "name": "test_continuous_eval",
                "description": "Test continuous eval description",
                "llm_eval_name": llm_eval.name,
                "llm_eval_version": llm_eval.version,
                "transform_id": str(transform.id),
            },
        )
        assert status_code == 200
        assert continuous_eval.id is not None
        assert continuous_eval.name == "test_continuous_eval"
        assert continuous_eval.description == "Test continuous eval description"
        assert continuous_eval.task_id == agentic_task.id
        assert continuous_eval.llm_eval_name == llm_eval.name
        assert continuous_eval.llm_eval_version == llm_eval.version
        assert continuous_eval.transform_id == transform.id
        assert continuous_eval.created_at is not None
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_create_continuous_eval_failures(client: GenaiEngineTestClientBase):
    """Test creating a continuous eval failures."""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_create_continuous_eval_failures",
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

        # Create a continuous eval for a non-existent task
        fake_task_id = str(uuid.uuid4())
        status_code, error = client.save_continuous_eval(
            task_id=fake_task_id,
            continuous_eval_data={
                "name": "test_continuous_eval",
                "description": "Test continuous eval description",
                "llm_eval_name": llm_eval.name,
                "llm_eval_version": llm_eval.version,
                "transform_id": str(transform.id),
            },
        )
        assert status_code == 404
        assert error is not None
        assert f"task {fake_task_id} not found" in error.get("detail", "").lower()

        # Create a continuous eval for a non-existent llm eval
        status_code, error = client.save_continuous_eval(
            task_id=agentic_task.id,
            continuous_eval_data={
                "name": "test_continuous_eval",
                "description": "Test continuous eval description",
                "llm_eval_name": "fake_llm_eval_name",
                "llm_eval_version": "latest",
                "transform_id": str(transform.id),
            },
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
def test_update_continuous_eval_success(client: GenaiEngineTestClientBase):
    """Test creating a continuous eval successfully."""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_create_continuous_eval_success",
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

        # Create a continuous eval
        status_code, continuous_eval = client.save_continuous_eval(
            task_id=agentic_task.id,
            continuous_eval_data={
                "name": "test_continuous_eval",
                "description": "Test continuous eval description",
                "llm_eval_name": llm_eval.name,
                "llm_eval_version": llm_eval.version,
                "transform_id": str(transform.id),
            },
        )
        assert status_code == 200

        # Update the continuous eval
        status_code, updated_continuous_eval = client.update_continuous_eval(
            continuous_eval_id=continuous_eval.id,
            continuous_eval_data={
                "name": "test_continuous_eval_updated",
                "description": "Test continuous eval description updated",
            },
        )
        assert status_code == 200
        assert updated_continuous_eval.id == continuous_eval.id
        assert updated_continuous_eval.name == "test_continuous_eval_updated"
        assert (
            updated_continuous_eval.description
            == "Test continuous eval description updated"
        )
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_update_continuous_eval_failures(client: GenaiEngineTestClientBase):
    """Test updating a continuous eval failures."""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_create_continuous_eval_success",
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

        # Update the continuous eval for non-existent continuous eval
        fake_eval_id = str(uuid.uuid4())
        status_code, error = client.update_continuous_eval(
            continuous_eval_id=fake_eval_id,
            continuous_eval_data={
                "name": "test_continuous_eval_updated",
                "description": "Test continuous eval description updated",
            },
        )
        assert status_code == 404
        assert error is not None
        assert (
            f"continuous eval {fake_eval_id} not found"
            in error.get("detail", "").lower()
        )

        # Create a continuous eval
        status_code, continuous_eval = client.save_continuous_eval(
            task_id=agentic_task.id,
            continuous_eval_data={
                "name": "test_continuous_eval",
                "description": "Test continuous eval description",
                "llm_eval_name": llm_eval.name,
                "llm_eval_version": llm_eval.version,
                "transform_id": str(transform.id),
            },
        )
        assert status_code == 200

        # Update the continuous eval name without version should raise an error
        status_code, error = client.update_continuous_eval(
            continuous_eval_id=continuous_eval.id,
            continuous_eval_data={
                "name": "test_continuous_eval_updated",
                "description": "Test continuous eval description updated",
                "llm_eval_name": llm_eval.name,
            },
        )
        assert status_code == 400
        assert error is not None
        assert (
            f"must specify which version of the llm eval this continuous eval should be associated with"
            in error.get("detail", "").lower()
        )
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_get_continuous_eval_by_id_success(client: GenaiEngineTestClientBase):
    """Test getting a continuous eval by id successfully."""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_get_continuous_eval_by_id_success",
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

        # Create a continuous eval
        status_code, continuous_eval = client.save_continuous_eval(
            task_id=agentic_task.id,
            continuous_eval_data={
                "name": "test_continuous_eval",
                "description": "Test continuous eval description",
                "llm_eval_name": llm_eval.name,
                "llm_eval_version": llm_eval.version,
                "transform_id": str(transform.id),
            },
        )
        assert status_code == 200

        status_code, retrieved_continuous_eval = client.get_continuous_eval_by_id(
            continuous_eval_id=continuous_eval.id,
        )
        assert status_code == 200
        assert retrieved_continuous_eval.id == continuous_eval.id
        assert retrieved_continuous_eval.task_id == agentic_task.id
        assert retrieved_continuous_eval.llm_eval_name == llm_eval.name
        assert retrieved_continuous_eval.llm_eval_version == llm_eval.version
        assert retrieved_continuous_eval.transform_id == transform.id
        assert retrieved_continuous_eval.created_at is not None
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_get_continuous_eval_by_id_for_non_existent_eval(
    client: GenaiEngineTestClientBase,
):
    """Test getting a continuous eval by id for a non-existent eval."""
    fake_eval_id = str(uuid.uuid4())
    status_code, error = client.get_continuous_eval_by_id(
        continuous_eval_id=fake_eval_id,
    )
    assert status_code == 404
    assert error is not None
    assert (
        f"continuous eval {fake_eval_id} not found" in error.get("detail", "").lower()
    )


@pytest.mark.unit_tests
def test_list_continuous_evals_success(client: GenaiEngineTestClientBase):
    """Test listing continuous evals successfully."""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_list_continuous_evals_success",
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
        continuous_evals = []
        for transform in transforms.values():
            status_code, continuous_eval = client.save_continuous_eval(
                task_id=agentic_task.id,
                continuous_eval_data={
                    "name": "test_continuous_eval",
                    "description": "Test continuous eval description",
                    "llm_eval_name": llm_eval.name,
                    "llm_eval_version": llm_eval.version,
                    "transform_id": str(transform.id),
                },
            )
            assert status_code == 200
            continuous_evals.append(continuous_eval)

        # Sort the transforms by created_at in descending order since that's what pagination defaults to
        continuous_evals = sorted(
            continuous_evals,
            key=lambda x: x.created_at,
            reverse=True,
        )
        sorted_continuous_evals = []
        for continuous_eval in continuous_evals:
            sorted_continuous_evals.append(transforms[continuous_eval.transform_id])

        # List the continuous evals
        status_code, received_continuous_evals = client.list_continuous_evals(
            task_id=agentic_task.id,
        )
        assert status_code == 200
        assert len(received_continuous_evals.evals) == len(transforms)
        assert received_continuous_evals.count == len(transforms)

        for i in range(len(transforms)):
            assert received_continuous_evals.evals[i].id == continuous_evals[i].id
            assert received_continuous_evals.evals[i].task_id == agentic_task.id
            assert received_continuous_evals.evals[i].llm_eval_name == llm_eval.name
            assert (
                received_continuous_evals.evals[i].llm_eval_version == llm_eval.version
            )
            assert (
                received_continuous_evals.evals[i].transform_id
                == sorted_continuous_evals[i].id
            )
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_list_continuous_evals_pagination(client: GenaiEngineTestClientBase):
    """Test listing continuous evals with pagination"""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_list_continuous_evals_pagination",
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

        # Save the continuous evals
        continuous_evals = []
        for transform in transforms.values():
            status_code, continuous_eval = client.save_continuous_eval(
                task_id=agentic_task.id,
                continuous_eval_data={
                    "name": "test_continuous_eval",
                    "description": "Test continuous eval description",
                    "llm_eval_name": llm_eval.name,
                    "llm_eval_version": llm_eval.version,
                    "transform_id": str(transform.id),
                },
            )
            assert status_code == 200
            continuous_evals.append(continuous_eval)

        # Test sort ascending
        continuous_evals = sorted(continuous_evals, key=lambda x: x.created_at)
        status_code, received_continuous_evals = client.list_continuous_evals(
            task_id=agentic_task.id,
            search_url="sort=asc",
        )
        assert status_code == 200
        assert len(received_continuous_evals.evals) == len(transforms)
        assert received_continuous_evals.count == len(transforms)

        for i in range(len(transforms)):
            assert received_continuous_evals.evals[i].id == continuous_evals[i].id
            assert (
                received_continuous_evals.evals[i].task_id
                == continuous_evals[i].task_id
            )
            assert (
                received_continuous_evals.evals[i].llm_eval_name
                == continuous_evals[i].llm_eval_name
            )
            assert (
                received_continuous_evals.evals[i].llm_eval_version
                == continuous_evals[i].llm_eval_version
            )
            assert (
                received_continuous_evals.evals[i].transform_id
                == continuous_evals[i].transform_id
            )

        # Test page size = 5
        status_code, received_continuous_evals = client.list_continuous_evals(
            task_id=agentic_task.id,
            search_url="sort=asc&page=0&page_size=5",
        )
        assert status_code == 200
        assert len(received_continuous_evals.evals) == len(transforms) // 2
        assert received_continuous_evals.count == len(transforms) // 2
        for i in range(len(received_continuous_evals.evals) // 2):
            assert received_continuous_evals.evals[i].id == continuous_evals[i].id
            assert (
                received_continuous_evals.evals[i].task_id
                == continuous_evals[i].task_id
            )
            assert (
                received_continuous_evals.evals[i].llm_eval_name
                == continuous_evals[i].llm_eval_name
            )
            assert (
                received_continuous_evals.evals[i].llm_eval_version
                == continuous_evals[i].llm_eval_version
            )
            assert (
                received_continuous_evals.evals[i].transform_id
                == continuous_evals[i].transform_id
            )

        # Test page size = 5 and page = 2 (over the number of items)
        status_code, received_continuous_evals = client.list_continuous_evals(
            task_id=agentic_task.id,
            search_url="sort=asc&page=2&page_size=5",
        )
        assert status_code == 200
        assert len(received_continuous_evals.evals) == 0
        assert received_continuous_evals.count == 0
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_list_continuous_evals_filtering(client: GenaiEngineTestClientBase):
    """Test listing continuous evals with filtering"""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_list_continuous_evals_filtering",
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

        # Save the continuous evals
        continuous_evals = []
        for i in range(4):
            status_code, continuous_eval = client.save_continuous_eval(
                task_id=agentic_task.id,
                continuous_eval_data={
                    "name": f"test_continuous_eval_{i % 2}",
                    "description": "Test continuous eval description",
                    "llm_eval_name": llm_evals[i % 2].name,
                    "llm_eval_version": llm_evals[i % 2].version,
                    "transform_id": str(transforms[i].id),
                },
            )
            assert status_code == 200
            continuous_evals.append(continuous_eval)

        # Test filtering by name
        status_code, received_continuous_evals = client.list_continuous_evals(
            task_id=agentic_task.id,
            search_url="name=test_continuous_eval_0",
        )
        assert status_code == 200
        assert len(received_continuous_evals.evals) == len(transforms) // 2
        assert received_continuous_evals.count == len(transforms) // 2

        # Test filtering by llm eval name
        status_code, received_continuous_evals = client.list_continuous_evals(
            task_id=agentic_task.id,
            search_url="llm_eval_name=test_llm_eval_0",
        )
        assert status_code == 200
        assert len(received_continuous_evals.evals) == len(transforms) // 2
        assert received_continuous_evals.count == len(transforms) // 2

        continuous_evals = sorted(continuous_evals, key=lambda x: x.created_at)

        # Test filtering by created after
        status_code, received_continuous_evals = client.list_continuous_evals(
            task_id=agentic_task.id,
            search_url=f"created_after={continuous_evals[-1].created_at.isoformat()}",
        )
        assert status_code == 200
        assert len(received_continuous_evals.evals) == 1
        assert received_continuous_evals.count == 1

        # Test filtering by created before
        status_code, received_continuous_evals = client.list_continuous_evals(
            task_id=agentic_task.id,
            search_url=f"created_before={continuous_evals[-1].created_at.isoformat()}",
        )
        assert status_code == 200
        assert len(received_continuous_evals.evals) == 3
        assert received_continuous_evals.count == 3
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_delete_continuous_eval_success(client: GenaiEngineTestClientBase):
    """Test deleting a continuous eval successfully."""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_delete_continuous_eval_success",
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

        # Save the continuous eval
        status_code, continuous_eval = client.save_continuous_eval(
            task_id=agentic_task.id,
            continuous_eval_data={
                "name": "test_continuous_eval",
                "description": "Test continuous eval description",
                "llm_eval_name": llm_eval.name,
                "llm_eval_version": llm_eval.version,
                "transform_id": str(transform.id),
            },
        )
        assert status_code == 200

        # Get the transform from the llm eval
        status_code, retrieved_continuous_eval = client.get_continuous_eval_by_id(
            continuous_eval_id=continuous_eval.id,
        )
        assert status_code == 200
        assert retrieved_continuous_eval.transform_id == transform.id

        # Delete the continuous eval
        status_code, _ = client.delete_continuous_eval(
            continuous_eval_id=continuous_eval.id,
        )
        assert status_code == 204

        # Verify the transform was removed
        status_code, error = client.get_continuous_eval_by_id(
            continuous_eval_id=continuous_eval.id,
        )
        assert status_code == 404
    finally:
        client.delete_task(agentic_task.id)


@pytest.mark.unit_tests
def test_delete_continuous_eval_failures(client: GenaiEngineTestClientBase):
    """Test deleting a continuous eval failures."""

    # Create a task
    status_code, agentic_task = client.create_task(
        name="test_delete_continuous_eval_failures",
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
        fake_continuous_eval_id = str(uuid.uuid4())
        status_code, error = client.delete_continuous_eval(
            continuous_eval_id=fake_continuous_eval_id,
        )
        assert status_code == 404
        assert error is not None
        assert (
            f"continuous eval {fake_continuous_eval_id} not found"
            in error.get("detail", "").lower()
        )
    finally:
        client.delete_task(agentic_task.id)
