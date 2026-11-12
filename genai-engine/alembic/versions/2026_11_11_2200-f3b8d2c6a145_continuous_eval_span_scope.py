"""continuous eval scope: span runs, rollups and their annotation columns

Revision ID: f3b8d2c6a145
Revises: e0a1b2c3d4f5
Create Date: 2026-11-11 22:00:00.000000

One migration for judging a continuous eval per span:

continuous_evals
- scope: 'trace' (one run per trace, as before) or 'span' (one run per matching span
  plus a per-trace rollup). Existing evals stay 'trace'.
- span_filter: which spans a span-scope eval judges (span name, kind, conditions).
- max_spans_per_trace: most span runs one trace gets (default 20).
- rollup_rule: how span verdicts decide the trace ('any_fail' or 'final_attempt').

agentic_annotations
- span_id: the span the row is about, NULL for the whole trace (human span labels and
  span runs alike); label: the category a person or judge gave.
- run_level: 'trace' (default: every existing row and every human annotation),
  'span' (one judged span) or 'span_rollup' (the trace's summary of its span runs).
- judged_span_count: spans in the trace when it was judged, so a run whose trace grew
  afterwards can be told apart.
- Partial unique indexes on span runs, so a retried fan-out never makes a second row
  for the same (eval, trace, span), live or within one test run.

span_id and label are added only if missing, so a database that ran the earlier
local-only revision a7c1e5d2b904 (same two columns) can be stamped to e0a1b2c3d4f5
and upgraded here.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "f3b8d2c6a145"
down_revision = "e0a1b2c3d4f5"
branch_labels = None
depends_on = None

_LIVE_SPAN_RUNS = "run_level = 'span' AND test_run_id IS NULL"
_TEST_SPAN_RUNS = "run_level = 'span' AND test_run_id IS NOT NULL"


def _columns(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    op.add_column(
        "continuous_evals",
        sa.Column("scope", sa.String(), nullable=False, server_default="trace"),
    )
    op.add_column(
        "continuous_evals",
        sa.Column("span_filter", sa.JSON(), nullable=True),
    )
    op.add_column(
        "continuous_evals",
        sa.Column(
            "max_spans_per_trace",
            sa.Integer(),
            nullable=False,
            server_default="20",
        ),
    )
    op.add_column(
        "continuous_evals",
        sa.Column("rollup_rule", sa.String(), nullable=True),
    )

    existing = _columns("agentic_annotations")
    if "span_id" not in existing:
        op.add_column(
            "agentic_annotations",
            sa.Column("span_id", sa.String(), nullable=True),
        )
    if "label" not in existing:
        op.add_column(
            "agentic_annotations",
            sa.Column("label", sa.String(), nullable=True),
        )
    op.add_column(
        "agentic_annotations",
        sa.Column("run_level", sa.String(), nullable=False, server_default="trace"),
    )
    op.add_column(
        "agentic_annotations",
        sa.Column("judged_span_count", sa.Integer(), nullable=True),
    )
    op.create_index(
        "uq_agentic_annotations_live_span_run",
        "agentic_annotations",
        ["continuous_eval_id", "trace_id", "span_id"],
        unique=True,
        postgresql_where=sa.text(_LIVE_SPAN_RUNS),
    )
    op.create_index(
        "uq_agentic_annotations_test_span_run",
        "agentic_annotations",
        ["continuous_eval_id", "trace_id", "span_id", "test_run_id"],
        unique=True,
        postgresql_where=sa.text(_TEST_SPAN_RUNS),
    )


def downgrade() -> None:
    # Without run_level a span run reads as one more whole-trace verdict, so drop
    # them first; each trace keeps its rollup, which holds the trace's verdict.
    op.execute("DELETE FROM agentic_annotations WHERE run_level = 'span'")
    op.drop_index(
        "uq_agentic_annotations_test_span_run",
        table_name="agentic_annotations",
    )
    op.drop_index(
        "uq_agentic_annotations_live_span_run",
        table_name="agentic_annotations",
    )
    op.drop_column("agentic_annotations", "judged_span_count")
    op.drop_column("agentic_annotations", "run_level")
    op.drop_column("agentic_annotations", "label")
    op.drop_column("agentic_annotations", "span_id")
    op.drop_column("continuous_evals", "rollup_rule")
    op.drop_column("continuous_evals", "max_spans_per_trace")
    op.drop_column("continuous_evals", "span_filter")
    op.drop_column("continuous_evals", "scope")
