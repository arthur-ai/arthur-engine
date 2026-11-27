"""add unpriced_span_count to traces and spans

Revision ID: c3e8a1f5d7b2
Revises: b1194cd9c938
Create Date: 2026-11-26 12:00:00.000000

Records which LLM spans couldn't be priced (model missing or unknown to litellm),
so a trace's cost can be shown as unknown or as leaving spans out instead of
reading as $0. Per span it is 1 or 0 (NULL for other span kinds); per trace it
is the sum.

Backfill, in order, in batches of traces:
1. LLM spans with tokens on one side only were left without a total, because
   zero tokens were never priced. Their total is the priced side and the empty
   side costs 0; their trace's total and split costs are corrected first.
2. Every LLM span is flagged: unpriced when it reports tokens (split or only a total)
   and has no total cost.
3. Each trace gets the sum of its spans' flags.
"""

import sqlalchemy as sa
from sqlalchemy import bindparam, text

from alembic import op

# revision identifiers, used by Alembic.
revision = "c3e8a1f5d7b2"
down_revision = "b1194cd9c938"
branch_labels = None
depends_on = None

# Traces per batch. Each batch runs every update below for its traces only, so no
# statement rewrites the whole spans or trace_metadata table.
BATCH_SIZE = 1000

# The prompt side has tokens and a cost; the completion side has 0 tokens and no
# cost. Matches when extract_token_cost_from_span now prices the empty side as 0.
ONE_SIDED_PROMPT = """
    span_kind = 'LLM'
    AND total_token_cost IS NULL
    AND prompt_token_cost IS NOT NULL
    AND prompt_token_count > 0
    AND completion_token_cost IS NULL
    AND completion_token_count = 0
"""

# The completion side has tokens and a cost; the prompt side has 0 tokens and no cost.
ONE_SIDED_COMPLETION = """
    span_kind = 'LLM'
    AND total_token_cost IS NULL
    AND completion_token_cost IS NOT NULL
    AND completion_token_count > 0
    AND prompt_token_cost IS NULL
    AND prompt_token_count = 0
"""

# Keyset pages over the traces that have LLM spans. The first page has no lower
# bound, so a trace id of "" (a span ingested without one) is included too.
FIRST_TRACE_IDS = text("""
    SELECT trace_id
      FROM spans
     WHERE span_kind = 'LLM'
     GROUP BY trace_id
     ORDER BY trace_id
     LIMIT :limit
    """)

NEXT_TRACE_IDS = text("""
    SELECT trace_id
      FROM spans
     WHERE span_kind = 'LLM' AND trace_id > :after
     GROUP BY trace_id
     ORDER BY trace_id
     LIMIT :limit
    """)

# Adds the one-sided spans' priced side to their trace's total, and sets the
# trace's empty side to 0 like the spans' below.
FIX_TRACE_COSTS = text(f"""
    UPDATE trace_metadata tm
       SET total_token_cost = COALESCE(tm.total_token_cost, 0) + fixed.total,
           prompt_token_cost = CASE
               WHEN fixed.zero_prompt = 1 THEN COALESCE(tm.prompt_token_cost, 0)
               ELSE tm.prompt_token_cost
           END,
           completion_token_cost = CASE
               WHEN fixed.zero_completion = 1 THEN COALESCE(tm.completion_token_cost, 0)
               ELSE tm.completion_token_cost
           END
      FROM (
            SELECT trace_id,
                   SUM(COALESCE(prompt_token_cost, 0) + COALESCE(completion_token_cost, 0)) AS total,
                   MAX(CASE WHEN {ONE_SIDED_COMPLETION} THEN 1 ELSE 0 END) AS zero_prompt,
                   MAX(CASE WHEN {ONE_SIDED_PROMPT} THEN 1 ELSE 0 END) AS zero_completion
              FROM spans
             WHERE trace_id IN :trace_ids
               AND (({ONE_SIDED_PROMPT}) OR ({ONE_SIDED_COMPLETION}))
             GROUP BY trace_id
           ) fixed
     WHERE tm.trace_id = fixed.trace_id
    """).bindparams(bindparam("trace_ids", expanding=True))

FIX_ONE_SIDED_PROMPT_SPANS = text(f"""
    UPDATE spans
       SET completion_token_cost = 0, total_token_cost = prompt_token_cost
     WHERE trace_id IN :trace_ids AND {ONE_SIDED_PROMPT}
    """).bindparams(bindparam("trace_ids", expanding=True))

FIX_ONE_SIDED_COMPLETION_SPANS = text(f"""
    UPDATE spans
       SET prompt_token_cost = 0, total_token_cost = completion_token_cost
     WHERE trace_id IN :trace_ids AND {ONE_SIDED_COMPLETION}
    """).bindparams(bindparam("trace_ids", expanding=True))

FLAG_SPANS = text("""
    UPDATE spans
       SET unpriced_span_count = CASE
               WHEN total_token_cost IS NULL
                AND (
                    COALESCE(prompt_token_count, 0) > 0
                    OR COALESCE(completion_token_count, 0) > 0
                    OR COALESCE(total_token_count, 0) > 0
                )
               THEN 1
               ELSE 0
           END
     WHERE trace_id IN :trace_ids AND span_kind = 'LLM'
    """).bindparams(bindparam("trace_ids", expanding=True))

COUNT_TRACES = text("""
    UPDATE trace_metadata tm
       SET unpriced_span_count = llm.unpriced
      FROM (
            SELECT trace_id, SUM(unpriced_span_count) AS unpriced
              FROM spans
             WHERE trace_id IN :trace_ids AND span_kind = 'LLM'
             GROUP BY trace_id
           ) llm
     WHERE tm.trace_id = llm.trace_id
    """).bindparams(bindparam("trace_ids", expanding=True))


def upgrade() -> None:
    op.add_column(
        "trace_metadata",
        sa.Column("unpriced_span_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "spans", sa.Column("unpriced_span_count", sa.Integer(), nullable=True)
    )

    connection = op.get_bind()
    trace_ids = list(
        connection.execute(FIRST_TRACE_IDS, {"limit": BATCH_SIZE}).scalars(),
    )
    while trace_ids:
        for statement in (
            FIX_TRACE_COSTS,
            FIX_ONE_SIDED_PROMPT_SPANS,
            FIX_ONE_SIDED_COMPLETION_SPANS,
            FLAG_SPANS,
            COUNT_TRACES,
        ):
            connection.execute(statement, {"trace_ids": trace_ids})
        trace_ids = list(
            connection.execute(
                NEXT_TRACE_IDS,
                {"after": trace_ids[-1], "limit": BATCH_SIZE},
            ).scalars(),
        )


def downgrade() -> None:
    op.drop_column("spans", "unpriced_span_count")
    op.drop_column("trace_metadata", "unpriced_span_count")
