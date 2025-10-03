import uuid
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from chat.embedding import EmbeddingModel
from db_models import DatabaseDocument, DatabaseEmbedding
from schemas.internal_schemas import Embedding

CHUNK_SIZE = 512


def chunk_text(words: List[str], chunk_size: int) -> List[str]:
    """Chunks a list of words into smaller lists of given chunk size

    :param words: list of words to be chunked
    :param chunk_size: size of each chunk
    """
    chunks = []
    start_index = 0
    end_index = chunk_size

    while start_index < len(words):
        chunk = " ".join(words[start_index : min(end_index, len(words))])
        chunks.append(chunk)
        start_index = end_index
        end_index += chunk_size

    return chunks


class EmbeddingRepository:
    def __init__(self, db_session: Session, embedding_model: EmbeddingModel):
        """Initializes repository for basic operations on the embedding table"""
        self.db_session = db_session
        self.embedding_model = embedding_model

    def add_embeddings(
        self,
        words: List[str],
        document_id: str,
        chunk_size: int = CHUNK_SIZE,
    ) -> List[Embedding]:
        """Adds all the embeddings from a document to the embeddings table

        :param words: list of words to be converted
        :param document_id: id of the document in the documents table
        :param chunk_size: chunk size of the document
        """
        embeddings: List[DatabaseEmbedding] = []

        # chunk the texts
        chunks = chunk_text(words, chunk_size)

        for seq, word_sentence in enumerate(chunks):
            embedding_row = DatabaseEmbedding(
                id=str(uuid.uuid4()),
                document_id=document_id,
                text=word_sentence,
                seq_num=seq,
                embedding=self.embedding_model.embed_query(word_sentence),
            )
            embeddings.append(embedding_row)

        self.db_session.add_all(embeddings)
        self.db_session.commit()

        return [Embedding._from_database_model(e) for e in embeddings]

    def get_embeddings(
        self,
        user_query: str,
        file_ids: List[str],
        limit: int = 5,
    ) -> list[Embedding]:
        """Gets most similar embeddings to the given user query

        :param user_query: user query
        :param file_ids: documents to retrieve from
        :param limit: number of embeddings returned
        """
        # convert query to embedding
        user_embedding = self.embedding_model.embed_query(user_query)

        query = (
            select(DatabaseEmbedding)
            .join(
                DatabaseDocument,
                DatabaseEmbedding.document_id == DatabaseDocument.id,
            )
            .filter(DatabaseDocument.id.in_(file_ids))
            .order_by(DatabaseEmbedding.embedding.l2_distance(user_embedding))
            .limit(limit)
        )

        similar_embeddings = self.db_session.scalars(query)

        return [Embedding._from_database_model(e) for e in similar_embeddings]
