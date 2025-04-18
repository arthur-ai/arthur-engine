"""adding pii entities

Revision ID: 083f1ae171fd
Revises: 9ff69176b1bf
Create Date: 2023-10-27 14:48:15.870824

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "083f1ae171fd"
down_revision = "9ff69176b1bf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "pii_entities",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("rule_result_detail_id", sa.String(), nullable=False),
        sa.Column("entity", sa.String(), nullable=False),
        sa.Column("span", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["rule_result_detail_id"],
            ["rule_result_details.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pii_entities_id"), "pii_entities", ["id"], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_pii_entities_id"), table_name="pii_entities")
    op.drop_table("pii_entities")
    # ### end Alembic commands ###
