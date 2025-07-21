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
    # Add task_type column to tasks table with default value "LLM"
    op.add_column(
        "tasks",
        sa.Column(
            "task_type",
            sa.String(),
            nullable=False,
            server_default=sa.text("'LLM'"),
        ),
    )


def downgrade() -> None:
    # Remove task_type column from tasks table
    op.drop_column("tasks", "task_type")
