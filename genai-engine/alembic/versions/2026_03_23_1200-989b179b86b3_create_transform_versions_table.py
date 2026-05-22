"""create transform_versions table

Revision ID: 989b179b86b3
Revises: add_api_version_secret
Create Date: 2026-03-23 12:00:00.000000

"""

import json
import uuid

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision = "989b179b86b3"
down_revision = "add_api_version_secret"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transform_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("transform_id", sa.UUID(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(
            ["transform_id"],
            ["trace_transforms.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "transform_id",
            "version_number",
            name="uq_transform_version_number",
        ),
    )
    op.create_index(
        op.f("ix_transform_versions_transform_id"),
        "transform_versions",
        ["transform_id"],
        unique=False,
    )

    # Backfill: seed a v1 snapshot for every existing transform
    conn = op.get_bind()
    transforms = conn.execute(
        text("SELECT id, task_id, definition, created_at FROM trace_transforms"),
    ).fetchall()

    if transforms:
        rows = [
            {
                "id": str(uuid.uuid4()),
                "transform_id": str(row.id),
                "version_number": 1,
                "definition": json.dumps(row.definition),
                "created_at": row.created_at,
            }
            for row in transforms
        ]
        conn.execute(
            text(
                """
                INSERT INTO transform_versions
                    (id, transform_id, version_number, definition, created_at)
                VALUES
                    (:id, :transform_id, :version_number, CAST(:definition AS json), :created_at)
                """,
            ),
            rows,
        )

    op.drop_column("trace_transforms", "definition")


def downgrade() -> None:
    # Add definition column back to trace_transforms
    op.add_column(
        "trace_transforms",
        sa.Column("definition", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.alter_column("trace_transforms", "definition", server_default=None)

    # Restore each transform's definition from its latest version snapshot
    conn = op.get_bind()
    latest_versions = conn.execute(
        text(
            """
            SELECT DISTINCT ON (transform_id)
                transform_id, definition
            FROM transform_versions
            ORDER BY transform_id, version_number DESC
            """,
        ),
    ).fetchall()

    for row in latest_versions:
        conn.execute(
            text(
                "UPDATE trace_transforms SET definition = CAST(:definition AS json) WHERE id = :transform_id",
            ),
            {
                "definition": json.dumps(row.definition),
                "transform_id": str(row.transform_id),
            },
        )

    op.drop_index(
        op.f("ix_transform_versions_transform_id"),
        table_name="transform_versions",
        if_exists=True,
    )
    op.drop_table("transform_versions", if_exists=True)
