"""add judge_changed_at to continuous_evals

Revision ID: 9c2f4a7d1e35
Revises: a7c4e2f9b851
Create Date: 2026-11-03 19:00:00.000000

continuous_evals.judge_changed_at is when the eval last switched evaluator (name
or version), so spend estimates price runs from the current judge only. Nullable
with no backfill: NULL prices from every run in the window, which is the
behaviour before this revision and right for evals that never switched.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "9c2f4a7d1e35"
down_revision = "a7c4e2f9b851"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "continuous_evals",
        sa.Column("judge_changed_at", sa.TIMESTAMP(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("continuous_evals", "judge_changed_at")
