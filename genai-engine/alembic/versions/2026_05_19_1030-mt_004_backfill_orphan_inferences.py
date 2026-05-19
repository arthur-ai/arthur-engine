"""backfill orphan inferences to the __unmapped__ task

Revision ID: mt_orphan_inferences
Revises: mt_api_keys_org_id
Create Date: 2026-05-19 10:30:00

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

Downgrade reverts inferences that point at __unmapped__ back to NULL.
Safe because step 2 (843e2d3f46d5) only assigned UNMAPPED_TASK_ID to
spans/traces, never inferences — anything pointing at it after step 4
came from THIS migration.
"""

from alembic import op
from utils.constants import UNMAPPED_TASK_ID

# revision identifiers, used by Alembic.
revision = "mt_orphan_inferences"
down_revision = "mt_api_keys_org_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
