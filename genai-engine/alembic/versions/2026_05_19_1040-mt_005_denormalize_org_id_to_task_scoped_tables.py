"""denormalize org_id to task-scoped tables

Revision ID: mt_denormalize_org_id
Revises: mt_orphan_inferences
Create Date: 2026-05-19 10:40:00

Multi-tenancy step 5 of 5. Denormalizes `org_id` onto every task-scoped
table that today reaches its org only via multi-hop joins:

  - inference_feedback        (1 hop via inferences)
  - prompt_rule_results       (2 hop via inference_prompts -> inferences)
  - response_rule_results     (2 hop via inference_responses -> inferences)
  - rule_result_details       (3 hop via parent prompt/response_rule_results)
  - hallucination_claims      (3 hop via rule_result_details)
  - pii_entities              (3 hop via rule_result_details)
  - keyword_matches           (3 hop via rule_result_details)
  - regex_matches             (3 hop via rule_result_details)
  - toxicity_scores           (3 hop via rule_result_details)
  - agentic_annotations       (1 hop via trace_metadata)

Two-phase nullable -> backfill -> SET NOT NULL, applied per-table. Backfill
order respects FK dependencies: parents must finish before children.

Step 4 (mt_orphan_inferences) guaranteed every inference has a non-null
task_id, so the inference-derived backfills can't strand rows. The
agentic_annotations chain has a continuous_evals fallback and finally a
system-org fallback for the rare "no parent" annotation allowed by the
CK constraints on that table.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "mt_denormalize_org_id"
down_revision = "mt_orphan_inferences"
branch_labels = None
depends_on = None


DENORMALIZED_NOT_NULL_TABLES = [
    "inference_feedback",
    "prompt_rule_results",
    "response_rule_results",
    "rule_result_details",
    "hallucination_claims",
    "pii_entities",
    "keyword_matches",
    "regex_matches",
    "toxicity_scores",
    "agentic_annotations",
]

# Per-check detail tables hanging off rule_result_details. Same backfill
# shape for all of them (FK rule_result_detail_id -> rule_result_details.org_id).
RULE_RESULT_DETAIL_CHILD_TABLES = (
    "hallucination_claims",
    "pii_entities",
    "keyword_matches",
    "regex_matches",
    "toxicity_scores",
)


def upgrade() -> None:
    # Step A: add nullable column on every table.
    for table in DENORMALIZED_NOT_NULL_TABLES:
        op.add_column(table, sa.Column("org_id", sa.UUID(), nullable=True))

    # Step B: backfill in dependency order.

    # inference_feedback <- inferences.task_id (every inference now has a task).
    op.execute("""
        UPDATE inference_feedback ifb
           SET org_id = t.org_id
          FROM inferences i
          JOIN tasks t ON t.id = i.task_id
         WHERE ifb.inference_id = i.id
        """)

    # prompt_rule_results <- inference_prompts.inference_id -> inferences.task_id.
    op.execute("""
        UPDATE prompt_rule_results prr
           SET org_id = t.org_id
          FROM inference_prompts ip
          JOIN inferences i ON i.id = ip.inference_id
          JOIN tasks t ON t.id = i.task_id
         WHERE prr.inference_prompt_id = ip.id
        """)

    # response_rule_results <- inference_responses.inference_id -> inferences.task_id.
    op.execute("""
        UPDATE response_rule_results rrr
           SET org_id = t.org_id
          FROM inference_responses ir
          JOIN inferences i ON i.id = ir.inference_id
          JOIN tasks t ON t.id = i.task_id
         WHERE rrr.inference_response_id = ir.id
        """)

    # rule_result_details <- prompt_rule_results.org_id OR response_rule_results.org_id.
    # Each row's parent FK chain points at exactly one of these; the other is NULL.
    op.execute("""
        UPDATE rule_result_details rrd
           SET org_id = prr.org_id
          FROM prompt_rule_results prr
         WHERE rrd.prompt_rule_result_id = prr.id
        """)
    op.execute("""
        UPDATE rule_result_details rrd
           SET org_id = rrr.org_id
          FROM response_rule_results rrr
         WHERE rrd.response_rule_result_id = rrr.id
           AND rrd.org_id IS NULL
        """)

    # Detail tables (hallucination_claims, pii_entities, keyword_matches,
    # regex_matches, toxicity_scores) <- rule_result_details.org_id.
    for child in RULE_RESULT_DETAIL_CHILD_TABLES:
        op.execute(f"""
            UPDATE {child} c
               SET org_id = rrd.org_id
              FROM rule_result_details rrd
             WHERE c.rule_result_detail_id = rrd.id
            """)

    # agentic_annotations: trace_id is nullable. Try trace_metadata first,
    # then continuous_evals.task_id, then fall back to the system org for the
    # rare annotation with neither parent (allowed by CK constraints on the
    # table — see agentic_annotation_models.py for the constraint set).
    op.execute("""
        UPDATE agentic_annotations aa
           SET org_id = t.org_id
          FROM trace_metadata tm
          JOIN tasks t ON t.id = tm.task_id
         WHERE aa.trace_id = tm.trace_id
        """)
    op.execute("""
        UPDATE agentic_annotations aa
           SET org_id = t.org_id
          FROM continuous_evals ce
          JOIN tasks t ON t.id = ce.task_id
         WHERE aa.continuous_eval_id = ce.id
           AND aa.org_id IS NULL
        """)
    op.execute("""
        UPDATE agentic_annotations
           SET org_id = (SELECT id FROM organizations WHERE name = 'system')
         WHERE org_id IS NULL
        """)

    # Step C: SET NOT NULL + index + FK on every table. If any row's parent
    # chain was broken (orphan data not covered by the fallbacks above),
    # SET NOT NULL fails loudly here rather than silently allowing it.
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
