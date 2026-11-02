"""add token usage to agentic_annotations

Revision ID: 3f7c2a9e41d8
Revises: e5a9c3b71f04
Create Date: 2026-11-02 09:00:00.000000

Records prompt, completion, cache-read and cache-write token counts for each continuous eval
run, so prompt-cache hit rates can be checked alongside the cost already stored per run.

Nullable, and nothing is backfilled: earlier runs never kept their usage.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "3f7c2a9e41d8"
down_revision = "e5a9c3b71f04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agentic_annotations", sa.Column("prompt_tokens", sa.Integer(), nullable=True))
    op.add_column("agentic_annotations", sa.Column("completion_tokens", sa.Integer(), nullable=True))
    op.add_column("agentic_annotations", sa.Column("cache_read_tokens", sa.Integer(), nullable=True))
    op.add_column("agentic_annotations", sa.Column("cache_write_tokens", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("agentic_annotations", "cache_write_tokens")
    op.drop_column("agentic_annotations", "cache_read_tokens")
    op.drop_column("agentic_annotations", "completion_tokens")
    op.drop_column("agentic_annotations", "prompt_tokens")
