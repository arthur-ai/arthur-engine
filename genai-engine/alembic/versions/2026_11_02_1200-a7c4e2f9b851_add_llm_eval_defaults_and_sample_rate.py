"""add llm_eval_defaults to secret_storage and sample_rate to continuous_evals

Revision ID: a7c4e2f9b851
Revises: e5a9c3b71f04
Create Date: 2026-11-02 12:00:00.000000

secret_storage.llm_eval_defaults holds a provider's default reasoning settings
for LLM eval calls. continuous_evals.sample_rate is the fraction of traces a
continuous eval runs on.

Both are nullable with no backfill: NULL sends no reasoning settings and
evaluates every trace, which is the behaviour before this revision.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "a7c4e2f9b851"
down_revision = "e5a9c3b71f04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "secret_storage",
        sa.Column("llm_eval_defaults", sa.JSON(), nullable=True),
    )
    op.add_column(
        "continuous_evals",
        sa.Column("sample_rate", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("continuous_evals", "sample_rate")
    op.drop_column("secret_storage", "llm_eval_defaults")
