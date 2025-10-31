from unittest.mock import Mock
from uuid import uuid4

from clients.rag_providers.rag_provider_client import RagProviderClient
from schemas.enums import ConnectionCheckOutcome
from schemas.internal_schemas import RagProviderConfiguration
from schemas.request_schemas import (
    RagKeywordSearchSettingRequest,
    RagVectorSimilarityTextSearchSettingRequest,
)
from schemas.response_schemas import (
    ConnectionCheckResult,
    RagProviderCollectionResponse,
    RagProviderQueryResponse,
    SearchRagProviderCollectionsResponse,
    WeaviateQueryResult,
    WeaviateQueryResultMetadata,
    WeaviateQueryResults,
)


class MockWeaviateClient(RagProviderClient):
    """Mock Weaviate client for testing RAG provider functionality.

    This mock simulates the behavior of the real WeaviateClient for testing purposes.
    It can be configured to simulate different scenarios like successful connections,
    connection failures, and various search results.
    """

    def __init__(self, provider_config: RagProviderConfiguration) -> None:
        super().__init__(provider_config)
        # Connection state
        self.is_connected_value = True
        self.connection_error = None

        # Search state
        self.search_error = None
        self.search_results = []

        # Collections state
        self.collections_error = None
        self.collections_results = []

    def test_connection(self) -> ConnectionCheckResult:
        """Mock test_connection method."""
        if self.connection_error:
            return ConnectionCheckResult(
                connection_check_outcome=ConnectionCheckOutcome.FAILED,
                failure_reason=self.connection_error,
            )

        if not self.is_connected_value:
            return ConnectionCheckResult(
                connection_check_outcome=ConnectionCheckOutcome.FAILED,
                failure_reason="No error was raised on connection creation but the client was not connected afterwards.",
            )

        return ConnectionCheckResult(
            connection_check_outcome=ConnectionCheckOutcome.PASSED,
        )

    def list_collections(self) -> SearchRagProviderCollectionsResponse:
        """Mock list_collections method."""
        if self.collections_error:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=400,
                detail=f"Error listing collections: {self.collections_error}.",
            )

        # Convert mock results to RagProviderCollectionResponse objects
        collections = [
            RagProviderCollectionResponse(
                identifier=result.get("identifier", "default_collection"),
                description=result.get("description"),
            )
            for result in self.collections_results
        ]

        return SearchRagProviderCollectionsResponse(
            count=len(collections),
            rag_provider_collections=collections,
        )

    def _mock_results_to_arthur_response(self) -> RagProviderQueryResponse:
        """Helper method to convert mock search results to Arthur response format.

        Reuses the same logic for both vector_similarity_text_search and keyword_search,
        similar to how the real WeaviateClient uses _client_result_to_arthur_response.
        """
        # Convert mock results to WeaviateQueryResult objects
        mock_objects = []
        for result in self.search_results:
            mock_obj = Mock()
            mock_obj.uuid = result.get("uuid", uuid4())
            mock_obj.properties = result.get("properties", {})

            # Create mock metadata object similar to Weaviate's structure
            metadata_dict = result.get("metadata", {})
            mock_metadata = Mock()
            mock_metadata.creation_time = metadata_dict.get("creation_time")
            mock_metadata.last_update_time = metadata_dict.get("last_update_time")
            mock_metadata.distance = metadata_dict.get("distance")
            mock_metadata.certainty = metadata_dict.get("certainty")
            mock_metadata.score = metadata_dict.get("score")
            mock_metadata.explain_score = metadata_dict.get("explain_score")
            mock_metadata.is_consistent = metadata_dict.get("is_consistent")

            mock_obj.metadata = mock_metadata
            mock_obj.vector = result.get("vector", None)
            mock_objects.append(mock_obj)

        return RagProviderQueryResponse(
            response=WeaviateQueryResults(
                objects=[
                    WeaviateQueryResult(
                        uuid=obj.uuid,
                        metadata=(
                            WeaviateQueryResultMetadata(
                                creation_time=obj.metadata.creation_time,
                                last_update_time=obj.metadata.last_update_time,
                                distance=obj.metadata.distance,
                                certainty=obj.metadata.certainty,
                                score=obj.metadata.score,
                                explain_score=obj.metadata.explain_score,
                                is_consistent=obj.metadata.is_consistent,
                            )
                            if hasattr(obj, "metadata") and obj.metadata
                            else None
                        ),
                        properties=obj.properties,
                        vector=obj.vector if hasattr(obj, "vector") else None,
                    )
                    for obj in mock_objects
                ],
            ),
        )

    def vector_similarity_text_search(
        self,
        settings_request: RagVectorSimilarityTextSearchSettingRequest,
    ) -> RagProviderQueryResponse:
        """Mock vector_similarity_text_search method."""
        if self.search_error:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=400,
                detail=f"Error querying Weaviate: {self.search_error}.",
            )

        return self._mock_results_to_arthur_response()

    def keyword_search(
        self,
        settings_request: RagKeywordSearchSettingRequest,
    ) -> RagProviderQueryResponse:
        """Mock keyword_search method."""
        if self.search_error:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=400,
                detail=f"Error querying Weaviate: {self.search_error}.",
            )

        return self._mock_results_to_arthur_response()


class MockWeaviateClientFactory:
    """Factory for creating mock Weaviate clients with different configurations.

    This factory provides pre-configured mock clients for common testing scenarios.
    """

    @staticmethod
    def create_successful_client(
        provider_config: RagProviderConfiguration,
    ) -> MockWeaviateClient:
        """Create a mock client that succeeds in all operations."""
        client = MockWeaviateClient(provider_config)
        client.search_results = [
            {
                "uuid": uuid4(),
                "properties": {"text": "Sample document 1", "title": "Document 1"},
                "metadata": {
                    "distance": 0.1,
                    "certainty": 0.9,
                    "score": 0.9,
                    "creation_time": None,
                    "last_update_time": None,
                    "explain_score": None,
                    "is_consistent": True,
                },
                "vector": None,
            },
            {
                "uuid": uuid4(),
                "properties": {"text": "Sample document 2", "title": "Document 2"},
                "metadata": {
                    "distance": 0.2,
                    "certainty": 0.8,
                    "score": 0.8,
                    "creation_time": None,
                    "last_update_time": None,
                    "explain_score": None,
                    "is_consistent": True,
                },
                "vector": None,
            },
        ]
        client.collections_results = [
            {
                "identifier": "test_collection_1",
                "description": "Test collection 1 for unit testing",
            },
            {
                "identifier": "test_collection_2",
                "description": "Test collection 2 for unit testing",
            },
        ]
        return client

    @staticmethod
    def create_connection_failure_client(
        provider_config: RagProviderConfiguration,
    ) -> MockWeaviateClient:
        """Create a mock client that fails connection tests."""
        client = MockWeaviateClient(provider_config)
        client.is_connected_value = False
        client.connection_error = "Connection timeout to Weaviate cluster"
        return client

    @staticmethod
    def create_empty_results_client(
        provider_config: RagProviderConfiguration,
    ) -> MockWeaviateClient:
        """Create a mock client that returns empty search results."""
        client = MockWeaviateClient(provider_config)
        client.search_results = []
        return client

    @staticmethod
    def create_custom_client(
        provider_config: RagProviderConfiguration,
        *,
        is_connected: bool = True,
        connection_error: str = None,
        search_error: str = None,
        search_results: list[dict] = None,
        collections_error: str = None,
        collections_results: list[dict] = None,
    ) -> MockWeaviateClient:
        """Create a custom mock client with specific configuration.

        Args:
            provider_config: The RAG provider configuration
            is_connected: Whether the client should report as connected
            connection_error: Error message for connection failures
            search_error: Error message for search failures
            search_results: List of search results to return
            collections_error: Error message for collections listing failures
            collections_results: List of collections to return
        """
        client = MockWeaviateClient(provider_config)
        client.is_connected_value = is_connected
        client.connection_error = connection_error
        client.search_error = search_error
        client.search_results = search_results or []
        client.collections_error = collections_error
        client.collections_results = collections_results or []
        return client
