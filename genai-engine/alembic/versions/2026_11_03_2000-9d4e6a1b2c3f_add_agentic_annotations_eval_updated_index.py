"""index agentic_annotations on (continuous_eval_id, updated_at)

Revision ID: 9d4e6a1b2c3f
Revises: 5b8e2d1f7c90
Create Date: 2026-11-03 20:00:00.000000

Before every judge call for a capped eval, the worker sums the eval's runs
judged since midnight, filtering on updated_at. The only eval-scoped index is
on (continuous_eval_id, created_at), so that sum reads the eval's whole history
(up to the 90-day trace retention), and on a large table Postgres reads every row.

A plain CREATE INDEX, like the engine's other index migrations: writes to
agentic_annotations wait while it builds (a few seconds on millions of rows),
and it rolls back cleanly if cut off.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "9d4e6a1b2c3f"
down_revision = "5b8e2d1f7c90"
branch_labels = None
depends_on = None

INDEX_NAME = "ix_agentic_annotations_continuous_eval_updated"
TABLE_NAME = "agentic_annotations"


def upgrade() -> None:
    op.create_index(
        INDEX_NAME,
        TABLE_NAME,
        ["continuous_eval_id", "updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name=TABLE_NAME)
