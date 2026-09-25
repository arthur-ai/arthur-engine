"""rename synthetic dataset system task to naming convention

Revision ID: c8d1e4f70a63
Revises: b3f2a91c4d17
Create Date: 2026-09-09 12:00:00.000000

Renames the synthetic data generation system task from the human-readable
"Synthetic Dataset Generation" to `__synthetic_dataset_generation__`, matching
the `__lower_snake_case__` convention already used by `__unmapped__` and
`__arthur_system_task__`.

The startup bootstrap only inserts the task row when it is absent, so changing
the constant alone renames nothing on an already-deployed engine — hence this
data migration. `tasks.name` carries no unique constraint or foreign key and
every code path reaches this task by ID, so the rename is inert.

Both the task ID and the names are hardcoded rather than imported from
`utils.constants` so this revision's meaning stays frozen even if the constant
changes again later. Safe to run on an engine where the row does not exist yet:
zero rows update, and the bootstrap then creates it with the new name.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "c8d1e4f70a63"
down_revision = "b3f2a91c4d17"
branch_labels = None
depends_on = None

SYNTHETIC_DATASET_TASK_ID = "00000000-da7a-0000-0000-000000000001"
OLD_TASK_NAME = "Synthetic Dataset Generation"
NEW_TASK_NAME = "__synthetic_dataset_generation__"


def upgrade() -> None:
    op.execute(
        sa.text("UPDATE tasks SET name = :new_name WHERE id = :task_id").bindparams(
            new_name=NEW_TASK_NAME,
            task_id=SYNTHETIC_DATASET_TASK_ID,
        ),
    )


def downgrade() -> None:
    op.execute(
        sa.text("UPDATE tasks SET name = :old_name WHERE id = :task_id").bindparams(
            old_name=OLD_TASK_NAME,
            task_id=SYNTHETIC_DATASET_TASK_ID,
        ),
    )
