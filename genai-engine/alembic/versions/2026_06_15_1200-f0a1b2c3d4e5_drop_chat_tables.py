"""Drop chat (RAG document Q&A) tables and pgvector extension

Removes the documents, embeddings, and inference_embeddings tables that backed
the removed chat feature, along with the conditionally-created pgvector
extension. Uses IF EXISTS / CASCADE so the migration is safe on deployments
where chat was never enabled (the vector extension may be absent).

Revision ID: f0a1b2c3d4e5
Revises: e1f2a3b4c5d6
Create Date: 2026-06-15 12:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "f0a1b2c3d4e5"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop in FK-safe order. CASCADE clears dependent indexes/constraints, and
    # IF EXISTS keeps this idempotent on databases that never created them.
    op.execute("DROP TABLE IF EXISTS inference_embeddings CASCADE")
    op.execute("DROP TABLE IF EXISTS embeddings CASCADE")
    op.execute("DROP TABLE IF EXISTS documents CASCADE")
    # The vector extension was only ever created when chat was enabled.
    op.execute("DROP EXTENSION IF EXISTS vector")


def downgrade() -> None:
    # Best-effort structural recreation (data is not restored). Mirrors the
    # original creation migrations; the embeddings.embedding column uses the
    # pgvector type when the extension is present, otherwise falls back to text.
    op.create_table(
        "documents",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("owner_id", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("is_global", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    connection = op.get_bind()
    result = connection.execute(
        sa.text("SELECT extname FROM pg_extension WHERE extname = 'vector';"),
    ).fetchone()

    if result:
        import pgvector

        op.create_table(
            "embeddings",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("document_id", sa.String(), nullable=False),
            sa.Column("text", sa.String(), nullable=False),
            sa.Column("seq_num", sa.Integer(), nullable=False),
            sa.Column(
                "embedding",
                pgvector.sqlalchemy.Vector(dim=1536),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "vector_index",
            "embeddings",
            ["embedding"],
            unique=False,
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_l2_ops"},
        )
    else:
        op.create_table(
            "embeddings",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("document_id", sa.String(), nullable=False),
            sa.Column("text", sa.String(), nullable=False),
            sa.Column("seq_num", sa.Integer(), nullable=False),
            sa.Column("embedding", sa.String(), nullable=False),
            sa.ForeignKeyConstraint(["document_id"], ["documents.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    op.create_index(
        op.f("ix_embeddings_document_id"),
        "embeddings",
        ["document_id"],
        unique=False,
    )

    op.create_table(
        "inference_embeddings",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("inference_id", sa.String(), nullable=False),
        sa.Column("embedding_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["embedding_id"], ["embeddings.id"]),
        sa.ForeignKeyConstraint(["inference_id"], ["inferences.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_inference_embeddings_id"),
        "inference_embeddings",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_inference_embeddings_inference_id"),
        "inference_embeddings",
        ["inference_id"],
        unique=False,
    )
