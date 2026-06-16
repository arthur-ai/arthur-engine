"""merge token_limit and eval_type heads

Revision ID: 646bea1451cf
Revises: 5e84b8d7aa1f, e1f2a3b4c5d6
Create Date: 2026-06-16 09:00:00.000000

Merges the two parallel migration heads:
  - 5e84b8d7aa1f (add_token_limit_to_organizations, UP-4390)
  - e1f2a3b4c5d6 (add_eval_type_support)

No-op merge: both upgrades are independent, so this revision just joins
the history graph back to a single head.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "646bea1451cf"
down_revision = ("5e84b8d7aa1f", "e1f2a3b4c5d6")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
