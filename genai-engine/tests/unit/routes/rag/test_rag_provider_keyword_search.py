from unittest.mock import Mock, patch

import pytest

from tests.clients.base_test_client import GenaiEngineTestClientBase
from tests.mocks.mock_weaviate_client import MockWeaviateClientFactory


@pytest.mark.unit_tests
@patch("routers.v1.rag_routes.RagClientConstructor")
def test_rag_provider_keyword_search_success(
    mock_rag_client_constructor,
    client: GenaiEngineTestClientBase,
) -> None:
    """Test successful RAG provider keyword search. Basic happy path"""
    # Create a task and RAG provider first
    status_code, task = client.create_task(name="Test Task for Keyword Search")
    assert status_code == 200
    task_id = task.id

    status_code, rag_provider = client.create_rag_provider(
        task_id=task_id,
        name="Test RAG Provider",
        description="Test RAG provider for keyword search",
    )
    assert status_code == 200
    provider_id = rag_provider.id

    # Mock the RagClientConstructor to return successful search results
    mock_client = MockWeaviateClientFactory.create_successful_client(Mock())
    mock_constructor_instance = Mock()
    mock_constructor_instance.execute_keyword_search.return_value = (
        mock_client.keyword_search(Mock())
    )
    mock_rag_client_constructor.return_value = mock_constructor_instance

    # Test keyword search with minimal parameters
    status_code, result = client.execute_keyword_search(
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
    mock_constructor_instance.execute_keyword_search.assert_called_once()

    # Clean up
    status_code = client.delete_rag_provider(provider_id)
    assert status_code == 204
    status_code = client.delete_task(task_id)
    assert status_code == 204


@pytest.mark.unit_tests
@patch("routers.v1.rag_routes.RagClientConstructor")
def test_rag_provider_keyword_search_with_operators(
    mock_rag_client_constructor,
    client: GenaiEngineTestClientBase,
) -> None:
    """Test keyword search with operator parameters (and_operator and minimum_match_or_operator)."""
    # Create a task and RAG provider first
    status_code, task = client.create_task(
        name="Test Task for Keyword Search with Operators",
    )
    assert status_code == 200
    task_id = task.id

    status_code, rag_provider = client.create_rag_provider(
        task_id=task_id,
        name="Test RAG Provider",
        description="Test RAG provider for keyword search with operators",
    )
    assert status_code == 200
    provider_id = rag_provider.id

    # Mock the RagClientConstructor to return successful search results
    mock_client = MockWeaviateClientFactory.create_successful_client(Mock())
    mock_constructor_instance = Mock()
    mock_constructor_instance.execute_keyword_search.return_value = (
        mock_client.keyword_search(Mock())
    )
    mock_rag_client_constructor.return_value = mock_constructor_instance

    # Test keyword search with operator parameters
    status_code, result = client.execute_keyword_search(
        provider_id=provider_id,
        query="test query with operators",
        collection_name="test_collection",
        and_operator=True,
        limit=5,
        include_vector=True,
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
    mock_constructor_instance.execute_keyword_search.assert_called_once()

    # Clean up
    status_code = client.delete_rag_provider(provider_id)
    assert status_code == 204
    status_code = client.delete_task(task_id)
    assert status_code == 204


@pytest.mark.unit_tests
@patch("routers.v1.rag_routes.RagClientConstructor")
def test_rag_provider_keyword_search_empty_results(
    mock_rag_client_constructor,
    client: GenaiEngineTestClientBase,
) -> None:
    """Test keyword search that returns empty results."""
    # Create a task and RAG provider first
    status_code, task = client.create_task(name="Test Task for Empty Keyword Search")
    assert status_code == 200
    task_id = task.id

    status_code, rag_provider = client.create_rag_provider(
        task_id=task_id,
        name="Test RAG Provider",
        description="Test RAG provider for empty keyword search",
    )
    assert status_code == 200
    provider_id = rag_provider.id

    # Mock the RagClientConstructor to return empty results
    mock_client = MockWeaviateClientFactory.create_empty_results_client(Mock())
    mock_constructor_instance = Mock()
    mock_constructor_instance.execute_keyword_search.return_value = (
        mock_client.keyword_search(Mock())
    )
    mock_rag_client_constructor.return_value = mock_constructor_instance

    # Test keyword search
    status_code, result = client.execute_keyword_search(
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
    mock_constructor_instance.execute_keyword_search.assert_called_once()

    # Clean up
    status_code = client.delete_rag_provider(provider_id)
    assert status_code == 204
    status_code = client.delete_task(task_id)
    assert status_code == 204


@pytest.mark.unit_tests
@patch("routers.v1.rag_routes.RagClientConstructor")
def test_rag_provider_keyword_search_failure(
    mock_rag_client_constructor,
    client: GenaiEngineTestClientBase,
) -> None:
    """Test keyword search that fails with an error.
    Want to re-raise error cleanly to user instead of failing with a 5XX so they know how to fix their query.
    """
    # Create a task and RAG provider first
    status_code, task = client.create_task(
        name="Test Task for Failed Keyword Search",
    )
    assert status_code == 200
    task_id = task.id

    status_code, rag_provider = client.create_rag_provider(
        task_id=task_id,
        name="Test RAG Provider",
        description="Test RAG provider for failed keyword search",
    )
    assert status_code == 200
    provider_id = rag_provider.id

    # Mock the RagClientConstructor to raise an HTTPException
    from fastapi import HTTPException

    mock_constructor_instance = Mock()
    mock_constructor_instance.execute_keyword_search.side_effect = HTTPException(
        status_code=400,
        detail="Error querying Weaviate: Collection 'test_collection' does not exist.",
    )
    mock_rag_client_constructor.return_value = mock_constructor_instance

    # Test keyword search
    status_code, result = client.execute_keyword_search(
        provider_id=provider_id,
        query="query that fails",
        collection_name="nonexistent_collection",
    )

    # Verify the response - should return 400 due to HTTPException
    assert status_code == 400
    assert result is None

    # Verify the constructor was called correctly
    mock_rag_client_constructor.assert_called_once()
    mock_constructor_instance.execute_keyword_search.assert_called_once()

    # Clean up
    status_code = client.delete_rag_provider(provider_id)
    assert status_code == 204
    status_code = client.delete_task(task_id)
    assert status_code == 204
