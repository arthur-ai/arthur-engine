"""add key_kind to service_name_task_mappings

Revision ID: 91bac5fc80b6
Revises: c8d1e4f70a63
Create Date: 2026-09-23 12:00:00.000000

Discovery resolution keys a discovered agent's `external_id` into
`service_name_task_mappings` alongside the service names OTEL resolution reads.
Without telling the two apart, an external ID is reported back as a service name
the agent emits telemetry under, and a trace whose `service.name` happens to equal
some record's external ID resolves to that record's task.

`key_kind` says which a row is. It joins the primary key so the same string can be
both a service name and an external ID, mapped to different tasks. Every existing
row was written by trace ingestion or GCP polling, so the backfill is uniformly
`service_name`, which the server default supplies.

The downgrade drops external-ID rows rather than folding them back in as service
names, which is the collision this revision exists to prevent.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "91bac5fc80b6"
down_revision = "c8d1e4f70a63"
branch_labels = None
depends_on = None

TABLE = "service_name_task_mappings"
PRIMARY_KEY = "service_name_task_mappings_pkey"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column(
            "key_kind",
            sa.String(),
            nullable=False,
            server_default="service_name",
        ),
    )
    op.drop_constraint(PRIMARY_KEY, TABLE, type_="primary")
    op.create_primary_key(PRIMARY_KEY, TABLE, ["service_name", "key_kind"])


def downgrade() -> None:
    op.execute(sa.text(f"DELETE FROM {TABLE} WHERE key_kind != 'service_name'"))
    op.drop_constraint(PRIMARY_KEY, TABLE, type_="primary")
    op.create_primary_key(PRIMARY_KEY, TABLE, ["service_name"])
    op.drop_column(TABLE, "key_kind")
