import pytest
from arthur_common.models.enums import PaginationSortMethod

from schemas.enums import (
    RagAPIKeyAuthenticationProviderEnum,
    RagProviderAuthenticationMethodEnum,
)
from tests.clients.base_test_client import GenaiEngineTestClientBase


@pytest.mark.unit_tests
def test_rag_providers_query(client: GenaiEngineTestClientBase) -> None:
    """Comprehensive test for RAG providers query endpoint with multiple test cases."""

    # Create test task first
    status_code, task = client.create_task(name="Test Task for RAG Provider Query")
    assert status_code == 200
    task_id = task.id

    # Create test RAG providers with different configurations
    provider1_name = "Weaviate Provider One"
    provider2_name = "Weaviate Provider Two"
    provider3_name = "Another Provider"

    status_code, provider1 = client.create_rag_provider(
        task_id=task_id,
        name=provider1_name,
        description="First test RAG provider",
        authentication_method=RagProviderAuthenticationMethodEnum.API_KEY_AUTHENTICATION,
        api_key="test-api-key-1",
        host_url="https://test-weaviate-1.example.com",
        rag_provider=RagAPIKeyAuthenticationProviderEnum.WEAVIATE,
    )
    assert status_code == 200

    status_code, provider2 = client.create_rag_provider(
        task_id=task_id,
        name=provider2_name,
        description="Second test RAG provider",
        authentication_method=RagProviderAuthenticationMethodEnum.API_KEY_AUTHENTICATION,
        api_key="test-api-key-2",
        host_url="https://test-weaviate-2.example.com",
        rag_provider=RagAPIKeyAuthenticationProviderEnum.WEAVIATE,
    )
    assert status_code == 200

    status_code, provider3 = client.create_rag_provider(
        task_id=task_id,
        name=provider3_name,
        description="Third test RAG provider",
        authentication_method=RagProviderAuthenticationMethodEnum.API_KEY_AUTHENTICATION,
        api_key="test-api-key-3",
        host_url="https://test-weaviate-3.example.com",
        rag_provider=RagAPIKeyAuthenticationProviderEnum.WEAVIATE,
    )
    assert status_code == 200

    # Test Case 1: Basic functionality without filters
    # Test basic search without filters - should return all RAG providers
    status_code, response = client.search_rag_providers(task_id=task_id)
    assert status_code == 200
    assert response.count >= 3
    assert len(response.rag_provider_configurations) >= 3

    # Verify all created RAG providers are in the response
    provider_ids = {p.id for p in response.rag_provider_configurations}
    assert provider1.id in provider_ids
    assert provider2.id in provider_ids
    assert provider3.id in provider_ids

    # Test Case 2: Name-based filtering
    # Test case insensitive search for "Weaviate"
    status_code, response = client.search_rag_providers(
        task_id=task_id,
        config_name="Weaviate",
    )
    assert status_code == 200
    assert response.count == 2
    assert len(response.rag_provider_configurations) == 2

    # Test no matches
    status_code, response = client.search_rag_providers(
        task_id=task_id,
        config_name="NonExistentProvider",
    )
    assert status_code == 200
    assert response.count == 0
    assert len(response.rag_provider_configurations) == 0

    # Test Case 3: Authentication method filtering
    # Test filtering by authentication method
    status_code, response = client.search_rag_providers(
        task_id=task_id,
        authentication_method=RagProviderAuthenticationMethodEnum.API_KEY_AUTHENTICATION,
    )
    assert status_code == 200
    assert response.count >= 3
    assert len(response.rag_provider_configurations) >= 3

    # Test Case 4: RAG provider name filtering
    # Test filtering by RAG provider name
    status_code, response = client.search_rag_providers(
        task_id=task_id,
        rag_provider_name=RagAPIKeyAuthenticationProviderEnum.WEAVIATE,
    )
    assert status_code == 200
    assert response.count >= 3
    assert len(response.rag_provider_configurations) >= 3

    # Test Case 5: Pagination functionality
    # Test page size
    status_code, response = client.search_rag_providers(
        task_id=task_id,
        page_size=2,
    )
    assert status_code == 200
    assert len(response.rag_provider_configurations) == 2
    assert response.count >= 3

    # Test page navigation
    status_code, response_page1 = client.search_rag_providers(
        task_id=task_id,
        page=0,
        page_size=2,
    )
    assert status_code == 200
    assert len(response_page1.rag_provider_configurations) == 2

    status_code, response_page2 = client.search_rag_providers(
        task_id=task_id,
        page=1,
        page_size=2,
    )
    assert status_code == 200
    # there may be RAG providers from other unit tests, but there are at least 3 total
    assert len(response_page2.rag_provider_configurations) >= 1

    # Test Case 6: Sorting functionality
    status_code, response_desc = client.search_rag_providers(
        task_id=task_id,
        sort=PaginationSortMethod.DESCENDING,
    )
    assert status_code == 200
    assert len(response_desc.rag_provider_configurations) >= 3

    # Verify that the order is descending (newest first) based on created_at
    for i in range(len(response_desc.rag_provider_configurations) - 1):
        assert (
            response_desc.rag_provider_configurations[i].updated_at
            >= response_desc.rag_provider_configurations[i + 1].updated_at
        )

    # Test Case 7: Combined filters
    # Test combining name filter with authentication method filter
    status_code, response = client.search_rag_providers(
        task_id=task_id,
        config_name="Weaviate",
        authentication_method=RagProviderAuthenticationMethodEnum.API_KEY_AUTHENTICATION,
    )
    assert status_code == 200
    assert response.count == 2
    assert len(response.rag_provider_configurations) == 2
