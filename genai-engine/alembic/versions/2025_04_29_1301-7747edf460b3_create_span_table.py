"""create_span_table

Revision ID: 7747edf460b3
Revises: 5c2dd37eed9e
Create Date: 2025-04-29 13:01:29.420778

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "7747edf460b3"
down_revision = "5c2dd37eed9e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "spans",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("trace_id", sa.String(), nullable=False, index=True),
        sa.Column("span_id", sa.String(), nullable=False, index=True),
        sa.Column("start_time", sa.TIMESTAMP(), nullable=False),
        sa.Column("end_time", sa.TIMESTAMP(), nullable=False),
        sa.Column(
            "task_id",
            sa.String(),
            sa.ForeignKey("tasks.id"),
            nullable=True,
            index=True,
        ),
        sa.Column("raw_data", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            index=True,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )


def downgrade() -> None:
    op.drop_table("spans")
