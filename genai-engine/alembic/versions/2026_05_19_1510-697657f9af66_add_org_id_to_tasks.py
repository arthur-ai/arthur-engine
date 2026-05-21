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
from utils.constants import DEFAULT_ORG_ID, SYSTEM_ORG_ID

# revision identifiers, used by Alembic.
revision = "697657f9af66"
down_revision = "514464b8ca3d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("org_id", sa.UUID(), nullable=True))

    # Backfill against the well-known UUIDs seeded by the
    # create_organizations_table migration. UUIDs sourced from
    # `utils.constants` — single source of truth shared with app code.
    op.execute(
        sa.text(
            "UPDATE tasks SET org_id = :system_id WHERE is_system_task = TRUE"
        ).bindparams(system_id=str(SYSTEM_ORG_ID))
    )
    op.execute(
        sa.text(
            "UPDATE tasks SET org_id = :default_id WHERE org_id IS NULL"
        ).bindparams(default_id=str(DEFAULT_ORG_ID))
    )

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
