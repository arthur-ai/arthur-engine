import pytest
from arthur_common.models.enums import PaginationSortMethod

from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.mark.unit_tests
def test_datasets_query(client: GenaiEngineTestClientBase) -> None:
    """Comprehensive test for datasets query endpoint with multiple test cases."""

    # Create test datasets once at the beginning
    dataset1_name = "Test Dataset One"
    dataset2_name = "Test Dataset Two"
    dataset3_name = "Another Dataset"

    status_code, dataset1 = client.create_dataset(
        name=dataset1_name,
        description="First test dataset",
        metadata={
            "type": "test",
        },
    )
    assert status_code == 200

    status_code, dataset2 = client.create_dataset(
        name=dataset2_name,
        description="Second test dataset",
        metadata={
            "type": "test",
        },
    )
    assert status_code == 200

    status_code, dataset3 = client.create_dataset(
        name=dataset3_name,
        description="Third test dataset",
        metadata={
            "type": "production",
        },
    )
    assert status_code == 200

    # Test Case 1: Basic functionality without filters
    # Test basic search without filters - should return all datasets
    status_code, response = client.search_datasets()
    assert status_code == 200
    assert response.count >= 3
    assert len(response.datasets) >= 3

    # Verify all created datasets are in the response
    dataset_ids = {d.id for d in response.datasets}
    assert dataset1.id in dataset_ids
    assert dataset2.id in dataset_ids
    assert dataset3.id in dataset_ids

    # Test Case 2: Name-based filtering
    # Test case insensitive search
    status_code, response = client.search_datasets(dataset_name="test dataset")
    assert status_code == 200
    assert response.count == 2

    # Test no matches
    status_code, response = client.search_datasets(
        dataset_name="NonExistentDataset",
    )
    assert status_code == 200
    assert response.count == 0
    assert len(response.datasets) == 0

    # Test Case 3: ID-based filtering
    # Test multiple IDs filter
    status_code, response = client.search_datasets(
        dataset_ids=[str(dataset1.id), str(dataset2.id)],
    )
    assert status_code == 200
    assert response.count == 2
    assert len(response.datasets) == 2
    returned_ids = {d.id for d in response.datasets}
    assert dataset1.id in returned_ids
    assert dataset2.id in returned_ids

    # Test non-existent ID
    status_code, response = client.search_datasets(
        dataset_ids=["00000000-0000-0000-0000-000000000000"],
    )
    assert status_code == 200
    assert response.count == 0
    assert len(response.datasets) == 0

    # Test Case 4: Pagination functionality
    # Test page size
    status_code, response = client.search_datasets(page_size=2)
    assert status_code == 200
    assert len(response.datasets) == 2
    assert response.count >= 3

    # Test page navigation
    status_code, response_page1 = client.search_datasets(page=0, page_size=2)
    assert status_code == 200
    assert len(response_page1.datasets) == 2

    status_code, response_page2 = client.search_datasets(page=1, page_size=2)
    assert status_code == 200
    # there are only 3 datasets, so the last page is only half ful
    assert len(response_page2.datasets) == 1

    # Test Case 5: Sorting functionality
    status_code, response_desc = client.search_datasets(
        sort=PaginationSortMethod.DESCENDING,
    )
    assert status_code == 200
    assert len(response_desc.datasets) >= 3

    # Verify that the order is descending (newest first) based on created_at
    for i in range(len(response_desc.datasets) - 1):
        assert (
            response_desc.datasets[i].created_at
            >= response_desc.datasets[i + 1].created_at
        )
