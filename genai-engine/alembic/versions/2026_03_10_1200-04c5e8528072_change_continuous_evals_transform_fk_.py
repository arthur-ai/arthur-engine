"""change continuous_evals transform FK from CASCADE to RESTRICT

Revision ID: 04c5e8528072
Revises: 53f5544bc0b8
Create Date: 2026-03-10 12:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "04c5e8528072"
down_revision = "53f5544bc0b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "continuous_evals_transform_id_fkey",
        "continuous_evals",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "continuous_evals_transform_id_fkey",
        "continuous_evals",
        "trace_transforms",
        ["transform_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "continuous_evals_transform_id_fkey",
        "continuous_evals",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "continuous_evals_transform_id_fkey",
        "continuous_evals",
        "trace_transforms",
        ["transform_id"],
        ["id"],
        ondelete="CASCADE",
    )
