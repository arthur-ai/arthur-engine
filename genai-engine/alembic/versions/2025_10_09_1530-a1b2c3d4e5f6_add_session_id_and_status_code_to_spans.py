"""add session_id and status_code to spans

Revision ID: a1b2c3d4e5f6
Revises: bf11fb90a818
Create Date: 2025-10-09 15:30:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "bf11fb90a818"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add session_id column (nullable)
    op.add_column("spans", sa.Column("session_id", sa.String(), nullable=True))

    # Add status_code column (non-null with default)
    op.add_column(
        "spans",
        sa.Column(
            "status_code",
            sa.String(),
            nullable=False,
            server_default=sa.text("'Unset'"),
        ),
    )


def downgrade() -> None:
    # Remove the columns in reverse order
    op.drop_column("spans", "status_code")
    op.drop_column("spans", "session_id")
