"""add transform_version_id to continuous_evals

Revision ID: b3f7a2c1d9e0
Revises: 989b179b86b3
Create Date: 2026-04-08 12:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "b3f7a2c1d9e0"
down_revision = "989b179b86b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "continuous_evals",
        sa.Column("transform_version_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_continuous_evals_transform_version_id",
        "continuous_evals",
        "transform_versions",
        ["transform_version_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_continuous_evals_transform_version_id",
        "continuous_evals",
        type_="foreignkey",
    )
    op.drop_column("continuous_evals", "transform_version_id")
