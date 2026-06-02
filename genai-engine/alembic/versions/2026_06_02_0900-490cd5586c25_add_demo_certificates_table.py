"""add demo_certificates table

Revision ID: 490cd5586c25
Revises: 7e1c3a4b5d2f
Create Date: 2026-06-02 09:00:00.000000

Stores PNG certificate images for demo walkthrough completions so that
users can share a stable URL to their certificate. Keyed by UUID; no
foreign key to tasks or users because certificates are issued to
unauthenticated demo participants.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "490cd5586c25"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "demo_certificates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("image", sa.LargeBinary(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("demo_certificates")
