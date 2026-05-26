"""create_onboarding_tables

Revision ID: d4e5f6a7b8c9
Revises: 7e1c3a4b5d2f
Create Date: 2026-05-19 12:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "d4e5f6a7b8c9"
down_revision = "7e1c3a4b5d2f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "onboarding_submissions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("form_variant", sa.String(), nullable=True),
        sa.Column("form_data", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("onboarding_submissions")
