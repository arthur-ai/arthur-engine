from typing import List

from scorer.llm_client import get_llm_executor


class EmbeddingModel:
    def __init__(self):
        """Creates an embedding model to parse documents and queries

        :param: model_name: optional model to compute embeddings
        """
        self.model = get_llm_executor().get_embeddings_model()

    def embed_query(self, query: str) -> List[float]:
        """Embeds a specific query

        :param query: user query
        """
        r = self.model.embed_query(query)

        return r
