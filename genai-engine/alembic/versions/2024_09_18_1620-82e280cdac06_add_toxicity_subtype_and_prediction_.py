"""add toxicity subtype and prediction span column


Revision ID: 82e280cdac06
Revises: 46d1663a0358
Create Date: 2024-09-18 16:20:55.431601

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "82e280cdac06"
down_revision = "46d1663a0358"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "toxicity_scores",
        sa.Column(
            "toxicity_violation_type",
            sa.String(),
            server_default=sa.text("'unknown'"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("toxicity_scores", "toxicity_violation_type")
