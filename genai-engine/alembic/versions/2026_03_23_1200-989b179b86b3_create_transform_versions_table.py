"""create transform_versions table

Revision ID: 989b179b86b3
Revises: 04c5e8528072
Create Date: 2026-03-23 12:00:00.000000

"""

import sqlalchemy as sa

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


def downgrade() -> None:
    op.drop_index(
        op.f("ix_transform_versions_task_id"),
        table_name="transform_versions",
    )
    op.drop_index(
        op.f("ix_transform_versions_transform_id"),
        table_name="transform_versions",
    )
    op.drop_table("transform_versions")
