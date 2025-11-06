from uuid import uuid4

import pytest

from schemas.enums import RagProviderEnum
from schemas.request_schemas import (
    WeaviateKeywordSearchSettingsConfigurationRequest,
)
from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.mark.unit_tests
def test_rag_provider_versions_crud(client: GenaiEngineTestClientBase) -> None:
    """Test the basic happy path for rag provider settings version CRUD operations: create, get, delete."""
    # First create a task to associate the RAG provider settings with
    status_code, task = client.create_task(name="Test Task for RAG Provider Versions")
    assert status_code == 200
    task_id = task.id

    # Create a RAG provider first
    status_code, rag_provider = client.create_rag_provider(
        task_id=task_id,
        name="Test RAG Provider",
        description="Test RAG provider for versions CRUD",
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
    assert created_settings.latest_version_number == 1

    # test version creation for non-existing settings config
    status_code, _ = client.create_rag_search_settings_version(
        setting_configuration_id=str(uuid4()),
        settings=WeaviateKeywordSearchSettingsConfigurationRequest(
            rag_provider=RagProviderEnum.WEAVIATE,
            collection_name=collection_name,
            limit=limit + 5,
        ),
    )
    assert status_code == 404

    # test version creation - create version 2
    tags_v2 = ["tag3", "tag4", "staging"]
    limit_v2 = 15
    offset_v2 = 5

    status_code, version_2 = client.create_rag_search_settings_version(
        setting_configuration_id=setting_configuration_id,
        settings=WeaviateKeywordSearchSettingsConfigurationRequest(
            rag_provider=RagProviderEnum.WEAVIATE,
            collection_name=collection_name,
            limit=limit_v2,
            offset=offset_v2,
        ),
        tags=tags_v2,
    )
    assert status_code == 200
    assert version_2.setting_configuration_id == setting_configuration_id
    assert version_2.version_number == 2
    assert version_2.tags == tags_v2
    assert version_2.settings.collection_name == collection_name
    assert version_2.settings.rag_provider == "weaviate"
    assert version_2.settings.search_kind == "keyword_search"
    assert version_2.settings.limit == limit_v2
    assert version_2.settings.offset == offset_v2
    assert version_2.deleted_at is None

    # Verify parent settings config was updated with new latest version
    status_code, updated_settings = client.get_rag_search_settings(
        setting_configuration_id,
    )
    assert status_code == 200
    assert updated_settings.latest_version_number == 2
    # Verify all_possible_tags includes tags from both versions
    assert set(updated_settings.all_possible_tags) == set(tags_v1 + tags_v2)

    # test version fetch - get version 1
    status_code, version_1 = client.get_rag_search_setting_version(
        setting_configuration_id,
        version_number=1,
    )
    assert status_code == 200
    assert version_1.setting_configuration_id == setting_configuration_id
    assert version_1.version_number == 1
    assert version_1.tags == tags_v1
    assert version_1.settings.limit == limit
    assert version_1.deleted_at is None

    # test version fetch - get version 2
    status_code, retrieved_version_2 = client.get_rag_search_setting_version(
        setting_configuration_id,
        version_number=2,
    )
    assert status_code == 200
    assert retrieved_version_2.setting_configuration_id == setting_configuration_id
    assert retrieved_version_2.version_number == 2
    assert retrieved_version_2.tags == tags_v2
    assert retrieved_version_2.settings.limit == limit_v2
    assert retrieved_version_2.settings.offset == offset_v2

    # test version fetch for non-existing version
    status_code, _ = client.get_rag_search_setting_version(
        setting_configuration_id,
        version_number=999,
    )
    assert status_code == 404

    # test version fetch for non-existing settings config
    status_code, _ = client.get_rag_search_setting_version(
        str(uuid4()),
        version_number=1,
    )
    assert status_code == 404

    # test soft delete version 2
    status_code = client.delete_rag_search_setting_version(
        setting_configuration_id,
        version_number=2,
    )
    assert status_code == 204

    # Verify version 2 is soft deleted - it can still be retrieved but the settings are emptied
    status_code, deleted_version_2 = client.get_rag_search_setting_version(
        setting_configuration_id,
        version_number=2,
    )
    assert status_code == 200
    assert deleted_version_2.deleted_at is not None
    # assert fields that should have been cleared
    assert deleted_version_2.settings is None
    assert deleted_version_2.tags is None

    # assert fields that should still have values
    assert deleted_version_2.created_at is not None
    assert deleted_version_2.updated_at is not None
    assert deleted_version_2.version_number == 2
    assert deleted_version_2.setting_configuration_id == setting_configuration_id

    # Verify version 1 is still accessible
    status_code, version_1_after_delete = client.get_rag_search_setting_version(
        setting_configuration_id,
        version_number=1,
    )
    assert status_code == 200
    assert version_1_after_delete.deleted_at is None
    assert version_1_after_delete.tags == tags_v1

    # verify parent settings can still be fetched
    # max version will still be the soft-deleted version, in line with prompts functionality
    status_code, updated_settings = client.get_rag_search_settings(
        setting_configuration_id,
    )
    assert status_code == 200
    assert updated_settings.latest_version_number == 2
    # version 2 tags should be removed
    assert set(updated_settings.all_possible_tags) == set(tags_v1)

    # test delete non-existing version
    status_code = client.delete_rag_search_setting_version(
        setting_configuration_id,
        version_number=999,
    )
    assert status_code == 404

    # test delete non-existing settings config
    status_code = client.delete_rag_search_setting_version(
        str(uuid4()),
        version_number=1,
    )
    assert status_code == 404

    # Clean up
    status_code = client.delete_rag_search_settings(setting_configuration_id)
    assert status_code == 204
    status_code = client.delete_rag_provider(rag_provider_id)
    assert status_code == 204
    status_code = client.delete_task(task_id)
    assert status_code == 204
