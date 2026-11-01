"""add observations to task_provenance_sources

Revision ID: e5a9c3b71f04
Revises: 8b1d4f6a2c37
Create Date: 2026-10-31 12:00:00.000000

Stores what each report saw of its record -- its version, install path, host -- beside
the address. A task's creation source holds only what the first report saw and is never
rewritten, so without this a discovered agent's version is lost after its first scan.
The row also keeps the version before its latest change, as `previous_version`.

Nullable, and nothing is backfilled: rows written before this revision never kept their
record's observations, and the next scan that reports each one fills them in.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "e5a9c3b71f04"
down_revision = "8b1d4f6a2c37"
branch_labels = None
depends_on = None

TABLE = "task_provenance_sources"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column(
            "observations",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(TABLE, "observations")
