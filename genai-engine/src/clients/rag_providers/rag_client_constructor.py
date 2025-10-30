from fastapi import HTTPException

from clients.rag_providers.rag_provider_client import RagProviderClient
from clients.rag_providers.weaviate_client import WeaviateClient
from schemas.enums import ConnectionCheckOutcome, RagAPIKeyAuthenticationProviderEnum
from schemas.internal_schemas import RagProviderConfiguration
from schemas.request_schemas import (
    RagVectorKeywordSearchSettingRequest,
    RagVectorSimilarityTextSearchSettingRequest,
)
from schemas.response_schemas import (
    ConnectionCheckResult,
    RagProviderQueryResponse,
)


class RagClientConstructor:
    """Responsible for picking a RAG client."""

    def __init__(self, provider_config: RagProviderConfiguration) -> None:
        self.provider_config = provider_config

    def pick_rag_provider_client(self) -> RagProviderClient:
        rag_provider = self.provider_config.authentication_config.rag_provider
        match rag_provider:
            case RagAPIKeyAuthenticationProviderEnum.WEAVIATE:
                return WeaviateClient(self.provider_config)
            case _:
                raise HTTPException(
                    status_code=404,
                    detail=f"Unsupported rag provider: {self.provider_config.authentication_config.rag_provider}",
                )

    def execute_test_connection(self) -> ConnectionCheckResult:
        """Some clients, like weaviate, initialize the connection in the client __init__ function. So we'll
        wrap the client initialization and test_connection calls in this parent executor to make sure we're raising
        all errors cleanly to the user."""
        try:
            rag_client = self.pick_rag_provider_client()
        except Exception as e:
            return ConnectionCheckResult(
                connection_check_outcome=ConnectionCheckOutcome.FAILED,
                failure_reason=str(e),
            )
        return rag_client.test_connection()

    def execute_similarity_text_search(
        self,
        settings_request: RagVectorSimilarityTextSearchSettingRequest,
    ) -> RagProviderQueryResponse:
        rag_client = self.pick_rag_provider_client()
        return rag_client.vector_similarity_text_search(settings_request)

    def execute_keyword_search(
        self,
        settings_request: RagVectorKeywordSearchSettingRequest,
    ) -> RagProviderQueryResponse:
        rag_client = self.pick_rag_provider_client()
        return rag_client.keyword_search(settings_request)
