from uuid import UUID

from common_client.arthur_common_generated.models import DatasetSchema


def convert_column_id_to_name(
    column_ids: list[str],
    dataset_schema: DatasetSchema,
) -> dict[str, str]:
    return {
        column_id: dataset_schema.column_names[UUID(column_id)]
        for column_id in column_ids
    }
