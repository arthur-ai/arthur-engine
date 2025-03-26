"""Add configurations table

Revision ID: 2313453ed5c1
Revises: eee0433afdbf
Create Date: 2023-08-04 07:56:35.854959

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "2313453ed5c1"
down_revision = "eee0433afdbf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "configurations",
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("name"),
        sa.UniqueConstraint("name"),
    )
    connection = op.get_bind()
    result = connection.execute(
        sa.text("SELECT extname FROM pg_extension WHERE extname = 'vector';"),
    ).fetchone()

    if result:
        op.drop_index("vector_index", table_name="embeddings")
        op.create_index(
            "my_index",
            "embeddings",
            ["embedding"],
            unique=False,
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_l2_ops"},
        )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    connection = op.get_bind()
    result = connection.execute(
        sa.text("SELECT extname FROM pg_extension WHERE extname = 'vector';"),
    ).fetchone()

    if result:
        op.drop_index(
            "my_index",
            table_name="embeddings",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_l2_ops"},
        )
        op.create_index("vector_index", "embeddings", ["embedding"], unique=False)
    op.drop_table("configurations")
    # ### end Alembic commands ###
