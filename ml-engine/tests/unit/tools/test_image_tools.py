from uuid import uuid4

from arthur_client.api_bindings import ConnectorType
from arthur_common.models.schema_definitions import (
    DatasetColumn,
    DatasetScalarType,
    DatasetSchema,
    DType,
)

from tools.image_tools import (
    get_bucket_from_uri,
    get_connector_type_for_image_uri,
    get_image_columns,
    is_supported_image_uri,
)


def test_is_supported_image_uri() -> None:
    assert is_supported_image_uri("gs://bucket/path/image.png")
    assert not is_supported_image_uri("unsupported_uri://bucket/path/image.png")
    assert not is_supported_image_uri("data:image/png;base64,abc")
    assert not is_supported_image_uri("just a string")


def test_get_connector_type_for_image_uri() -> None:
    assert get_connector_type_for_image_uri("gs://b/i.png") == ConnectorType.GCS
    assert get_connector_type_for_image_uri("unsupported_uri://b/i.png") is None
    assert get_connector_type_for_image_uri("not a uri") is None


def test_get_bucket_from_uri() -> None:
    assert get_bucket_from_uri("gs://my-bucket/path/image.png") == "my-bucket"
    assert get_bucket_from_uri("gs://my-bucket") == "my-bucket"
    assert get_bucket_from_uri("no-scheme") is None
    assert get_bucket_from_uri("gs://") is None


def test_get_image_columns() -> None:
    image_col_id = uuid4()
    string_col_id = uuid4()
    schema = DatasetSchema(
        alias_mask={},
        columns=[
            DatasetColumn(
                id=image_col_id,
                source_name="image_col",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.IMAGE),
            ),
            DatasetColumn(
                id=string_col_id,
                source_name="text_col",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.STRING),
            ),
        ],
    )

    assert get_image_columns(schema) == ["image_col"]


def test_get_image_columns_uses_alias_mask() -> None:
    image_col_id = uuid4()
    schema = DatasetSchema(
        alias_mask={image_col_id: "aliased_image"},
        columns=[
            DatasetColumn(
                id=image_col_id,
                source_name="image_col",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.IMAGE),
            ),
        ],
    )

    assert get_image_columns(schema) == ["aliased_image"]


def test_get_image_columns_empty() -> None:
    schema = DatasetSchema(alias_mask={}, columns=[])
    assert get_image_columns(schema) == []
