"""create organizations table

Revision ID: mt_create_organizations
Revises: b3f7a2c1d9e0
Create Date: 2026-05-19 10:00:00

Multi-tenancy step 1 of 5. Creates the `organizations` table that owns
tasks and (transitively) every task-scoped resource. Seeds two rows:

  - `default` — the bucket for pre-multi-tenancy tasks and any admin-
    created task without tenant context. Tenants never carry org_id = default.
  - `system`  — internal tasks (is_system_task=True) live here. Tenants
    never carry org_id = system.

Both orgs are created during this migration. Subsequent migrations
backfill `tasks.org_id` from these orgs.

Partial unique index `uq_organizations_is_system_true` enforces "at most
one row with is_system=TRUE."
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "mt_create_organizations"
down_revision = "b3f7a2c1d9e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "is_system",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organizations"),
        sa.UniqueConstraint("name", name="uq_organizations_name"),
    )
    op.create_index(
        "uq_organizations_is_system_true",
        "organizations",
        ["is_system"],
        unique=True,
        postgresql_where=sa.text("is_system = TRUE"),
    )

    op.execute(
        "INSERT INTO organizations (name, is_system) VALUES "
        "('default', FALSE), ('system', TRUE)"
    )


def downgrade() -> None:
    op.drop_index("uq_organizations_is_system_true", table_name="organizations")
    op.drop_table("organizations")
