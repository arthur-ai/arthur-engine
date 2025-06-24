from uuid import UUID

from arthur_common.models.schema_definitions import DatasetSchema


def convert_column_id_to_name(
    column_ids: list[str],
    dataset_schema: DatasetSchema,
) -> dict[str, str]:
    return {
        column_id: dataset_schema.column_names[UUID(column_id)]
        for column_id in column_ids
    }
