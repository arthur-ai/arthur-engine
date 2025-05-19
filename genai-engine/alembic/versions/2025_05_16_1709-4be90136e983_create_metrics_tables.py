"""create_metrics_tables

Revision ID: 4be90136e983
Revises: 7747edf460b3
Create Date: 2025-05-16 17:09:02.310159

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4be90136e983'
down_revision = '7747edf460b3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create metrics table
    op.create_table(
        'metrics',
        sa.Column('id', sa.String(), primary_key=True, index=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('metric_type', sa.String(), nullable=False),
        sa.Column('metric_name', sa.String(), nullable=False),
        sa.Column('metric_metadata', sa.String(), nullable=False),
        sa.Column('metric_config', sa.String(), nullable=True),
        sa.Column('archived', sa.Boolean(), nullable=False, server_default='false'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create tasks_to_metrics table
    op.create_table(
        'tasks_to_metrics',
        sa.Column('task_id', sa.String(), nullable=False),
        sa.Column('metric_id', sa.String(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
        sa.ForeignKeyConstraint(['metric_id'], ['metrics.id'], ),
        sa.PrimaryKeyConstraint('task_id', 'metric_id')
    )
    op.create_index(op.f('ix_tasks_to_metrics_task_id'), 'tasks_to_metrics', ['task_id'], unique=False)
    op.create_index(op.f('ix_tasks_to_metrics_metric_id'), 'tasks_to_metrics', ['metric_id'], unique=False)


def downgrade() -> None:
    # Drop tasks_to_metrics table first due to foreign key constraints
    op.drop_index(op.f('ix_tasks_to_metrics_metric_id'), table_name='tasks_to_metrics')
    op.drop_index(op.f('ix_tasks_to_metrics_task_id'), table_name='tasks_to_metrics')
    op.drop_table('tasks_to_metrics')
    
    # Drop metrics table
    op.drop_table('metrics')
