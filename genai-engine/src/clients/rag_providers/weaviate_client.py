import weaviate
from fastapi import HTTPException
from weaviate.classes.init import Auth
from weaviate.exceptions import WeaviateQueryError

from clients.rag_providers.rag_provider_client import RagProviderClient
from schemas.enums import ConnectionCheckOutcome
from schemas.internal_schemas import (
    ApiKeyRagAuthenticationConfig,
    RagProviderConfiguration,
)
from schemas.request_schemas import RagVectorSimilarityTextSearchSettingRequest
from schemas.response_schemas import (
    ConnectionCheckResult,
    RagProviderSimilarityTextSearchResponse,
    WeaviateSimilaritySearchMetadata,
    WeaviateSimilaritySearchTextResult,
    WeaviateSimilarityTextSearchResponse,
)


class WeaviateClient(RagProviderClient):
    def __init__(self, provider_config: RagProviderConfiguration) -> None:
        if not isinstance(
            provider_config.authentication_config,
            ApiKeyRagAuthenticationConfig,
        ):
            raise HTTPException(
                status_code=404,
                detail=f"Unsupported authentication method: {provider_config.authentication_config.authentication_method}",
            )

        self.host_url = provider_config.authentication_config.host_url
        self.api_key = provider_config.authentication_config.api_key
        self.client = weaviate.connect_to_weaviate_cloud(
            cluster_url=str(self.host_url),
            auth_credentials=Auth.api_key(self.api_key.get_secret_value()),
        )

        super().__init__(provider_config)

    def test_connection(self) -> ConnectionCheckResult:
        # the constructor initiates the connection to weaviate and there doesn't seem to be a good way
        # to skip it—for now if the request gets here we can consider it to have passed.
        if not self.client.is_connected():
            return ConnectionCheckResult(
                connection_check_outcome=ConnectionCheckOutcome.FAILED,
                failure_reason=f"No error was raised on connection creation but the client was not connected afterwards.",
            )

        return ConnectionCheckResult(
            connection_check_outcome=ConnectionCheckOutcome.PASSED,
        )

    def vector_similarity_text_search(
        self,
        settings_request: RagVectorSimilarityTextSearchSettingRequest,
    ) -> RagProviderSimilarityTextSearchResponse:
        weaviate_settings = settings_request.settings
        collection = self.client.collections.use(weaviate_settings.collection_name)
        try:
            response = collection.query.near_text(
                # collection_name should not be passed as an argument to this function - it was already used above
                **weaviate_settings.model_dump(
                    exclude={"collection_name", "rag_provider"},
                ),
            )
        except WeaviateQueryError as e:
            # raise query errors cleanly so the user knows what went wrong
            # (eg. no vectorizer configured for the collection)
            raise HTTPException(
                status_code=400,
                detail=f"Error querying Weaviate: {e}.",
            )

        return RagProviderSimilarityTextSearchResponse(
            response=WeaviateSimilarityTextSearchResponse(
                objects=[
                    WeaviateSimilaritySearchTextResult(
                        uuid=obj.uuid,
                        metadata=(
                            WeaviateSimilaritySearchMetadata(
                                creation_time=obj.metadata.creation_time,
                                last_update_time=obj.metadata.last_update_time,
                                distance=obj.metadata.distance,
                                certainty=obj.metadata.certainty,
                                score=obj.metadata.score,
                                explain_score=obj.metadata.explain_score,
                                is_consistent=obj.metadata.is_consistent,
                            )
                            if hasattr(obj, "metadata")
                            else None
                        ),
                        properties=obj.properties,
                        vector=obj.vector if hasattr(obj, "vector") else None,
                    )
                    for obj in response.objects
                ],
            ),
        )

    def __del__(self):
        # client may not have been initialized if clean up happens after a failed class instantiation so validate
        # before closing the connection
        if hasattr(self, "client"):
            self.client.close()
