import pytest

from schemas.request_schemas import (
    NewDatasetVersionRowColumnItemRequest,
    NewDatasetVersionRowRequest,
    NewDatasetVersionUpdateRowRequest,
)
from tests.clients.base_test_client import GenaiEngineTestClientBase


def _extract_row_data(rows):
    """Helper function to extract name->age mapping from dataset version rows."""
    row_data = {}
    for row in rows:
        name = next(
            (item.column_value for item in row.data if item.column_name == "name"),
            None,
        )
        age = next(
            (item.column_value for item in row.data if item.column_name == "age"),
            None,
        )
        if name:
            row_data[name] = age
    return row_data


@pytest.mark.unit_tests
def test_dataset_versions_basic_functionality(
    client: GenaiEngineTestClientBase,
) -> None:
    # create a dataset
    dataset_name = "Dataset for Versions"
    dataset_description = "dataset for version operations"

    status_code, created_dataset = client.create_dataset(
        name=dataset_name,
        description=dataset_description,
    )
    assert status_code == 200
    assert created_dataset.id is not None

    dataset_id = created_dataset.id

    # Test 1: Create first dataset version with some rows
    row1_data = [
        NewDatasetVersionRowColumnItemRequest(
            column_name="name",
            column_value="John Doe",
        ),
        NewDatasetVersionRowColumnItemRequest(column_name="age", column_value="30"),
    ]
    row2_data = [
        NewDatasetVersionRowColumnItemRequest(
            column_name="name",
            column_value="Jane Smith",
        ),
        NewDatasetVersionRowColumnItemRequest(column_name="age", column_value="25"),
    ]
    row3_data = [
        NewDatasetVersionRowColumnItemRequest(
            column_name="name",
            column_value="Bob Johnson",
        ),
        NewDatasetVersionRowColumnItemRequest(column_name="age", column_value="35"),
    ]

    rows_to_add = [
        NewDatasetVersionRowRequest(data=row1_data),
        NewDatasetVersionRowRequest(data=row2_data),
        NewDatasetVersionRowRequest(data=row3_data),
    ]

    status_code, created_version = client.create_dataset_version(
        dataset_id=dataset_id,
        rows_to_add=rows_to_add,
    )
    assert status_code == 200
    assert created_version.version_number == 1
    assert created_version.dataset_id == dataset_id
    assert created_version.total_count == 3
    assert len(created_version.rows) == 3

    # Test 2: Basic get of the dataset version
    status_code, retrieved_version = client.get_dataset_version(
        dataset_id=dataset_id,
        version_number=1,
    )
    assert status_code == 200
    assert retrieved_version.version_number == 1
    assert retrieved_version.dataset_id == dataset_id
    assert retrieved_version.total_count == 3
    assert len(retrieved_version.rows) == 3
    assert retrieved_version.page == 0  # Default page
    assert retrieved_version.page_size == 10  # Default page size

    # Test 3: Basic Get with pagination (page size less than total rows)
    status_code, paginated_version = client.get_dataset_version(
        dataset_id=dataset_id,
        version_number=1,
        page=0,
        page_size=2,
    )
    assert status_code == 200
    assert paginated_version.version_number == 1
    assert paginated_version.dataset_id == dataset_id
    assert paginated_version.total_count == 3
    assert len(paginated_version.rows) == 2  # Only 2 rows returned due to pagination
    assert paginated_version.page == 0
    assert paginated_version.page_size == 2
    assert paginated_version.total_pages == 2  # 3 rows / 2 per page = 2 pages

    # Test 4: Create second version with comprehensive operations (delete, update, add rows)
    # Store row IDs from version 1 for operations
    row_ids = [row.id for row in created_version.rows]

    # Row to delete (Jane Smith's row - index 1)
    row_to_delete_id = row_ids[1]

    # Row to update (Bob Johnson's row - index 2) - update age
    row_to_update = NewDatasetVersionUpdateRowRequest(
        id=row_ids[2],  # Bob Johnson's row
        data=[
            NewDatasetVersionRowColumnItemRequest(
                column_name="name",
                column_value="Bob Johnson",
            ),
            NewDatasetVersionRowColumnItemRequest(
                column_name="age",
                column_value="36",
            ),  # Updated age
        ],
    )

    # New row to add
    new_row = NewDatasetVersionRowRequest(
        data=[
            NewDatasetVersionRowColumnItemRequest(
                column_name="name",
                column_value="Alice Brown",
            ),
            NewDatasetVersionRowColumnItemRequest(column_name="age", column_value="28"),
        ],
    )

    status_code, version_2 = client.create_dataset_version(
        dataset_id=dataset_id,
        rows_to_delete=[row_to_delete_id],
        rows_to_update=[row_to_update],
        rows_to_add=[new_row],
    )
    assert status_code == 200
    assert version_2.version_number == 2
    assert version_2.total_count == 3  # 3 - 1 (deleted) + 1 (added) = 3
    assert len(version_2.rows) == 3

    # verify the persisted values in version 2
    status_code, retrieved_version_2 = client.get_dataset_version(
        dataset_id=dataset_id,
        version_number=2,
    )
    assert status_code == 200
    assert retrieved_version_2.version_number == 2
    assert retrieved_version_2.total_count == 3
    assert len(retrieved_version_2.rows) == 3

    # Verify the rows in version 2 by checking their data content
    row_data = _extract_row_data(retrieved_version_2.rows)

    # Verify expected data is present and correct
    assert row_data["John Doe"] == "30"  # Unchanged
    assert row_data["Bob Johnson"] == "36"  # Updated age
    assert row_data["Alice Brown"] == "28"  # New row
    assert "Jane Smith" not in row_data  # Deleted

    # Verify version 1 is still intact (unchanged)
    status_code, retrieved_version_1 = client.get_dataset_version(
        dataset_id=dataset_id,
        version_number=1,
    )
    assert status_code == 200
    assert retrieved_version_1.version_number == 1
    assert retrieved_version_1.total_count == 3
    assert len(retrieved_version_1.rows) == 3

    # Verify version 1 still has original data
    version_1_data = _extract_row_data(retrieved_version_1.rows)

    assert version_1_data["Jane Smith"] == "25"  # Still present in v1
    assert version_1_data["Bob Johnson"] == "35"  # Original age in v1

    # test fetching all versions
    status_code, versions_response = client.get_dataset_versions(created_dataset.id)
    assert status_code == 200
    assert versions_response.total_count == 2
    assert len(versions_response.versions) == 2
    # default sort is latest version first
    last_version = versions_response.versions[0]
    assert last_version.version_number == 2
    assert versions_response.page_size == 10
    assert versions_response.page == 0
    assert versions_response.total_pages == 1

    # test fetching only the latest version
    status_code, versions_response = client.get_dataset_versions(
        created_dataset.id,
        latest_version_only=True,
    )
    assert status_code == 200
    assert versions_response.total_count == 1
    assert len(versions_response.versions) == 1
    last_version = versions_response.versions[0]
    assert last_version.version_number == 2
    assert versions_response.page_size == 10

    # test pagination
    status_code, versions_response = client.get_dataset_versions(
        created_dataset.id,
        page=1,
        page_size=1,
    )
    assert status_code == 200
    assert versions_response.total_count == 2
    assert len(versions_response.versions) == 1
    # fetched the second page of versions, sorted from highest version number to lowest
    last_version = versions_response.versions[0]
    assert last_version.version_number == 1
    assert versions_response.page_size == 1
    assert versions_response.page == 1
    assert versions_response.total_pages == 2

    # Test 5: Verify deleting dataset with versions doesn't result in an error
    status_code = client.delete_dataset(dataset_id)
    assert status_code == 204

    # Test 6: Verify getting dataset version for deleted dataset returns error code
    status_code, _ = client.get_dataset_version(
        dataset_id=dataset_id,
        version_number=1,
    )
    assert status_code == 404
