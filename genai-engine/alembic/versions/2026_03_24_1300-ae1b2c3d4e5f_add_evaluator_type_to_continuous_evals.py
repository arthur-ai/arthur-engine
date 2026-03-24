"""add evaluator_type and rule_type to continuous_evals

Revision ID: ae1b2c3d4e5f
Revises: 04c5e8528072
Create Date: 2026-03-24 13:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ae1b2c3d4e5f"
down_revision = "04c5e8528072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add evaluator_type column with default 'llm' for all existing rows
    op.add_column(
        "continuous_evals",
        sa.Column(
            "evaluator_type",
            sa.String(),
            nullable=False,
            server_default="llm",
        ),
    )

    # Add rule_type column (nullable — only set for rule-based evals)
    op.add_column(
        "continuous_evals",
        sa.Column("rule_type", sa.String(), nullable=True),
    )

    # Make llm_eval_name nullable (rule-based evals don't reference an LLM eval)
    op.alter_column(
        "continuous_evals",
        "llm_eval_name",
        existing_type=sa.String(),
        nullable=True,
    )

    # Make llm_eval_version nullable (rule-based evals don't reference an LLM eval)
    op.alter_column(
        "continuous_evals",
        "llm_eval_version",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    # Revert llm_eval_version to non-nullable (may fail if rule-based rows exist)
    op.alter_column(
        "continuous_evals",
        "llm_eval_version",
        existing_type=sa.Integer(),
        nullable=False,
    )

    # Revert llm_eval_name to non-nullable (may fail if rule-based rows exist)
    op.alter_column(
        "continuous_evals",
        "llm_eval_name",
        existing_type=sa.String(),
        nullable=False,
    )

    op.drop_column("continuous_evals", "rule_type")
    op.drop_column("continuous_evals", "evaluator_type")
