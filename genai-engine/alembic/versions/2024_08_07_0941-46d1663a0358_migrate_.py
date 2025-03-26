"""Migrate ModelHallucinationRuleExperimental to ModelHallucinationRuleV3

Revision ID: 46d1663a0358
Revises: 8927105d0493
Create Date: 2024-08-07 09:41:39.615918

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "46d1663a0358"
down_revision = "8927105d0493"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "update rules set type = 'ModelHallucinationRuleV3' where type = 'ModelHallucinationRuleExperimental'",
    )


def downgrade() -> None:
    op.execute(
        "update rules set type = 'ModelHallucinationRuleExperimental' where type = 'ModelHallucinationRuleV3'",
    )
