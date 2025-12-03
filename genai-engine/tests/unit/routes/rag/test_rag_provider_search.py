from unittest.mock import Mock, patch

import pytest

from schemas.enums import ConnectionCheckOutcome
from tests.clients.base_test_client import GenaiEngineTestClientBase
from tests.mocks.mock_weaviate_client import MockWeaviateClientFactory


@pytest.mark.unit_tests
@patch("routers.v1.rag_routes.RagClientConstructor")
def test_rag_provider_connection_success(
    mock_rag_client_constructor,
    client: GenaiEngineTestClientBase,
) -> None:
    """Test successful RAG provider connection test. Basic happy path"""
    # Create a task first
    status_code, task = client.create_task(name="Test Task for RAG Connection")
    assert status_code == 200
    task_id = task.id

    # Mock the RagClientConstructor to return a successful connection
    mock_client = MockWeaviateClientFactory.create_successful_client(Mock())
    mock_constructor_instance = Mock()
    mock_constructor_instance.execute_test_connection.return_value = (
        mock_client.test_connection()
    )
    mock_rag_client_constructor.return_value = mock_constructor_instance

    # Test the connection
    status_code, result = client.test_rag_provider_connection(
        task_id=task_id,
        api_key="test-api-key",
        host_url="https://test-weaviate.example.com",
    )

    # Verify the response
    assert status_code == 200
    assert result is not None
    assert result.connection_check_outcome == ConnectionCheckOutcome.PASSED
    assert result.failure_reason is None

    # Verify the constructor was called correctly
    mock_rag_client_constructor.assert_called_once()
    mock_constructor_instance.execute_test_connection.assert_called_once()

    # Clean up
    status_code = client.delete_task(task_id)
    assert status_code == 204


@pytest.mark.unit_tests
@patch("clients.rag_providers.rag_client_constructor.WeaviateClient")
def test_rag_provider_connection_failure(
    mock_weaviate_client,
    client: GenaiEngineTestClientBase,
) -> None:
    """Test RAG provider connection when WeaviateClient instantiation raises an exception on instantiation.
    Error should be reported cleanly as a test failure to the user.
    """
    # Create a task first
    status_code, task = client.create_task(name="Test Task for RAG Connection Failure")
    assert status_code == 200
    task_id = task.id

    # Mock the WeaviateClient constructor to raise an exception during instantiation
    mock_weaviate_client.side_effect = Exception(
        "Invalid authentication credentials",
    )

    # Test the connection
    status_code, result = client.test_rag_provider_connection(
        task_id=task_id,
        api_key="invalid-api-key",
        host_url="https://invalid-weaviate.example.com",
    )

    # Verify the response
    assert status_code == 200
    assert result is not None
    assert result.connection_check_outcome == ConnectionCheckOutcome.FAILED
    assert result.failure_reason is not None
    assert "Invalid authentication credentials" in result.failure_reason

    # Verify the WeaviateClient constructor was called correctly
    mock_weaviate_client.assert_called_once()

    # Clean up
    status_code = client.delete_task(task_id)
    assert status_code == 204


@pytest.mark.unit_tests
@patch("routers.v1.rag_routes.RagClientConstructor")
def test_rag_provider_connection_constructor_exception(
    mock_rag_client_constructor,
    client: GenaiEngineTestClientBase,
) -> None:
    """Test RAG provider connection when client.is_connected() returns False at the connection test time.
    Error should be raised cleanly to the user.
    """
    # Create a task first
    status_code, task = client.create_task(
        name="Test Task for RAG Connection Not Connected",
    )
    assert status_code == 200
    task_id = task.id

    # Mock the RagClientConstructor to return a client that is not connected
    mock_client = MockWeaviateClientFactory.create_connection_failure_client(Mock())
    # Override to simulate the specific case where is_connected() returns False
    mock_client.is_connected_value = False
    mock_client.connection_error = None  # Clear any connection error
    mock_constructor_instance = Mock()
    mock_constructor_instance.execute_test_connection.return_value = (
        mock_client.test_connection()
    )
    mock_rag_client_constructor.return_value = mock_constructor_instance

    # Test the connection
    status_code, result = client.test_rag_provider_connection(
        task_id=task_id,
        api_key="invalid-api-key",
        host_url="https://invalid-weaviate.example.com",
    )

    # Verify the response
    assert status_code == 200
    assert result is not None
    assert result.connection_check_outcome == ConnectionCheckOutcome.FAILED
    assert result.failure_reason is not None
    assert (
        "No error was raised on connection creation but the client was not connected afterwards"
        in result.failure_reason
    )

    # Verify the constructor was called correctly
    mock_rag_client_constructor.assert_called_once()
    mock_constructor_instance.execute_test_connection.assert_called_once()

    # Clean up
    status_code = client.delete_task(task_id)
    assert status_code == 204


@pytest.mark.unit_tests
@patch("routers.v1.rag_routes.RagClientConstructor")
def test_execute_similarity_text_search_minimal_params(
    mock_rag_client_constructor,
    client: GenaiEngineTestClientBase,
) -> None:
    """Test similarity text search with minimal parameters (query and collection_name only). Basic happy path."""
    # Create a task and RAG provider first
    status_code, task = client.create_task(name="Test Task for Similarity Search")
    assert status_code == 200
    task_id = task.id

    status_code, rag_provider = client.create_rag_provider(
        task_id=task_id,
        name="Test RAG Provider",
        description="Test RAG provider for similarity search",
    )
    assert status_code == 200
    provider_id = rag_provider.id

    # Mock the RagClientConstructor to return successful search results
    mock_client = MockWeaviateClientFactory.create_successful_client(Mock())
    mock_constructor_instance = Mock()
    mock_constructor_instance.execute_similarity_text_search.return_value = (
        mock_client.vector_similarity_text_search(Mock())
    )
    mock_rag_client_constructor.return_value = mock_constructor_instance

    # Test similarity search with minimal parameters
    status_code, result = client.execute_similarity_text_search(
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
    mock_constructor_instance.execute_similarity_text_search.assert_called_once()

    # Clean up
    status_code = client.delete_rag_provider(provider_id)
    assert status_code == 204
    status_code = client.delete_task(task_id)
    assert status_code == 204


@pytest.mark.unit_tests
@patch("routers.v1.rag_routes.RagClientConstructor")
def test_execute_similarity_text_search_full_params(
    mock_rag_client_constructor,
    client: GenaiEngineTestClientBase,
) -> None:
    """Test similarity text search with all parameters set at route level. More complex happy path."""
    # Create a task and RAG provider first
    status_code, task = client.create_task(name="Test Task for Full Similarity Search")
    assert status_code == 200
    task_id = task.id

    status_code, rag_provider = client.create_rag_provider(
        task_id=task_id,
        name="Test RAG Provider",
        description="Test RAG provider for full similarity search",
    )
    assert status_code == 200
    provider_id = rag_provider.id

    # Mock the RagClientConstructor to return successful search results
    mock_client = MockWeaviateClientFactory.create_successful_client(Mock())
    mock_constructor_instance = Mock()
    mock_constructor_instance.execute_similarity_text_search.return_value = (
        mock_client.vector_similarity_text_search(Mock())
    )
    mock_rag_client_constructor.return_value = mock_constructor_instance

    # Test similarity search with all parameters
    status_code, result = client.execute_similarity_text_search(
        provider_id=provider_id,
        query="comprehensive test query",
        collection_name="comprehensive_test_collection",
        certainty=0.8,
        limit=5,
        include_vector=True,
        offset=10,
        distance=0.3,
        auto_limit=3,
        move_to={"concepts": ["positive concept"], "force": 0.5},
        move_away={"concepts": ["negative concept"], "force": 0.3},
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
    mock_constructor_instance.execute_similarity_text_search.assert_called_once()

    # Clean up
    status_code = client.delete_rag_provider(provider_id)
    assert status_code == 204
    status_code = client.delete_task(task_id)
    assert status_code == 204


@pytest.mark.unit_tests
@patch("routers.v1.rag_routes.RagClientConstructor")
def test_execute_similarity_text_search_empty_results(
    mock_rag_client_constructor,
    client: GenaiEngineTestClientBase,
) -> None:
    """Test similarity text search that returns empty results at route level."""
    # Create a task and RAG provider first
    status_code, task = client.create_task(name="Test Task for Empty Similarity Search")
    assert status_code == 200
    task_id = task.id

    status_code, rag_provider = client.create_rag_provider(
        task_id=task_id,
        name="Test RAG Provider",
        description="Test RAG provider for empty similarity search",
    )
    assert status_code == 200
    provider_id = rag_provider.id

    # Mock the RagClientConstructor to return empty results
    mock_client = MockWeaviateClientFactory.create_empty_results_client(Mock())
    mock_constructor_instance = Mock()
    mock_constructor_instance.execute_similarity_text_search.return_value = (
        mock_client.vector_similarity_text_search(Mock())
    )
    mock_rag_client_constructor.return_value = mock_constructor_instance

    # Test similarity search
    status_code, result = client.execute_similarity_text_search(
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
    mock_constructor_instance.execute_similarity_text_search.assert_called_once()

    # Clean up
    status_code = client.delete_rag_provider(provider_id)
    assert status_code == 204
    status_code = client.delete_task(task_id)
    assert status_code == 204


@pytest.mark.unit_tests
@patch("routers.v1.rag_routes.RagClientConstructor")
def test_execute_similarity_text_search_failure(
    mock_rag_client_constructor,
    client: GenaiEngineTestClientBase,
) -> None:
    """Test similarity text search that fails with an error at route level.
    Want to re-raise error cleanly to user instead of failing with a 5XX so they know how to fix their query.
    """
    # Create a task and RAG provider first
    status_code, task = client.create_task(
        name="Test Task for Failed Similarity Search",
    )
    assert status_code == 200
    task_id = task.id

    status_code, rag_provider = client.create_rag_provider(
        task_id=task_id,
        name="Test RAG Provider",
        description="Test RAG provider for failed similarity search",
    )
    assert status_code == 200
    provider_id = rag_provider.id

    # Mock the RagClientConstructor to raise an HTTPException
    from fastapi import HTTPException

    mock_constructor_instance = Mock()
    mock_constructor_instance.execute_similarity_text_search.side_effect = HTTPException(
        status_code=400,
        detail="Error querying Weaviate: Collection 'test_collection' does not exist.",
    )
    mock_rag_client_constructor.return_value = mock_constructor_instance

    # Test similarity search
    status_code, result = client.execute_similarity_text_search(
        provider_id=provider_id,
        query="query that fails",
        collection_name="nonexistent_collection",
    )

    # Verify the response - should return 400 due to HTTPException
    assert status_code == 400
    assert result is None

    # Verify the constructor was called correctly
    mock_rag_client_constructor.assert_called_once()
    mock_constructor_instance.execute_similarity_text_search.assert_called_once()

    # Clean up
    status_code = client.delete_rag_provider(provider_id)
    assert status_code == 204
    status_code = client.delete_task(task_id)
    assert status_code == 204


@pytest.mark.unit_tests
@patch("routers.v1.rag_routes.RagClientConstructor")
def test_list_rag_provider_collections_success(
    mock_rag_client_constructor,
    client: GenaiEngineTestClientBase,
) -> None:
    """Test successful RAG provider collections listing. Basic happy path."""
    # Create a task and RAG provider first
    status_code, task = client.create_task(name="Test Task for Collections Listing")
    assert status_code == 200
    task_id = task.id

    status_code, rag_provider = client.create_rag_provider(
        task_id=task_id,
        name="Test RAG Provider",
        description="Test RAG provider for collections listing",
    )
    assert status_code == 200
    provider_id = rag_provider.id

    # Mock the RagClientConstructor to return successful collections listing
    mock_client = MockWeaviateClientFactory.create_successful_client(Mock())
    mock_constructor_instance = Mock()
    mock_constructor_instance.list_collections.return_value = (
        mock_client.list_collections()
    )
    mock_rag_client_constructor.return_value = mock_constructor_instance

    # Test collections listing
    status_code, result = client.list_rag_provider_collections(
        provider_id=provider_id,
    )

    # Verify the response
    assert status_code == 200
    assert result is not None
    assert result.count == 2
    assert len(result.rag_provider_collections) == 2
    assert result.rag_provider_collections[0].identifier == "test_collection_1"
    assert (
        result.rag_provider_collections[0].description
        == "Test collection 1 for unit testing"
    )
    assert result.rag_provider_collections[1].identifier == "test_collection_2"
    assert (
        result.rag_provider_collections[1].description
        == "Test collection 2 for unit testing"
    )

    # Verify the constructor was called correctly
    mock_rag_client_constructor.assert_called_once()
    mock_constructor_instance.list_collections.assert_called_once()

    # Clean up
    status_code = client.delete_rag_provider(provider_id)
    assert status_code == 204
    status_code = client.delete_task(task_id)
    assert status_code == 204
