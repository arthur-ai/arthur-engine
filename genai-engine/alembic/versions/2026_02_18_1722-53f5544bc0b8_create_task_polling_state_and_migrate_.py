d"""create task_polling_state and migrate from agent_polling_data

Revision ID: 53f5544bc0b8
Revises: 843e2d3f46d5
Create Date: 2026-02-18 17:22:10.509721

"""
from alembic import op
import sqlalchemy as sa


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

    # Step 3: Transform task_metadata JSON for existing GCP tasks
    # Old format: {"provider": "GCP", "gcp_metadata": {"project_id": "...", "region": "...", "resource_id": "..."}, "service_names": [...]}
    # New format: {"creation_source": {"type": "GCP", "gcp_project_id": "...", "gcp_region": "...", "gcp_reasoning_engine_id": "..."}}
    # Note: service_names are NOT stored in task_metadata — they live in service_name_task_mappings table
    connection.execute(
        sa.text("""
            UPDATE tasks
            SET task_metadata = jsonb_build_object(
                'creation_source', jsonb_build_object(
                    'type', 'GCP',
                    'gcp_project_id', COALESCE(task_metadata->'gcp_metadata'->>'project_id', ''),
                    'gcp_region', COALESCE(task_metadata->'gcp_metadata'->>'region', ''),
                    'gcp_reasoning_engine_id', COALESCE(task_metadata->'gcp_metadata'->>'resource_id', '')
                )
            )
            WHERE task_metadata IS NOT NULL
              AND task_metadata->>'provider' = 'GCP'
        """)
    )

    # Transform non-GCP registered agent tasks (if any)
    connection.execute(
        sa.text("""
            UPDATE tasks
            SET task_metadata = jsonb_build_object(
                'creation_source', jsonb_build_object(
                    'type', 'MANUAL'
                )
            )
            WHERE task_metadata IS NOT NULL
              AND task_metadata->>'provider' IS NOT NULL
              AND task_metadata->>'provider' != 'GCP'
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

    # Revert non-GCP tasks
    connection.execute(
        sa.text("""
            UPDATE tasks
            SET task_metadata = jsonb_build_object(
                'provider', 'external'
            )
            WHERE task_metadata IS NOT NULL
              AND task_metadata->'creation_source'->>'type' = 'MANUAL'
        """)
    )

    # Step 4: Drop task_polling_state table
    op.drop_table('task_polling_state')
