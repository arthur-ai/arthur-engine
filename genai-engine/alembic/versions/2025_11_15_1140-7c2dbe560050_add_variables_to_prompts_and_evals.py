"""add variables to prompts and evals

Revision ID: 7c2dbe560050
Revises: 52c0a0da3ef1
Create Date: 2025-11-15 11:40:52.442535
"""

import json

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from src.schemas.agentic_prompt_schemas import AgenticPrompt
from src.services.prompt.chat_completion_service import ChatCompletionService

# revision identifiers, used by Alembic.
revision = "7c2dbe560050"
down_revision = "52c0a0da3ef1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agentic_prompts",
        sa.Column("variables", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "llm_evals",
        sa.Column("variables", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )

    connection = op.get_bind()
    chat_service = ChatCompletionService()

    # Update agentic_prompts
    prompts_result = connection.execute(
        sa.text(
            "SELECT task_id, name, version, messages, model_name, model_provider, tools, config, created_at, deleted_at FROM agentic_prompts",
        ),
    )

    # Backfill existing prompts with their variables
    for row in prompts_result:
        prompt_dict = {
            "task_id": row[0],
            "name": row[1],
            "version": row[2],
            "messages": row[3],
            "model_name": row[4],
            "model_provider": row[5],
            "tools": row[6],
            "config": row[7],
            "created_at": row[8],
            "deleted_at": row[9],
        }

        # Validate to convert JSON to proper format (like from_db_model does)
        prompt = AgenticPrompt.model_validate(prompt_dict)

        variables = list(
            chat_service.find_missing_variables_in_messages(
                variable_map={},
                messages=prompt.messages,
            ),
        )
        connection.execute(
            sa.text(
                "UPDATE agentic_prompts SET variables = :variables "
                "WHERE task_id = :task_id AND name = :name AND version = :version",
            ),
            {
                "variables": json.dumps(variables),
                "task_id": prompt_dict["task_id"],
                "name": prompt_dict["name"],
                "version": prompt_dict["version"],
            },
        )

    # Backfill existing evals with their variables
    evals_result = connection.execute(
        sa.text("SELECT task_id, name, version, instructions FROM llm_evals"),
    )

    for row in evals_result:
        task_id, name, version, instructions = row
        variables = list(chat_service.find_undeclared_variables_in_text(instructions))
        connection.execute(
            sa.text(
                "UPDATE llm_evals SET variables = :variables "
                "WHERE task_id = :task_id AND name = :name AND version = :version",
            ),
            {
                "variables": json.dumps(variables),
                "task_id": task_id,
                "name": name,
                "version": version,
            },
        )


def downgrade() -> None:
    op.drop_column("llm_evals", "variables")
    op.drop_column("agentic_prompts", "variables")
