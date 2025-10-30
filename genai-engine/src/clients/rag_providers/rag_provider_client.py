from abc import ABC, abstractmethod

from schemas.internal_schemas import RagProviderConfiguration
from schemas.request_schemas import RagVectorSimilarityTextSearchSettingRequest
from schemas.response_schemas import (
    ConnectionCheckResult,
    RagProviderSimilarityTextSearchResponse,
)


class RagProviderClient(ABC):
    def __init__(self, provider_config: RagProviderConfiguration) -> None:
        self.provider_config = provider_config

    @abstractmethod
    def test_connection(self) -> ConnectionCheckResult:
        raise NotImplementedError

    @abstractmethod
    def vector_similarity_text_search(
        self,
        settings_request: RagVectorSimilarityTextSearchSettingRequest,
    ) -> RagProviderSimilarityTextSearchResponse:
        raise NotImplementedError
