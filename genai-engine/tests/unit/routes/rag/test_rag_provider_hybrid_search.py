from unittest.mock import Mock, patch

import pytest
from weaviate.collections.classes.grpc import HybridFusion

from tests.clients.base_test_client import GenaiEngineTestClientBase
from tests.mocks.mock_weaviate_client import MockWeaviateClientFactory


@pytest.mark.unit_tests
@patch("routers.v1.rag_routes.RagClientConstructor")
def test_rag_provider_hybrid_search_success(
    mock_rag_client_constructor,
    client: GenaiEngineTestClientBase,
) -> None:
    """Test successful RAG provider hybrid search. Basic happy path"""
    # Create a task and RAG provider first
    status_code, task = client.create_task(name="Test Task for Hybrid Search")
    assert status_code == 200
    task_id = task.id

    status_code, rag_provider = client.create_rag_provider(
        task_id=task_id,
        name="Test RAG Provider",
        description="Test RAG provider for hybrid search",
    )
    assert status_code == 200
    provider_id = rag_provider.id

    # Mock the RagClientConstructor to return successful search results
    mock_client = MockWeaviateClientFactory.create_successful_client(Mock())
    mock_constructor_instance = Mock()
    mock_constructor_instance.execute_hybrid_search.return_value = (
        mock_client.hybrid_search(Mock())
    )
    mock_rag_client_constructor.return_value = mock_constructor_instance

    # Test hybrid search with minimal parameters
    status_code, result = client.execute_hybrid_search(
        provider_id=provider_id,
        query="test query",
        collection_name="test_collection",
    )

    # Verify the response
    assert status_code == 200
    assert result is not None
    assert result.response is not None
    assert len(result.response.objects) == 2
    assert result.response.objects[0].properties["text"] == "Sample document 1"
    assert result.response.objects[1].properties["text"] == "Sample document 2"

    # Verify the constructor was called correctly
    mock_rag_client_constructor.assert_called_once()
    mock_constructor_instance.execute_hybrid_search.assert_called_once()

    # Clean up
    status_code = client.delete_rag_provider(provider_id)
    assert status_code == 204
    status_code = client.delete_task(task_id)
    assert status_code == 204


@pytest.mark.unit_tests
@patch("routers.v1.rag_routes.RagClientConstructor")
def test_rag_provider_hybrid_search_with_parameters(
    mock_rag_client_constructor,
    client: GenaiEngineTestClientBase,
) -> None:
    """Test hybrid search with all parameters set at route level. More complex happy path."""
    # Create a task and RAG provider first
    status_code, task = client.create_task(
        name="Test Task for Full Hybrid Search",
    )
    assert status_code == 200
    task_id = task.id

    status_code, rag_provider = client.create_rag_provider(
        task_id=task_id,
        name="Test RAG Provider",
        description="Test RAG provider for full hybrid search",
    )
    assert status_code == 200
    provider_id = rag_provider.id

    # Mock the RagClientConstructor to return successful search results
    mock_client = MockWeaviateClientFactory.create_successful_client(Mock())
    mock_constructor_instance = Mock()
    mock_constructor_instance.execute_hybrid_search.return_value = (
        mock_client.hybrid_search(Mock())
    )
    mock_rag_client_constructor.return_value = mock_constructor_instance

    # Test hybrid search with all parameters
    status_code, result = client.execute_hybrid_search(
        provider_id=provider_id,
        query="comprehensive test query",
        collection_name="comprehensive_test_collection",
        alpha=0.8,
        limit=5,
        include_vector=True,
        offset=10,
        query_properties=["text", "title"],
        fusion_type=HybridFusion.RELATIVE_SCORE,
        max_vector_distance=0.3,
        minimum_match_or_operator=2,
    )

    # Verify the response
    assert status_code == 200
    assert result is not None
    assert result.response is not None
    assert len(result.response.objects) == 2
    assert result.response.objects[0].properties["text"] == "Sample document 1"
    assert result.response.objects[1].properties["text"] == "Sample document 2"

    # Verify the constructor was called correctly
    mock_rag_client_constructor.assert_called_once()
    mock_constructor_instance.execute_hybrid_search.assert_called_once()

    # Clean up
    status_code = client.delete_rag_provider(provider_id)
    assert status_code == 204
    status_code = client.delete_task(task_id)
    assert status_code == 204


@pytest.mark.unit_tests
@patch("routers.v1.rag_routes.RagClientConstructor")
def test_rag_provider_hybrid_search_with_operators(
    mock_rag_client_constructor,
    client: GenaiEngineTestClientBase,
) -> None:
    """Test hybrid search with operator parameters (and_operator and minimum_match_or_operator)."""
    # Create a task and RAG provider first
    status_code, task = client.create_task(
        name="Test Task for Hybrid Search with Operators",
    )
    assert status_code == 200
    task_id = task.id

    status_code, rag_provider = client.create_rag_provider(
        task_id=task_id,
        name="Test RAG Provider",
        description="Test RAG provider for hybrid search with operators",
    )
    assert status_code == 200
    provider_id = rag_provider.id

    # Mock the RagClientConstructor to return successful search results
    mock_client = MockWeaviateClientFactory.create_successful_client(Mock())
    mock_constructor_instance = Mock()
    mock_constructor_instance.execute_hybrid_search.return_value = (
        mock_client.hybrid_search(Mock())
    )
    mock_rag_client_constructor.return_value = mock_constructor_instance

    # Test hybrid search with operator parameters
    status_code, result = client.execute_hybrid_search(
        provider_id=provider_id,
        query="test query with operators",
        collection_name="test_collection",
        and_operator=True,
        limit=5,
        include_vector=True,
        alpha=0.6,
    )

    # Verify the response
    assert status_code == 200
    assert result is not None
    assert result.response is not None
    assert len(result.response.objects) == 2
    assert result.response.objects[0].properties["text"] == "Sample document 1"
    assert result.response.objects[1].properties["text"] == "Sample document 2"

    # Verify the constructor was called correctly
    mock_rag_client_constructor.assert_called_once()
    mock_constructor_instance.execute_hybrid_search.assert_called_once()

    # Clean up
    status_code = client.delete_rag_provider(provider_id)
    assert status_code == 204
    status_code = client.delete_task(task_id)
    assert status_code == 204


@pytest.mark.unit_tests
@patch("routers.v1.rag_routes.RagClientConstructor")
def test_rag_provider_hybrid_search_empty_results(
    mock_rag_client_constructor,
    client: GenaiEngineTestClientBase,
) -> None:
    """Test hybrid search that returns empty results at route level."""
    # Create a task and RAG provider first
    status_code, task = client.create_task(name="Test Task for Empty Hybrid Search")
    assert status_code == 200
    task_id = task.id

    status_code, rag_provider = client.create_rag_provider(
        task_id=task_id,
        name="Test RAG Provider",
        description="Test RAG provider for empty hybrid search",
    )
    assert status_code == 200
    provider_id = rag_provider.id

    # Mock the RagClientConstructor to return empty results
    mock_client = MockWeaviateClientFactory.create_empty_results_client(Mock())
    mock_constructor_instance = Mock()
    mock_constructor_instance.execute_hybrid_search.return_value = (
        mock_client.hybrid_search(Mock())
    )
    mock_rag_client_constructor.return_value = mock_constructor_instance

    # Test hybrid search
    status_code, result = client.execute_hybrid_search(
        provider_id=provider_id,
        query="query with no results",
        collection_name="empty_collection",
    )

    # Verify the response
    assert status_code == 200
    assert result is not None
    assert result.response is not None
    assert len(result.response.objects) == 0

    # Verify the constructor was called correctly
    mock_rag_client_constructor.assert_called_once()
    mock_constructor_instance.execute_hybrid_search.assert_called_once()

    # Clean up
    status_code = client.delete_rag_provider(provider_id)
    assert status_code == 204
    status_code = client.delete_task(task_id)
    assert status_code == 204
