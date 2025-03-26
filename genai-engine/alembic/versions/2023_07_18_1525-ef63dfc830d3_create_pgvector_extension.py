"""Create pgvector extension

Revision ID: ef63dfc830d3
Revises: ae36d2222a3f
Create Date: 2023-07-18 15:25:20.487820

"""

import os

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = "ef63dfc830d3"
down_revision = "ae36d2222a3f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if (
        os.environ.get("GENAI_ENGINE_CHAT_ENABLED") == "enabled"
        or os.environ.get("CHAT_ENABLED") == "enabled"
    ):
        conn = op.get_bind()
        conn.execute(text("create extension if not exists vector"))


def downgrade() -> None:
    pass
