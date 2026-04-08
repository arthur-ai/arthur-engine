"""add ml_evals table and update continuous_evals for ML eval support

Revision ID: a1b2c3d4e5f7
Revises: 04c5e8528072
Create Date: 2026-04-06 12:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f7"
down_revision = "04c5e8528072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Create ml_evals table ---
    op.create_table(
        "ml_evals",
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("ml_eval_type", sa.String(), nullable=False),
        sa.Column(
            "model_provider",
            sa.String(),
            nullable=False,
            server_default="arthur_builtin",
        ),
        sa.Column("config", JSON(), nullable=True),
        sa.Column(
            "variables",
            JSON(),
            nullable=False,
            server_default='["input"]',
        ),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("deleted_at", sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], name="fk_ml_evals_task_id"),
        sa.PrimaryKeyConstraint("task_id", "name", "version", name="pk_ml_evals"),
    )
    op.create_index("ix_ml_evals_task_id", "ml_evals", ["task_id"])

    # --- Create ml_eval_version_tags table ---
    op.create_table(
        "ml_eval_version_tags",
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("tag", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["task_id", "name", "version"],
            ["ml_evals.task_id", "ml_evals.name", "ml_evals.version"],
            name="fk_ml_eval_version_tags_eval",
        ),
        sa.PrimaryKeyConstraint(
            "task_id",
            "name",
            "version",
            "tag",
            name="pk_ml_eval_version_tags",
        ),
        sa.UniqueConstraint("task_id", "name", "tag", name="uq_ml_eval_task_name_tag"),
    )
    op.create_index(
        "ix_ml_eval_version_tags_task_id",
        "ml_eval_version_tags",
        ["task_id"],
    )

    # --- Update continuous_evals ---

    # 1. Drop old FK constraint that references llm_evals (non-nullable columns)
    op.drop_constraint(
        "fk_llm_eval_transforms_eval",
        "continuous_evals",
        type_="foreignkey",
    )

    # 2. Make llm_eval_name and llm_eval_version nullable
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

    # 3. Add eval_type column (NOT NULL, default 'llm_eval')
    op.add_column(
        "continuous_evals",
        sa.Column(
            "eval_type",
            sa.String(),
            nullable=False,
            server_default="llm_eval",
        ),
    )

    # 4. Add ml_eval_name and ml_eval_version columns (nullable)
    op.add_column(
        "continuous_evals",
        sa.Column("ml_eval_name", sa.String(), nullable=True),
    )
    op.add_column(
        "continuous_evals",
        sa.Column("ml_eval_version", sa.Integer(), nullable=True),
    )

    # 5. Re-create FK for LLM eval (now with nullable columns)
    op.create_foreign_key(
        "fk_continuous_evals_llm_eval",
        "continuous_evals",
        "llm_evals",
        ["task_id", "llm_eval_name", "llm_eval_version"],
        ["task_id", "name", "version"],
        ondelete="CASCADE",
    )

    # 6. Create FK for ML eval
    op.create_foreign_key(
        "fk_continuous_evals_ml_eval",
        "continuous_evals",
        "ml_evals",
        ["task_id", "ml_eval_name", "ml_eval_version"],
        ["task_id", "name", "version"],
        ondelete="CASCADE",
    )

    # 7. Add check constraint
    op.create_check_constraint(
        "ck_continuous_evals_eval_ref",
        "continuous_evals",
        "(eval_type = 'llm_eval' AND llm_eval_name IS NOT NULL AND llm_eval_version IS NOT NULL)"
        " OR (eval_type = 'ml_eval' AND ml_eval_name IS NOT NULL AND ml_eval_version IS NOT NULL)",
    )


def downgrade() -> None:
    # Remove check constraint
    op.drop_constraint(
        "ck_continuous_evals_eval_ref",
        "continuous_evals",
        type_="check",
    )

    # Remove ML eval FK
    op.drop_constraint(
        "fk_continuous_evals_ml_eval",
        "continuous_evals",
        type_="foreignkey",
    )

    # Remove LLM eval FK
    op.drop_constraint(
        "fk_continuous_evals_llm_eval",
        "continuous_evals",
        type_="foreignkey",
    )

    # Remove ml eval columns
    op.drop_column("continuous_evals", "ml_eval_version")
    op.drop_column("continuous_evals", "ml_eval_name")
    op.drop_column("continuous_evals", "eval_type")

    # Restore llm_eval_name and llm_eval_version as NOT NULL
    op.alter_column(
        "continuous_evals",
        "llm_eval_name",
        existing_type=sa.String(),
        nullable=False,
    )
    op.alter_column(
        "continuous_evals",
        "llm_eval_version",
        existing_type=sa.Integer(),
        nullable=False,
    )

    # Restore original FK
    op.create_foreign_key(
        "fk_llm_eval_transforms_eval",
        "continuous_evals",
        "llm_evals",
        ["task_id", "llm_eval_name", "llm_eval_version"],
        ["task_id", "name", "version"],
        ondelete="CASCADE",
    )

    # Drop ml_eval_version_tags
    op.drop_index("ix_ml_eval_version_tags_task_id", "ml_eval_version_tags")
    op.drop_table("ml_eval_version_tags")

    # Drop ml_evals
    op.drop_index("ix_ml_evals_task_id", "ml_evals")
    op.drop_table("ml_evals")
