"""Add inference response context column

Revision ID: f9c19016756d
Revises: d298a8a6e360
Create Date: 2023-09-27 13:29:56.681387

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f9c19016756d"
down_revision = "d298a8a6e360"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "inference_response_contents",
        sa.Column("context", sa.String(), nullable=True),
    )
    op.alter_column(
        "prompt_rule_results",
        "user_input_tokens",
        existing_type=sa.INTEGER(),
        nullable=False,
    )
    op.alter_column(
        "prompt_rule_results",
        "prompt_tokens",
        existing_type=sa.INTEGER(),
        nullable=False,
    )
    op.alter_column(
        "prompt_rule_results",
        "completion_tokens",
        existing_type=sa.INTEGER(),
        nullable=False,
    )
    op.alter_column(
        "response_rule_results",
        "user_input_tokens",
        existing_type=sa.INTEGER(),
        nullable=False,
    )
    op.alter_column(
        "response_rule_results",
        "prompt_tokens",
        existing_type=sa.INTEGER(),
        nullable=False,
    )
    op.alter_column(
        "response_rule_results",
        "completion_tokens",
        existing_type=sa.INTEGER(),
        nullable=False,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "response_rule_results",
        "completion_tokens",
        existing_type=sa.INTEGER(),
        nullable=True,
    )
    op.alter_column(
        "response_rule_results",
        "prompt_tokens",
        existing_type=sa.INTEGER(),
        nullable=True,
    )
    op.alter_column(
        "response_rule_results",
        "user_input_tokens",
        existing_type=sa.INTEGER(),
        nullable=True,
    )
    op.alter_column(
        "prompt_rule_results",
        "completion_tokens",
        existing_type=sa.INTEGER(),
        nullable=True,
    )
    op.alter_column(
        "prompt_rule_results",
        "prompt_tokens",
        existing_type=sa.INTEGER(),
        nullable=True,
    )
    op.alter_column(
        "prompt_rule_results",
        "user_input_tokens",
        existing_type=sa.INTEGER(),
        nullable=True,
    )
    op.drop_column("inference_response_contents", "context")
    # ### end Alembic commands ###
