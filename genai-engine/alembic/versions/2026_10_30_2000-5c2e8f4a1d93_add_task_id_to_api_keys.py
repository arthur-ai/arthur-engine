"""add task_id to api_keys

Revision ID: 5c2e8f4a1d93
Revises: 8b1d4f6a2c37
Create Date: 2026-10-30 20:00:00.000000

Lets an API key be scoped to one task. NULL keeps every existing key's behaviour;
nothing is backfilled. Deleting a task deletes the keys scoped to it.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "5c2e8f4a1d93"
down_revision = "8b1d4f6a2c37"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("api_keys", sa.Column("task_id", sa.String(), nullable=True))
    op.create_foreign_key(
        "fk_api_keys_task_id",
        "api_keys",
        "tasks",
        ["task_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_api_keys_task_id",
        "api_keys",
        ["task_id"],
        postgresql_where=sa.text("task_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_api_keys_task_id", table_name="api_keys")
    op.drop_constraint("fk_api_keys_task_id", "api_keys", type_="foreignkey")
    op.drop_column("api_keys", "task_id")
