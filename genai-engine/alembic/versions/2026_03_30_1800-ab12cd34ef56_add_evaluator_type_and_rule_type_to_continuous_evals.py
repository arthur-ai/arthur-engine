"""add evaluator_type and rule_type to continuous_evals

Revision ID: ab12cd34ef56
Revises: 04c5e8528072
Create Date: 2026-03-30 18:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ab12cd34ef56"
down_revision = "04c5e8528072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add evaluator_type column with default "llm_eval" for existing rows
    op.add_column(
        "continuous_evals",
        sa.Column(
            "evaluator_type",
            sa.String(),
            nullable=False,
            server_default="llm_eval",
        ),
    )
    # Add rule_type column (nullable, only set for rule_based evaluator type)
    op.add_column(
        "continuous_evals",
        sa.Column("rule_type", sa.String(), nullable=True),
    )
    # Make llm_eval_name nullable (not required for rule_based)
    op.alter_column("continuous_evals", "llm_eval_name", nullable=True)
    # Make llm_eval_version nullable (not required for rule_based)
    op.alter_column("continuous_evals", "llm_eval_version", nullable=True)
    # Make transform_id nullable (not required for rule_based)
    op.alter_column("continuous_evals", "transform_id", nullable=True)


def downgrade() -> None:
    # Revert transform_id to non-nullable (assumes no rule_based rows exist)
    op.alter_column("continuous_evals", "transform_id", nullable=False)
    # Revert llm_eval_version to non-nullable
    op.alter_column("continuous_evals", "llm_eval_version", nullable=False)
    # Revert llm_eval_name to non-nullable
    op.alter_column("continuous_evals", "llm_eval_name", nullable=False)
    op.drop_column("continuous_evals", "rule_type")
    op.drop_column("continuous_evals", "evaluator_type")
