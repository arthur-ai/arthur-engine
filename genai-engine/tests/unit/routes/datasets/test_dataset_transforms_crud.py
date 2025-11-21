import pytest

from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.mark.unit_tests
def test_user_story_transforms_crud(client: GenaiEngineTestClientBase) -> None:
    """Test the basic happy path for dataset transform CRUD operations: create, get, list, update, delete."""
    # First create a dataset to attach transforms to
    dataset_name = "Test Dataset for Transforms"
    dataset_description = "Dataset to test transform operations"

    status_code, created_dataset = client.create_dataset(
        name=dataset_name,
        description=dataset_description,
    )
    assert status_code == 200
    assert created_dataset.id is not None

    try:
        # Test transform creation
        transform_name = "Extract SQL Queries"
        transform_description = "Extracts SQL queries from RAG spans"
        transform_definition = {
            "columns": [
                {
                    "column_name": "sqlQuery",
                    "span_name": "rag-retrieval-savedQueries",
                    "attribute_path": "attributes.input.value.sqlQuery",
                    "fallback": None,
                },
                {
                    "column_name": "trace_id",
                    "span_name": "rag-retrieval-savedQueries",
                    "attribute_path": "traceId",
                    "fallback": None,
                },
            ],
        }

        status_code, created_transform = client.create_transform(
            dataset_id=created_dataset.id,
            name=transform_name,
            description=transform_description,
            definition=transform_definition,
        )
        assert status_code == 200
        assert created_transform.id is not None
        assert created_transform.dataset_id == created_dataset.id
        assert created_transform.name == transform_name
        assert created_transform.description == transform_description
        assert created_transform.definition == transform_definition
        assert created_transform.created_at is not None
        assert created_transform.updated_at is not None

        # Test transform fetch
        status_code, retrieved_transform = client.get_transform(
            dataset_id=created_dataset.id,
            transform_id=created_transform.id,
        )
        assert status_code == 200
        assert retrieved_transform.id == created_transform.id
        assert retrieved_transform.name == transform_name
        assert retrieved_transform.description == transform_description
        assert retrieved_transform.definition == transform_definition

        # Test list transforms (should have 1)
        status_code, transforms_list = client.list_transforms(created_dataset.id)
        assert status_code == 200
        assert len(transforms_list.transforms) == 1
        assert transforms_list.transforms[0].id == created_transform.id

        # Create a second transform
        transform_name_2 = "Extract Token Costs"
        transform_definition_2 = {
            "columns": [
                {
                    "column_name": "token_count",
                    "span_name": "llm: 'gpt-4.1'",
                    "attribute_path": "attributes.llm.token_cost",
                    "fallback": 0,
                },
            ],
        }

        status_code, created_transform_2 = client.create_transform(
            dataset_id=created_dataset.id,
            name=transform_name_2,
            definition=transform_definition_2,
        )
        assert status_code == 200
        assert created_transform_2.id is not None
        assert created_transform_2.id != created_transform.id

        # Test list transforms (should now have 2)
        status_code, transforms_list = client.list_transforms(created_dataset.id)
        assert status_code == 200
        assert len(transforms_list.transforms) == 2
        transform_ids = {t.id for t in transforms_list.transforms}
        assert created_transform.id in transform_ids
        assert created_transform_2.id in transform_ids

        # Test transform update
        updated_name = "Updated Transform Name"
        updated_description = "Updated description"
        updated_definition = {
            "columns": [
                {
                    "column_name": "updated_column",
                    "span_name": "updated-span",
                    "attribute_path": "attributes.updated",
                    "fallback": "default",
                },
            ],
        }

        status_code, updated_transform = client.update_transform(
            dataset_id=created_dataset.id,
            transform_id=created_transform.id,
            name=updated_name,
            description=updated_description,
            definition=updated_definition,
        )
        assert status_code == 200
        assert updated_transform.id == created_transform.id
        assert updated_transform.name == updated_name
        assert updated_transform.description == updated_description
        assert updated_transform.definition == updated_definition
        assert updated_transform.updated_at > updated_transform.created_at

        # Validate updates persisted on fetch
        status_code, final_transform = client.get_transform(
            dataset_id=created_dataset.id,
            transform_id=created_transform.id,
        )
        assert status_code == 200
        assert final_transform.name == updated_name
        assert final_transform.description == updated_description
        assert final_transform.definition == updated_definition

        # Test partial update (only name)
        partial_updated_name = "Partially Updated Name"
        status_code, partial_updated_transform = client.update_transform(
            dataset_id=created_dataset.id,
            transform_id=created_transform.id,
            name=partial_updated_name,
        )
        assert status_code == 200
        assert partial_updated_transform.name == partial_updated_name
        assert partial_updated_transform.description == updated_description  # unchanged
        assert partial_updated_transform.definition == updated_definition  # unchanged

        # Delete first transform
        status_code = client.delete_transform(
            dataset_id=created_dataset.id,
            transform_id=created_transform.id,
        )
        assert status_code == 204

        # Verify transform was deleted
        status_code, _ = client.get_transform(
            dataset_id=created_dataset.id,
            transform_id=created_transform.id,
        )
        assert status_code == 404

        # List should now only have the second transform
        status_code, transforms_list = client.list_transforms(created_dataset.id)
        assert status_code == 200
        assert len(transforms_list.transforms) == 1
        assert transforms_list.transforms[0].id == created_transform_2.id

        # Delete second transform
        status_code = client.delete_transform(
            dataset_id=created_dataset.id,
            transform_id=created_transform_2.id,
        )
        assert status_code == 204

        # List should now be empty
        status_code, transforms_list = client.list_transforms(created_dataset.id)
        assert status_code == 200
        assert len(transforms_list.transforms) == 0

        # Fail to delete transform that doesn't exist
        status_code = client.delete_transform(
            dataset_id=created_dataset.id,
            transform_id=created_transform.id,
        )
        assert status_code == 404

    finally:
        # Clean up: delete the dataset
        client.delete_dataset(created_dataset.id)


@pytest.mark.unit_tests
def test_transform_unique_name_constraint(client: GenaiEngineTestClientBase) -> None:
    """Test that transform names must be unique within a dataset."""
    # Create a dataset
    status_code, created_dataset = client.create_dataset(
        name="Test Dataset for Name Uniqueness",
        description="Testing unique constraint",
    )
    assert status_code == 200

    try:
        # Create first transform
        transform_name = "Duplicate Name Test"
        transform_definition = {
            "columns": [
                {
                    "column_name": "test_column",
                    "span_name": "test-span",
                    "attribute_path": "attributes.test",
                    "fallback": None,
                },
            ],
        }

        status_code, transform_1 = client.create_transform(
            dataset_id=created_dataset.id,
            name=transform_name,
            definition=transform_definition,
        )
        assert status_code == 200

        # Try to create another transform with the same name (should fail with 409 Conflict)
        status_code, _ = client.create_transform(
            dataset_id=created_dataset.id,
            name=transform_name,
            definition=transform_definition,
        )
        assert status_code == 409  # Conflict - unique constraint violation

    finally:
        # Clean up
        client.delete_dataset(created_dataset.id)


@pytest.mark.unit_tests
def test_transform_update_unique_name_constraint(
    client: GenaiEngineTestClientBase,
) -> None:
    """Test that updating a transform to a duplicate name fails."""
    # Create a dataset
    status_code, created_dataset = client.create_dataset(
        name="Test Dataset for Update Name Uniqueness",
        description="Testing unique constraint on update",
    )
    assert status_code == 200

    try:
        # Create first transform
        transform_definition = {
            "columns": [
                {
                    "column_name": "test_column",
                    "span_name": "test-span",
                    "attribute_path": "attributes.test",
                    "fallback": None,
                },
            ],
        }

        status_code, transform_1 = client.create_transform(
            dataset_id=created_dataset.id,
            name="Transform 1",
            definition=transform_definition,
        )
        assert status_code == 200

        # Create second transform
        status_code, transform_2 = client.create_transform(
            dataset_id=created_dataset.id,
            name="Transform 2",
            definition=transform_definition,
        )
        assert status_code == 200

        # Try to update transform_2 to have the same name as transform_1 (should fail)
        status_code, _ = client.update_transform(
            dataset_id=created_dataset.id,
            transform_id=transform_2.id,
            name="Transform 1",  # Duplicate name
        )
        assert status_code == 409  # Conflict - unique constraint violation

    finally:
        # Clean up
        client.delete_dataset(created_dataset.id)


@pytest.mark.unit_tests
def test_transform_cascade_delete_with_dataset(
    client: GenaiEngineTestClientBase,
) -> None:
    """Test that transforms are automatically deleted when their parent dataset is deleted."""
    # Create a dataset
    status_code, created_dataset = client.create_dataset(
        name="Test Dataset for Cascade Delete",
        description="Testing cascade deletion",
    )
    assert status_code == 200

    # Create a transform
    transform_definition = {
        "columns": [
            {
                "column_name": "test_column",
                "span_name": "test-span",
                "attribute_path": "attributes.test",
                "fallback": None,
            },
        ],
    }

    status_code, created_transform = client.create_transform(
        dataset_id=created_dataset.id,
        name="Transform to be cascade deleted",
        definition=transform_definition,
    )
    assert status_code == 200

    # Delete the dataset
    status_code = client.delete_dataset(created_dataset.id)
    assert status_code == 204

    # Verify transform is also gone (accessing it should fail)
    status_code, _ = client.get_transform(
        dataset_id=created_dataset.id,
        transform_id=created_transform.id,
    )
    assert status_code == 404


@pytest.mark.unit_tests
def test_transform_operations_on_nonexistent_dataset(
    client: GenaiEngineTestClientBase,
) -> None:
    """Test that transform operations fail gracefully on non-existent datasets."""
    fake_dataset_id = "00000000-0000-0000-0000-000000000000"
    transform_definition = {
        "columns": [
            {
                "column_name": "test_column",
                "span_name": "test-span",
                "attribute_path": "attributes.test",
                "fallback": None,
            },
        ],
    }

    # Try to create transform on non-existent dataset
    status_code, _ = client.create_transform(
        dataset_id=fake_dataset_id,
        name="Test Transform",
        definition=transform_definition,
    )
    assert status_code == 404

    # Try to list transforms on non-existent dataset
    status_code, _ = client.list_transforms(fake_dataset_id)
    assert status_code == 404
