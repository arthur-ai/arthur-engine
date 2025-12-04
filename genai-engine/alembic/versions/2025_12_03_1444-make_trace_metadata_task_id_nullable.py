"""make trace_metadata task_id nullable

Revision ID: a1b2c3d4e5f67890
Revises: 714d70516fae
Create Date: 2025-12-03 14:44:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f67890"
down_revision = "714d70516fae"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make task_id nullable in trace_metadata table
    op.alter_column(
        "trace_metadata",
        "task_id",
        existing_type=sa.String(),
        nullable=True,
        existing_nullable=False,
    )


def downgrade() -> None:
    # Update NULL task_id to the UUID zero value string to avoid failure.
    op.execute(
        """
        UPDATE trace_metadata
        SET task_id = '00000000-0000-0000-0000-000000000000'
        WHERE task_id IS NULL;
        """
    )
    op.alter_column(
        "trace_metadata",
        "task_id",
        existing_type=sa.String(),
        nullable=False,
        existing_nullable=True,
    )

