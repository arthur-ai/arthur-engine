"""merge onboarding and demo_certificates heads

Revision ID: 2966018cec1d
Revises: d4e5f6a7b8c9, 490cd5586c25
Create Date: 2026-06-03 09:00:00.000000

Merges two parallel migration heads that both descended from
7e1c3a4b5d2f: d4e5f6a7b8c9 (create_onboarding_tables) and
490cd5586c25 (add_demo_certificates_table).
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "2966018cec1d"
down_revision = ("d4e5f6a7b8c9", "490cd5586c25")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
