from uuid import uuid4

import pytest
from arthur_common.models.enums import PaginationSortMethod

from schemas.enums import RagProviderEnum
from schemas.request_schemas import (
    WeaviateKeywordSearchSettingsConfigurationRequest,
)
from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.mark.unit_tests
def test_get_rag_search_setting_configuration_versions(
    client: GenaiEngineTestClientBase,
) -> None:
    """Test the get_rag_search_setting_configuration_versions endpoint with various filters."""
    # First create a task to associate the RAG provider settings with
    status_code, task = client.create_task(
        name="Test Task for RAG Provider Versions Query",
    )
    assert status_code == 200
    task_id = task.id

    # Create a RAG provider first
    status_code, rag_provider = client.create_rag_provider(
        task_id=task_id,
        name="Test RAG Provider",
        description="Test RAG provider for versions query",
    )
    assert status_code == 200
    rag_provider_id = rag_provider.id

    # Create initial RAG search settings
    settings_name = "My Test RAG Provider Settings"
    collection_name = "test-collection"
    limit = 10
    tags_v1 = ["tag1", "tag2", "production"]

    status_code, created_settings = client.create_rag_search_settings(
        task_id=task_id,
        rag_provider_id=rag_provider_id,
        name=settings_name,
        tags=tags_v1,
        settings=WeaviateKeywordSearchSettingsConfigurationRequest(
            rag_provider=RagProviderEnum.WEAVIATE,
            collection_name=collection_name,
            limit=limit,
        ),
    )
    assert status_code == 200
    setting_configuration_id = created_settings.id

    # Create version 2
    tags_v2 = ["tag3", "tag4", "staging"]
    limit_v2 = 15

    status_code, version_2 = client.create_rag_search_settings_version(
        setting_configuration_id=setting_configuration_id,
        settings=WeaviateKeywordSearchSettingsConfigurationRequest(
            rag_provider=RagProviderEnum.WEAVIATE,
            collection_name=collection_name,
            limit=limit_v2,
        ),
        tags=tags_v2,
    )
    assert status_code == 200
    assert version_2.version_number == 2

    # Create version 3
    tags_v3 = ["tag5", "development"]
    limit_v3 = 20

    status_code, version_3 = client.create_rag_search_settings_version(
        setting_configuration_id=setting_configuration_id,
        settings=WeaviateKeywordSearchSettingsConfigurationRequest(
            rag_provider=RagProviderEnum.WEAVIATE,
            collection_name=collection_name,
            limit=limit_v3,
        ),
        tags=tags_v3,
    )
    assert status_code == 200
    assert version_3.version_number == 3

    # test get all versions - default pagination
    status_code, all_versions = client.get_rag_search_setting_configuration_versions(
        setting_configuration_id=setting_configuration_id,
    )
    assert status_code == 200
    assert all_versions.count == 3
    assert len(all_versions.rag_provider_setting_configurations) == 3
    # Should be sorted by version number descending by default
    assert all_versions.rag_provider_setting_configurations[0].version_number == 3
    assert all_versions.rag_provider_setting_configurations[1].version_number == 2
    assert all_versions.rag_provider_setting_configurations[2].version_number == 1

    # test get all versions - ascending sort
    status_code, ascending_versions = (
        client.get_rag_search_setting_configuration_versions(
            setting_configuration_id=setting_configuration_id,
            sort=PaginationSortMethod.ASCENDING,
        )
    )
    assert status_code == 200
    assert ascending_versions.count == 3
    assert len(ascending_versions.rag_provider_setting_configurations) == 3
    # Should be sorted by version number ascending
    assert ascending_versions.rag_provider_setting_configurations[0].version_number == 1
    assert ascending_versions.rag_provider_setting_configurations[1].version_number == 2
    assert ascending_versions.rag_provider_setting_configurations[2].version_number == 3

    # test pagination - first page
    status_code, page_1 = client.get_rag_search_setting_configuration_versions(
        setting_configuration_id=setting_configuration_id,
        page=0,
        page_size=2,
    )
    assert status_code == 200
    assert page_1.count == 3
    assert len(page_1.rag_provider_setting_configurations) == 2
    assert page_1.rag_provider_setting_configurations[0].version_number == 3
    assert page_1.rag_provider_setting_configurations[1].version_number == 2

    # test pagination - second page
    status_code, page_2 = client.get_rag_search_setting_configuration_versions(
        setting_configuration_id=setting_configuration_id,
        page=1,
        page_size=2,
    )
    assert status_code == 200
    assert page_2.count == 3
    assert len(page_2.rag_provider_setting_configurations) == 1
    assert page_2.rag_provider_setting_configurations[0].version_number == 1

    # test filter by tags - should return versions with matching tags
    status_code, tagged_versions = client.get_rag_search_setting_configuration_versions(
        setting_configuration_id=setting_configuration_id,
        tags=["tag1"],
    )
    assert status_code == 200
    assert tagged_versions.count == 1  # version 1 has tag1
    version_numbers = [
        v.version_number for v in tagged_versions.rag_provider_setting_configurations
    ]
    assert 1 in version_numbers
    assert 3 not in version_numbers
    assert 2 not in version_numbers

    # test filter by multiple tags - should return versions with any matching tag
    status_code, multi_tag_versions = (
        client.get_rag_search_setting_configuration_versions(
            setting_configuration_id=setting_configuration_id,
            tags=["production", "staging"],
        )
    )
    assert status_code == 200
    assert (
        multi_tag_versions.count == 2
    )  # version 1 has production, version 2 has staging
    version_numbers = [
        v.version_number for v in multi_tag_versions.rag_provider_setting_configurations
    ]
    assert 1 in version_numbers
    assert 2 in version_numbers
    assert 3 not in version_numbers

    # test filter by version_numbers
    status_code, filtered_versions = (
        client.get_rag_search_setting_configuration_versions(
            setting_configuration_id=setting_configuration_id,
            version_numbers=[1, 3],
        )
    )
    assert status_code == 200
    assert filtered_versions.count == 2
    version_numbers = [
        v.version_number for v in filtered_versions.rag_provider_setting_configurations
    ]
    assert 1 in version_numbers
    assert 3 in version_numbers
    assert 2 not in version_numbers

    # test filter by tags and version_numbers together
    status_code, combined_filter_versions = (
        client.get_rag_search_setting_configuration_versions(
            setting_configuration_id=setting_configuration_id,
            tags=["tag1", "tag5"],
            version_numbers=[1, 2],
        )
    )
    assert status_code == 200
    assert combined_filter_versions.count == 1  # Only version 1 matches both filters
    assert (
        combined_filter_versions.rag_provider_setting_configurations[0].version_number
        == 1
    )

    # test filter by non-existent tag
    status_code, no_match_versions = (
        client.get_rag_search_setting_configuration_versions(
            setting_configuration_id=setting_configuration_id,
            tags=["nonexistent"],
        )
    )
    assert status_code == 200
    assert no_match_versions.count == 0
    assert len(no_match_versions.rag_provider_setting_configurations) == 0

    # test for non-existing settings config
    status_code, _ = client.get_rag_search_setting_configuration_versions(
        setting_configuration_id=str(uuid4()),
    )
    assert status_code == 404

    # Clean up
    status_code = client.delete_rag_search_settings(setting_configuration_id)
    assert status_code == 204
    status_code = client.delete_rag_provider(rag_provider_id)
    assert status_code == 204
    status_code = client.delete_task(task_id)
    assert status_code == 204
