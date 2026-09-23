"""add task_provenance_sources

Revision ID: 4e7a2c9d1b35
Revises: 91bac5fc80b6
Create Date: 2026-09-23 18:00:00.000000

Persists a task's provenance: which discovery source reported the agent, at which
upstream address, and when a scan last handed it over. One row per (source,
external_id), joined to `tasks`, rather than a JSON column on the task -- one agent
can be reported at hundreds of addresses, and the fetch job's question, "which tasks
did source X report since T", is answered by the (source_id, last_reported_at) index
instead of by reading every task's JSON.

Nothing is backfilled: no discovery source has reported through the resolver before
this revision, and tasks that predate discovery derive their provenance from their
creation source when it is served.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "4e7a2c9d1b35"
down_revision = "91bac5fc80b6"
branch_labels = None
depends_on = None

TABLE = "task_provenance_sources"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("source_class", sa.String(), nullable=False),
        sa.Column("vendor", sa.String(), nullable=True),
        sa.Column(
            "address",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
        sa.Column("first_reported_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("last_reported_at", sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
            name="fk_task_provenance_sources_task_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("source_id", "external_id"),
    )
    op.create_index(
        op.f("ix_task_provenance_sources_task_id"),
        TABLE,
        ["task_id"],
        unique=False,
    )
    op.create_index(
        "idx_task_provenance_sources_source_reported",
        TABLE,
        ["source_id", "last_reported_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_task_provenance_sources_source_reported", table_name=TABLE)
    op.drop_index(op.f("ix_task_provenance_sources_task_id"), table_name=TABLE)
    op.drop_table(TABLE)
