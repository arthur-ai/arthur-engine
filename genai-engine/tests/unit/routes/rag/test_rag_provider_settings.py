from uuid import uuid4

import pytest

from schemas.enums import RagProviderEnum
from schemas.request_schemas import WeaviateKeywordSearchSettingsConfigurationRequest
from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.mark.unit_tests
def test_rag_provider_settings_crud(client: GenaiEngineTestClientBase) -> None:
    """Test the basic happy path for rag provider settings CRUD operations: create, get, delete."""
    # First create a task to associate the RAG provider settings with
    status_code, task = client.create_task(name="Test Task for RAG Provider Settings")
    assert status_code == 200
    task_id = task.id

    # Create a RAG provider first
    status_code, rag_provider = client.create_rag_provider(
        task_id=task_id,
        name="Test RAG Provider",
        description="Test RAG provider for settings CRUD",
    )
    assert status_code == 200
    rag_provider_id = rag_provider.id

    # test rag provider settings creation
    settings_name = "My Test RAG Provider Settings"
    settings_description = "Test RAG provider settings for CRUD operations"
    collection_name = "test-collection"
    limit = 10
    include_vector = True
    offset = 0
    auto_limit = 5
    minimum_match_or_operator = 2
    tags = ["tag1", "tag2", "production"]

    # test settings creation for non-existing task
    status_code, _ = client.create_rag_provider_settings(
        task_id=str(uuid4()),
        rag_provider_id=rag_provider_id,
        name=settings_name,
        tags=tags,
        settings=WeaviateKeywordSearchSettingsConfigurationRequest(
            rag_provider=RagProviderEnum.WEAVIATE,
            collection_name=collection_name,
            limit=limit,
        ),
    )
    assert status_code == 404

    status_code, created_settings = client.create_rag_provider_settings(
        task_id=task_id,
        rag_provider_id=rag_provider_id,
        name=settings_name,
        description=settings_description,
        tags=tags,
        settings=WeaviateKeywordSearchSettingsConfigurationRequest(
            rag_provider=RagProviderEnum.WEAVIATE,
            collection_name=collection_name,
            limit=limit,
            include_vector=include_vector,
            offset=offset,
            auto_limit=auto_limit,
            minimum_match_or_operator=minimum_match_or_operator,
        ),
    )
    assert status_code == 200
    assert created_settings.task_id == task_id
    assert created_settings.rag_provider_id == rag_provider_id
    assert created_settings.name == settings_name
    assert created_settings.description == settings_description
    assert created_settings.id is not None
    assert created_settings.latest_version_number == 1
    assert created_settings.latest_version.tags == tags
    assert set(created_settings.all_possible_tags) == set(tags)
    # Validate settings
    assert created_settings.latest_version.settings.collection_name == collection_name
    assert created_settings.latest_version.settings.rag_provider == "weaviate"
    assert created_settings.latest_version.settings.search_kind == "keyword_search"
    assert created_settings.latest_version.settings.limit == limit
    assert created_settings.latest_version.settings.include_vector == include_vector
    assert created_settings.latest_version.settings.offset == offset
    assert created_settings.latest_version.settings.auto_limit == auto_limit
    assert (
        created_settings.latest_version.settings.minimum_match_or_operator
        == minimum_match_or_operator
    )

    # test rag provider settings fetch
    status_code, retrieved_settings = client.get_rag_provider_settings(
        created_settings.id,
    )
    assert status_code == 200
    assert retrieved_settings.id == created_settings.id
    assert retrieved_settings.rag_provider_id == rag_provider_id
    assert retrieved_settings.name == settings_name
    assert retrieved_settings.description == settings_description
    assert retrieved_settings.latest_version.tags == tags
    assert set(retrieved_settings.all_possible_tags) == set(tags)
    # Validate settings in retrieved response
    assert retrieved_settings.latest_version.settings.collection_name == collection_name
    assert retrieved_settings.latest_version.settings.rag_provider == "weaviate"
    assert retrieved_settings.latest_version.settings.search_kind == "keyword_search"
    assert retrieved_settings.latest_version.settings.limit == limit
    assert retrieved_settings.latest_version.settings.include_vector == include_vector
    assert retrieved_settings.latest_version.settings.offset == offset
    assert retrieved_settings.latest_version.settings.auto_limit == auto_limit
    assert (
        retrieved_settings.latest_version.settings.minimum_match_or_operator
        == minimum_match_or_operator
    )

    # deleting parent rag provider doesn't delete its settings
    status_code = client.delete_rag_provider(rag_provider_id)
    assert status_code == 204

    status_code, retrieved_settings = client.get_rag_provider_settings(
        created_settings.id,
    )
    assert status_code == 200
    assert retrieved_settings.rag_provider_id is None

    # delete rag provider settings
    status_code = client.delete_rag_provider_settings(created_settings.id)
    assert status_code == 204

    # fail to fetch rag provider settings because it was deleted
    status_code, _ = client.get_rag_provider_settings(created_settings.id)
    assert status_code == 404

    # fail to delete rag provider settings that doesn't exist
    status_code = client.delete_rag_provider_settings(created_settings.id)
    assert status_code == 404

    # Clean up the task (rag_provider already deleted above)
    status_code = client.delete_task(task_id)
    assert status_code == 204
