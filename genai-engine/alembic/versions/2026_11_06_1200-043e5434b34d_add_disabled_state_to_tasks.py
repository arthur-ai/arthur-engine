"""add disabled state to tasks

Revision ID: 043e5434b34d
Revises: a7c4e2f9b851
Create Date: 2026-11-06 12:00:00.000000

tasks.disabled is the kill switch: a disabled task rejects every task-scoped
prompt and response validation until it is re-enabled. disabled_reason and
disabled_at record why and when it was turned off.

disabled is NOT NULL with a server default of false, so existing rows backfill
to enabled. The other two are nullable with no backfill.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "043e5434b34d"
down_revision = "a7c4e2f9b851"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column(
            "disabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "tasks",
        sa.Column("disabled_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "tasks",
        sa.Column("disabled_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tasks", "disabled_at")
    op.drop_column("tasks", "disabled_reason")
    op.drop_column("tasks", "disabled")
