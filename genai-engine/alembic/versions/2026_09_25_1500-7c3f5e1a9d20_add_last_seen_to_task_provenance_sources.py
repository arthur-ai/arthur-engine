"""add last_seen to task_provenance_sources

Revision ID: 7c3f5e1a9d20
Revises: 4e7a2c9d1b35
Create Date: 2026-09-25 15:00:00.000000

Stores each report's `last_seen`: when the source itself last observed the agent, as
the discovered record says, beside `last_reported_at`, which is only when a scan last
handed the finding over. A source can keep reporting an agent it has not seen in
weeks, and the Platform needs to tell the two apart.

Nullable, and nothing is backfilled: rows written before this revision never had the
record's value, and the next scan that reports each one fills it in.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "7c3f5e1a9d20"
down_revision = "4e7a2c9d1b35"
branch_labels = None
depends_on = None

TABLE = "task_provenance_sources"


def upgrade() -> None:
    op.add_column(TABLE, sa.Column("last_seen", sa.TIMESTAMP(), nullable=True))


def downgrade() -> None:
    op.drop_column(TABLE, "last_seen")
