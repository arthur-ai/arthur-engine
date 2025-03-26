"""hallucination_rule_v3_beta_name_migration

Revision ID: 8927105d0493
Revises: 1dcbca1f3baa
Create Date: 2024-08-05 11:30:07.038433

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "8927105d0493"
down_revision = "1dcbca1f3baa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "update rules set type = 'ModelHallucinationRuleV3' where type = 'ModelHallucinationRuleV3(Beta)'",
    )


def downgrade() -> None:
    op.execute(
        "update rules set type = 'ModelHallucinationRuleV3(Beta)' where type = 'ModelHallucinationRuleV3'",
    )
