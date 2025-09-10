"""metric_details_to_json

Revision ID: 4617f961d9f0
Revises: 0135e39e511f
Create Date: 2025-09-10 16:13:04.362940

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "4617f961d9f0"
down_revision = "0135e39e511f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Convert String column to JSON column for PostgreSQL
    # Since existing data should be valid JSON strings, we can directly alter the column type
    op.execute(
        "ALTER TABLE metric_results ALTER COLUMN details TYPE jsonb USING details::jsonb",
    )


def downgrade() -> None:
    # Convert JSONB column back to String/Text
    op.execute(
        "ALTER TABLE metric_results ALTER COLUMN details TYPE text USING details::text",
    )
