"""add trace_id to dataset_version_rows

Revision ID: ea519bf96e9c
Revises: 5e84b8d7aa1f
Create Date: 2026-07-23 12:00:00.000000

Stores the originating trace ID on dataset rows created from traces so
records can link back to their source trace. Nullable with no backfill:
pre-existing rows have no recorded source trace.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "ea519bf96e9c"
down_revision = "5e84b8d7aa1f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dataset_version_rows",
        sa.Column("trace_id", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("dataset_version_rows", "trace_id")
