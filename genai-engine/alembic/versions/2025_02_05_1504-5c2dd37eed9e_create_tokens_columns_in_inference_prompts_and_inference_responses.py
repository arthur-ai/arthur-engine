"""create tokens columns in inference_prompts and inference_responses

Revision ID: 5c2dd37eed9e
Revises: 68c62e902853
Create Date: 2025-02-05 15:04:17.286472

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5c2dd37eed9e"
down_revision = "68c62e902853"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add tokens column to inference_prompts table
    op.add_column("inference_prompts", sa.Column("tokens", sa.Integer, nullable=True))

    # Add tokens column to inference_responses table
    op.add_column("inference_responses", sa.Column("tokens", sa.Integer, nullable=True))

    # Copy data from old columns to new columns using inference_id
    op.execute(
        """
        UPDATE inference_prompts AS ip
        SET tokens = subquery.max_tokens
        FROM (
            SELECT inference_prompt_id, MAX(user_input_tokens) AS max_tokens
            FROM prompt_rule_results
            GROUP BY inference_prompt_id
        ) AS subquery
        WHERE ip.id = subquery.inference_prompt_id
    """,
    )

    op.execute(
        """
        UPDATE inference_responses AS ir
        SET tokens = subquery.max_tokens
        FROM (
            SELECT inference_response_id, MAX(user_input_tokens) AS max_tokens
            FROM response_rule_results
            GROUP BY inference_response_id
        ) AS subquery
        WHERE ir.id = subquery.inference_response_id
    """,
    )

    op.drop_column("prompt_rule_results", "user_input_tokens")
    op.drop_column("response_rule_results", "user_input_tokens")


def downgrade() -> None:
    op.add_column(
        "prompt_rule_results",
        sa.Column("user_input_tokens", sa.Integer(), nullable=True),
    )
    op.add_column(
        "response_rule_results",
        sa.Column("user_input_tokens", sa.Integer(), nullable=True),
    )

    op.execute(
        """
        UPDATE prompt_rule_results
        SET user_input_tokens = inference_prompts.tokens
        FROM inference_prompts
        WHERE prompt_rule_results.inference_prompt_id = inference_prompts.id
    """,
    )

    op.execute(
        """
        UPDATE response_rule_results
        SET user_input_tokens = inference_responses.tokens
        FROM inference_responses
        WHERE response_rule_results.inference_response_id = inference_responses.id
    """,
    )

    # Make columns non-nullable
    op.alter_column(
        "prompt_rule_results",
        "user_input_tokens",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "response_rule_results",
        "user_input_tokens",
        existing_type=sa.Integer(),
        nullable=False,
    )

    # Remove tokens columns
    op.drop_column("inference_prompts", "tokens")
    op.drop_column("inference_responses", "tokens")
