"""add_trace_meta_table

Revision ID: 48b468cd92f9
Revises: fc6de48cfedf
Create Date: 2025-08-27 21:30:39.260543

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "48b468cd92f9"
down_revision = "fc6de48cfedf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create traces metadata table
    op.create_table(
        "trace_metadata",
        sa.Column("trace_id", sa.String(255), primary_key=True),
        sa.Column("task_id", sa.String(), nullable=False, index=True),
        sa.Column("start_time", sa.TIMESTAMP(), nullable=False),
        sa.Column("end_time", sa.TIMESTAMP(), nullable=False),
        sa.Column("span_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], name="fk_traces_task_id"),
    )

    # Backfill existing trace data from spans table
    op.execute(
        """
        INSERT INTO trace_metadata (trace_id, task_id, start_time, end_time, span_count)
        SELECT
            trace_id,
            task_id,
            MIN(start_time) as start_time,
            MAX(end_time) as end_time,
            COUNT(*) as span_count
        FROM spans
        WHERE task_id IS NOT NULL
        GROUP BY trace_id, task_id
    """,
    )

    # Create essential indexes for traces table
    op.create_index(
        "idx_traces_task_start_desc",
        "trace_metadata",
        ["task_id", sa.text("start_time DESC")],
    )
    op.create_index(
        "idx_traces_task_start_asc",
        "trace_metadata",
        ["task_id", sa.text("start_time ASC")],
    )

    # Complex time range queries
    op.create_index(
        "idx_traces_task_time_range",
        "trace_metadata",
        ["task_id", "start_time", "end_time"],
    )

    # Covering index for pagination (avoids table lookups) - PostgreSQL specific
    op.execute(
        """
        CREATE INDEX idx_traces_covering ON trace_metadata (task_id, start_time DESC)
        INCLUDE (trace_id, end_time, span_count)
    """,
    )


def downgrade() -> None:
    # Drop the trace indexes in reverse order
    op.drop_index("idx_traces_covering", "trace_metadata")
    op.drop_index("idx_traces_task_time_range", "trace_metadata")
    op.drop_index("idx_traces_task_start_asc", "trace_metadata")
    op.drop_index("idx_traces_task_start_desc", "trace_metadata")

    # Drop the traces table
    op.drop_table("trace_metadata")
