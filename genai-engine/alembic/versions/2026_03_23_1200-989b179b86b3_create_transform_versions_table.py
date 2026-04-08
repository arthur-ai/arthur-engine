"""create transform_versions table

Revision ID: 989b179b86b3
Revises: 04c5e8528072
Create Date: 2026-03-23 12:00:00.000000

"""

import uuid

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision = "989b179b86b3"
down_revision = "04c5e8528072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transform_versions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("transform_id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("config_snapshot", sa.JSON(), nullable=False),
        sa.Column("author", sa.String(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            ondelete="CASCADE",
        ),
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
    op.create_index(
        op.f("ix_transform_versions_task_id"),
        "transform_versions",
        ["task_id"],
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
                "task_id": row.task_id,
                "version_number": 1,
                "config_snapshot": row.definition,
                "author": None,
                "created_at": row.created_at,
            }
            for row in transforms
        ]
        conn.execute(
            text(
                """
                INSERT INTO transform_versions
                    (id, transform_id, task_id, version_number, config_snapshot, author, created_at)
                VALUES
                    (:id, :transform_id, :task_id, :version_number, :config_snapshot::jsonb, :author, :created_at)
                """,
            ),
            rows,
        )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_transform_versions_task_id"),
        table_name="transform_versions",
        if_exists=True,
    )
    op.drop_index(
        op.f("ix_transform_versions_transform_id"),
        table_name="transform_versions",
        if_exists=True,
    )
    op.drop_table("transform_versions", if_exists=True)
