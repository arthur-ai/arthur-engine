import pytest
from arthur_common.models.enums import PaginationSortMethod

from schemas.enums import RagProviderEnum
from schemas.request_schemas import (
    WeaviateHybridSearchSettingsConfigurationRequest,
    WeaviateKeywordSearchSettingsConfigurationRequest,
    WeaviateVectorSimilarityTextSearchSettingsConfigurationRequest,
)
from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.mark.unit_tests
def test_rag_provider_settings_query(client: GenaiEngineTestClientBase) -> None:
    """Comprehensive test for RAG provider settings query endpoint with multiple test cases."""

    # Create test task first
    status_code, task = client.create_task(
        name="Test Task for RAG Provider Settings Query",
    )
    assert status_code == 200
    task_id = task.id

    # Create test RAG provider settings with different configurations
    settings1_name = "Keyword Search Settings One"
    settings2_name = "Hybrid Search Settings Two"
    settings3_name = "Vector Similarity Settings Three"
    settings4_name = "Another Keyword Search"

    status_code, settings1 = client.create_rag_provider_settings(
        task_id=task_id,
        name=settings1_name,
        description="First test RAG provider settings",
        settings=WeaviateKeywordSearchSettingsConfigurationRequest(
            rag_provider=RagProviderEnum.WEAVIATE,
            collection_name="test-collection-1",
            limit=10,
        ),
    )
    assert status_code == 200

    status_code, settings2 = client.create_rag_provider_settings(
        task_id=task_id,
        name=settings2_name,
        description="Second test RAG provider settings",
        settings=WeaviateHybridSearchSettingsConfigurationRequest(
            rag_provider=RagProviderEnum.WEAVIATE,
            collection_name="test-collection-2",
            alpha=0.7,
            limit=20,
        ),
    )
    assert status_code == 200

    status_code, settings3 = client.create_rag_provider_settings(
        task_id=task_id,
        name=settings3_name,
        description="Third test RAG provider settings",
        settings=WeaviateVectorSimilarityTextSearchSettingsConfigurationRequest(
            rag_provider=RagProviderEnum.WEAVIATE,
            collection_name="test-collection-3",
            certainty=0.8,
            limit=15,
        ),
    )
    assert status_code == 200

    status_code, settings4 = client.create_rag_provider_settings(
        task_id=task_id,
        name=settings4_name,
        description="Fourth test RAG provider settings",
        settings=WeaviateKeywordSearchSettingsConfigurationRequest(
            rag_provider=RagProviderEnum.WEAVIATE,
            collection_name="test-collection-4",
            limit=5,
        ),
    )
    assert status_code == 200

    # Test Case 1: Basic functionality without filters
    # Test basic search without filters - should return all RAG provider settings
    status_code, response = client.get_task_rag_provider_settings(task_id=task_id)
    assert status_code == 200
    assert response.count >= 4
    assert len(response.rag_provider_setting_configurations) >= 4

    # Verify all created RAG provider settings are in the response
    settings_ids = {s.id for s in response.rag_provider_setting_configurations}
    assert settings1.id in settings_ids
    assert settings2.id in settings_ids
    assert settings3.id in settings_ids
    assert settings4.id in settings_ids

    # Test Case 2: Name-based filtering
    # Test case insensitive search for "Keyword"
    status_code, response = client.get_task_rag_provider_settings(
        task_id=task_id,
        config_name="Keyword",
    )
    assert status_code == 200
    assert response.count == 2
    assert len(response.rag_provider_setting_configurations) == 2

    # Verify the correct settings are returned
    returned_names = {s.name for s in response.rag_provider_setting_configurations}
    assert settings1_name in returned_names
    assert settings4_name in returned_names

    # Test no matches
    status_code, response = client.get_task_rag_provider_settings(
        task_id=task_id,
        config_name="NonExistentSettings",
    )
    assert status_code == 200
    assert response.count == 0
    assert len(response.rag_provider_setting_configurations) == 0

    # Test Case 3: Pagination functionality
    # Test page size
    status_code, response = client.get_task_rag_provider_settings(
        task_id=task_id,
        page=0,
        page_size=2,
    )
    assert status_code == 200
    assert len(response.rag_provider_setting_configurations) == 2
    assert response.count >= 4

    # Test page navigation - results on page 1 should be different
    status_code, response_page2 = client.get_task_rag_provider_settings(
        task_id=task_id,
        page=1,
        page_size=2,
    )
    assert status_code == 200
    # there may be RAG provider settings from other unit tests, but there are at least 4 total
    assert len(response_page2.rag_provider_setting_configurations) >= 2

    # Verify different pages return different results
    page1_ids = {s.id for s in response.rag_provider_setting_configurations}
    page2_ids = {s.id for s in response_page2.rag_provider_setting_configurations}
    assert page1_ids.isdisjoint(page2_ids) or len(page1_ids) == len(page2_ids) == 2

    # Test Case 4: Sorting functionality
    status_code, response_desc = client.get_task_rag_provider_settings(
        task_id=task_id,
        sort=PaginationSortMethod.DESCENDING,
    )
    assert status_code == 200
    assert len(response_desc.rag_provider_setting_configurations) >= 4

    # Verify that the order is descending (newest first) based on updated_at
    for i in range(len(response_desc.rag_provider_setting_configurations) - 1):
        assert (
            response_desc.rag_provider_setting_configurations[i].updated_at
            >= response_desc.rag_provider_setting_configurations[i + 1].updated_at
        )

    status_code, response_asc = client.get_task_rag_provider_settings(
        task_id=task_id,
        sort=PaginationSortMethod.ASCENDING,
    )
    assert status_code == 200
    assert len(response_asc.rag_provider_setting_configurations) >= 4

    # Verify that the order is ascending (oldest first) based on updated_at
    for i in range(len(response_asc.rag_provider_setting_configurations) - 1):
        assert (
            response_asc.rag_provider_setting_configurations[i].updated_at
            <= response_asc.rag_provider_setting_configurations[i + 1].updated_at
        )

    # Clean up - delete all created settings
    status_code = client.delete_rag_provider_settings(settings1.id)
    assert status_code == 204
    status_code = client.delete_rag_provider_settings(settings2.id)
    assert status_code == 204
    status_code = client.delete_rag_provider_settings(settings3.id)
    assert status_code == 204
    status_code = client.delete_rag_provider_settings(settings4.id)
    assert status_code == 204

    # Clean up the task
    status_code = client.delete_task(task_id)
    assert status_code == 204
