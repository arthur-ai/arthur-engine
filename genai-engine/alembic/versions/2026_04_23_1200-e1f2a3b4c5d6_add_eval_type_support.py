"""add eval_type support to llm_evals and continuous_evals

Revision ID: e1f2a3b4c5d6
Revises: f15ac7955e6f
Create Date: 2026-04-23 12:00:00.000000

- Adds eval_type discriminator to llm_evals so the table stores all eval types
  (llm_as_a_judge, pii, toxicity, prompt_injection, etc.).
- Makes LLM-specific llm_evals fields (instructions, model_name, model_provider)
  nullable since ML eval types don't use them.
- Adds eval_type discriminator to continuous_evals.
- llm_eval_name/llm_eval_version remain NOT NULL; ML continuous evals populate
  them with the ML eval's name/version (which lives in the same llm_evals table).
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

    # Delete ML-type continuous evals before dropping eval_type; they reference
    # ML evals which will be removed below.
    conn.execute(
        sa.text("DELETE FROM continuous_evals WHERE eval_type = 'ml_eval'"),
    )
    op.drop_column("continuous_evals", "eval_type")

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
