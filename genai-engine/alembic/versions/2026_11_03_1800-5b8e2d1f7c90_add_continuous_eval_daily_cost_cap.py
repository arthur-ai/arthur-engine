"""add daily_cost_cap_usd to continuous_evals

Revision ID: 5b8e2d1f7c90
Revises: b1194cd9c938
Create Date: 2026-11-03 18:00:00.000000

continuous_evals.daily_cost_cap_usd is the most a continuous eval may spend on
judge calls per day. Nullable with no backfill: NULL means no cap, which is the
behaviour before this revision.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "5b8e2d1f7c90"
down_revision = "b1194cd9c938"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "continuous_evals",
        sa.Column("daily_cost_cap_usd", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("continuous_evals", "daily_cost_cap_usd")
