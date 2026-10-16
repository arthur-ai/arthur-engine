"""drop task_polling_state

Revision ID: 5510bc73cbd4
Revises: d2ffff9e0a56
Create Date: 2026-10-16 14:00:00.000000

The GCP trace poller was the table's only writer, and it is gone, along with the model and
the agent-tasks read of `last_fetched`. The table outlived them by one release: migrations
run at pod start, and during a rolling upgrade older pods still read it.

The downgrade recreates the table empty. Its rows were the poller's last-pull times, which
nothing writes any more.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "5510bc73cbd4"
down_revision = "d2ffff9e0a56"
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
