"""add eval_type support to llm_evals and continuous_evals

Revision ID: e1f2a3b4c5d6
Revises: f15ac7955e6f
Create Date: 2026-04-23 12:00:00.000000

- Adds eval_type discriminator to llm_evals so the table stores all eval types
  (llm_as_a_judge, pii, toxicity, prompt_injection, etc.).
- Makes LLM-specific llm_evals fields (instructions, model_name, model_provider)
  nullable since ML eval types don't use them.
- Adds eval_type discriminator to continuous_evals.
- Makes llm_eval_name/llm_eval_version nullable in continuous_evals.
- Drops the FK constraint that hard-wired continuous_evals to llm_evals
  (referential integrity is managed in app code).
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "e1f2a3b4c5d6"
down_revision = "f15ac7955e6f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- llm_evals ---

    # Add eval_type — existing rows default to "llm_as_a_judge"
    op.add_column(
        "llm_evals",
        sa.Column(
            "eval_type",
            sa.String(),
            nullable=False,
            server_default="llm_as_a_judge",
        ),
    )

    # Make LLM-specific fields nullable (ML eval types don't use them)
    op.alter_column(
        "llm_evals",
        "instructions",
        existing_type=sa.String(),
        nullable=True,
    )
    op.alter_column("llm_evals", "model_name", existing_type=sa.String(), nullable=True)
    op.alter_column(
        "llm_evals",
        "model_provider",
        existing_type=sa.String(),
        nullable=True,
    )

    # --- continuous_evals ---

    # Drop the FK that hard-links continuous_evals to llm_evals
    op.drop_constraint(
        "fk_continuous_evals_llm_eval",
        "continuous_evals",
        type_="foreignkey",
    )

    # Make llm_eval_name/llm_eval_version nullable
    op.alter_column(
        "continuous_evals",
        "llm_eval_name",
        existing_type=sa.String(),
        nullable=True,
    )
    op.alter_column(
        "continuous_evals",
        "llm_eval_version",
        existing_type=sa.Integer(),
        nullable=True,
    )

    # Add eval_type discriminator — backfill existing rows as "llm_eval"
    op.add_column(
        "continuous_evals",
        sa.Column(
            "eval_type",
            sa.String(),
            nullable=False,
            server_default="llm_eval",
        ),
    )


def downgrade() -> None:
    conn = op.get_bind()

    # --- continuous_evals ---
    op.drop_column("continuous_evals", "eval_type")

    # ML continuous evals have NULL llm_eval_name/llm_eval_version.
    # Delete them before restoring NOT NULL constraints; downgrading removes ML eval support.
    conn.execute(
        sa.text(
            "DELETE FROM continuous_evals WHERE llm_eval_name IS NULL OR llm_eval_version IS NULL",
        ),
    )

    op.alter_column(
        "continuous_evals",
        "llm_eval_version",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "continuous_evals",
        "llm_eval_name",
        existing_type=sa.String(),
        nullable=False,
    )

    op.create_foreign_key(
        "fk_continuous_evals_llm_eval",
        "continuous_evals",
        "llm_evals",
        ["task_id", "llm_eval_name", "llm_eval_version"],
        ["task_id", "name", "version"],
        ondelete="CASCADE",
    )

    # --- llm_evals ---

    # ML evals (pii, toxicity, prompt_injection) have NULL model_name, model_provider,
    # instructions. Delete them before restoring NOT NULL constraints.
    conn.execute(sa.text("DELETE FROM llm_evals WHERE eval_type != 'llm_as_a_judge'"))

    op.alter_column(
        "llm_evals",
        "model_provider",
        existing_type=sa.String(),
        nullable=False,
    )
    op.alter_column(
        "llm_evals",
        "model_name",
        existing_type=sa.String(),
        nullable=False,
    )
    op.alter_column(
        "llm_evals",
        "instructions",
        existing_type=sa.String(),
        nullable=False,
    )

    op.drop_column("llm_evals", "eval_type")
