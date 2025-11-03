import pytest

from schemas.enums import RagProviderEnum
from schemas.request_schemas import (
    WeaviateHybridSearchSettingsConfigurationRequest,
    WeaviateKeywordSearchSettingsConfigurationRequest,
    WeaviateVectorSimilarityTextSearchSettingsConfigurationRequest,
)
from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.mark.unit_tests
def test_rag_provider_settings_keyword_search(
    client: GenaiEngineTestClientBase,
) -> None:
    """Test creating and retrieving keyword search settings."""
    status_code, task = client.create_task(name="Test Task for Keyword Search")
    assert status_code == 200
    task_id = task.id

    minimum_match_or_operator = 2
    status_code, created_settings = client.create_rag_provider_settings(
        task_id=task_id,
        name="Keyword Search Settings",
        settings=WeaviateKeywordSearchSettingsConfigurationRequest(
            rag_provider=RagProviderEnum.WEAVIATE,
            collection_name="test-collection",
            minimum_match_or_operator=minimum_match_or_operator,
        ),
    )
    assert status_code == 200
    assert created_settings.latest_version.settings.search_kind == "keyword_search"
    assert (
        created_settings.latest_version.settings.minimum_match_or_operator
        == minimum_match_or_operator
    )

    status_code, retrieved_settings = client.get_rag_provider_settings(
        created_settings.id,
    )
    assert status_code == 200
    assert retrieved_settings.latest_version.settings.search_kind == "keyword_search"
    assert (
        retrieved_settings.latest_version.settings.minimum_match_or_operator
        == minimum_match_or_operator
    )

    # Cleanup
    client.delete_rag_provider_settings(created_settings.id)
    client.delete_task(task_id)


@pytest.mark.unit_tests
def test_rag_provider_settings_hybrid_search(client: GenaiEngineTestClientBase) -> None:
    """Test creating and retrieving hybrid search settings."""
    status_code, task = client.create_task(name="Test Task for Hybrid Search")
    assert status_code == 200
    task_id = task.id

    settings = WeaviateHybridSearchSettingsConfigurationRequest(
        rag_provider=RagProviderEnum.WEAVIATE,
        collection_name="test-collection",
        alpha=0.8,
    )
    status_code, created_settings = client.create_rag_provider_settings(
        task_id=task_id,
        name="Hybrid Search Settings",
        settings=settings,
    )
    assert status_code == 200
    assert created_settings.latest_version.settings.search_kind == "hybrid_search"
    assert created_settings.latest_version.settings.alpha == 0.8

    status_code, retrieved_settings = client.get_rag_provider_settings(
        created_settings.id,
    )
    assert status_code == 200
    assert retrieved_settings.latest_version.settings.search_kind == "hybrid_search"
    assert retrieved_settings.latest_version.settings.alpha == 0.8

    # Cleanup
    client.delete_rag_provider_settings(created_settings.id)
    client.delete_task(task_id)


@pytest.mark.unit_tests
def test_rag_provider_settings_vector_similarity_search(
    client: GenaiEngineTestClientBase,
) -> None:
    """Test creating and retrieving vector similarity search settings."""
    status_code, task = client.create_task(
        name="Test Task for Vector Similarity Search",
    )
    assert status_code == 200
    task_id = task.id

    settings = WeaviateVectorSimilarityTextSearchSettingsConfigurationRequest(
        rag_provider=RagProviderEnum.WEAVIATE,
        collection_name="test-collection",
        certainty=0.85,
    )
    status_code, created_settings = client.create_rag_provider_settings(
        task_id=task_id,
        name="Vector Similarity Search Settings",
        settings=settings,
    )
    assert status_code == 200
    assert (
        created_settings.latest_version.settings.search_kind
        == "vector_similarity_text_search"
    )
    assert created_settings.latest_version.settings.certainty == 0.85

    status_code, retrieved_settings = client.get_rag_provider_settings(
        created_settings.id,
    )
    assert status_code == 200
    assert (
        retrieved_settings.latest_version.settings.search_kind
        == "vector_similarity_text_search"
    )
    assert retrieved_settings.latest_version.settings.certainty == 0.85

    # Cleanup
    client.delete_rag_provider_settings(created_settings.id)
    client.delete_task(task_id)
