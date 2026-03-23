import uuid
from datetime import datetime

import pytest

from db_models.agentic_experiment_models import DatabaseAgenticExperiment
from db_models.agentic_notebook_models import DatabaseAgenticNotebook
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    override_get_db_session,
)


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
    transform_id = str(uuid.uuid4())

    # Test getting a transform that doesn't exist for a real task returns a 404 err
    status_code, error = client.get_transform(
        transform_id=transform_id,
    )
    assert status_code == 404
    assert error is not None
    assert f"transform {transform_id} not found" in error.get("detail", "").lower()


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
    transform_id = str(uuid.uuid4())

    # updating a nonexistent transform returns a 404 error
    status_code, error = client.update_transform(
        transform_id=transform_id,
        name="test_updated_transform",
        description="test updated transform description",
    )
    assert status_code == 404
    assert error is not None
    assert f"transform {transform_id} not found" in error.get("detail", "").lower()


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
            transform_id=transform.id,
        )
        assert status_code == 204
    finally:
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_deleting_transform_failures(client: GenaiEngineTestClientBase) -> None:
    """Test deleting a transform failures."""

    transform_id = str(uuid.uuid4())

    # deleting a nonexistent transform returns a 404 error
    status_code, error = client.delete_transform(
        transform_id=transform_id,
    )
    assert status_code == 404
    assert error is not None
    assert f"transform {transform_id} not found" in error.get("detail", "").lower()


def create_test_llm_eval(client: GenaiEngineTestClientBase, task_id: str):
    return client.save_llm_eval(
        task_id=task_id,
        llm_eval_name="test_llm_eval",
        llm_eval_data={
            "model_name": "gpt-4o",
            "model_provider": "openai",
            "instructions": "Test instructions {{test_variable}}",
        },
    )


def create_continuous_eval_for_transform(
    client: GenaiEngineTestClientBase,
    task_id: str,
    transform_id: str,
    llm_eval_name: str,
    llm_eval_version: int,
):
    return client.save_continuous_eval(
        task_id=task_id,
        continuous_eval_data={
            "name": "test_continuous_eval",
            "description": "Test continuous eval",
            "llm_eval_name": llm_eval_name,
            "llm_eval_version": llm_eval_version,
            "transform_id": transform_id,
            "transform_variable_mapping": [
                {
                    "transform_variable": "test_variable",
                    "eval_variable": "test_variable",
                },
            ],
        },
    )


def insert_agentic_experiment(task_id: str, transform_id: str) -> str:
    db_session = override_get_db_session()
    exp_id = str(uuid.uuid4())
    exp = DatabaseAgenticExperiment(
        id=exp_id,
        task_id=task_id,
        name="test_experiment",
        status="queued",
        dataset_id=uuid.uuid4(),
        dataset_version=1,
        http_template={"endpoint_url": "http://localhost", "request_body": "{}"},
        template_variable_mapping=[],
        eval_configs=[
            {
                "name": "test_eval",
                "version": 1,
                "transform_id": transform_id,
                "variable_mapping": [],
            }
        ],
        total_rows=0,
        completed_rows=0,
        failed_rows=0,
        created_at=datetime.now(),
    )
    db_session.add(exp)
    db_session.commit()
    return exp_id


def insert_agentic_notebook(task_id: str, transform_id: str) -> str:
    db_session = override_get_db_session()
    nb_id = str(uuid.uuid4())
    nb = DatabaseAgenticNotebook(
        id=nb_id,
        task_id=task_id,
        name="test_notebook",
        eval_configs=[
            {
                "name": "test_eval",
                "version": 1,
                "transform_id": transform_id,
                "variable_mapping": [],
            }
        ],
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(nb)
    db_session.commit()
    return nb_id


def delete_db_row(model_class, row_id: str) -> None:
    db_session = override_get_db_session()
    row = db_session.query(model_class).filter(model_class.id == row_id).first()
    if row:
        db_session.delete(row)
        db_session.commit()


@pytest.mark.unit_tests
def test_get_transform_dependents_empty(
    client: GenaiEngineTestClientBase,
    transform_definition: dict,
) -> None:
    """Test getting dependents for a transform with no dependents returns empty lists."""
    # Create a task
    status_code, task = client.create_task(
        name="test_dependents_empty", is_agentic=True
    )
    assert status_code == 200

    try:
        # Create a transform
        status_code, transform = client.create_transform(
            task_id=task.id,
            name="test_transform",
            definition=transform_definition,
        )
        assert status_code == 200

        # Get dependents
        status_code, dependents = client.get_transform_dependents(transform.id)
        assert status_code == 200
        assert dependents["continuous_evals"] == []
        assert dependents["agentic_experiments"] == []
        assert dependents["agentic_notebooks"] == []
    finally:
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_get_transform_dependents_with_continuous_eval(
    client: GenaiEngineTestClientBase,
    transform_definition: dict,
) -> None:
    """Test getting dependents returns continuous evals that reference the transform."""
    # Create a task
    status_code, task = client.create_task(
        name="test_dependents_ce", is_agentic=True
    )
    assert status_code == 200

    try:
        # Create a transform
        status_code, transform = client.create_transform(
            task_id=task.id,
            name="test_transform",
            definition=transform_definition,
        )
        assert status_code == 200

        # Create an LLM eval
        status_code, llm_eval = create_test_llm_eval(client, task.id)
        assert status_code == 200

        # Create a continuous eval referencing the transform
        status_code, ce = create_continuous_eval_for_transform(
            client, task.id, str(transform.id), llm_eval.name, llm_eval.version
        )
        assert status_code == 200

        # Get dependents
        status_code, dependents = client.get_transform_dependents(transform.id)
        assert status_code == 200
        assert len(dependents["continuous_evals"]) == 1
        assert dependents["continuous_evals"][0]["id"] == str(ce.id)
        assert dependents["continuous_evals"][0]["name"] == ce.name
        assert dependents["agentic_experiments"] == []
        assert dependents["agentic_notebooks"] == []
    finally:
        client.delete_continuous_eval(ce.id)
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_get_transform_dependents_with_experiment_and_notebook(
    client: GenaiEngineTestClientBase,
    transform_definition: dict,
) -> None:
    """Test getting dependents returns agentic experiments and notebooks."""
    # Create a task
    status_code, task = client.create_task(
        name="test_dependents_exp_nb", is_agentic=True
    )
    assert status_code == 200

    exp_id = None
    nb_id = None
    try:
        # Create a transform
        status_code, transform = client.create_transform(
            task_id=task.id,
            name="test_transform",
            definition=transform_definition,
        )
        assert status_code == 200

        # Insert agentic experiment and notebook referencing the transform
        exp_id = insert_agentic_experiment(task.id, str(transform.id))
        nb_id = insert_agentic_notebook(task.id, str(transform.id))

        # Get dependents
        status_code, dependents = client.get_transform_dependents(transform.id)
        assert status_code == 200
        assert dependents["continuous_evals"] == []
        assert len(dependents["agentic_experiments"]) == 1
        assert dependents["agentic_experiments"][0]["id"] == exp_id
        assert dependents["agentic_experiments"][0]["name"] == "test_experiment"
        assert len(dependents["agentic_notebooks"]) == 1
        assert dependents["agentic_notebooks"][0]["id"] == nb_id
        assert dependents["agentic_notebooks"][0]["name"] == "test_notebook"
    finally:
        if nb_id:
            delete_db_row(DatabaseAgenticNotebook, nb_id)
        if exp_id:
            delete_db_row(DatabaseAgenticExperiment, exp_id)
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_get_transform_dependents_nonexistent_transform(
    client: GenaiEngineTestClientBase,
) -> None:
    """Test getting dependents for a nonexistent transform returns 404."""
    transform_id = str(uuid.uuid4())

    # Getting dependents for a nonexistent transform returns a 404 error
    status_code, error = client.get_transform_dependents(transform_id)
    assert status_code == 404
    assert f"transform {transform_id} not found" in error.get("detail", "").lower()


@pytest.mark.unit_tests
def test_delete_transform_blocked_by_continuous_eval(
    client: GenaiEngineTestClientBase,
    transform_definition: dict,
) -> None:
    """Test deleting a transform returns 409 when a continuous eval depends on it."""
    # Create a task
    status_code, task = client.create_task(
        name="test_delete_blocked_ce", is_agentic=True
    )
    assert status_code == 200

    try:
        # Create a transform
        status_code, transform = client.create_transform(
            task_id=task.id,
            name="test_transform",
            definition=transform_definition,
        )
        assert status_code == 200

        # Create an LLM eval
        status_code, llm_eval = create_test_llm_eval(client, task.id)
        assert status_code == 200

        # Create a continuous eval referencing the transform
        status_code, ce = create_continuous_eval_for_transform(
            client, task.id, str(transform.id), llm_eval.name, llm_eval.version
        )
        assert status_code == 200

        # Attempt to delete the transform
        status_code, error = client.delete_transform(transform.id)
        assert status_code == 409

        detail = error["detail"]
        assert "dependents" in detail
        assert len(detail["dependents"]["continuous_evals"]) == 1
        assert detail["dependents"]["continuous_evals"][0]["id"] == str(ce.id)
    finally:
        client.delete_continuous_eval(ce.id)
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_delete_transform_blocked_by_experiment_and_notebook(
    client: GenaiEngineTestClientBase,
    transform_definition: dict,
) -> None:
    """Test deleting a transform returns 409 when agentic resources depend on it."""
    # Create a task
    status_code, task = client.create_task(
        name="test_delete_blocked_exp_nb", is_agentic=True
    )
    assert status_code == 200

    exp_id = None
    nb_id = None
    try:
        # Create a transform
        status_code, transform = client.create_transform(
            task_id=task.id,
            name="test_transform",
            definition=transform_definition,
        )
        assert status_code == 200

        # Insert agentic experiment and notebook referencing the transform
        exp_id = insert_agentic_experiment(task.id, str(transform.id))
        nb_id = insert_agentic_notebook(task.id, str(transform.id))

        # Attempt to delete the transform
        status_code, error = client.delete_transform(transform.id)
        assert status_code == 409

        detail = error["detail"]
        assert "dependents" in detail
        assert len(detail["dependents"]["agentic_experiments"]) == 1
        assert detail["dependents"]["agentic_experiments"][0]["id"] == exp_id
        assert len(detail["dependents"]["agentic_notebooks"]) == 1
        assert detail["dependents"]["agentic_notebooks"][0]["id"] == nb_id
    finally:
        if nb_id:
            delete_db_row(DatabaseAgenticNotebook, nb_id)
        if exp_id:
            delete_db_row(DatabaseAgenticExperiment, exp_id)
        client.delete_task(task.id)
