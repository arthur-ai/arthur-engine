"""add token limit to organizations

Revision ID: 5e84b8d7aa1f
Revises: e1f2a3b4c5d6
Create Date: 2026-06-04 10:00:00.000000

Adds the tenant token-credit columns introduced for UP-4390.

  tokens_limit  BIGINT NULL                 -- NULL = unlimited.
  tokens_used   BIGINT NOT NULL DEFAULT 0   -- monotonic counter, never reset.

Token limiting is opt-in per deployment. Both the schema default and the
post-upgrade state of existing rows depend on whether
`GENAI_ENGINE_DEFAULT_TENANT_TOKEN_LIMIT` is set in the environment when
the migration runs:

  - Unset / invalid / non-positive  → all rows stay tokens_limit = NULL.
                                       Token limiting is fully disabled.
  - Set to a positive integer N     → every existing TENANT org is
                                       backfilled to N. Default / system
                                       orgs always stay NULL (unmetered).

New tenant signups receive `Config.default_tenant_token_limit()` at
creation time, so a single env var controls both backfill and ongoing
behavior.
"""

import os

import sqlalchemy as sa

from alembic import op
from utils.constants import (
    DEFAULT_ORG_ID,
    GENAI_ENGINE_DEFAULT_TENANT_TOKEN_LIMIT_ENV_VAR,
    SYSTEM_ORG_ID,
)

# revision identifiers, used by Alembic.
revision = "5e84b8d7aa1f"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def _parse_default_limit_from_env() -> int | None:
    """Parse the deployment's opt-in tenant token limit.

    Inlined from Config.default_tenant_token_limit() so the migration
    doesn't pull in the wider config import chain at upgrade time.
    """
    raw = os.environ.get(GENAI_ENGINE_DEFAULT_TENANT_TOKEN_LIMIT_ENV_VAR)
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value > 0 else None


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

    # Conditional retroactive backfill — only fires when the deployment
    # has opted in via env. Default / system orgs always stay NULL.
    default_limit = _parse_default_limit_from_env()
    if default_limit is not None:
        op.execute(
            sa.text(
                "UPDATE organizations "
                "SET tokens_limit = :default_limit "
                "WHERE id NOT IN (:default_org, :system_org)"
            ).bindparams(
                default_limit=default_limit,
                default_org=str(DEFAULT_ORG_ID),
                system_org=str(SYSTEM_ORG_ID),
            )
        )


def downgrade() -> None:
    op.drop_column("organizations", "tokens_used")
    op.drop_column("organizations", "tokens_limit")
