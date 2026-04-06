"""add index on trace_metadata end_time for retention queries

Revision ID: a1b2c3d4e5f6
Revises: 04c5e8528072
Create Date: 2026-04-06 15:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "04c5e8528072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "idx_traces_end_time",
        "trace_metadata",
        ["end_time"],
    )


def downgrade() -> None:
    op.drop_index("idx_traces_end_time", table_name="trace_metadata")
