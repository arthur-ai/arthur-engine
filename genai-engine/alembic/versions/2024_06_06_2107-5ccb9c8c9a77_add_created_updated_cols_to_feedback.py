"""add created updated cols to feedback

Adds created_at/updated_at columns as well as a user_id to the inference_feedback table.
By default, it sets the created_at/updated_at columns to the current timestamp.

Revision ID: 5ccb9c8c9a77
Revises: 234b9fdee6c2
Create Date: 2024-06-06 21:07:51.703784

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5ccb9c8c9a77"
down_revision = "234b9fdee6c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add user_id column
    op.add_column(
        "inference_feedback",
        sa.Column("user_id", sa.String(), nullable=True),
    )
    # Add created_at/updated_at columns
    op.add_column(
        "inference_feedback",
        sa.Column("created_at", sa.DateTime(), default=sa.func.now()),
    )
    op.add_column(
        "inference_feedback",
        sa.Column("updated_at", sa.DateTime(), default=sa.func.now()),
    )

    # Set values of created_at/updated_at columns to the current timestamp
    current_timestamp = sa.func.now()
    op.execute(
        f"UPDATE inference_feedback SET created_at = {current_timestamp} WHERE created_at is NULL",
    )
    op.execute(
        f"UPDATE inference_feedback SET updated_at = {current_timestamp} WHERE updated_at is NULL",
    )

    # Set created_at/updated_at to be non-nullable
    op.alter_column("inference_feedback", "created_at", nullable=False)
    op.alter_column("inference_feedback", "updated_at", nullable=False)


def downgrade() -> None:
    op.drop_column("inference_feedback", "updated_at")
    op.drop_column("inference_feedback", "created_at")
