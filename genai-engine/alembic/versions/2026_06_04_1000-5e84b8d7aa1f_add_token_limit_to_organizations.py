"""add token limit to organizations

Revision ID: 5e84b8d7aa1f
Revises: 2966018cec1d
Create Date: 2026-06-04 10:00:00.000000

Adds the tenant token-credit columns introduced for UP-4390.

  tokens_limit  BIGINT NULL                 -- NULL = unlimited.
  tokens_used   BIGINT NOT NULL DEFAULT 0   -- monotonic counter, never reset.

Existing rows (default org, system org, and any pre-existing tenant orgs)
keep tokens_limit = NULL on upgrade so nothing suddenly becomes credit-
gated. New tenant signups populate tokens_limit from
Config.default_tenant_token_limit() at creation time.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "5e84b8d7aa1f"
down_revision = "2966018cec1d"
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


def downgrade() -> None:
    op.drop_column("organizations", "tokens_used")
    op.drop_column("organizations", "tokens_limit")
