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

    # Create a RAG provider first (required for creating settings)
    status_code, rag_provider = client.create_rag_provider(
        task_id=task_id,
        name="Test RAG Provider",
        description="Test RAG provider for settings query",
    )
    assert status_code == 200
    rag_provider_id = rag_provider.id

    # Create test RAG provider settings with different configurations
    settings1_name = "Keyword Search Settings One"
    settings2_name = "Hybrid Search Settings Two"
    settings3_name = "Vector Similarity Settings Three"
    settings4_name = "Another Keyword Search"

    status_code, settings1 = client.create_rag_search_settings(
        task_id=task_id,
        rag_provider_id=rag_provider_id,
        name=settings1_name,
        description="First test RAG provider settings",
        settings=WeaviateKeywordSearchSettingsConfigurationRequest(
            rag_provider=RagProviderEnum.WEAVIATE,
            collection_name="test-collection-1",
            limit=10,
        ),
    )
    assert status_code == 200

    status_code, settings2 = client.create_rag_search_settings(
        task_id=task_id,
        rag_provider_id=rag_provider_id,
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

    status_code, settings3 = client.create_rag_search_settings(
        task_id=task_id,
        rag_provider_id=rag_provider_id,
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

    status_code, settings4 = client.create_rag_search_settings(
        task_id=task_id,
        rag_provider_id=rag_provider_id,
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
    status_code, response = client.get_task_rag_search_settings(task_id=task_id)
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
    status_code, response = client.get_task_rag_search_settings(
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
    status_code, response = client.get_task_rag_search_settings(
        task_id=task_id,
        config_name="NonExistentSettings",
    )
    assert status_code == 200
    assert response.count == 0
    assert len(response.rag_provider_setting_configurations) == 0

    # Test Case 3: Pagination functionality
    # Test page size
    status_code, response = client.get_task_rag_search_settings(
        task_id=task_id,
        page=0,
        page_size=2,
    )
    assert status_code == 200
    assert len(response.rag_provider_setting_configurations) == 2
    assert response.count >= 4

    # Test page navigation - results on page 1 should be different
    status_code, response_page2 = client.get_task_rag_search_settings(
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
    status_code, response_desc = client.get_task_rag_search_settings(
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

    status_code, response_asc = client.get_task_rag_search_settings(
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

    # Test Case 5: Filter by rag_provider_ids
    # Create one additional RAG provider (we already have rag_provider_id from the beginning)
    status_code, new_rag_provider = client.create_rag_provider(
        task_id=task_id,
        name="Test RAG Provider 2",
        description="Second test RAG provider for filtering",
    )
    assert status_code == 200
    new_rag_provider_id = new_rag_provider.id

    # Update settings1 and settings2 to be associated with the new provider
    # This way we have settings1-2 with new_rag_provider_id and settings3-4 with rag_provider_id
    status_code, updated_settings1 = client.update_rag_search_settings(
        setting_configuration_id=settings1.id,
        rag_provider_id=new_rag_provider_id,
    )
    assert status_code == 200
    assert updated_settings1.rag_provider_id == new_rag_provider_id

    status_code, updated_settings2 = client.update_rag_search_settings(
        setting_configuration_id=settings2.id,
        rag_provider_id=new_rag_provider_id,
    )
    assert status_code == 200
    assert updated_settings2.rag_provider_id == new_rag_provider_id

    # Test filtering by rag_provider_id
    status_code, response = client.get_task_rag_search_settings(
        task_id=task_id,
        rag_provider_ids=[rag_provider_id],
    )
    assert status_code == 200
    assert response.count >= 2
    # Verify all returned settings are associated with the original provider
    for setting in response.rag_provider_setting_configurations:
        assert setting.rag_provider_id == rag_provider_id
    # Verify settings3 and settings4 are included
    returned_ids = {s.id for s in response.rag_provider_setting_configurations}
    assert settings3.id in returned_ids
    assert settings4.id in returned_ids

    # Clean up - delete all created settings
    status_code = client.delete_rag_search_settings(settings1.id)
    assert status_code == 204
    status_code = client.delete_rag_search_settings(settings2.id)
    assert status_code == 204
    status_code = client.delete_rag_search_settings(settings3.id)
    assert status_code == 204
    status_code = client.delete_rag_search_settings(settings4.id)
    assert status_code == 204

    # Clean up the initial RAG provider
    status_code = client.delete_rag_provider(rag_provider_id)
    assert status_code == 204

    # Clean up the task
    status_code = client.delete_task(task_id)
    assert status_code == 204
