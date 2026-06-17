"""add token limit to organizations

Revision ID: 5e84b8d7aa1f
Revises: e1f2a3b4c5d6
Create Date: 2026-06-04 10:00:00.000000

Adds the tenant token-credit columns introduced for UP-4390.

  tokens_limit  BIGINT NULL                 -- NULL = unlimited.
  tokens_used   BIGINT NOT NULL DEFAULT 0   -- monotonic counter, never reset.

Default org and system org keep tokens_limit = NULL (unmetered).
Existing tenant orgs are backfilled with the default credit allocation
(`DEFAULT_TENANT_TOKEN_LIMIT`) so they don't suddenly become unmetered
either. New tenant signups receive the same value via
Config.default_tenant_token_limit() at creation time.
"""

import sqlalchemy as sa

from alembic import op
from utils.constants import (
    DEFAULT_ORG_ID,
    DEFAULT_TENANT_TOKEN_LIMIT,
    SYSTEM_ORG_ID,
)

# revision identifiers, used by Alembic.
revision = "5e84b8d7aa1f"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("tokens_limit", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column(
            "tokens_used",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )

    # Backfill: every pre-existing tenant org gets the default credit cap.
    # Default and system orgs explicitly keep tokens_limit = NULL so they
    # remain unmetered. UUIDs sourced from utils.constants for single
    # source of truth with app code.
    op.execute(
        sa.text(
            "UPDATE organizations "
            "SET tokens_limit = :default_limit "
            "WHERE id NOT IN (:default_org, :system_org)"
        ).bindparams(
            default_limit=DEFAULT_TENANT_TOKEN_LIMIT,
            default_org=str(DEFAULT_ORG_ID),
            system_org=str(SYSTEM_ORG_ID),
        )
    )


def downgrade() -> None:
    op.drop_column("organizations", "tokens_used")
    op.drop_column("organizations", "tokens_limit")
