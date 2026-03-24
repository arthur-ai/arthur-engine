"""add evaluator_type and rule_type to continuous_evals

Revision ID: a1b2c3d4e5f6
Revises: 04c5e8528072
Create Date: 2026-03-24 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "04c5e8528072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add evaluator_type column — defaults to 'llm_eval' for all existing rows
    op.add_column(
        "continuous_evals",
        sa.Column(
            "evaluator_type",
            sa.String(),
            nullable=False,
            server_default="llm_eval",
        ),
    )

    # Add rule_type column — nullable, populated only for rule-based evaluators
    op.add_column(
        "continuous_evals",
        sa.Column("rule_type", sa.String(), nullable=True),
    )

    # Make llm_eval_name nullable — rule-based evaluators do not reference an LLM eval
    op.alter_column(
        "continuous_evals",
        "llm_eval_name",
        existing_type=sa.String(),
        nullable=True,
    )

    # Make llm_eval_version nullable — rule-based evaluators do not reference an LLM eval
    op.alter_column(
        "continuous_evals",
        "llm_eval_version",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    # Revert llm_eval_version to NOT NULL — requires no NULL values exist
    op.alter_column(
        "continuous_evals",
        "llm_eval_version",
        existing_type=sa.Integer(),
        nullable=False,
    )

    # Revert llm_eval_name to NOT NULL — requires no NULL values exist
    op.alter_column(
        "continuous_evals",
        "llm_eval_name",
        existing_type=sa.String(),
        nullable=False,
    )

    op.drop_column("continuous_evals", "rule_type")
    op.drop_column("continuous_evals", "evaluator_type")
