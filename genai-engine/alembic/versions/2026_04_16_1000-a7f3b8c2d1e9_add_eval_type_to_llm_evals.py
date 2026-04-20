"""add eval_type to llm_evals and make llm-specific fields nullable

Revision ID: a7f3b8c2d1e9
Revises: 04c5e8528072
Create Date: 2026-04-16 10:00:00.000000

Adds eval_type discriminator column to llm_evals so the table can store
all eval types (llm_as_a_judge, pii, toxicity, prompt_injection, etc.).
Makes instructions, model_name, and model_provider nullable since ML eval
types do not use them.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "a7f3b8c2d1e9"
down_revision = "04c5e8528072"
branch_labels = None
depends_on = None

_TABLE = "llm_evals"
_COLUMN_EVAL_TYPE = "eval_type"
_DEFAULT_EVAL_TYPE = "llm_as_a_judge"


def upgrade() -> None:
    # 1. Add eval_type column — existing rows default to "llm_as_a_judge"
    op.add_column(
        _TABLE,
        sa.Column(
            _COLUMN_EVAL_TYPE,
            sa.String(),
            nullable=False,
            server_default=_DEFAULT_EVAL_TYPE,
        ),
    )

    # 2. Make LLM-specific fields nullable (ML eval types don't use them)
    op.alter_column(_TABLE, "instructions", existing_type=sa.String(), nullable=True)
    op.alter_column(_TABLE, "model_name", existing_type=sa.String(), nullable=True)
    op.alter_column(_TABLE, "model_provider", existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    # Restore NOT NULL on LLM-specific fields (will fail if any ML eval rows exist)
    op.alter_column(_TABLE, "model_provider", existing_type=sa.String(), nullable=False)
    op.alter_column(_TABLE, "model_name", existing_type=sa.String(), nullable=False)
    op.alter_column(_TABLE, "instructions", existing_type=sa.String(), nullable=False)

    # Remove eval_type column
    op.drop_column(_TABLE, _COLUMN_EVAL_TYPE)
