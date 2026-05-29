"""denormalize org_id to trace_metadata and spans

Revision ID: 7e1c3a4b5d2f
Revises: 3abf881da275
Create Date: 2026-05-22 09:00:00.000000

Follow-up to revision 3abf881da275 (Migration 3 of the org_id denormalization
work) — adds `org_id` to the two high-traffic telemetry tables:

  - trace_metadata  (1 hop via tasks)
  - spans           (1 hop via tasks)

The Pattern C reads added in UP-4429 join through `tasks` to filter by
caller's org_id. That join is hit on every tenant-facing trace/span read,
and is a common access pattern, so materializing `org_id` on the row
turns it into a single-column filter (matches the shape of the other
denormalized tables added in Migration 3).

Two-phase nullable -> backfill -> SET NOT NULL per table.

Both writes paths (`trace_ingestion_service` and the existing
`SpanRepository.create_traces_from_gcp` flow) set `org_id` at insert
time after this revision lands, so the migration only has to cover the
historical rows.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "7e1c3a4b5d2f"
down_revision = "3abf881da275"
branch_labels = None
depends_on = None


DENORMALIZED_NOT_NULL_TABLES = ["trace_metadata", "spans"]


def upgrade() -> None:
    # Step A: add nullable column on both tables.
    for table in DENORMALIZED_NOT_NULL_TABLES:
        op.add_column(table, sa.Column("org_id", sa.UUID(), nullable=True))

    # Step B: backfill from tasks.org_id. Both tables already carry task_id
    # NOT NULL, so a single join lands every row.
    op.execute("""
        UPDATE trace_metadata tm
           SET org_id = t.org_id
          FROM tasks t
         WHERE tm.task_id = t.id
        """)
    op.execute("""
        UPDATE spans s
           SET org_id = t.org_id
          FROM tasks t
         WHERE s.task_id = t.id
        """)

    # Step C: SET NOT NULL + index + FK on both tables. If any row's task_id
    # didn't resolve, SET NOT NULL fails here rather than silently allowing it.
    for table in DENORMALIZED_NOT_NULL_TABLES:
        op.alter_column(table, "org_id", nullable=False)
        op.create_index(op.f(f"ix_{table}_org_id"), table, ["org_id"], unique=False)
        op.create_foreign_key(
            f"fk_{table}_org_id_organizations",
            table,
            "organizations",
            ["org_id"],
            ["id"],
        )


def downgrade() -> None:
    for table in reversed(DENORMALIZED_NOT_NULL_TABLES):
        op.drop_constraint(
            f"fk_{table}_org_id_organizations", table, type_="foreignkey"
        )
        op.drop_index(op.f(f"ix_{table}_org_id"), table_name=table)
        op.drop_column(table, "org_id")
