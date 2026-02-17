import logging
from datetime import datetime, timezone
from unittest.mock import Mock
from uuid import uuid4

import duckdb
import pytest
from arthur_client.api_bindings import (
    ConnectorType,
    DatasetColumn,
    DatasetConnector,
    DatasetLocator,
    DatasetScalarType,
    DatasetSchema,
    Dataset,
    Definition,
)
from arthur_common.models.schema_definitions import STATIC_DATASET_TIMESTAMP_COL
from arthur_common.tools.functions import uuid_to_base26

from dataset_loader import DatasetLoader

logger = logging.getLogger("test_dataset_loader")

# Fixed UUIDs so assertions are deterministic
_VALUE_COL_ID = "bb2c3d4e-5f60-7890-bcde-f01234567890"
_STATIC_TS_COL_ID = "aa1b2c3d-4e5f-6789-abcd-ef0123456789"


def _make_static_dataset_dict() -> dict:
    """Return a Dataset-compatible dict with is_static=True and a schema that includes
    the synthetic __arthur_calculated_at column."""
    return {
        "id": str(uuid4()),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "project_id": str(uuid4()),
        "connector": DatasetConnector(
            id=str(uuid4()),
            connector_type=ConnectorType.S3,
        ),
        "data_plane_id": str(uuid4()),
        "dataset_locator": DatasetLocator(fields=[]),
        "is_static": True,
        "dataset_schema": DatasetSchema(
            alias_mask={},
            columns=[
                DatasetColumn(
                    id=_VALUE_COL_ID,
                    source_name="value",
                    definition=Definition(
                        DatasetScalarType(
                            tag_hints=[],
                            nullable=False,
                            id=str(uuid4()),
                            dtype="float",
                        ),
                    ),
                ),
                DatasetColumn(
                    id=_STATIC_TS_COL_ID,
                    source_name=STATIC_DATASET_TIMESTAMP_COL,
                    definition=Definition(
                        DatasetScalarType(
                            tag_hints=[],
                            nullable=False,
                            id=str(uuid4()),
                            dtype="timestamp",
                        ),
                    ),
                ),
            ],
            column_names={
                "value": _VALUE_COL_ID,
                STATIC_DATASET_TIMESTAMP_COL: _STATIC_TS_COL_ID,
            },
        ),
    }


def _make_loader_with_mock_connector(data: list[dict]) -> tuple[DatasetLoader, duckdb.DuckDBPyConnection]:
    mock_connector = Mock()
    mock_connector.read.return_value = data
    mock_connector_constructor = Mock()
    mock_connector_constructor.get_connector_from_spec.return_value = mock_connector
    conn = duckdb.connect()
    loader = DatasetLoader(mock_connector_constructor, Mock(), logger)
    return loader, conn


def test_static_dataset_synthetic_column_added_with_uuid_name():
    """The __arthur_calculated_at column must be added to DuckDB under its schema UUID,
    not its source name, so that apply_alias_mask can locate it later."""
    loader, conn = _make_loader_with_mock_connector([{"value": 1.0}, {"value": 2.0}])
    dataset = Dataset.model_validate(_make_static_dataset_dict())
    table_name = uuid_to_base26(dataset.id)

    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 1, 2, tzinfo=timezone.utc)
    loader.load_physical_dataset(conn, dataset, start, end)

    column_names = [col[0] for col in conn.execute(f'DESCRIBE "{table_name}"').fetchall()]

    # Column must exist under its UUID, not under the source name
    assert _STATIC_TS_COL_ID in column_names
    assert STATIC_DATASET_TIMESTAMP_COL not in column_names


def test_static_dataset_synthetic_column_populated():
    """Every row in a static dataset must have a non-null value for the synthetic timestamp column."""
    loader, conn = _make_loader_with_mock_connector(
        [{"value": 1.0}, {"value": 2.0}, {"value": 3.0}]
    )
    dataset = Dataset.model_validate(_make_static_dataset_dict())
    table_name = uuid_to_base26(dataset.id)

    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 1, 2, tzinfo=timezone.utc)
    loader.load_physical_dataset(conn, dataset, start, end)

    rows = conn.execute(f'SELECT "{_STATIC_TS_COL_ID}" FROM "{table_name}"').fetchall()
    assert len(rows) == 3
    assert all(row[0] is not None for row in rows)


def test_static_dataset_does_not_fail_on_missing_source_column():
    """DuckDB must not fail with a column count mismatch when the source data doesn't contain
    __arthur_calculated_at — the column is stripped from the schema before loading and added after."""
    # Connector returns data without __arthur_calculated_at (realistic case)
    loader, conn = _make_loader_with_mock_connector([{"value": 42.0}])
    dataset = Dataset.model_validate(_make_static_dataset_dict())
    table_name = uuid_to_base26(dataset.id)

    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 1, 2, tzinfo=timezone.utc)

    # Would raise "table has N columns but M values were supplied" without the fix
    loader.load_physical_dataset(conn, dataset, start, end)

    count = conn.execute(f'SELECT count(*) FROM "{table_name}"').fetchone()[0]
    assert count == 1
