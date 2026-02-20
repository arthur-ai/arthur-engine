"""create task_polling_state and migrate from agent_polling_data

Revision ID: 53f5544bc0b8
Revises: 843e2d3f46d5
Create Date: 2026-02-18 17:22:10.509721

"""
import json

from alembic import op
import sqlalchemy as sa

from services.agent_discovery_service import parse_gcp_resource_path


# revision identifiers, used by Alembic.
revision = '53f5544bc0b8'
down_revision = '843e2d3f46d5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Create the new task_polling_state table
    op.create_table('task_polling_state',
    sa.Column('task_id', sa.String(), nullable=False),
    sa.Column('last_fetched', sa.TIMESTAMP(), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
    sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
    sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('task_id')
    )

    # Step 2: Migrate last_fetched data from agent_polling_data -> task_polling_state
    connection = op.get_bind()
    connection.execute(
        sa.text("""
            INSERT INTO task_polling_state (task_id, last_fetched, created_at, updated_at)
            SELECT task_id, last_fetched, created_at, updated_at
            FROM agent_polling_data
        """)
    )

    # Step 3: Transform task_metadata from old format to new creation_source format.
    # Uses parse_gcp_resource_path() to extract engine ID from the full resource path.
    gcp_rows = connection.execute(
        sa.text("""
            SELECT id, task_metadata
            FROM tasks
            WHERE task_metadata IS NOT NULL
              AND task_metadata->>'provider' = 'GCP'
        """)
    ).fetchall()

    for row in gcp_rows:
        task_id = row[0]
        metadata = row[1] if isinstance(row[1], dict) else json.loads(row[1])
        gcp_metadata = metadata.get("gcp_metadata", {})
        resource_id = gcp_metadata.get("resource_id", "")

        parsed_project, parsed_region, parsed_engine_id = parse_gcp_resource_path(
            resource_id
        )

        new_metadata = {
            "creation_source": {
                "type": "GCP",
                "gcp_project_id": parsed_project or gcp_metadata.get("project_id", ""),
                "gcp_region": parsed_region or gcp_metadata.get("region", ""),
                "gcp_reasoning_engine_id": parsed_engine_id or "",
            }
        }

        connection.execute(
            sa.text("UPDATE tasks SET task_metadata = :metadata WHERE id = :id"),
            {"metadata": json.dumps(new_metadata), "id": task_id},
        )

    # Non-GCP registered agent tasks → MANUAL
    connection.execute(
        sa.text("""
            UPDATE tasks
            SET task_metadata = '{"creation_source": {"type": "MANUAL"}}'::jsonb
            WHERE task_metadata IS NOT NULL
              AND task_metadata->>'provider' IS NOT NULL
              AND task_metadata->>'provider' != 'GCP'
        """)
    )

    # Auto-created tasks (from trace ingestion) → OTEL
    connection.execute(
        sa.text("""
            UPDATE tasks
            SET task_metadata = '{"creation_source": {"type": "OTEL"}}'::jsonb
            WHERE task_metadata IS NULL
              AND is_autocreated = TRUE
        """)
    )

    # Manually created agentic tasks with no metadata → MANUAL
    connection.execute(
        sa.text("""
            UPDATE tasks
            SET task_metadata = '{"creation_source": {"type": "MANUAL"}}'::jsonb
            WHERE task_metadata IS NULL
              AND is_agentic = TRUE
              AND is_autocreated = FALSE
        """)
    )

    # Step 4: Drop old agent_polling_data table
    op.drop_index(op.f("ix_agent_polling_data_updated_at"), table_name="agent_polling_data")
    op.drop_index(op.f("ix_agent_polling_data_task_id"), table_name="agent_polling_data")
    op.drop_index(op.f("ix_agent_polling_data_created_at"), table_name="agent_polling_data")
    op.drop_table("agent_polling_data")


def downgrade() -> None:
    # Step 1: Recreate agent_polling_data table
    op.create_table(
        "agent_polling_data",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("failed_runs", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("last_fetched", sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_polling_data_created_at"), "agent_polling_data", ["created_at"], unique=False)
    op.create_index(op.f("ix_agent_polling_data_task_id"), "agent_polling_data", ["task_id"], unique=False)
    op.create_index(op.f("ix_agent_polling_data_updated_at"), "agent_polling_data", ["updated_at"], unique=False)

    # Step 2: Migrate data back from task_polling_state -> agent_polling_data
    connection = op.get_bind()
    connection.execute(
        sa.text("""
            INSERT INTO agent_polling_data (id, task_id, status, failed_runs, error_message, created_at, updated_at, last_fetched)
            SELECT gen_random_uuid(), task_id, 'IDLE', 0, NULL, created_at, updated_at, last_fetched
            FROM task_polling_state
        """)
    )

    # Step 3: Revert task_metadata JSON back to old format for GCP tasks
    connection.execute(
        sa.text("""
            UPDATE tasks
            SET task_metadata = jsonb_build_object(
                'provider', 'GCP',
                'gcp_metadata', jsonb_build_object(
                    'project_id', COALESCE(task_metadata->'creation_source'->>'gcp_project_id', ''),
                    'region', COALESCE(task_metadata->'creation_source'->>'gcp_region', ''),
                    'resource_id', COALESCE(task_metadata->'creation_source'->>'gcp_reasoning_engine_id', '')
                )
            )
            WHERE task_metadata IS NOT NULL
              AND task_metadata->'creation_source'->>'type' = 'GCP'
        """)
    )

    # Revert non-GCP registered agent tasks
    connection.execute(
        sa.text("""
            UPDATE tasks
            SET task_metadata = '{"provider": "external"}'::jsonb
            WHERE task_metadata IS NOT NULL
              AND task_metadata->'creation_source'->>'type' = 'MANUAL'
              AND is_autocreated = FALSE
              AND is_agentic = FALSE
        """)
    )

    # Revert OTEL and MANUAL tasks that originally had no metadata
    connection.execute(
        sa.text("""
            UPDATE tasks
            SET task_metadata = NULL
            WHERE task_metadata IS NOT NULL
              AND task_metadata->'creation_source'->>'type' IN ('OTEL', 'MANUAL')
              AND (is_autocreated = TRUE OR is_agentic = TRUE)
        """)
    )

    # Step 4: Drop task_polling_state table
    op.drop_table('task_polling_state')
