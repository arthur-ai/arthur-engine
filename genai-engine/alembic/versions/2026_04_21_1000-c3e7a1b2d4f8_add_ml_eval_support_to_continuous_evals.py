"""add ml eval support to continuous_evals

Revision ID: c3e7a1b2d4f8
Revises: 8f5b46f379f5
Create Date: 2026-04-21 10:00:00.000000

Adds eval_type discriminator and ML eval reference columns to the continuous_evals
table. Makes llm_eval_name/llm_eval_version nullable (they are irrelevant for ML
continuous evals) and drops the FK constraint that hard-wired continuous evals to
llm_evals, allowing ML evals to be referenced instead.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "c3e7a1b2d4f8"
down_revision = "8f5b46f379f5"
branch_labels = None
depends_on = None

_TABLE = "continuous_evals"
_FK_NAME = "fk_llm_eval_transforms_eval"


def upgrade() -> None:
    # 1. Drop the FK constraint that hard-links continuous_evals to llm_evals.
    #    ML continuous evals reference llm_evals too (ML evals are stored there),
    #    but via a different eval_type, so we manage referential integrity in app code.
    op.drop_constraint(_FK_NAME, _TABLE, type_="foreignkey")

    # 2. Make llm_eval_name / llm_eval_version nullable (not needed for ML evals).
    op.alter_column(_TABLE, "llm_eval_name", existing_type=sa.String(), nullable=True)
    op.alter_column(
        _TABLE,
        "llm_eval_version",
        existing_type=sa.Integer(),
        nullable=True,
    )

    # 3. Add eval_type discriminator — backfill existing rows as "llm_eval".
    op.add_column(
        _TABLE,
        sa.Column(
            "eval_type",
            sa.String(),
            nullable=False,
            server_default="llm_eval",
        ),
    )

    # 4. Add ML eval reference columns (nullable; only populated for ML evals).
    op.add_column(_TABLE, sa.Column("ml_eval_name", sa.String(), nullable=True))
    op.add_column(_TABLE, sa.Column("ml_eval_version", sa.Integer(), nullable=True))


def downgrade() -> None:
    # Remove new columns
    op.drop_column(_TABLE, "ml_eval_version")
    op.drop_column(_TABLE, "ml_eval_name")
    op.drop_column(_TABLE, "eval_type")

    # Restore NOT NULL on llm_eval fields (will fail if any ML eval rows exist)
    op.alter_column(
        _TABLE,
        "llm_eval_version",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(_TABLE, "llm_eval_name", existing_type=sa.String(), nullable=False)

    # Restore FK constraint
    op.create_foreign_key(
        _FK_NAME,
        _TABLE,
        "llm_evals",
        ["task_id", "llm_eval_name", "llm_eval_version"],
        ["task_id", "name", "version"],
        ondelete="CASCADE",
    )
