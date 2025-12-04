"""add task id to datasets

Revision ID: 6273338ffe42
Revises: ee4b2e171875
Create Date: 2025-11-26 11:27:31.376285

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "6273338ffe42"
down_revision = "ee4b2e171875"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Add task_id column as nullable first
    op.add_column("datasets", sa.Column("task_id", sa.String(), nullable=True))

    # Step 2: Populate task_id for existing datasets
    # Try to get task_id from multiple sources in priority order:
    # 1. dataset_metadata JSON field (if it has a task_id key)
    # 2. notebooks that reference this dataset
    # 3. prompt_experiments that use this dataset
    # 4. Fallback to most recently created task
    op.execute(
        """
        UPDATE datasets d
        SET task_id = COALESCE(
            (
                -- First: Try to get task_id from dataset_metadata JSON field
                d.dataset_metadata->>'task_id'
            ),
            (
                -- Second: Try to get task_id from a notebook that references this dataset
                SELECT n.task_id
                FROM notebooks n
                WHERE n.dataset_id = d.id::text
                LIMIT 1
            ),
            (
                -- Third: Try to get task_id from a prompt_experiment that uses this dataset
                SELECT pe.task_id
                FROM prompt_experiments pe
                WHERE pe.dataset_id = d.id
                LIMIT 1
            ),
            (
                -- Fallback: use the most recently created task
                SELECT id
                FROM tasks
                ORDER BY created_at DESC
                LIMIT 1
            )
        )
        WHERE task_id IS NULL
    """,
    )

    # Step 3: Make the column non-nullable now that all rows have values
    op.alter_column("datasets", "task_id", nullable=False)

    # Step 4: Create index on task_id
    op.create_index(op.f("ix_datasets_task_id"), "datasets", ["task_id"], unique=False)

    # Step 5: Add foreign key constraint
    op.create_foreign_key(
        "fk_datasets_task_id",
        "datasets",
        "tasks",
        ["task_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # Drop in reverse order
    op.drop_constraint("fk_datasets_task_id", "datasets", type_="foreignkey")
    op.drop_index(op.f("ix_datasets_task_id"), table_name="datasets")
    op.drop_column("datasets", "task_id")
