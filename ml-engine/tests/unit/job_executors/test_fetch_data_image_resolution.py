import logging
from unittest.mock import Mock
from uuid import uuid4

from arthur_common.models.schema_definitions import (
    DatasetColumn,
    DatasetScalarType,
    DatasetSchema,
    DType,
)

from job_executors.fetch_data_executor import FetchDataExecutor

LOGGER = logging.getLogger(__name__)


def make_executor() -> FetchDataExecutor:
    return FetchDataExecutor(
        models_client=Mock(),
        datasets_client=Mock(),
        data_retrieval_client=Mock(),
        connector_constructor=Mock(),
        logger=LOGGER,
    )


def make_schema_with_image_col(col_name: str) -> DatasetSchema:
    return DatasetSchema(
        alias_mask={},
        columns=[
            DatasetColumn(
                id=uuid4(),
                source_name=col_name,
                definition=DatasetScalarType(id=uuid4(), dtype=DType.IMAGE),
            ),
        ],
    )


def test_resolve_images_replaces_image_cells() -> None:
    executor = make_executor()
    schema = make_schema_with_image_col("image")
    rows = [
        {"image": "gs://bucket/a.png"},
        {"image": "gs://bucket/b.png"},
    ]

    resolver = Mock()
    resolver.resolve_image.side_effect = lambda uri: f"resolved:{uri}"

    executor._resolve_images(rows, schema, resolver)

    assert rows == [
        {"image": "resolved:gs://bucket/a.png"},
        {"image": "resolved:gs://bucket/b.png"},
    ]


def test_resolve_images_skips_non_image_uris() -> None:
    executor = make_executor()
    schema = make_schema_with_image_col("image")
    rows = [
        {"image": "data:image/png;base64,inline"},
        {"image": "test"},
        {"image": ""},
    ]

    resolver = Mock()

    executor._resolve_images(rows, schema, resolver)

    resolver.resolve_image.assert_not_called()
    assert rows == [
        {"image": "data:image/png;base64,inline"},
        {"image": "test"},
        {"image": ""},
    ]


def test_resolve_images_no_image_columns_noop() -> None:
    executor = make_executor()
    schema = DatasetSchema(
        alias_mask={},
        columns=[
            DatasetColumn(
                id=uuid4(),
                source_name="text",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.STRING),
            ),
        ],
    )
    rows = [{"text": "gs://bucket/a.png"}]

    resolver = Mock()
    executor._resolve_images(rows, schema, resolver)

    resolver.resolve_image.assert_not_called()
    assert rows == [{"text": "gs://bucket/a.png"}]
