"""create organizations table

Revision ID: 514464b8ca3d
Revises: b3f7a2c1d9e0
Create Date: 2026-05-19 15:10:05.190824

Multi-tenancy step 1 of 5. Creates the `organizations` table that owns
tasks and (transitively) every task-scoped resource. Seeds two rows:

  - `default` — the bucket for pre-multi-tenancy tasks and any admin-
    created task without tenant context. Tenants never carry org_id = default.
  - `system`  — internal tasks (is_system_task=True) live here. Tenants
    never carry org_id = system.

Subsequent migrations backfill `tasks.org_id` from these orgs.

Partial unique index `uq_organizations_is_system_true` enforces "at most
one row with is_system=TRUE."

The seed INSERT uses ON CONFLICT DO NOTHING so partial-failure-then-retry
of this revision (e.g., commit aborted on the partial index validation)
doesn't double-insert.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "514464b8ca3d"
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
        "('default', FALSE), ('system', TRUE) "
        "ON CONFLICT (name) DO NOTHING"
    )


def downgrade() -> None:
    op.drop_index("uq_organizations_is_system_true", table_name="organizations")
    op.drop_table("organizations")
