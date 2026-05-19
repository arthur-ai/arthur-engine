"""add org_id to api_keys (nullable)

Revision ID: mt_api_keys_org_id
Revises: mt_tasks_org_id
Create Date: 2026-05-19 10:20:00

Multi-tenancy step 3 of 5. Adds `api_keys.org_id` as NULLABLE so existing
keys stay admin (cross-org). Tenant keys minted by the future signup flow
will carry a non-null org_id.

Partial index covers only the tenant rows so the admin-key common case
doesn't pay an index lookup.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "mt_api_keys_org_id"
down_revision = "mt_tasks_org_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("api_keys", sa.Column("org_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_api_keys_org_id_organizations",
        "api_keys",
        "organizations",
        ["org_id"],
        ["id"],
    )
    op.create_index(
        "ix_api_keys_org_id",
        "api_keys",
        ["org_id"],
        unique=False,
        postgresql_where=sa.text("org_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_api_keys_org_id", table_name="api_keys")
    op.drop_constraint(
        "fk_api_keys_org_id_organizations", "api_keys", type_="foreignkey"
    )
    op.drop_column("api_keys", "org_id")
