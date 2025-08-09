"""add_metric_table_and_parent_id_to_span_table

Revision ID: fc6de48cfedf
Revises: 862b72075d60
Create Date: 2025-07-22 10:54:43.726022

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "fc6de48cfedf"
down_revision = "862b72075d60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create metrics table
    op.create_table(
        "metrics",
        sa.Column("id", sa.String(), primary_key=True, index=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("metric_metadata", sa.String(), nullable=False),
        sa.Column("config", sa.String(), nullable=True),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default="false"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create tasks_to_metrics table
    op.create_table(
        "tasks_to_metrics",
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("metric_id", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
        ),
        sa.ForeignKeyConstraint(
            ["metric_id"],
            ["metrics.id"],
        ),
        sa.PrimaryKeyConstraint("task_id", "metric_id"),
    )
    op.create_index(
        op.f("ix_tasks_to_metrics_task_id"),
        "tasks_to_metrics",
        ["task_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tasks_to_metrics_metric_id"),
        "tasks_to_metrics",
        ["metric_id"],
        unique=False,
    )

    # Create metric_results table with span_id and metric_id columns
    op.create_table(
        "metric_results",
        sa.Column("id", sa.String(), primary_key=True, index=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("metric_type", sa.String(), nullable=False),
        sa.Column(
            "details",
            sa.String(),
            nullable=True,
        ),  # JSON-serialized MetricScoreDetails
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("span_id", sa.String(), nullable=False),
        sa.Column("metric_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["span_id"],
            ["spans.id"],
        ),
        sa.ForeignKeyConstraint(
            ["metric_id"],
            ["metrics.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_metric_results_span_id"),
        "metric_results",
        ["span_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_metric_results_metric_id"),
        "metric_results",
        ["metric_id"],
        unique=False,
    )

    # Add parent_span_id column to spans table
    op.add_column("spans", sa.Column("parent_span_id", sa.String(), nullable=True))
    op.create_index(
        op.f("ix_spans_parent_span_id"),
        "spans",
        ["parent_span_id"],
        unique=False,
    )

    # Add span_kind column to spans table
    op.add_column("spans", sa.Column("span_kind", sa.String(), nullable=True))


def downgrade() -> None:
    # Drop span_kind column
    op.drop_column("spans", "span_kind")

    # Drop parent_span_id column and its index
    op.drop_index(op.f("ix_spans_parent_span_id"), table_name="spans")
    op.drop_column("spans", "parent_span_id")

    # Drop metric_results table
    op.drop_index(op.f("ix_metric_results_metric_id"), table_name="metric_results")
    op.drop_index(op.f("ix_metric_results_span_id"), table_name="metric_results")
    op.drop_table("metric_results")

    # Drop tasks_to_metrics table
    op.drop_index(op.f("ix_tasks_to_metrics_metric_id"), table_name="tasks_to_metrics")
    op.drop_index(op.f("ix_tasks_to_metrics_task_id"), table_name="tasks_to_metrics")
    op.drop_table("tasks_to_metrics")

    # Drop metrics table
    op.drop_table("metrics")
