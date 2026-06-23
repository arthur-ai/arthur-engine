from arthur_client.api_bindings import ConnectorType
from arthur_common.models.schema_definitions import (
    DatasetScalarType,
    DatasetSchema,
    DType,
)

IMAGE_CONNECTOR_PREFIX_TO_TYPE = {
    "gs://": ConnectorType.GCS,
    "s3://": ConnectorType.S3,
}
IMAGE_CONNECTOR_PREFIX_TUPLE = tuple(IMAGE_CONNECTOR_PREFIX_TO_TYPE.keys())


def is_supported_image_uri(uri: str) -> bool:
    return uri.startswith(IMAGE_CONNECTOR_PREFIX_TUPLE)


def get_connector_type_for_image_uri(image_uri: str) -> ConnectorType | None:
    for key, val in IMAGE_CONNECTOR_PREFIX_TO_TYPE.items():
        if image_uri.startswith(key):
            return val

    return None


def get_bucket_from_uri(image_uri: str) -> str | None:
    _, _, rest = image_uri.partition("://")
    if not rest:
        return None

    bucket, _, _ = rest.partition("/")
    if not bucket:
        return None

    return bucket


def get_image_columns(schema: DatasetSchema) -> list[str]:
    image_columns = []
    for col in schema.columns:
        if (
            isinstance(col.definition, DatasetScalarType)
            and col.definition.dtype == DType.IMAGE
        ):
            image_columns.append(schema.column_names[col.id])

    return image_columns
