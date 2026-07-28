"""add model_whitelist to secret_storage

Revision ID: b3f2a91c4d17
Revises: ea519bf96e9c
Create Date: 2026-07-27 12:00:00.000000

Stores an admin-curated list of models to expose for a provider.
Nullable with no backfill: NULL means unfiltered, which preserves existing
behaviour for every already-configured provider.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "b3f2a91c4d17"
down_revision = "ea519bf96e9c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "secret_storage",
        sa.Column("model_whitelist", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("secret_storage", "model_whitelist")
