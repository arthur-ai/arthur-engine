"""drop task_polling_state

Revision ID: 5510bc73cbd4
Revises: 8b1d4f6a2c37
Create Date: 2026-10-16 14:00:00.000000

The GCP trace poller was the table's only writer, and it is gone, along with the model and
the agent-tasks read of `last_fetched`. The table outlived them by one release: migrations
run at pod start, and during a rolling upgrade older pods still read it.

The downgrade recreates the table empty. Its rows were the poller's last-pull times, which
nothing writes any more. It is only for a release that still has the poller (before
2.1.1023): its first poll after the downgrade finds no last-pull time and re-pulls up to 30
days of GCP traces, so roll back to such a release only with GOOGLE_CLOUD_PROJECT unset,
which keeps its poller off.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "5510bc73cbd4"
down_revision = "8b1d4f6a2c37"
branch_labels = None
depends_on = None

TABLE = "task_polling_state"


def upgrade() -> None:
    op.drop_table(TABLE)


def downgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("last_fetched", sa.TIMESTAMP(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("task_id"),
    )
