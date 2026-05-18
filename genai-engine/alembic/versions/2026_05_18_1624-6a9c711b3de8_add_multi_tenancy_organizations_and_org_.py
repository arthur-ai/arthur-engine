"""add multi-tenancy organizations and org_id

Revision ID: 6a9c711b3de8
Revises: b3f7a2c1d9e0
Create Date: 2026-05-18 16:24:30.136592

Multi-tenancy v1 schema migration. Bundles the four migrations from the
MULTI_TENANCY_DESIGN doc into a single Alembic revision:

  0. Create organizations table; seed default + system orgs.
  1. tasks.org_id (NOT NULL). Backfill: is_system_task -> system, else default.
  2. api_keys.org_id (NULL). Existing keys stay NULL (admin behavior).
  3. Denormalize org_id onto high-volume task-scoped tables.

Every NOT NULL column is added in two phases (add nullable, backfill, set
NOT NULL) so the migration can run safely against a populated database.
Rows whose parent chain is broken cause SET NOT NULL to fail loudly.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6a9c711b3de8'
down_revision = 'b3f7a2c1d9e0'
branch_labels = None
depends_on = None


# Tables denormalized in Migration 3. Each backfill chain ultimately resolves
# to tasks.org_id via either inferences, trace_metadata, or rule_result_details.
DENORMALIZED_NOT_NULL_TABLES = [
    "inference_feedback",
    "prompt_rule_results",
    "response_rule_results",
    "rule_result_details",
    "agentic_annotations",
    "hallucination_claims",
    "pii_entities",
    "keyword_matches",
    "regex_matches",
    "toxicity_scores",
]


def upgrade() -> None:
    # ── Migration 0: organizations table + seed default/system ──────────────
    op.create_table(
        "organizations",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "is_system",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organizations"),
        sa.UniqueConstraint("name", name="uq_organizations_name"),
    )
    # Enforces "at most one row with is_system=TRUE."
    op.create_index(
        "uq_organizations_is_system_true",
        "organizations",
        ["is_system"],
        unique=True,
        postgresql_where=sa.text("is_system = TRUE"),
    )

    op.execute(
        "INSERT INTO organizations (name, is_system) VALUES "
        "('default', FALSE), ('system', TRUE)"
    )

    # ── Migration 1: tasks.org_id ───────────────────────────────────────────
    op.add_column("tasks", sa.Column("org_id", sa.UUID(), nullable=True))
    op.execute(
        """
        UPDATE tasks
           SET org_id = (SELECT id FROM organizations WHERE name = 'system')
         WHERE is_system_task = TRUE
        """
    )
    op.execute(
        """
        UPDATE tasks
           SET org_id = (SELECT id FROM organizations WHERE name = 'default')
         WHERE org_id IS NULL
        """
    )
    op.alter_column("tasks", "org_id", nullable=False)
    op.create_index(
        op.f("ix_tasks_org_id"), "tasks", ["org_id"], unique=False
    )
    op.create_foreign_key(
        "fk_tasks_org_id_organizations",
        "tasks",
        "organizations",
        ["org_id"],
        ["id"],
    )

    # ── Migration 2: api_keys.org_id (nullable; admin behavior preserved) ───
    op.add_column("api_keys", sa.Column("org_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_api_keys_org_id_organizations",
        "api_keys",
        "organizations",
        ["org_id"],
        ["id"],
    )
    # Partial index — only indexes tenant keys.
    op.create_index(
        "ix_api_keys_org_id",
        "api_keys",
        ["org_id"],
        unique=False,
        postgresql_where=sa.text("org_id IS NOT NULL"),
    )

    # ── Migration 3: denormalize org_id onto high-volume tables ─────────────
    # Step 3a: add nullable on every table.
    for table in DENORMALIZED_NOT_NULL_TABLES:
        op.add_column(table, sa.Column("org_id", sa.UUID(), nullable=True))

    # Step 3b: backfill in dependency order.

    # inference_feedback ← inferences.task_id
    op.execute(
        """
        UPDATE inference_feedback ifb
           SET org_id = t.org_id
          FROM inferences i
          JOIN tasks t ON t.id = i.task_id
         WHERE ifb.inference_id = i.id
        """
    )

    # prompt_rule_results ← inference_prompts.inference_id → inferences.task_id
    op.execute(
        """
        UPDATE prompt_rule_results prr
           SET org_id = t.org_id
          FROM inference_prompts ip
          JOIN inferences i ON i.id = ip.inference_id
          JOIN tasks t ON t.id = i.task_id
         WHERE prr.inference_prompt_id = ip.id
        """
    )

    # response_rule_results ← inference_responses.inference_id → inferences.task_id
    op.execute(
        """
        UPDATE response_rule_results rrr
           SET org_id = t.org_id
          FROM inference_responses ir
          JOIN inferences i ON i.id = ir.inference_id
          JOIN tasks t ON t.id = i.task_id
         WHERE rrr.inference_response_id = ir.id
        """
    )

    # rule_result_details ← prompt_rule_results.org_id OR response_rule_results.org_id
    op.execute(
        """
        UPDATE rule_result_details rrd
           SET org_id = prr.org_id
          FROM prompt_rule_results prr
         WHERE rrd.prompt_rule_result_id = prr.id
        """
    )
    op.execute(
        """
        UPDATE rule_result_details rrd
           SET org_id = rrr.org_id
          FROM response_rule_results rrr
         WHERE rrd.response_rule_result_id = rrr.id
           AND rrd.org_id IS NULL
        """
    )

    # agentic_annotations: trace_id is nullable. Resolve via trace_metadata when
    # available, otherwise via continuous_evals.task_id.
    op.execute(
        """
        UPDATE agentic_annotations aa
           SET org_id = t.org_id
          FROM trace_metadata tm
          JOIN tasks t ON t.id = tm.task_id
         WHERE aa.trace_id = tm.trace_id
        """
    )
    op.execute(
        """
        UPDATE agentic_annotations aa
           SET org_id = t.org_id
          FROM continuous_evals ce
          JOIN tasks t ON t.id = ce.task_id
         WHERE aa.continuous_eval_id = ce.id
           AND aa.org_id IS NULL
        """
    )

    # rule-detail children ← rule_result_details.org_id (one shape, four tables).
    for child in (
        "hallucination_claims",
        "pii_entities",
        "keyword_matches",
        "regex_matches",
        "toxicity_scores",
    ):
        op.execute(
            f"""
            UPDATE {child} c
               SET org_id = rrd.org_id
              FROM rule_result_details rrd
             WHERE c.rule_result_detail_id = rrd.id
            """
        )

    # Step 3c: SET NOT NULL, add index + FK on each table. If any row's parent
    # chain was broken, SET NOT NULL fails loudly here.
    for table in DENORMALIZED_NOT_NULL_TABLES:
        op.alter_column(table, "org_id", nullable=False)
        op.create_index(
            op.f(f"ix_{table}_org_id"), table, ["org_id"], unique=False
        )
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

    op.drop_index("ix_api_keys_org_id", table_name="api_keys")
    op.drop_constraint(
        "fk_api_keys_org_id_organizations", "api_keys", type_="foreignkey"
    )
    op.drop_column("api_keys", "org_id")

    op.drop_constraint(
        "fk_tasks_org_id_organizations", "tasks", type_="foreignkey"
    )
    op.drop_index(op.f("ix_tasks_org_id"), table_name="tasks")
    op.drop_column("tasks", "org_id")

    op.drop_index(
        "uq_organizations_is_system_true", table_name="organizations"
    )
    op.drop_table("organizations")
