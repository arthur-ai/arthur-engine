"""add_parent_id_to_span_table

Revision ID: d8853cfad672
Revises: 4be90136e983
Create Date: 2025-07-08 16:51:53.049431

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "d8853cfad672"
down_revision = "4be90136e983"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add parent_span_id column
    op.add_column("spans", sa.Column("parent_span_id", sa.String(), nullable=True))
    op.create_index(
        op.f("ix_spans_parent_span_id"),
        "spans",
        ["parent_span_id"],
        unique=False,
    )

    # Add span_kind column
    op.add_column("spans", sa.Column("span_kind", sa.String(), nullable=True))


def downgrade() -> None:
    # Drop span_kind column
    op.drop_column("spans", "span_kind")

    # Drop parent_span_id column and its index
    op.drop_index(op.f("ix_spans_parent_span_id"), table_name="spans")
    op.drop_column("spans", "parent_span_id")
