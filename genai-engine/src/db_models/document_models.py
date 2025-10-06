from typing import List

import pgvector.sqlalchemy
from sqlalchemy import Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db_models.base import OUTPUT_DIMENSION_SIZE_ADA_002, Base


class DatabaseDocument(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    owner_id: Mapped[str] = mapped_column(String)
    is_global: Mapped[bool] = mapped_column(Boolean)
    type: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    path: Mapped[str] = mapped_column(String)
    embeddings: Mapped[List["DatabaseEmbedding"]] = relationship(
        "DatabaseEmbedding",
        cascade="all,delete",
        back_populates="documents",
    )


class DatabaseEmbedding(Base):
    __tablename__ = "embeddings"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    document_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("documents.id"),
        index=True,
    )
    text: Mapped[str] = mapped_column(String)
    seq_num: Mapped[int] = mapped_column(Integer)
    embedding: Mapped[List[float]] = mapped_column(
        pgvector.sqlalchemy.Vector(OUTPUT_DIMENSION_SIZE_ADA_002),
    )
    documents = relationship("DatabaseDocument", back_populates="embeddings")


index = Index(
    "my_index",
    DatabaseEmbedding.embedding,
    postgresql_using="ivfflat",
    postgresql_with={"lists": 100},
    postgresql_ops={"embedding": "vector_l2_ops"},
)


class DatabaseEmbeddingReference(Base):
    __tablename__ = "inference_embeddings"
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    inference_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("inferences.id"),
        index=True,
    )
    embedding_id: Mapped[str] = mapped_column(String, ForeignKey("embeddings.id"))
    embedding: Mapped["DatabaseEmbedding"] = relationship(
        "DatabaseEmbedding",
        cascade="all,delete",
        lazy="joined",
    )
