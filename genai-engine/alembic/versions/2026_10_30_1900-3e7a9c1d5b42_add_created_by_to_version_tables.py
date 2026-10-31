"""add created_by to version tables

Revision ID: 3e7a9c1d5b42
Revises: 8b1d4f6a2c37
Create Date: 2026-10-30 19:00:00.000000

Records who created each prompt version, eval version, transform version and rule:
the kind of credential (user, api_key, master_key, on_behalf_of_user), a stable id,
and a readable name.

Nullable, and nothing is backfilled: earlier rows were written without an author,
and the engine's own system and demo writes have none.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "3e7a9c1d5b42"
down_revision = "8b1d4f6a2c37"
branch_labels = None
depends_on = None

TABLES = ["agentic_prompts", "llm_evals", "transform_versions", "rules"]
COLUMNS = ["created_by_kind", "created_by_id", "created_by_name"]


def upgrade() -> None:
    for table in TABLES:
        for column in COLUMNS:
            op.add_column(table, sa.Column(column, sa.String(), nullable=True))


def downgrade() -> None:
    for table in TABLES:
        for column in reversed(COLUMNS):
            op.drop_column(table, column)
