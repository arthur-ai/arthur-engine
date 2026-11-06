"""copy default rules into task rules and archive them

Revision ID: b1194cd9c938
Revises: a7c4e2f9b851
Create Date: 2026-11-06 12:00:00.000000

Default rules (scope='default') were one shared rule row linked to every task
that existed when the rule was created, the system tasks included. The engine
no longer creates them or attaches them to new tasks, but the rows from before
are still linked and still run on those tasks.

Each task now owns its rules. For every live default rule linked to a user
task, this revision inserts a task-scoped copy (with its rule_data) and moves
the task's link onto the copy, so the link keeps its enabled flag and the task
keeps running the same check. A copy on an archived task is archived with it,
the way archive_task archives a task's own rules, and comes back when the task
is unarchived.

The links that remain are dropped: those on system tasks (nothing validates
against them) and those to default rules already archived (they no longer
ran). Every default rule is then archived. Rule results recorded before this
revision keep pointing at the archived originals.

Downgrade is a no-op: the copies are ordinary task rules to an older engine
too, and with the originals archived it finds no default rules to attach to
new tasks.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "b1194cd9c938"
down_revision = "a7c4e2f9b851"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TEMPORARY TABLE default_rule_copies AS
        SELECT l.task_id,
               l.rule_id AS default_rule_id,
               gen_random_uuid()::text AS task_rule_id,
               t.archived AS task_archived
          FROM tasks_to_rules l
          JOIN rules r ON r.id = l.rule_id
          JOIN tasks t ON t.id = l.task_id
         WHERE r.scope = 'default'
           AND r.archived = false
           AND t.is_system_task = false
        """)

    op.execute("""
        INSERT INTO rules (
            id, name, type, created_at, updated_at,
            prompt_enabled, response_enabled, scoring_method,
            scope, archived
        )
        SELECT c.task_rule_id, r.name, r.type, r.created_at, r.updated_at,
               r.prompt_enabled, r.response_enabled, r.scoring_method,
               'task', c.task_archived
          FROM default_rule_copies c
          JOIN rules r ON r.id = c.default_rule_id
        """)

    op.execute("""
        INSERT INTO rule_data (id, rule_id, data_type, data)
        SELECT gen_random_uuid()::text, c.task_rule_id, d.data_type, d.data
          FROM default_rule_copies c
          JOIN rule_data d ON d.rule_id = c.default_rule_id
        """)

    op.execute("""
        UPDATE tasks_to_rules l
           SET rule_id = c.task_rule_id
          FROM default_rule_copies c
         WHERE l.task_id = c.task_id
           AND l.rule_id = c.default_rule_id
        """)

    op.execute("""
        DELETE FROM tasks_to_rules
         WHERE rule_id IN (SELECT id FROM rules WHERE scope = 'default')
        """)

    op.execute("""
        UPDATE rules
           SET archived = true
         WHERE scope = 'default'
           AND archived = false
        """)

    op.execute("DROP TABLE default_rule_copies")


def downgrade() -> None:
    pass
