"""merge trace_end_time_index and continuous_eval_test

Revision ID: f15ac7955e6f
Revises: 6939d74b3750, 711e7d7236ae
Create Date: 2026-04-09 14:33:22.665275

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f15ac7955e6f'
down_revision = ('6939d74b3750', '711e7d7236ae')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
