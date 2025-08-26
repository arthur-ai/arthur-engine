import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from uuid import uuid4

import pytest
import pytz
from arthur_client.api_bindings import (
    ConnectorSpec,
    Dataset,
    DatasetColumn,
    DatasetLocator,
    DatasetLocatorField,
    DatasetScalarType,
    DatasetSchema,
    Definition,
)
from arthur_common.models.connectors import (
    BIG_QUERY_DATASET_DATASET_ID_FIELD,
    BIG_QUERY_DATASET_TABLE_NAME_FIELD,
    ConnectorPaginationOptions,
)
from arthur_common.models import ModelProblemType
from connectors.big_query_connector import BigQueryConnector
from mock_data.connector_helpers import *

logger = logging.getLogger("job_logger")


MOCK_BQ_DATASET_NO_TIMESTAMP_TAG = {
    "id": str(uuid4()),
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
    "project_id": str(uuid4()),
    "connector_id": str(uuid4()),
    "data_plane_id": str(uuid4()),
    "dataset_locator": DatasetLocator(
        fields=[
            DatasetLocatorField(
                key=BIG_QUERY_DATASET_TABLE_NAME_FIELD,
                value="test_table",
            ),
            DatasetLocatorField(
                key=BIG_QUERY_DATASET_DATASET_ID_FIELD,
                value="test_dataset",
            ),
        ],
    ),
    "model_problem_type": ModelProblemType.BINARY_CLASSIFICATION.value,
    "dataset_schema": DatasetSchema(
        alias_mask={},
        columns=[
            DatasetColumn(
                id="6715c83c-7653-4fbd-9bd7-3d1ebc60049b",
                source_name="id",
                definition=Definition(
                    DatasetScalarType(
                        tag_hints=[],
                        nullable=False,
                        id="bccf8f64-8910-4786-8c41-a266fe42c349",
                        dtype="uuid",
                    ),
                ),
            ),
            DatasetColumn(
                id="981a56d2-921e-4d64-9ead-b22b6923a69b",
                source_name="name",
                definition=Definition(
                    DatasetScalarType(
                        tag_hints=[],
                        nullable=False,
                        id="dbb003d7-8980-4a62-92d5-49835cd4d942",
                        dtype="str",
                    ),
                ),
            ),
            DatasetColumn(
                id="782fd973-efef-43cb-a3da-f864d9142ea4",
                source_name="timestamp",
                definition=Definition(
                    DatasetScalarType(
                        tag_hints=[],
                        nullable=False,
                        id="c51e8d04-eaa7-460c-9c39-6eed75d16401",
                        dtype="timestamp",
                    ),
                ),
            ),
        ],
        column_names={
            "id": "6715c83c-7653-4fbd-9bd7-3d1ebc60049b",
            "name": "981a56d2-921e-4d64-9ead-b22b6923a69b",
            "timestamp": "782fd973-efef-43cb-a3da-f864d9142ea4",
        },
    ),
}


start_timestamp = datetime(2024, 1, 1).astimezone(pytz.timezone("UTC"))
end_timestamp = start_timestamp + timedelta(days=1)


@pytest.mark.parametrize(
    "mock_dataset,pagination_options,expected_query,should_err",
    [
        (
            MOCK_BQ_DATASET,
            None,
            f"SELECT * FROM `my_project_id.test_dataset.test_table` WHERE `timestamp` >= '{start_timestamp}' AND `timestamp` < '{end_timestamp}' ORDER BY `timestamp` DESC",
            False,
        ),
        (
            MOCK_BQ_DATASET,
            ConnectorPaginationOptions(page_size=10),
            f"SELECT * FROM `my_project_id.test_dataset.test_table` WHERE `timestamp` >= '{start_timestamp}' AND `timestamp` < '{end_timestamp}' ORDER BY `timestamp` DESC LIMIT 10 OFFSET 0",
            False,
        ),
        (
            MOCK_BQ_DATASET,
            ConnectorPaginationOptions(page_size=10, page=3),
            f"SELECT * FROM `my_project_id.test_dataset.test_table` WHERE `timestamp` >= '{start_timestamp}' AND `timestamp` < '{end_timestamp}' ORDER BY `timestamp` DESC LIMIT 10 OFFSET 20",
            False,
        ),
        (MOCK_BQ_DATASET_NO_TIMESTAMP_TAG, None, "", True),
        (
            MOCK_BQ_DATASET_NO_TIMESTAMP_TAG,
            ConnectorPaginationOptions(page_size=10, page=3),
            f"SELECT * FROM `my_project_id.test_dataset.test_table` LIMIT 10 OFFSET 20",
            False,
        ),
    ],
)
def test_bigquery_basic_read(
    mock_bigquery_client,
    mock_dataset,
    pagination_options,
    expected_query,
    should_err,
):
    # mock data
    expected_data = [
        {
            "id": str(uuid4()),
            "name": "Test1",
            "timestamp": datetime(2024, 1, 1).astimezone(pytz.timezone("UTC")),
        },
        {
            "id": str(uuid4()),
            "name": "Test2",
            "timestamp": datetime(2024, 1, 1, hour=2).astimezone(pytz.timezone("UTC")),
        },
    ]
    mock_query_job = Mock()
    mock_query_job.result.return_value = expected_data
    mock_bigquery_client.query.return_value = mock_query_job

    # fetch data
    dataset = Dataset.model_validate(mock_dataset)
    spec = ConnectorSpec.model_validate(MOCK_BQ_CONNECTOR_SPEC)
    conn = BigQueryConnector(spec, logger)

    if not should_err:
        conn.read(dataset, start_timestamp, end_timestamp, None, pagination_options)
        mock_bigquery_client.query_and_wait.assert_called_once_with(
            expected_query.format(
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
            ),
        )
    else:
        with pytest.raises(ValueError):
            conn.read(dataset, start_timestamp, end_timestamp, None, pagination_options)


def test_pagination_options() -> None:
    with pytest.raises(ValueError):
        ConnectorPaginationOptions(page=0, page_size=10)


def test_escape_identifier() -> None:
    assert (
        BigQueryConnector._escape_identifier("some table ` name")
        == "`some table \\` name`"
    )
