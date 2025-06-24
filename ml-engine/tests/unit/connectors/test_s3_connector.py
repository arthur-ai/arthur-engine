import logging
import os
from unittest.mock import patch

import pytest
import pytz
from arthur_client.api_bindings import (
    AvailableDataset,
    ConnectorFieldDataType,
    ConnectorSpec,
    DataResultFilter,
    DataResultFilterOp,
    Dataset,
)
from arthur_common.models.connectors import (
    BUCKET_BASED_CONNECTOR_BUCKET_FIELD,
    S3_CONNECTOR_ENDPOINT_FIELD,
    ConnectorPaginationOptions,
)
from connectors.s3_connector import S3Connector
from helpers import *

logger = logging.getLogger("job_logger")


MOCK_S3_CONNECTOR_SPEC = mock_bucket_based_connector_spec(
    connector_type=ConnectorType.S3,
    fields=[
        {
            "key": S3_CONNECTOR_ENDPOINT_FIELD,
            "value": "http://some.onprem.s3.host",
            "is_sensitive": False,
            "d_type": ConnectorFieldDataType.STRING.value,
        },
        {
            "key": BUCKET_BASED_CONNECTOR_BUCKET_FIELD,
            "value": "./tests/unit/mock_data/expel_tabular_s3_bucket",
            "is_sensitive": False,
            "d_type": ConnectorFieldDataType.STRING.value,
        },
    ],
)


# mocks s3fs.ls and s3fs.open as local directory calls
@patch("s3fs.S3FileSystem.open", side_effect=open)
@patch("s3fs.S3FileSystem.walk", side_effect=os.walk)
@patch("s3fs.S3FileSystem.isfile", side_effect=os.path.isfile)
@pytest.mark.parametrize(
    "dataset_spec,end_timestamp,expected_rows,should_error,filters,pagination_options",
    [
        # UTC timezone, should read all 20 inferences in the time range
        (
            mock_expel_tabular_dataset(dataset_locator_happy_path),
            datetime(2024, 1, 4).astimezone(pytz.timezone("UTC")),
            20,
            False,
            {},
            None,
        ),
        # should read all 20 inferences. tests support for file prefix with leading and trailing slashes
        (
            mock_expel_tabular_dataset(dataset_locator_file_prefix_has_leading_slash),
            datetime(2024, 1, 4).astimezone(pytz.timezone("UTC")),
            20,
            False,
            {},
            None,
        ),
        # ET timezone, no inferences should fall in the time range - range if data is in UTC in test_data is
        # 1/1/24 to 1/2/24, if in ET then it's 1/1/24 at 4 AM to 1/2/24 AM once translated to UTC
        (
            mock_expel_tabular_dataset(dataset_locator_et_tz),
            datetime(2024, 1, 1, hour=3).astimezone(pytz.timezone("UTC")),
            0,
            False,
            {},
            None,
        ),
        # dataset without small enough time partition in file prefix
        (
            mock_expel_tabular_dataset(
                dataset_locator_file_prefix_without_small_enough_partition,
            ),
            datetime(2024, 1, 4).astimezone(pytz.timezone("UTC")),
            20,
            True,
            {},
            None,
        ),
        # limit filter
        (
            mock_expel_tabular_dataset(dataset_locator_happy_path),
            datetime(2024, 1, 4).astimezone(pytz.timezone("UTC")),
            8,
            False,
            {},
            ConnectorPaginationOptions(page_size=8),
        ),
        # limit filter exceeds total present inferences
        (
            mock_expel_tabular_dataset(dataset_locator_happy_path),
            datetime(2024, 1, 4).astimezone(pytz.timezone("UTC")),
            20,
            False,
            {},
            ConnectorPaginationOptions(page_size=25),
        ),
        # column value filter
        (
            mock_expel_tabular_dataset(dataset_locator_happy_path),
            datetime(2024, 1, 4).astimezone(pytz.timezone("UTC")),
            1,
            False,
            {"organization_id": "0b3d6803-2096-430f-acf5-16e64195436a"},
            None,
        ),
        # limit filter and column value filter - return less than limit because only one inference matches
        (
            mock_expel_tabular_dataset(dataset_locator_happy_path),
            datetime(2024, 1, 4).astimezone(pytz.timezone("UTC")),
            1,
            False,
            {"organization_id": "0b3d6803-2096-430f-acf5-16e64195436a"},
            ConnectorPaginationOptions(page_size=3),
        ),
        # page size and page filter - return complete page
        (
            mock_expel_tabular_dataset(dataset_locator_happy_path),
            datetime(2024, 1, 4).astimezone(pytz.timezone("UTC")),
            2,
            False,
            {},
            ConnectorPaginationOptions(page=2, page_size=2),
        ),
        # page filter default page size - returns no inferences because default size is larger than total number of inferences
        (
            mock_expel_tabular_dataset(dataset_locator_happy_path),
            datetime(2024, 1, 4).astimezone(pytz.timezone("UTC")),
            0,
            False,
            {},
            ConnectorPaginationOptions(page=2),
        ),
        # page size, page, and limit filter, limit < page size
        (
            mock_expel_tabular_dataset(dataset_locator_happy_path),
            datetime(2024, 1, 4).astimezone(pytz.timezone("UTC")),
            2,
            False,
            {},
            ConnectorPaginationOptions(page=2, page_size=2),
        ),
        # page size, page, and limit filter, page size < limit
        (
            mock_expel_tabular_dataset(dataset_locator_happy_path),
            datetime(2024, 1, 4).astimezone(pytz.timezone("UTC")),
            1,
            False,
            {},
            ConnectorPaginationOptions(page=2, page_size=1),
        ),
        # page size, page, limit, and column name filter - no inferences because only one matches & page 2 is requested
        (
            mock_expel_tabular_dataset(dataset_locator_happy_path),
            datetime(2024, 1, 4).astimezone(pytz.timezone("UTC")),
            0,
            False,
            {"organization_id": "0b3d6803-2096-430f-acf5-16e64195436a"},
            ConnectorPaginationOptions(page=2, page_size=1),
        ),
        # page size, page, limit, and column name filter - basic happy path
        (
            mock_expel_tabular_dataset(dataset_locator_happy_path),
            datetime(2024, 1, 4).astimezone(pytz.timezone("UTC")),
            1,
            False,
            {"organization_id": "0b3d6803-2096-430f-acf5-16e64195436a"},
            ConnectorPaginationOptions(page=1, page_size=2),
        ),
        # page requested is past available data, so no inferences should be returned
        (
            mock_expel_tabular_dataset(dataset_locator_happy_path),
            datetime(2024, 1, 4).astimezone(pytz.timezone("UTC")),
            0,
            False,
            {},
            ConnectorPaginationOptions(page=5, page_size=12),
        ),
        # insufficient data - return incomplete page
        (
            mock_expel_tabular_dataset(dataset_locator_happy_path),
            datetime(2024, 1, 4).astimezone(pytz.timezone("UTC")),
            2,
            False,
            {},
            ConnectorPaginationOptions(page=4, page_size=6),
        ),
        # read data without timestamp tag - mock schema inference job
        (
            mock_expel_tabular_dataset_no_primary_timestamp_tag(
                dataset_locator_happy_path,
            ),
            datetime(2024, 1, 4).astimezone(pytz.timezone("UTC")),
            6,
            False,
            {},
            ConnectorPaginationOptions(page=1, page_size=6),
        ),
        # read data without timestamp tag - should fail b/c no timestamp tag is found in schema, and no pagination options were set
        (
            mock_expel_tabular_dataset_no_primary_timestamp_tag(
                dataset_locator_happy_path,
            ),
            datetime(2024, 1, 4).astimezone(pytz.timezone("UTC")),
            6,
            True,
            {},
            None,
        ),
    ],
)
def test_s3_read_data(
    mock_s3fs_walk,
    mock_s3fs_open,
    mock_s3fs_is_file,
    dataset_spec,
    end_timestamp,
    expected_rows,
    should_error,
    filters,
    pagination_options,
):
    start_timestamp = datetime(2024, 1, 1).astimezone(pytz.timezone("UTC"))
    dataset = Dataset.model_validate(dataset_spec)
    spec = ConnectorSpec.model_validate(MOCK_S3_CONNECTOR_SPEC)
    conn = S3Connector(spec, logger)
    filters = [
        DataResultFilter(field_name=k, op="equals", value=v) for k, v in filters.items()
    ]

    if should_error:
        with pytest.raises(Exception):
            conn.read(
                dataset,
                start_time=start_timestamp,
                end_time=end_timestamp,
                filters=filters,
                pagination_options=pagination_options,
            )
    else:
        rows = conn.read(
            dataset,
            start_time=start_timestamp,
            end_time=end_timestamp,
            filters=filters,
            pagination_options=pagination_options,
        )
        assert len(rows) == expected_rows


MOCK_AXIOS_S3_CONNECTOR_SPEC = mock_bucket_based_connector_spec(
    connector_type=ConnectorType.S3,
    fields=[
        {
            "key": S3_CONNECTOR_ENDPOINT_FIELD,
            "value": "http://some.onprem.s3.host",
            "is_sensitive": False,
            "d_type": ConnectorFieldDataType.STRING.value,
        },
        {
            "key": BUCKET_BASED_CONNECTOR_BUCKET_FIELD,
            "value": "./tests/unit/mock_data/axios_regression_dataset",
            "is_sensitive": False,
            "d_type": ConnectorFieldDataType.STRING.value,
        },
    ],
)

MOCK_AXIOS_S3_AVAILABLE_DATASET = {
    "id": str(uuid4()),
    "data_plane_id": str(uuid4()),
    "dataset_locator": DatasetLocator(
        fields=[
            DatasetLocatorField(
                key=BUCKET_BASED_DATASET_FILE_PREFIX_FIELD,
                value="subject-line-open-rate/inferences/year=%Y/month=%m/day=%d/hour=%H",
            ),
            DatasetLocatorField(
                key=BUCKET_BASED_DATASET_FILE_SUFFIX_FIELD,
                value=".*.parquet",
            ),
            DatasetLocatorField(
                key=BUCKET_BASED_DATASET_FILE_TYPE_FIELD,
                value=DatasetFileType.PARQUET,
            ),
            DatasetLocatorField(
                key=BUCKET_BASED_DATASET_TIMESTAMP_TIME_ZONE_FIELD,
                value="UTC",
            ),
        ],
    ),
    "connector_id": MOCK_AXIOS_S3_CONNECTOR_SPEC["id"],
    "project_id": MOCK_AXIOS_S3_CONNECTOR_SPEC["project_id"],
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
}


@patch("s3fs.S3FileSystem.open", side_effect=open)
@patch("s3fs.S3FileSystem.walk", side_effect=os.walk)
@patch("s3fs.S3FileSystem.isfile", side_effect=os.path.isfile)
def test_s3_read_parquet_data(mock_s3fs_walk, mock_s3fs_open, mock_s3fs_is_file):
    start_timestamp = datetime(2024, 10, 1).astimezone(pytz.timezone("UTC"))
    end_timestamp = datetime(2024, 10, 3).astimezone(pytz.timezone("UTC"))
    avail_dataset = AvailableDataset.model_validate(MOCK_AXIOS_S3_AVAILABLE_DATASET)
    spec = ConnectorSpec.model_validate(MOCK_AXIOS_S3_CONNECTOR_SPEC)
    conn = S3Connector(spec, logger)
    rows = conn.read(
        avail_dataset,
        start_time=start_timestamp,
        end_time=end_timestamp,
        filters=None,
        pagination_options=ConnectorPaginationOptions(page=2, page_size=50),
    )

    assert len(rows) == 50


@patch("s3fs.S3FileSystem.open", side_effect=open)
@patch("s3fs.S3FileSystem.walk", side_effect=os.walk)
@patch("s3fs.S3FileSystem.isfile", side_effect=os.path.isfile)
def test_s3_read_data_deterministic(mock_s3fs_walk, mock_s3fs_open, mock_s3fs_is_file):
    # tests reading data returns data in deterministic order even though threading is used
    start_timestamp = datetime(2024, 1, 1).astimezone(pytz.timezone("UTC"))
    end_timestamp = datetime(2024, 1, 4).astimezone(pytz.timezone("UTC"))
    dataset = Dataset.model_validate(
        mock_expel_tabular_dataset(dataset_locator_happy_path),
    )
    spec = ConnectorSpec.model_validate(MOCK_S3_CONNECTOR_SPEC)
    conn = S3Connector(spec, logger)

    rows = conn.read(
        dataset,
        start_time=start_timestamp,
        end_time=end_timestamp,
        filters=None,
        pagination_options=ConnectorPaginationOptions(page=2, page_size=4),
    )
    assert len(rows) == 4
    # data will be sorted in descending order by default
    ordered_expected_alerts = [
        "49129fe9-8955-4ee2-8725-8b84c2c0e153",
        "d5bba627-99e2-4593-9b46-cb2b8da5554d",
        "60161e2f-0584-4b2d-b6de-8e47d584b324",
        "8ce06ce0-6967-494f-aee4-ec424236c73c",
    ]
    for i in range(4):
        assert rows[i]["expel_alert_id"] == ordered_expected_alerts[i]


@patch("s3fs.S3FileSystem.open", side_effect=open)
@patch("s3fs.S3FileSystem.walk", side_effect=os.walk)
@patch("s3fs.S3FileSystem.isfile", side_effect=os.path.isfile)
def test_s3_read_data_time_range_inclusive(
    mock_s3fs_walk,
    mock_s3fs_open,
    mock_s3fs_is_file,
):
    # submit job for timestamp that includes time information more granular than the smallest timedelta range (which is
    # day for this dataset) to ensure the read function correctly handles rendering the file prefixes so that all
    # data in the range is included
    # tests reading data returns data in files where the rendered file timestamp needs to include a rendering for a
    # timestamp less than the start_timestamp and a rendering for the file prefix produced by the end_timestamp
    start_timestamp = datetime(2024, 1, 1, hour=4).astimezone(pytz.timezone("UTC"))
    end_timestamp = datetime(2024, 1, 2, hour=8).astimezone(pytz.timezone("UTC"))
    dataset = Dataset.model_validate(
        mock_expel_tabular_dataset(dataset_locator_happy_path),
    )
    spec = ConnectorSpec.model_validate(MOCK_S3_CONNECTOR_SPEC)
    conn = S3Connector(spec, logger)

    rows = conn.read(
        dataset,
        start_time=start_timestamp,
        end_time=end_timestamp,
        filters=None,
        pagination_options=ConnectorPaginationOptions(page_size=50),
    )
    assert len(rows) == 10


@patch("s3fs.S3FileSystem.open", side_effect=open)
@patch("s3fs.S3FileSystem.walk", side_effect=os.walk)
@patch("s3fs.S3FileSystem.isfile", side_effect=os.path.isfile)
@pytest.mark.parametrize(
    "filters,expected_rows",
    [
        # test in filters with both iterable & non-iterable values set
        (
            [
                DataResultFilter(
                    field_name="organization_id",
                    op=DataResultFilterOp.IN,
                    value="75d13ab3-5b87-4675-9fc1-4df2bcfd7728",
                ),
                DataResultFilter(
                    field_name="predicted_label",
                    op=DataResultFilterOp.IN,
                    value=["NOT_MARKETING"],
                ),
            ],
            1,
        ),
        # test not in filters with both iterable & non-iterable values set
        (
            [
                DataResultFilter(
                    field_name="organization_id",
                    op=DataResultFilterOp.NOT_IN,
                    value="75d13ab3-5b87-4675-9fc1-4df2bcfd7728",
                ),
                DataResultFilter(
                    field_name="predicted_label",
                    op=DataResultFilterOp.NOT_IN,
                    value=["MARKETING"],
                ),
            ],
            5,
        ),
    ],
)
def test_s3_read_filters(
    mock_s3fs_walk,
    mock_s3fs_open,
    mock_s3fs_is_file,
    filters,
    expected_rows,
):
    start_timestamp = datetime(2024, 1, 1).astimezone(pytz.timezone("UTC"))
    end_timestamp = datetime(2024, 1, 3).astimezone(pytz.timezone("UTC"))
    dataset = Dataset.model_validate(
        mock_expel_tabular_dataset(dataset_locator_happy_path),
    )
    spec = ConnectorSpec.model_validate(MOCK_S3_CONNECTOR_SPEC)
    conn = S3Connector(spec, logger)
    rows = conn.read(
        dataset,
        start_time=start_timestamp,
        end_time=end_timestamp,
        filters=filters,
        pagination_options=ConnectorPaginationOptions(page=1, page_size=5),
    )

    assert len(rows) == expected_rows
