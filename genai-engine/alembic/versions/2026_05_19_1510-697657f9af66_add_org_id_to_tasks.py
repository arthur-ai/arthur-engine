"""add org_id to tasks

Revision ID: 697657f9af66
Revises: 514464b8ca3d
Create Date: 2026-05-19 15:10:16.081085

Multi-tenancy step 2 of 5. Adds `tasks.org_id` (NOT NULL, FK to
organizations, indexed). Two-phase nullable -> backfill -> SET NOT NULL
keeps the migration safe against a live database.

Backfill:
  - tasks.is_system_task = TRUE  -> system org
  - everything else              -> default org
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "697657f9af66"
down_revision = "514464b8ca3d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("org_id", sa.UUID(), nullable=True))

    op.execute("""
        UPDATE tasks
           SET org_id = (SELECT id FROM organizations WHERE name = 'system')
         WHERE is_system_task = TRUE
        """)
    op.execute("""
        UPDATE tasks
           SET org_id = (SELECT id FROM organizations WHERE name = 'default')
         WHERE org_id IS NULL
        """)

    op.alter_column("tasks", "org_id", nullable=False)
    op.create_index(op.f("ix_tasks_org_id"), "tasks", ["org_id"], unique=False)
    op.create_foreign_key(
        "fk_tasks_org_id_organizations",
        "tasks",
        "organizations",
        ["org_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_tasks_org_id_organizations", "tasks", type_="foreignkey")
    op.drop_index(op.f("ix_tasks_org_id"), table_name="tasks")
    op.drop_column("tasks", "org_id")
