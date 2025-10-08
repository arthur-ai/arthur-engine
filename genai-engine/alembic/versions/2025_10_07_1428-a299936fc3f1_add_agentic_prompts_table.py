"""add_agentic_prompts_table

Revision ID: a299936fc3f1
Revises: 4617f961d9f0
Create Date: 2025-10-07 14:28:21.273054
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "a299936fc3f1"
down_revision = "4617f961d9f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agentic_prompts",
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("model_provider", sa.String(), nullable=False),
        sa.Column("messages", sa.JSON(), nullable=False),
        sa.Column("tools", sa.JSON(), nullable=True),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("task_id", "name", name="agentic_prompts_pkey"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"]),
    )

    op.create_index(
        op.f("ix_agentic_prompts_task_id"),
        "agentic_prompts",
        ["task_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_task_prompt_name",
        "agentic_prompts",
        ["task_id", "name"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_task_prompt_name", "agentic_prompts", type_="unique")
    op.drop_index(op.f("ix_agentic_prompts_task_id"), table_name="agentic_prompts")
    op.drop_table("agentic_prompts")
