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


@pytest.fixture
def updated_definition() -> dict:
    return {
        "variables": [
            {
                "variable_name": "updated_variable",
                "span_name": "updated-span",
                "attribute_path": "attributes.updated",
                "fallback": "fallback_value",
            },
        ],
    }


@pytest.mark.unit_tests
def test_create_transform_creates_initial_version(
    client: GenaiEngineTestClientBase,
    transform_definition: dict,
) -> None:
    """Test that creating a transform automatically creates version 1."""
    status_code, task = client.create_task(
        name="test_version_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        status_code, transform = client.create_transform(
            task_id=task.id,
            name="test_transform",
            definition=transform_definition,
        )
        assert status_code == 200

        status_code, versions = client.list_transform_versions(str(transform.id))
        assert status_code == 200
        assert versions.count == 1
        assert len(versions.versions) == 1
        assert versions.versions[0].version_number == 1
        assert versions.versions[0].transform_id == transform.id
        assert versions.versions[0].task_id == task.id
        assert versions.versions[0].config_snapshot == transform_definition
    finally:
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_update_transform_creates_new_version(
    client: GenaiEngineTestClientBase,
    transform_definition: dict,
    updated_definition: dict,
) -> None:
    """Test that updating a transform creates a new version snapshot."""
    status_code, task = client.create_task(
        name="test_version_update_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        status_code, transform = client.create_transform(
            task_id=task.id,
            name="test_transform",
            definition=transform_definition,
        )
        assert status_code == 200

        status_code, _ = client.update_transform(
            transform_id=str(transform.id),
            definition=updated_definition,
        )
        assert status_code == 200

        status_code, versions = client.list_transform_versions(str(transform.id))
        assert status_code == 200
        assert versions.count == 2
        # Ordered descending by version_number
        assert versions.versions[0].version_number == 2
        assert versions.versions[0].config_snapshot == updated_definition
        assert versions.versions[1].version_number == 1
        assert versions.versions[1].config_snapshot == transform_definition
    finally:
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_list_versions_nonexistent_transform(
    client: GenaiEngineTestClientBase,
) -> None:
    """Test listing versions for a nonexistent transform returns 404."""
    transform_id = str(uuid.uuid4())
    status_code, error = client.list_transform_versions(transform_id)
    assert status_code == 404
    assert f"transform {transform_id} not found" in error.get("detail", "").lower()


@pytest.mark.unit_tests
def test_get_transform_version_success(
    client: GenaiEngineTestClientBase,
    transform_definition: dict,
) -> None:
    """Test fetching a specific version snapshot by ID."""
    status_code, task = client.create_task(
        name="test_get_version_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        status_code, transform = client.create_transform(
            task_id=task.id,
            name="test_transform",
            definition=transform_definition,
        )
        assert status_code == 200

        # Get the list to find the version ID
        status_code, versions = client.list_transform_versions(str(transform.id))
        assert status_code == 200
        assert versions.count == 1
        version_id = str(versions.versions[0].id)

        status_code, version = client.get_transform_version(
            transform_id=str(transform.id),
            version_id=version_id,
        )
        assert status_code == 200
        assert str(version.id) == version_id
        assert version.version_number == 1
        assert version.config_snapshot == transform_definition
        assert version.transform_id == transform.id
        assert version.task_id == task.id
    finally:
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_get_transform_version_wrong_transform(
    client: GenaiEngineTestClientBase,
    transform_definition: dict,
) -> None:
    """Test that a version cannot be fetched using a different transform's ID."""
    status_code, task = client.create_task(
        name="test_wrong_transform_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        status_code, transform1 = client.create_transform(
            task_id=task.id,
            name="test_transform_1",
            definition=transform_definition,
        )
        assert status_code == 200

        status_code, transform2 = client.create_transform(
            task_id=task.id,
            name="test_transform_2",
            definition=transform_definition,
        )
        assert status_code == 200

        # Get a version from transform1
        status_code, versions = client.list_transform_versions(str(transform1.id))
        assert status_code == 200
        version_id = str(versions.versions[0].id)

        # Try to access it using transform2's ID — should 404
        status_code, error = client.get_transform_version(
            transform_id=str(transform2.id),
            version_id=version_id,
        )
        assert status_code == 404
    finally:
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_get_transform_version_nonexistent(
    client: GenaiEngineTestClientBase,
    transform_definition: dict,
) -> None:
    """Test that fetching a nonexistent version ID returns 404."""
    status_code, task = client.create_task(
        name="test_nonexistent_version_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        status_code, transform = client.create_transform(
            task_id=task.id,
            name="test_transform",
            definition=transform_definition,
        )
        assert status_code == 200

        nonexistent_version_id = str(uuid.uuid4())
        status_code, error = client.get_transform_version(
            transform_id=str(transform.id),
            version_id=nonexistent_version_id,
        )
        assert status_code == 404
    finally:
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_restore_transform_version(
    client: GenaiEngineTestClientBase,
    transform_definition: dict,
    updated_definition: dict,
) -> None:
    """Test that restoring a version applies the snapshot and creates a new version."""
    status_code, task = client.create_task(
        name="test_restore_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        status_code, transform = client.create_transform(
            task_id=task.id,
            name="test_transform",
            definition=transform_definition,
        )
        assert status_code == 200

        # Update to create version 2
        status_code, _ = client.update_transform(
            transform_id=str(transform.id),
            definition=updated_definition,
        )
        assert status_code == 200

        # Get version 1's ID
        status_code, versions = client.list_transform_versions(str(transform.id))
        assert status_code == 200
        assert versions.count == 2
        # Descending order: version 2 first, version 1 second
        v1_id = str(versions.versions[1].id)

        # Restore version 1
        status_code, restored_transform = client.restore_transform_version(
            transform_id=str(transform.id),
            version_id=v1_id,
        )
        assert status_code == 200
        assert restored_transform.id == transform.id
        assert restored_transform.definition.model_dump() == transform_definition

        # Should now have 3 versions
        status_code, versions = client.list_transform_versions(str(transform.id))
        assert status_code == 200
        assert versions.count == 3
        assert versions.versions[0].version_number == 3
        assert versions.versions[0].config_snapshot == transform_definition
    finally:
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_restore_nonexistent_version(
    client: GenaiEngineTestClientBase,
    transform_definition: dict,
) -> None:
    """Test that restoring a nonexistent version returns 404."""
    status_code, task = client.create_task(
        name="test_restore_nonexistent_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        status_code, transform = client.create_transform(
            task_id=task.id,
            name="test_transform",
            definition=transform_definition,
        )
        assert status_code == 200

        nonexistent_version_id = str(uuid.uuid4())
        status_code, error = client.restore_transform_version(
            transform_id=str(transform.id),
            version_id=nonexistent_version_id,
        )
        assert status_code == 404
    finally:
        client.delete_task(task.id)


@pytest.mark.unit_tests
def test_update_name_only_creates_new_version(
    client: GenaiEngineTestClientBase,
    transform_definition: dict,
) -> None:
    """Test that updating only the name still creates a new version."""
    status_code, task = client.create_task(
        name="test_name_update_task",
        is_agentic=True,
    )
    assert status_code == 200

    try:
        status_code, transform = client.create_transform(
            task_id=task.id,
            name="test_transform",
            definition=transform_definition,
        )
        assert status_code == 200

        status_code, _ = client.update_transform(
            transform_id=str(transform.id),
            name="new_name",
        )
        assert status_code == 200

        status_code, versions = client.list_transform_versions(str(transform.id))
        assert status_code == 200
        assert versions.count == 2
        # Both versions should have same config_snapshot (definition unchanged)
        assert versions.versions[0].config_snapshot == transform_definition
        assert versions.versions[1].config_snapshot == transform_definition
    finally:
        client.delete_task(task.id)
