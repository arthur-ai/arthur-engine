"""add api_version to secret_storage

Revision ID: add_api_version_secret
Revises: f15ac7955e6f
Create Date: 2026-04-30 10:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_api_version_secret"
down_revision = "f15ac7955e6f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "secret_storage",
        sa.Column("api_version", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM secret_storage WHERE secret_type = 'model_provider' AND name = 'azure'",
    )
    op.drop_column("secret_storage", "api_version")
