"""rollback pii config

Revision ID: d2e6156f6c12
Revises: ac767af544d6
Create Date: 2024-03-15 12:45:20.203348

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "d2e6156f6c12"
down_revision = "ac767af544d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    op.execute("BEGIN")

    op.execute(
        """
        delete from pii_entities where
        rule_result_detail_id in (
            select distinct id from rule_result_details where prompt_rule_result_id in (
                select distinct id from prompt_rule_results where rule_id in (
                    select distinct rule_id from rule_data where data_type in ('pii_confidence_threshold', 'disabled_pii_entities', 'allow_list')
                )
            )
        )
    """,
    )

    op.execute(
        """
        delete from rule_result_details where
        prompt_rule_result_id in (
            select distinct id from prompt_rule_results where rule_id in (
                select distinct rule_id from rule_data where data_type in ('pii_confidence_threshold', 'disabled_pii_entities', 'allow_list')
            )
        )
    """,
    )

    op.execute(
        """
        delete from prompt_rule_results where
        rule_id in (
            select distinct rule_id from rule_data where data_type in ('pii_confidence_threshold', 'disabled_pii_entities', 'allow_list')
        )
    """,
    )

    op.execute(
        """
        delete from prompt_rule_results where
        rule_id in (
            select distinct rule_id from rule_data where data_type in ('pii_confidence_threshold', 'disabled_pii_entities', 'allow_list')
        )
    """,
    )

    op.execute(
        """
        delete from pii_entities where
        rule_result_detail_id in (
            select distinct id from rule_result_details where response_rule_result_id in (
                select distinct id from response_rule_results where rule_id in (
                    select distinct rule_id from rule_data where data_type in ('pii_confidence_threshold', 'disabled_pii_entities', 'allow_list')
                )
            )
        )
    """,
    )

    op.execute(
        """
        delete from rule_result_details where
        response_rule_result_id in (
            select distinct id from response_rule_results where rule_id in (
                select distinct rule_id from rule_data where data_type in ('pii_confidence_threshold', 'disabled_pii_entities', 'allow_list')
            )
        )
    """,
    )

    op.execute(
        """
        delete
        from response_rule_results where
        rule_id in (
            select distinct rule_id from rule_data where data_type in ('pii_confidence_threshold', 'disabled_pii_entities', 'allow_list')
        )
    """,
    )

    op.execute(
        """
        delete from tasks_to_rules where
        rule_id in (
            select
            distinct rule_id from rule_data where data_type in ('pii_confidence_threshold', 'disabled_pii_entities', 'allow_list')
        )
    """,
    )

    op.execute("ALTER TABLE rule_data DROP CONSTRAINT rule_data_rule_id_fkey;")

    op.execute(
        """
        delete from rules where
        id in (select distinct rule_id from rule_data where data_type in ('pii_confidence_threshold', 'disabled_pii_entities', 'allow_list'))
    """,
    )

    op.execute(
        """
        delete from rule_data where
        data_type in ('pii_confidence_threshold', 'disabled_pii_entities', 'allow_list')
    """,
    )

    op.execute(
        """
        ALTER TABLE rule_data ADD CONSTRAINT rule_data_rule_id_fkey FOREIGN KEY (rule_id) REFERENCES rules(id)
    """,
    )

    op.execute("COMMIT")
