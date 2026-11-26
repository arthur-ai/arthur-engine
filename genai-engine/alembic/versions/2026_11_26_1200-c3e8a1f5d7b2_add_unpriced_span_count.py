"""add unpriced_span_count to traces and spans

Revision ID: c3e8a1f5d7b2
Revises: b1194cd9c938
Create Date: 2026-11-26 12:00:00.000000

Records which LLM spans couldn't be priced (model missing or unknown to litellm),
so a trace's cost can be shown as unknown or as leaving spans out instead of
reading as $0. Per span it is 1 or 0 (NULL for other span kinds); per trace it
is the sum.

Backfill, in order:
1. LLM spans with tokens on one side only were left without a total, because
   zero tokens were never priced. Their total is the priced side, and it is added
   to their trace's total before the spans are fixed.
2. Every LLM span is flagged: unpriced when it has tokens and no total.
3. Each trace gets the sum of its spans' flags.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "c3e8a1f5d7b2"
down_revision = "b1194cd9c938"
branch_labels = None
depends_on = None

ONE_SIDED_PROMPT = """
    span_kind = 'LLM'
    AND total_token_cost IS NULL
    AND prompt_token_cost IS NOT NULL
    AND completion_token_cost IS NULL
    AND completion_token_count = 0
"""

ONE_SIDED_COMPLETION = """
    span_kind = 'LLM'
    AND total_token_cost IS NULL
    AND completion_token_cost IS NOT NULL
    AND prompt_token_cost IS NULL
    AND prompt_token_count = 0
"""


def upgrade() -> None:
    op.add_column(
        "trace_metadata",
        sa.Column("unpriced_span_count", sa.Integer(), nullable=True),
    )
    op.add_column("spans", sa.Column("unpriced_span_count", sa.Integer(), nullable=True))

    op.execute(f"""
        UPDATE trace_metadata tm
           SET total_token_cost = COALESCE(tm.total_token_cost, 0) + fixed.total
          FROM (
                SELECT trace_id,
                       SUM(COALESCE(prompt_token_cost, 0) + COALESCE(completion_token_cost, 0)) AS total
                  FROM spans
                 WHERE ({ONE_SIDED_PROMPT}) OR ({ONE_SIDED_COMPLETION})
                 GROUP BY trace_id
               ) fixed
         WHERE tm.trace_id = fixed.trace_id
        """)
    op.execute(f"""
        UPDATE spans
           SET completion_token_cost = 0, total_token_cost = prompt_token_cost
         WHERE {ONE_SIDED_PROMPT}
        """)
    op.execute(f"""
        UPDATE spans
           SET prompt_token_cost = 0, total_token_cost = completion_token_cost
         WHERE {ONE_SIDED_COMPLETION}
        """)

    op.execute("""
        UPDATE spans
           SET unpriced_span_count = CASE
                   WHEN total_token_cost IS NULL
                    AND (COALESCE(prompt_token_count, 0) > 0 OR COALESCE(completion_token_count, 0) > 0)
                   THEN 1
                   ELSE 0
               END
         WHERE span_kind = 'LLM'
        """)
    op.execute("""
        UPDATE trace_metadata tm
           SET unpriced_span_count = llm.unpriced
          FROM (
                SELECT trace_id, SUM(unpriced_span_count) AS unpriced
                  FROM spans
                 WHERE span_kind = 'LLM'
                 GROUP BY trace_id
               ) llm
         WHERE tm.trace_id = llm.trace_id
        """)


def downgrade() -> None:
    op.drop_column("spans", "unpriced_span_count")
    op.drop_column("trace_metadata", "unpriced_span_count")
