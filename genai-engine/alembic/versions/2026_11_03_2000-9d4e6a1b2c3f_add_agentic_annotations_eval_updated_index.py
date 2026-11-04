"""index agentic_annotations on (continuous_eval_id, updated_at)

Revision ID: 9d4e6a1b2c3f
Revises: 5b8e2d1f7c90
Create Date: 2026-11-03 20:00:00.000000

Before every judge call for a capped eval, the worker sums the eval's runs
finished since midnight, filtering on updated_at. The only eval-scoped index is
on (continuous_eval_id, created_at), so that sum reads the eval's whole history
(up to the 90-day trace retention), and on a large table Postgres reads every row.

upgrade():
- CREATE INDEX CONCURRENTLY, outside the migration transaction, so enqueuing and
  finishing runs keep writing to agentic_annotations while it builds. A plain
  CREATE INDEX blocks those writes for the whole build, and for as long as any
  transaction already open on the table runs.
- A session advisory lock makes engine replicas that start together build it one
  at a time; two concurrent builds deadlock.
- If an earlier attempt left an INVALID index of that name (a cut-off concurrent
  build does this), drop it and rebuild. The revision is only recorded once the
  index is valid.
- Idempotent: safe to re-run, and safe to run by hand before deploying.

Manual equivalent (psql, autocommit):

    SELECT indisvalid FROM pg_index
     WHERE indexrelid = to_regclass('ix_agentic_annotations_continuous_eval_updated');
    -- if that returns false:
    DROP INDEX CONCURRENTLY IF EXISTS ix_agentic_annotations_continuous_eval_updated;
    CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_agentic_annotations_continuous_eval_updated
        ON agentic_annotations (continuous_eval_id, updated_at);

downgrade(): DROP INDEX CONCURRENTLY IF EXISTS.
"""

from typing import Optional

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "9d4e6a1b2c3f"
down_revision = "5b8e2d1f7c90"
branch_labels = None
depends_on = None

INDEX_NAME = "ix_agentic_annotations_continuous_eval_updated"
TABLE_NAME = "agentic_annotations"
INDEX_COLUMNS = "continuous_eval_id, updated_at"
ADVISORY_LOCK_KEY = 7290410263


def _index_state(connection: sa.Connection) -> Optional[str]:
    """'valid', 'invalid', or None when the index does not exist."""
    row = connection.execute(
        sa.text(
            "SELECT indisvalid FROM pg_index WHERE indexrelid = to_regclass(:name)",
        ),
        {"name": INDEX_NAME},
    ).first()
    if row is None:
        return None
    return "valid" if row[0] else "invalid"


def upgrade() -> None:
    bind = op.get_bind()
    # CONCURRENTLY cannot run inside a transaction; autocommit_block commits the
    # migration transaction, runs this block, then reopens one.
    with op.get_context().autocommit_block():
        bind.execute(
            sa.text("SELECT pg_advisory_lock(:key)"),
            {"key": ADVISORY_LOCK_KEY},
        )
        try:
            state = _index_state(bind)
            if state == "invalid":
                bind.execute(
                    sa.text(f"DROP INDEX CONCURRENTLY IF EXISTS {INDEX_NAME}"),
                )
                state = None
            if state == "valid":
                return
            bind.execute(
                sa.text(
                    f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {INDEX_NAME} "
                    f"ON {TABLE_NAME} ({INDEX_COLUMNS})",
                ),
            )
            if _index_state(bind) != "valid":
                raise RuntimeError(
                    f"{INDEX_NAME} was created but is not valid; re-run the "
                    "migration (it drops the invalid index and rebuilds)",
                )
        finally:
            bind.execute(
                sa.text("SELECT pg_advisory_unlock(:key)"),
                {"key": ADVISORY_LOCK_KEY},
            )


def downgrade() -> None:
    bind = op.get_bind()
    with op.get_context().autocommit_block():
        bind.execute(sa.text(f"DROP INDEX CONCURRENTLY IF EXISTS {INDEX_NAME}"))
