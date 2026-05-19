"""backfill orphan inferences to the __unmapped__ task

Revision ID: d894934c8994
Revises: 5de5704b5892
Create Date: 2026-05-19 15:10:36.733558

Multi-tenancy step 4 of 5. `inferences.task_id` is the only nullable
task FK in the schema. The deprecated `/api/v2/validate_prompt` endpoint
persists inferences with task_id=NULL. Those rows would orphan their
descendants (inference_feedback, prompt/response_rule_results, and the
cascading rule-detail tables) and break the SET NOT NULL in step 5.

Fix: assign every task-less inference to the `__unmapped__` system task
(created in revision 843e2d3f46d5, id constants.UNMAPPED_TASK_ID). That
task already lives under the system org after step 2, so these rows
remain admin-visible and tenant-invisible — same semantics as before,
but now they have a real task_id and the join chain is intact.

Defense-in-depth: this revision also `INSERT ... ON CONFLICT DO NOTHING`
the __unmapped__ task in case the row was deleted between revisions
(843e2d3f46d5's downgrade DELETEs it). Without the preflight, the
backfill UPDATE would hit the inferences.task_id -> tasks.id FK and abort.

Downgrade reverts inferences that point at __unmapped__ back to NULL.
Safe because step 2 (843e2d3f46d5) only assigned UNMAPPED_TASK_ID to
spans/traces, never inferences — anything pointing at it after step 4
came from THIS migration.
"""

from alembic import op
from utils.constants import DEFAULT_SERVICE_NAME, UNMAPPED_TASK_ID

# revision identifiers, used by Alembic.
revision = "d894934c8994"
down_revision = "5de5704b5892"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Defense-in-depth: ensure the __unmapped__ task exists before we point
    # inferences at it. The row was created in 843e2d3f46d5 but that
    # migration's downgrade deletes it — so a downgrade-then-upgrade path
    # would otherwise hit the inferences.task_id FK.
    #
    # is_system_task=true buckets this task under the system org (the
    # backfill in revision 697657f9af66 routes system tasks there).
    op.execute(f"""
        INSERT INTO tasks (
            id, name, created_at, updated_at,
            archived, is_agentic, is_autocreated, is_system_task,
            org_id
        )
        VALUES (
            '{UNMAPPED_TASK_ID}', '{DEFAULT_SERVICE_NAME}',
            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
            false, false, false, true,
            (SELECT id FROM organizations WHERE name = 'system')
        )
        ON CONFLICT (id) DO NOTHING
        """)

    op.execute(f"""
        UPDATE inferences
           SET task_id = '{UNMAPPED_TASK_ID}'
         WHERE task_id IS NULL
        """)


def downgrade() -> None:
    op.execute(f"""
        UPDATE inferences
           SET task_id = NULL
         WHERE task_id = '{UNMAPPED_TASK_ID}'
        """)
