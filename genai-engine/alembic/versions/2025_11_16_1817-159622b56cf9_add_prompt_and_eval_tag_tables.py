"""add prompt and eval tag tables

Revision ID: 159622b56cf9
Revises: 0381fe93ad77
Create Date: 2025-11-16 18:17:36.711432

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "159622b56cf9"
down_revision = "0381fe93ad77"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -------------------------
    # AGENTIC PROMPT VERSION TAGS
    # -------------------------

    op.create_table(
        "agentic_prompt_version_tags",
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("tag", sa.String(), nullable=False),
        # FK to the prompt version row
        sa.ForeignKeyConstraint(
            ["task_id", "name", "version"],
            [
                "agentic_prompts.task_id",
                "agentic_prompts.name",
                "agentic_prompts.version",
            ],
            name="fk_agentic_prompt_version_tags_prompt",
        ),
        # Composite PK INCLUDING tag
        sa.PrimaryKeyConstraint(
            "task_id",
            "name",
            "version",
            "tag",
            name="pk_agentic_prompt_version_tags",
        ),
        # Tag uniqueness per prompt name
        sa.UniqueConstraint(
            "task_id",
            "name",
            "tag",
            name="uq_agentic_prompt_task_name_tag",
        ),
    )

    op.create_index(
        "ix_agentic_prompt_version_tags_task_id",
        "agentic_prompt_version_tags",
        ["task_id"],
        unique=False,
    )

    # -------------------------
    # LLM EVAL VERSION TAGS
    # -------------------------

    op.create_table(
        "llm_eval_version_tags",
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("tag", sa.String(), nullable=False),
        # FK to eval version row
        sa.ForeignKeyConstraint(
            ["task_id", "name", "version"],
            ["llm_evals.task_id", "llm_evals.name", "llm_evals.version"],
            name="fk_llm_eval_version_tags_eval",
        ),
        # Composite PK INCLUDING tag
        sa.PrimaryKeyConstraint(
            "task_id",
            "name",
            "version",
            "tag",
            name="pk_llm_eval_version_tags",
        ),
        # Ensure tag is unique per task + name
        sa.UniqueConstraint(
            "task_id",
            "name",
            "tag",
            name="uq_llm_eval_task_name_tag",
        ),
    )

    op.create_index(
        "ix_llm_eval_version_tags_task_id",
        "llm_eval_version_tags",
        ["task_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_llm_eval_version_tags_task_id",
        table_name="llm_eval_version_tags",
    )
    op.drop_table("llm_eval_version_tags")

    op.drop_index(
        "ix_agentic_prompt_version_tags_task_id",
        table_name="agentic_prompt_version_tags",
    )
    op.drop_table("agentic_prompt_version_tags")
