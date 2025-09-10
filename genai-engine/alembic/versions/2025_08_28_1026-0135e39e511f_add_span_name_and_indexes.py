"""add_span_name_and_indexes

Revision ID: 0135e39e511f
Revises: 48b468cd92f9
Create Date: 2025-08-28 10:26:39.306767

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0135e39e511f"
down_revision = "48b468cd92f9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add span_name column to existing spans table
    op.add_column("spans", sa.Column("span_name", sa.String(), nullable=True))

    # Backfill span_name from existing raw_data JSON
    op.execute(
        """
        UPDATE spans
        SET span_name = (raw_data->>'name')::text
        WHERE raw_data->>'name' IS NOT NULL
        AND raw_data->>'name' != ''
    """,
    )

    # Create enhanced indexes for spans table
    op.create_index(
        "idx_spans_task_time_kind",
        "spans",
        ["task_id", "start_time", "span_kind"],
    )

    # Create conditional index for span name filtering
    op.create_index(
        "idx_spans_task_span_name",
        "spans",
        ["task_id", "span_name", "start_time"],
        postgresql_where=sa.text("span_name IS NOT NULL"),
    )

    # Create index for trace-specific span queries
    op.create_index(
        "idx_spans_trace_task_time",
        "spans",
        ["trace_id", "task_id", "start_time"],
    )

    # Create LLM spans optimization index
    op.create_index(
        "idx_spans_llm_task_time",
        "spans",
        ["task_id", "start_time"],
        postgresql_where=sa.text("span_kind = 'LLM'"),
    )


def downgrade() -> None:
    # Drop the span indexes in reverse order
    op.drop_index("idx_spans_llm_task_time", "spans")
    op.drop_index("idx_spans_trace_task_time", "spans")
    op.drop_index("idx_spans_task_span_name", "spans")
    op.drop_index("idx_spans_task_time_kind", "spans")

    # Remove span_name column from spans table
    op.drop_column("spans", "span_name")
