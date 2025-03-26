"""Add order number to claims.

Revision ID: 1dcbca1f3baa
Revises: e00e4d87eea5
Create Date: 2024-07-12 08:30:07.517776

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1dcbca1f3baa"
down_revision = "e00e4d87eea5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "hallucination_claims",
        sa.Column(
            "order_number",
            sa.Integer(),
            server_default=sa.text("-1"),
            nullable=False,
        ),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("hallucination_claims", "order_number")
    # ### end Alembic commands ###
