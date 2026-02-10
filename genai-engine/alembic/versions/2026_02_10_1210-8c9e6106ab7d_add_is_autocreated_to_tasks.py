"""add_is_autocreated_to_tasks

Revision ID: 8c9e6106ab7d
Revises: 843e2d3f46d5
Create Date: 2026-02-10 12:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8c9e6106ab7d'
down_revision = '843e2d3f46d5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_autocreated column to tasks table with default False
    op.add_column('tasks', sa.Column('is_autocreated', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    # Remove is_autocreated column from tasks table
    op.drop_column('tasks', 'is_autocreated')
