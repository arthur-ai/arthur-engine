"""update_raw_span_structure

Revision ID: 2264832c91c0
Revises: 5a02e38003af
Create Date: 2025-10-29 16:45:15.459000

"""

# Import the normalization service
import sys
from pathlib import Path

from psycopg2.extras import Json
from sqlalchemy import text

from alembic import op

# Add the src directory to path for imports
migration_dir = Path(__file__).parent.parent.parent
src_dir = migration_dir / "src"
sys.path.insert(0, str(src_dir))

from services.trace.span_normalization_service import SpanNormalizationService

# revision identifiers, used by Alembic.
revision = "2264832c91c0"
down_revision = "5a02e38003af"
branch_labels = None
depends_on = None

BATCH_SIZE = 1000


def is_already_normalized(attributes: dict) -> bool:
    """Check for nested structure - top-level keys contain dict values"""

    if not isinstance(attributes, dict):
        return False

    return any(
        isinstance(v, dict)
        and k in ["llm", "input", "output", "embedding", "retrieval", "tool"]
        for k, v in attributes.items()
    )


def upgrade() -> None:
    """
    Migrate existing spans from flat attribute format to nested format.

    This is a breaking change that normalizes all span raw_data to use
    nested dictionary structure based on OpenInference semantic conventions.
    """
    connection = op.get_bind()
    normalizer = SpanNormalizationService()

    result = connection.execute(text("SELECT COUNT(*) FROM spans"))
    total_spans = result.scalar()

    if total_spans == 0:
        return

    offset = 0

    while True:
        result = connection.execute(
            text(
                """
                SELECT id, raw_data
                FROM spans
                ORDER BY created_at
                LIMIT :limit OFFSET :offset
            """,
            ),
            {"limit": BATCH_SIZE, "offset": offset},
        )

        batch = result.fetchall()
        if not batch:
            break

        for span_id, raw_data in batch:
            # Check if already normalized
            attributes = raw_data.get("attributes", {})
            if is_already_normalized(attributes):
                offset += 1
                continue

            # Normalize using the service
            normalized_data = normalizer.normalize_span_to_nested_dict(raw_data)

            if "arthur_span_version" not in normalized_data:
                normalized_data["arthur_span_version"] = raw_data.get(
                    "arthur_span_version",
                    "arthur_span_v1",
                )

            connection.execute(
                text(
                    """
                    UPDATE spans
                    SET raw_data = :raw_data,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :span_id
                """,
                ),
                {"span_id": span_id, "raw_data": Json(normalized_data)},
            )

            offset += 1

        # Commit after each batch
        connection.commit()


def downgrade() -> None:
    """
    Downgrade is not supported for this migration.

    This is a breaking fail-forward change. To revert, restore from backup.
    """
    raise RuntimeError(
        "Downgrade is not supported for migration 2264832c91c0. "
        "This is a breaking fail-forward change. "
        "To revert, restore from a backup taken before this migration.",
    )
