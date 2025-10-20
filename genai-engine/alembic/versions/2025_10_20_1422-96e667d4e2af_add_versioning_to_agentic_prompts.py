"""add versioning to agentic prompts

Revision ID: 96e667d4e2af
Revises: 897c39909e73
Create Date: 2025-10-20 14:22:19.855260

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "96e667d4e2af"
down_revision = "897c39909e73"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop old constraints first
    op.drop_constraint("agentic_prompts_pkey", "agentic_prompts", type_="primary")
    op.drop_constraint("uq_task_prompt_name", "agentic_prompts", type_="unique")

    # Add columns (version with default to backfill existing rows)
    op.add_column(
        "agentic_prompts",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "agentic_prompts",
        sa.Column("deleted_at", sa.TIMESTAMP(), nullable=True),
    )

    # Recreate constraints using new version column
    op.create_primary_key(
        "agentic_prompts_pkey",
        "agentic_prompts",
        ["task_id", "name", "version"],
    )
    op.create_unique_constraint(
        "uq_task_prompt_version",
        "agentic_prompts",
        ["task_id", "name", "version"],
    )

    # Remove default so version becomes required for future inserts
    op.alter_column("agentic_prompts", "version", server_default=None)


def downgrade() -> None:
    op.drop_constraint("uq_task_prompt_version", "agentic_prompts", type_="unique")
    op.drop_constraint("agentic_prompts_pkey", "agentic_prompts", type_="primary")
    op.create_primary_key(
        "agentic_prompts_pkey",
        "agentic_prompts",
        ["task_id", "name"],
    )
    op.create_unique_constraint(
        "uq_task_prompt_name",
        "agentic_prompts",
        ["task_id", "name"],
    )
    op.drop_column("agentic_prompts", "deleted_at")
    op.drop_column("agentic_prompts", "version")
