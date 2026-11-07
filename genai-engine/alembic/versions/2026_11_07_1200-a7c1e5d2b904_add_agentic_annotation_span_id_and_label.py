"""add span_id and label to agentic_annotations

Revision ID: a7c1e5d2b904
Revises: e0a1b2c3d4f5
Create Date: 2026-11-07 12:00:00.000000

agentic_annotations.span_id is the span an annotation is about (NULL for the whole
trace) and agentic_annotations.label is its category, such as "wrong_tool", given
by a person or by a judge whose instructions define categories. Both nullable with
no backfill: existing annotations stay whole-trace and unlabelled.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "a7c1e5d2b904"
down_revision = "e0a1b2c3d4f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agentic_annotations",
        sa.Column("span_id", sa.String(), nullable=True),
    )
    op.add_column(
        "agentic_annotations",
        sa.Column("label", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agentic_annotations", "label")
    op.drop_column("agentic_annotations", "span_id")
