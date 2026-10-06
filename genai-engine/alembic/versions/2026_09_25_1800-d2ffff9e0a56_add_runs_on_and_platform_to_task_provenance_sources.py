"""add runs_on and platform to task_provenance_sources

Revision ID: d2ffff9e0a56
Revises: 7c3f5e1a9d20
Create Date: 2026-09-25 18:00:00.000000

Stores what each report said about where the agent runs: `runs_on`, the location of the
machine, and `platform`, its OS. A task's provenance serves both as one scalar each, and
without a stored answer every discovered agent read `runs_on=unknown` -- a Jamf laptop
could not be told apart from a SIEM row.

Nullable, and nothing is backfilled: rows written before this revision never carried the
record's values, and the next scan that reports each one fills them in.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "d2ffff9e0a56"
down_revision = "7c3f5e1a9d20"
branch_labels = None
depends_on = None

TABLE = "task_provenance_sources"


def upgrade() -> None:
    op.add_column(TABLE, sa.Column("runs_on", sa.String(), nullable=True))
    op.add_column(TABLE, sa.Column("platform", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column(TABLE, "platform")
    op.drop_column(TABLE, "runs_on")
