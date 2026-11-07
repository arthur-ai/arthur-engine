"""add trace_filter to continuous_evals

Revision ID: c4f8a2d6e913
Revises: b1194cd9c938
Create Date: 2026-11-06 18:00:00.000000

continuous_evals.trace_filter holds the conditions a trace must meet for the eval
to judge it. Nullable with no backfill: NULL judges every sampled trace, which is
the behaviour before this revision.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "c4f8a2d6e913"
down_revision = "b1194cd9c938"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "continuous_evals",
        sa.Column("trace_filter", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("continuous_evals", "trace_filter")
