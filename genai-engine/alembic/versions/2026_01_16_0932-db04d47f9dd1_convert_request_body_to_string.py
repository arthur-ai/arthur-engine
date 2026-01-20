"""convert request body to string

Revision ID: db04d47f9dd1
Revises: 93d50a704235
Create Date: 2026-01-16 09:32:00.000000

"""

import json

from psycopg2.extras import Json
from sqlalchemy import text

from alembic import op

# revision identifiers, used by Alembic.
revision = "db04d47f9dd1"
down_revision = "93d50a704235"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Convert request_body fields from JSON (dict) to string.

    This migration updates:
    1. request_body in agentic_experiment_test_case_agentic_results (JSON column -> Text column)
    2. request_body field within http_template JSON in agentic_experiments (dict -> JSON string)
    3. request_body field within http_template JSON in agentic_notebooks (dict -> JSON string)
    """
    connection = op.get_bind()

    # 1. Alter the column type from JSON to Text
    # PostgreSQL will automatically convert JSON to text (JSON string representation)
    op.execute(
        """
        ALTER TABLE agentic_experiment_test_case_agentic_results
        ALTER COLUMN request_body TYPE text USING request_body::text
    """,
    )

    # 2. Convert request_body field within http_template JSON in agentic_experiments
    experiments = connection.execute(
        text(
            """
            SELECT id, http_template
            FROM agentic_experiments
        """,
        ),
    ).fetchall()

    updated_experiments = 0
    for experiment_id, http_template in experiments:
        if http_template is None:
            continue

        # PostgreSQL JSONB columns are returned as Python dicts by SQLAlchemy
        # No need to parse - it's already a dict
        template_dict = http_template

        # Ensure request_body is always a string
        # Convert any non-string value (dict, list, None, etc.) to a JSON string
        needs_update = False
        if "request_body" in template_dict:
            request_body = template_dict["request_body"]
            if not isinstance(request_body, str):
                # Convert non-string values to JSON string
                if request_body is None:
                    template_dict["request_body"] = ""
                else:
                    # Convert dict, list, or any other type to JSON string
                    template_dict["request_body"] = json.dumps(request_body)
                needs_update = True
        else:
            # If request_body doesn't exist, set it to empty string
            template_dict["request_body"] = ""
            needs_update = True

        if needs_update:
            updated_experiments += 1
            connection.execute(
                text(
                    """
                    UPDATE agentic_experiments
                    SET http_template = :template
                    WHERE id = :id
                """,
                ),
                {
                    "id": experiment_id,
                    "template": Json(template_dict),
                },
            )

    # 3. Convert request_body field within http_template JSON in agentic_notebooks
    notebooks = connection.execute(
        text(
            """
            SELECT id, http_template
            FROM agentic_notebooks
            WHERE http_template IS NOT NULL
        """,
        ),
    ).fetchall()

    updated_notebooks = 0
    for notebook_id, http_template in notebooks:
        # PostgreSQL JSONB columns are returned as Python dicts by SQLAlchemy
        # No need to parse - it's already a dict
        template_dict = http_template

        # Ensure request_body is always a string
        # Convert any non-string value (dict, list, None, etc.) to a JSON string
        needs_update = False
        if "request_body" in template_dict:
            request_body = template_dict["request_body"]
            if not isinstance(request_body, str):
                # Convert non-string values to JSON string
                if request_body is None:
                    template_dict["request_body"] = ""
                else:
                    # Convert dict, list, or any other type to JSON string
                    template_dict["request_body"] = json.dumps(request_body)
                needs_update = True
        else:
            # If request_body doesn't exist, set it to empty string
            template_dict["request_body"] = ""
            needs_update = True

        if needs_update:
            updated_notebooks += 1
            connection.execute(
                text(
                    """
                    UPDATE agentic_notebooks
                    SET http_template = :template
                    WHERE id = :id
                """,
                ),
                {
                    "id": notebook_id,
                    "template": Json(template_dict),
                },
            )


def downgrade() -> None:
    """
    Convert request_body fields back from string to JSON (dict).

    This reverses:
    1. request_body in agentic_experiment_test_case_agentic_results (Text column -> JSON column)
    2. request_body field within http_template JSON in agentic_experiments (JSON string -> dict)
    3. request_body field within http_template JSON in agentic_notebooks (JSON string -> dict)
    """
    connection = op.get_bind()

    # 1. Convert request_body in agentic_experiment_test_case_agentic_results
    # First convert string data back to JSON objects before altering column type
    results = connection.execute(
        text(
            """
            SELECT id, request_body
            FROM agentic_experiment_test_case_agentic_results
        """,
        ),
    ).fetchall()

    updated_results = 0
    for result_id, request_body in results:
        if request_body is None:
            continue

        # Convert JSON string back to JSON object
        if isinstance(request_body, str):
            try:
                # Try to parse as JSON
                body_dict = json.loads(request_body)
            except json.JSONDecodeError:
                # If it's not valid JSON, wrap it in a dict
                body_dict = {"raw": request_body}
        else:
            # Already a dict/object
            body_dict = request_body

        # Update with JSON object (will be converted to jsonb when we alter column)
        connection.execute(
            text(
                """
                UPDATE agentic_experiment_test_case_agentic_results
                SET request_body = :body
                WHERE id = :id
            """,
            ),
            {
                "id": result_id,
                "body": json.dumps(body_dict),
            },
        )
        updated_results += 1

    # 2. Alter the column type from Text back to JSON
    op.execute(
        """
        ALTER TABLE agentic_experiment_test_case_agentic_results
        ALTER COLUMN request_body TYPE jsonb USING request_body::jsonb
    """,
    )

    # 3. Convert request_body field within http_template JSON in agentic_experiments
    experiments = connection.execute(
        text(
            """
            SELECT id, http_template
            FROM agentic_experiments
        """,
        ),
    ).fetchall()

    updated_experiments = 0
    for experiment_id, http_template in experiments:
        if http_template is None:
            continue

        # PostgreSQL JSONB columns are returned as Python dicts by SQLAlchemy
        # No need to parse - it's already a dict
        template_dict = http_template

        # Check if request_body exists and is a string, convert to dict
        if "request_body" in template_dict:
            request_body = template_dict["request_body"]
            if isinstance(request_body, str):
                try:
                    # Try to parse as JSON
                    template_dict["request_body"] = json.loads(request_body)
                    updated_experiments += 1

                    connection.execute(
                        text(
                            """
                            UPDATE agentic_experiments
                            SET http_template = :template
                            WHERE id = :id
                        """,
                        ),
                        {
                            "id": experiment_id,
                            "template": Json(template_dict),
                        },
                    )
                except json.JSONDecodeError:
                    # If it's not valid JSON, wrap it in a dict
                    template_dict["request_body"] = {"raw": request_body}
                    updated_experiments += 1

                    connection.execute(
                        text(
                            """
                            UPDATE agentic_experiments
                            SET http_template = :template
                            WHERE id = :id
                        """,
                        ),
                        {
                            "id": experiment_id,
                            "template": Json(template_dict),
                        },
                    )

    # 4. Convert request_body field within http_template JSON in agentic_notebooks
    notebooks = connection.execute(
        text(
            """
            SELECT id, http_template
            FROM agentic_notebooks
            WHERE http_template IS NOT NULL
        """,
        ),
    ).fetchall()

    updated_notebooks = 0
    for notebook_id, http_template in notebooks:
        # PostgreSQL JSONB columns are returned as Python dicts by SQLAlchemy
        # No need to parse - it's already a dict
        template_dict = http_template

        # Check if request_body exists and is a string, convert to dict
        if "request_body" in template_dict:
            request_body = template_dict["request_body"]
            if isinstance(request_body, str):
                try:
                    # Try to parse as JSON
                    template_dict["request_body"] = json.loads(request_body)
                    updated_notebooks += 1

                    connection.execute(
                        text(
                            """
                            UPDATE agentic_notebooks
                            SET http_template = :template
                            WHERE id = :id
                        """,
                        ),
                        {
                            "id": notebook_id,
                            "template": Json(template_dict),
                        },
                    )
                except json.JSONDecodeError:
                    # If it's not valid JSON, wrap it in a dict
                    template_dict["request_body"] = {"raw": request_body}
                    updated_notebooks += 1

                    connection.execute(
                        text(
                            """
                            UPDATE agentic_notebooks
                            SET http_template = :template
                            WHERE id = :id
                        """,
                        ),
                        {
                            "id": notebook_id,
                            "template": Json(template_dict),
                        },
                    )
