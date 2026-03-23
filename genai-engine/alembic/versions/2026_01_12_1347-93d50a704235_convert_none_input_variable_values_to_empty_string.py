"""convert none input variable values to empty string

Revision ID: 93d50a704235
Revises: a1b2c3d4e5f6
Create Date: 2026-01-12 13:47:00.000000

"""

import json

from psycopg2.extras import Json
from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision = "93d50a704235"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Convert None values in InputVariable.value fields to empty strings.
    These were previously failing to deserialize from the DB. The creation logic has since been updated so that
    this will happen automatically for new requests, but we want to be able to deserialize old experiments.

    This migration updates:
    1. prompt_input_variables in prompt_experiment_test_cases
    2. eval_input_variables in prompt_experiment_test_case_prompt_result_eval_scores
    """
    connection = op.get_bind()

    # Update prompt_input_variables in test cases
    print("Migrating prompt_input_variables in test cases...")
    test_cases = connection.execute(
        text(
            """
            SELECT id, prompt_input_variables
            FROM prompt_experiment_test_cases
        """,
        ),
    ).fetchall()

    updated_test_cases = 0
    for test_case_id, input_variables in test_cases:
        if input_variables is None:
            continue

        # Parse JSON if it's a string, otherwise use directly
        if isinstance(input_variables, str):
            variables_list = json.loads(input_variables)
        else:
            variables_list = input_variables

        # Check if any value is None and convert to empty string
        updated = False
        for var in variables_list:
            if isinstance(var, dict) and var.get("value") is None:
                var["value"] = ""
                updated = True

        if updated:
            connection.execute(
                text(
                    """
                    UPDATE prompt_experiment_test_cases
                    SET prompt_input_variables = :variables
                    WHERE id = :id
                """,
                ),
                {
                    "id": test_case_id,
                    "variables": Json(variables_list),
                },
            )
            updated_test_cases += 1

    print(
        f"Updated {updated_test_cases} test cases with None values in prompt_input_variables",
    )

    # Update eval_input_variables in eval scores
    print("Migrating eval_input_variables in eval scores...")
    eval_scores = connection.execute(
        text(
            """
            SELECT id, eval_input_variables
            FROM prompt_experiment_test_case_prompt_result_eval_scores
        """,
        ),
    ).fetchall()

    updated_eval_scores = 0
    for eval_score_id, input_variables in eval_scores:
        if input_variables is None:
            continue

        # Parse JSON if it's a string, otherwise use directly
        if isinstance(input_variables, str):
            variables_list = json.loads(input_variables)
        else:
            variables_list = input_variables

        # Check if any value is None and convert to empty string
        updated = False
        for var in variables_list:
            if isinstance(var, dict) and var.get("value") is None:
                var["value"] = ""
                updated = True

        if updated:
            connection.execute(
                text(
                    """
                    UPDATE prompt_experiment_test_case_prompt_result_eval_scores
                    SET eval_input_variables = :variables
                    WHERE id = :id
                """,
                ),
                {
                    "id": eval_score_id,
                    "variables": Json(variables_list),
                },
            )
            updated_eval_scores += 1

    print(
        f"Updated {updated_eval_scores} eval scores with None values in eval_input_variables",
    )


def downgrade() -> None:
    """
    Downgrade is not supported for this migration.

    This is a data migration that converts None to empty strings.
    Reverting would require knowing which empty strings were originally None,
    which is not possible to determine.
    """
    raise RuntimeError(
        "Downgrade is not supported for migration 93d50a704235. "
        "This is a data migration that converts None values to empty strings. "
        "To revert, restore from a backup taken before this migration.",
    )
