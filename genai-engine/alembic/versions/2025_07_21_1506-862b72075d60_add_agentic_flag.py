"""add_agentic_flag

Revision ID: 862b72075d60
Revises: 7747edf460b3
Create Date: 2025-07-21 15:06:40.917636

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "862b72075d60"
down_revision = "7747edf460b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_agentic column to tasks table with default value False
    op.add_column(
        "tasks",
        sa.Column(
            "is_agentic",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    # Remove is_agentic column from tasks table
    op.drop_column("tasks", "is_agentic")
