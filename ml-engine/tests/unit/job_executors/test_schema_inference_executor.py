import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from uuid import uuid4

import pandas as pd
import pytest
from arthur_client.api_bindings import (
    AvailableDataset,
    DatasetLocator,
    DatasetLocatorField,
    DatasetSchema,
    SchemaInspectionJobSpec,
)
from arthur_common.models.connectors import (
    ConnectorPaginationOptions,
)  # TODO: replace when property method fixed in openapi
from job_executors.schema_inference_executor import (
    INFER_SCHEMA_DATA_LIMIT,
    INFER_SCHEMA_DATE_RANGE_DAYS,
    SchemaInferenceExecutor,
)


@pytest.fixture
def mock_datasets_client():
    return Mock()


@pytest.fixture
def mock_connector_constructor():
    return Mock()


@pytest.fixture
def mock_connector():
    connector = Mock()
    # Mock the read method to return empty data
    connector.read.return_value = pd.DataFrame()
    return connector


@pytest.fixture
def test_schema_inspection_job_spec():
    return SchemaInspectionJobSpec(
        connector_id=str(uuid4()),
        available_dataset_id=str(uuid4()),
    )


@pytest.fixture
def test_schema_inspection_dataset(test_schema_inspection_job_spec):
    return AvailableDataset(
        id=test_schema_inspection_job_spec.available_dataset_id,
        name="test-avail-dataset",
        dataset_locator=DatasetLocator(
            fields=[
                DatasetLocatorField(key="dataset_id", value="test_dataset"),
                DatasetLocatorField(key="table_name", value="test_table"),
            ],
        ),
        connector_id=test_schema_inspection_job_spec.connector_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        project_id=str(uuid4()),
        data_plane_id=str(uuid4()),
    )


def test_schema_inference_no_data(
    mock_datasets_client,
    mock_connector_constructor,
    mock_connector,
    test_schema_inspection_job_spec,
    test_schema_inspection_dataset,
):
    # set up mocks for test case where there is no data in the dataset to be used for the schema inference job in the
    # last 90 days
    logger = logging.getLogger("test_logger")
    executor = SchemaInferenceExecutor(
        mock_datasets_client,
        mock_connector_constructor,
        logger,
    )

    # mock the connector construction
    mock_connector_constructor.get_connector_from_spec.return_value = mock_connector

    # mock the get_available_dataset call
    mock_datasets_client.get_available_dataset.return_value = (
        test_schema_inspection_dataset
    )

    # Execute schema inspection job
    with pytest.raises(ValueError) as exc_info:
        executor.execute(test_schema_inspection_job_spec)

    # validate error message
    expected_error = f"No data found in the last {INFER_SCHEMA_DATE_RANGE_DAYS} days in dataset. Schema could not be inferred."
    assert str(exc_info.value) == expected_error

    # validate the connector's read method was called the expected number of times
    mock_connector.read.assert_called_once()

    # validate the pagination options were correct in all calls
    call = mock_connector.read.call_args_list[0]
    _, kwargs = call
    assert kwargs["pagination_options"] == ConnectorPaginationOptions(
        page_size=INFER_SCHEMA_DATA_LIMIT,
    )
    # check time parameters were as expected
    assert (
        datetime.now(timezone.utc) - kwargs["start_time"]
    ).days == INFER_SCHEMA_DATE_RANGE_DAYS
    assert datetime.now(timezone.utc) - kwargs["end_time"] < timedelta(seconds=1)


@pytest.fixture
def mock_connector_with_data():
    connector = Mock()
    # Mock the read method to return some data
    connector.read.return_value = pd.DataFrame(
        {"id": [1, 2, 3], "name": ["test1", "test2", "test3"]},
    )
    return connector


def test_schema_inference_with_data(
    mock_datasets_client,
    mock_connector_constructor,
    mock_connector_with_data,
    test_schema_inspection_job_spec,
    test_schema_inspection_dataset,
):
    # tests case where there's no data found in the last month but there is data the month before
    # set up mocks
    logger = logging.getLogger("test_logger")
    executor = SchemaInferenceExecutor(
        mock_datasets_client,
        mock_connector_constructor,
        logger,
    )

    # mock the connector construction
    mock_connector_constructor.get_connector_from_spec.return_value = (
        mock_connector_with_data
    )

    # mock the get_available_dataset call
    mock_datasets_client.get_available_dataset.return_value = (
        test_schema_inspection_dataset
    )

    # mock the schema inferer
    mock_schema = DatasetSchema(columns=[], column_names={}, alias_mask={})
    with patch("arthur_common.tools.schema_inferer.SchemaInferer") as mock_inferer:
        mock_inferer.return_value.infer_schema.return_value = mock_schema

        # run schema inspection job
        executor.execute(test_schema_inspection_job_spec)

        # validate schema was inferred and saved
        mock_datasets_client.put_available_dataset_schema.assert_called_once()

        # validate one call is made to read function of connector
        mock_connector_with_data.read.assert_called_once()

        # validate the pagination options were correct in all calls
        call = mock_connector_with_data.read.call_args_list[0]
        _, kwargs = call
        assert kwargs["pagination_options"] == ConnectorPaginationOptions(
            page_size=INFER_SCHEMA_DATA_LIMIT,
        )
        # check time parameters were as expected
        assert (
            datetime.now(timezone.utc) - kwargs["start_time"]
        ).days == INFER_SCHEMA_DATE_RANGE_DAYS
        assert datetime.now(timezone.utc) - kwargs["end_time"] < timedelta(seconds=1)
