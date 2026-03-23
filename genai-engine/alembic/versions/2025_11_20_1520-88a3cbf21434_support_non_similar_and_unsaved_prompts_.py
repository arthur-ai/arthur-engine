"""support_non_similar_and_unsaved_prompts_in_experiments

Revision ID: 88a3cbf21434
Revises: 49afefacd064
Create Date: 2025-11-20 15:20:03.216077

"""

import json

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "88a3cbf21434"
down_revision = "49afefacd064"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Upgrade to multi-prompt support:
    1. Add new columns with nullable=True temporarily
    2. Migrate data from old format to new format
    3. Make new columns non-nullable
    4. Drop old columns
    """
    conn = op.get_bind()

    # Step 1: Add new columns to prompt_experiment_test_case_prompt_results (nullable initially)
    op.add_column(
        "prompt_experiment_test_case_prompt_results",
        sa.Column("prompt_key", sa.String(), nullable=True),
    )
    op.add_column(
        "prompt_experiment_test_case_prompt_results",
        sa.Column("prompt_type", sa.String(), nullable=True),
    )
    op.add_column(
        "prompt_experiment_test_case_prompt_results",
        sa.Column("unsaved_prompt_auto_name", sa.String(), nullable=True),
    )

    # Step 2: Add new column to prompt_experiments (nullable initially)
    op.add_column(
        "prompt_experiments",
        sa.Column(
            "prompt_configs",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    # Step 3: Migrate existing experiments data
    print("Migrating experiments to multi-prompt format...")

    # Get all existing experiments
    experiments = conn.execute(
        text(
            """
            SELECT id, task_id, prompt_name, prompt_versions
            FROM prompt_experiments
            WHERE prompt_name IS NOT NULL
        """,
        ),
    ).fetchall()

    print(f"Found {len(experiments)} experiments to migrate")

    for exp in experiments:
        exp_id, task_id, prompt_name, prompt_versions = exp

        # prompt_versions is already a list (parsed by SQLAlchemy from JSON column)
        # If it's a string, parse it; otherwise use it directly
        if isinstance(prompt_versions, str):
            versions_list = json.loads(prompt_versions)
        else:
            versions_list = prompt_versions

        # Build new prompt_configs from old format
        prompt_configs = [
            {"type": "saved", "name": prompt_name, "version": v} for v in versions_list
        ]

        print(
            f"  Migrating experiment {exp_id}: {prompt_name} with versions {versions_list}",
        )

        # Update experiment with new structure
        conn.execute(
            text(
                """
                UPDATE prompt_experiments
                SET prompt_configs = :configs
                WHERE id = :id
            """,
            ),
            {"configs": json.dumps(prompt_configs), "id": exp_id},
        )

        # Update all prompt results for this experiment
        results = conn.execute(
            text(
                """
                SELECT pr.id, pr.name, pr.version
                FROM prompt_experiment_test_case_prompt_results pr
                JOIN prompt_experiment_test_cases tc ON pr.test_case_id = tc.id
                WHERE tc.experiment_id = :exp_id
            """,
            ),
            {"exp_id": exp_id},
        ).fetchall()

        for result in results:
            result_id, name, version = result
            prompt_key = f"saved:{name}:{version}"

            conn.execute(
                text(
                    """
                    UPDATE prompt_experiment_test_case_prompt_results
                    SET prompt_key = :key, prompt_type = 'saved'
                    WHERE id = :id
                """,
                ),
                {"key": prompt_key, "id": result_id},
            )

        print(f"    Updated {len(results)} prompt results")

    print(f"Successfully migrated {len(experiments)} experiments")

    # Step 4: Make name and version nullable (they were NOT NULL before)
    op.alter_column(
        "prompt_experiment_test_case_prompt_results",
        "name",
        existing_type=sa.VARCHAR(),
        nullable=True,
    )
    op.alter_column(
        "prompt_experiment_test_case_prompt_results",
        "version",
        existing_type=sa.INTEGER(),
        nullable=True,
    )

    # Step 5: Make new columns NOT NULL now that data is migrated
    op.alter_column(
        "prompt_experiment_test_case_prompt_results",
        "prompt_key",
        existing_type=sa.VARCHAR(),
        nullable=False,
    )
    op.alter_column(
        "prompt_experiment_test_case_prompt_results",
        "prompt_type",
        existing_type=sa.VARCHAR(),
        nullable=False,
    )
    op.alter_column(
        "prompt_experiments",
        "prompt_configs",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        nullable=False,
    )

    # Step 6: Create index on prompt_key
    op.create_index(
        op.f("ix_prompt_experiment_test_case_prompt_results_prompt_key"),
        "prompt_experiment_test_case_prompt_results",
        ["prompt_key"],
        unique=False,
    )

    # Step 7: Drop old columns and index
    op.drop_index(
        op.f("ix_prompt_experiments_prompt_name"),
        table_name="prompt_experiments",
    )
    op.drop_column("prompt_experiments", "prompt_name")
    op.drop_column("prompt_experiments", "prompt_versions")

    print("Migration complete!")


def downgrade() -> None:
    """
    Downgrade from multi-prompt support:
    1. Add back old columns
    2. Migrate saved prompts back to old format
    3. Delete unsaved prompts (they cannot be represented in old format)
    4. Drop new columns
    """
    conn = op.get_bind()

    print("Downgrading from multi-prompt format...")

    # Step 1: Add back old columns (nullable initially)
    op.add_column(
        "prompt_experiments",
        sa.Column(
            "prompt_versions",
            postgresql.JSON(astext_type=sa.Text()),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "prompt_experiments",
        sa.Column("prompt_name", sa.VARCHAR(), autoincrement=False, nullable=True),
    )

    # Step 2: Migrate data back from new format to old format
    experiments = conn.execute(
        text(
            """
            SELECT id, prompt_configs
            FROM prompt_experiments
        """,
        ),
    ).fetchall()

    print(f"Found {len(experiments)} experiments to downgrade")

    for exp in experiments:
        exp_id, prompt_configs = exp

        # prompt_configs is already a list (parsed by SQLAlchemy from JSON column)
        # If it's a string, parse it; otherwise use it directly
        if isinstance(prompt_configs, str):
            configs = json.loads(prompt_configs)
        else:
            configs = prompt_configs

        # Filter to only saved prompts (unsaved prompts will be lost)
        saved_prompts = [c for c in configs if c.get("type") == "saved"]

        if not saved_prompts:
            print(
                f"  WARNING: Experiment {exp_id} has no saved prompts, will be deleted",
            )
            # Delete test cases and experiment
            conn.execute(
                text(
                    """
                    DELETE FROM prompt_experiments WHERE id = :exp_id
                """,
                ),
                {"exp_id": exp_id},
            )
            continue

        # Take the first saved prompt as the primary one
        first_prompt = saved_prompts[0]
        prompt_name = first_prompt["name"]

        # Collect all versions from saved prompts with same name
        versions = [c["version"] for c in saved_prompts if c["name"] == prompt_name]

        if len(saved_prompts) > len(versions):
            print(
                f"  WARNING: Experiment {exp_id} has multiple different saved prompts, "
                f"only keeping {prompt_name}",
            )

        print(
            f"  Downgrading experiment {exp_id}: {prompt_name} with versions {versions}",
        )

        # Update experiment with old structure
        conn.execute(
            text(
                """
                UPDATE prompt_experiments
                SET prompt_name = :name, prompt_versions = :versions
                WHERE id = :id
            """,
            ),
            {"name": prompt_name, "versions": json.dumps(versions), "id": exp_id},
        )

        # Delete prompt results that are unsaved (cannot be represented in old format)
        deleted_count = conn.execute(
            text(
                """
                DELETE FROM prompt_experiment_test_case_prompt_results pr
                USING prompt_experiment_test_cases tc
                WHERE pr.test_case_id = tc.id
                  AND tc.experiment_id = :exp_id
                  AND pr.prompt_type = 'unsaved'
            """,
            ),
            {"exp_id": exp_id},
        ).rowcount

        if deleted_count > 0:
            print(f"    Deleted {deleted_count} unsaved prompt results")

    print(f"Successfully downgraded {len(experiments)} experiments")

    # Step 3: Make old columns NOT NULL
    op.alter_column(
        "prompt_experiments",
        "prompt_name",
        existing_type=sa.VARCHAR(),
        nullable=False,
    )
    op.alter_column(
        "prompt_experiments",
        "prompt_versions",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        nullable=False,
    )

    # Step 4: Recreate index
    op.create_index(
        op.f("ix_prompt_experiments_prompt_name"),
        "prompt_experiments",
        ["prompt_name"],
        unique=False,
    )

    # Step 5: Drop new columns and index
    op.drop_column("prompt_experiments", "prompt_configs")
    op.drop_index(
        op.f("ix_prompt_experiment_test_case_prompt_results_prompt_key"),
        table_name="prompt_experiment_test_case_prompt_results",
    )

    # Step 6: Make name/version NOT NULL again
    op.alter_column(
        "prompt_experiment_test_case_prompt_results",
        "version",
        existing_type=sa.INTEGER(),
        nullable=False,
    )
    op.alter_column(
        "prompt_experiment_test_case_prompt_results",
        "name",
        existing_type=sa.VARCHAR(),
        nullable=False,
    )

    # Step 7: Drop multi-prompt columns
    op.drop_column(
        "prompt_experiment_test_case_prompt_results",
        "unsaved_prompt_auto_name",
    )
    op.drop_column("prompt_experiment_test_case_prompt_results", "prompt_type")
    op.drop_column("prompt_experiment_test_case_prompt_results", "prompt_key")

    print("Downgrade complete!")
