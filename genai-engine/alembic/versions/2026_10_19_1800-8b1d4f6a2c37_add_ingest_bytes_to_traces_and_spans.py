"""add ingest_bytes to traces and spans

Revision ID: 8b1d4f6a2c37
Revises: d2ffff9e0a56
Create Date: 2026-10-19 18:00:00.000000

Records the OTLP payload bytes received on the trace ingestion endpoints, per span (its
share of the request body) and summed per trace. The trace total feeds the ingest_bytes
consumption metric shown on the Arthur Platform's organization Consumption dashboard.

Nullable, and nothing is backfilled: the request bodies of earlier traces were never
kept, so consumption is counted from this revision onward.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "8b1d4f6a2c37"
down_revision = "d2ffff9e0a56"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("trace_metadata", sa.Column("ingest_bytes", sa.BigInteger(), nullable=True))
    op.add_column("spans", sa.Column("ingest_bytes", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("spans", "ingest_bytes")
    op.drop_column("trace_metadata", "ingest_bytes")
