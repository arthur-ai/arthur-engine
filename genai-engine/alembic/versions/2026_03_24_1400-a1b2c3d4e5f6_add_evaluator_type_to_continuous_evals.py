"""add evaluator_type, rule_type, rule_config to continuous_evals; make llm_eval fields nullable

Revision ID: a1b2c3d4e5f6
Revises: 04c5e8528072
Create Date: 2026-03-24 14:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "04c5e8528072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the FK constraint that ties continuous_evals to llm_evals.
    # Rule-based evaluator CEs don't reference an llm_eval row.
    op.drop_constraint(
        "fk_llm_eval_transforms_eval",
        "continuous_evals",
        type_="foreignkey",
    )

    # Add evaluator_type discriminator column (default 'llm' for existing rows)
    op.add_column(
        "continuous_evals",
        sa.Column(
            "evaluator_type",
            sa.String(),
            nullable=False,
            server_default="llm",
        ),
    )

    # Add rule_type column (only populated for rule-based evaluator CEs)
    op.add_column(
        "continuous_evals",
        sa.Column("rule_type", sa.String(), nullable=True),
    )

    # Add rule_config column (JSON config for rule-based evaluators)
    op.add_column(
        "continuous_evals",
        sa.Column("rule_config", JSON(), nullable=True),
    )

    # Make llm_eval_name nullable (not required for rule-based evaluator CEs)
    op.alter_column("continuous_evals", "llm_eval_name", nullable=True)

    # Make llm_eval_version nullable (not required for rule-based evaluator CEs)
    op.alter_column("continuous_evals", "llm_eval_version", nullable=True)


def downgrade() -> None:
    # Restore llm_eval_name and llm_eval_version as non-nullable.
    # NOTE: rows with null values must be cleaned up before running downgrade.
    op.alter_column("continuous_evals", "llm_eval_version", nullable=False)
    op.alter_column("continuous_evals", "llm_eval_name", nullable=False)

    op.drop_column("continuous_evals", "rule_config")
    op.drop_column("continuous_evals", "rule_type")
    op.drop_column("continuous_evals", "evaluator_type")

    # Restore FK constraint to llm_evals
    op.create_foreign_key(
        "fk_llm_eval_transforms_eval",
        "continuous_evals",
        "llm_evals",
        ["task_id", "llm_eval_name", "llm_eval_version"],
        ["task_id", "name", "version"],
        ondelete="CASCADE",
    )
