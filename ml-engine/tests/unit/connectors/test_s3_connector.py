import logging
import os
from datetime import datetime

import fsspec
import pandas as pd
import pytz
from arthur_client.api_bindings import (
    AvailableDataset,
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
from arthur_common.models.datasets import DatasetFileType
from connectors.bucket_based_connector import BucketBasedConnector, CSVConfig, read_file
from connectors.s3_connector import S3Connector
from mock_data.connector_helpers import *

logger = logging.getLogger("job_logger")


def assert_column_names_are_strings(rows: list[dict]) -> None:
    """Assert that all column names in the returned rows are strings, not integers."""
    if not rows:
        return  # Empty results are OK
    for row in rows:
        for key in row.keys():
            assert isinstance(
                key, str
            ), f"Column name {key} is type {type(key)}, expected str. Row: {row}"


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
        # Verify all column names are strings, not integers
        assert_column_names_are_strings(rows)


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
    # Verify all column names are strings, not integers
    assert_column_names_are_strings(rows)


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
    # Verify all column names are strings, not integers
    assert_column_names_are_strings(rows)
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
    # Verify all column names are strings, not integers
    assert_column_names_are_strings(rows)


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
    # Verify all column names are strings, not integers
    assert_column_names_are_strings(rows)


@patch("s3fs.S3FileSystem.open", side_effect=open)
@patch("s3fs.S3FileSystem.walk", side_effect=os.walk)
@patch("s3fs.S3FileSystem.isfile", side_effect=os.path.isfile)
def test_s3_read_static_dataset(mock_s3fs_walk, mock_s3fs_open, mock_s3fs_is_file):
    """Static datasets must bypass time-range filtering and read all files under the prefix."""
    static_locator = DatasetLocator(
        fields=[
            DatasetLocatorField(
                key=BUCKET_BASED_DATASET_FILE_PREFIX_FIELD,
                value="7461c078-cc90-4cad-a590-25c534458dfd/b2f420b8-92ed-425e-9d35-bab014af965e/",
            ),
            DatasetLocatorField(
                key=BUCKET_BASED_DATASET_FILE_SUFFIX_FIELD,
                value=".json",
            ),
            DatasetLocatorField(
                key=BUCKET_BASED_DATASET_FILE_TYPE_FIELD,
                value=DatasetFileType.JSON,
            ),
        ],
    )
    dataset_dict = mock_expel_tabular_dataset(static_locator)
    dataset_dict["is_static"] = True
    dataset = Dataset.model_validate(dataset_dict)

    spec = ConnectorSpec.model_validate(MOCK_S3_CONNECTOR_SPEC)
    conn = S3Connector(spec, logger)

    # time range is irrelevant for static datasets — all files should be returned
    rows = conn.read(
        dataset,
        start_time=datetime(2099, 1, 1).astimezone(pytz.timezone("UTC")),
        end_time=datetime(2099, 1, 2).astimezone(pytz.timezone("UTC")),
        filters=None,
        pagination_options=None,
    )

    assert len(rows) > 0
    assert_column_names_are_strings(rows)


def test_secondary_filter_primary_timestamp_with_different_types():
    """Test that _secondary_filter_primary_timestamp handles both string and datetime/pd.Timestamp types.

    This tests the fix for the issue where parquet files return timestamps as pd.Timestamp objects
    rather than strings, which caused parser.parse() to fail with:
    TypeError: Parser must be a string or character stream, not Timestamp
    """
    tz = pytz.timezone("UTC")
    start_time = datetime(2024, 1, 1, hour=0).astimezone(tz)
    end_time = datetime(2024, 1, 2, hour=0).astimezone(tz)

    # Test with string timestamps (original behavior from JSON files)
    inferences_with_strings = [
        {"id": 1, "timestamp": "2024-01-01 12:00:00"},
        {"id": 2, "timestamp": "2024-01-01 18:00:00"},
        {"id": 3, "timestamp": "2024-01-02 12:00:00"},  # outside range
    ]

    filtered = BucketBasedConnector._secondary_filter_primary_timestamp(
        "timestamp",
        inferences_with_strings,
        start_time,
        end_time,
        tz,
    )
    assert len(filtered) == 2
    assert filtered[0]["id"] == 1
    assert filtered[1]["id"] == 2

    # Test with datetime objects (from parquet files with datetime columns)
    inferences_with_datetime = [
        {"id": 4, "timestamp": datetime(2024, 1, 1, hour=12).astimezone(tz)},
        {"id": 5, "timestamp": datetime(2024, 1, 1, hour=18).astimezone(tz)},
        {"id": 6, "timestamp": datetime(2024, 1, 2, hour=12).astimezone(tz)},  # outside range
    ]

    filtered = BucketBasedConnector._secondary_filter_primary_timestamp(
        "timestamp",
        inferences_with_datetime,
        start_time,
        end_time,
        tz,
    )
    assert len(filtered) == 2
    assert filtered[0]["id"] == 4
    assert filtered[1]["id"] == 5

    # Test with pd.Timestamp objects (from parquet files)
    inferences_with_pd_timestamp = [
        {"id": 7, "timestamp": pd.Timestamp("2024-01-01 12:00:00", tz=tz)},
        {"id": 8, "timestamp": pd.Timestamp("2024-01-01 18:00:00", tz=tz)},
        {"id": 9, "timestamp": pd.Timestamp("2024-01-02 12:00:00", tz=tz)},  # outside range
    ]

    filtered = BucketBasedConnector._secondary_filter_primary_timestamp(
        "timestamp",
        inferences_with_pd_timestamp,
        start_time,
        end_time,
        tz,
    )
    assert len(filtered) == 2
    assert filtered[0]["id"] == 7
    assert filtered[1]["id"] == 8

    # Test with naive pd.Timestamp objects (need tz_localize, not astimezone)
    inferences_with_naive_pd_timestamp = [
        {"id": 13, "timestamp": pd.Timestamp("2024-01-01 12:00:00")},  # naive
        {"id": 14, "timestamp": pd.Timestamp("2024-01-01 18:00:00")},  # naive
        {"id": 15, "timestamp": pd.Timestamp("2024-01-02 12:00:00")},  # outside range
    ]

    filtered = BucketBasedConnector._secondary_filter_primary_timestamp(
        "timestamp",
        inferences_with_naive_pd_timestamp,
        start_time,
        end_time,
        tz,
    )
    assert len(filtered) == 2
    assert filtered[0]["id"] == 13
    assert filtered[1]["id"] == 14

    # Test mixed types (edge case, but should work)
    inferences_mixed = [
        {"id": 10, "timestamp": "2024-01-01 06:00:00"},
        {"id": 11, "timestamp": datetime(2024, 1, 1, hour=12).astimezone(tz)},
        {"id": 12, "timestamp": pd.Timestamp("2024-01-01 18:00:00", tz=tz)},
    ]

    filtered = BucketBasedConnector._secondary_filter_primary_timestamp(
        "timestamp",
        inferences_mixed,
        start_time,
        end_time,
        tz,
    )
    assert len(filtered) == 3


@patch("s3fs.S3FileSystem.open", side_effect=open)
@patch("s3fs.S3FileSystem.walk", side_effect=os.walk)
@patch("s3fs.S3FileSystem.isfile", side_effect=os.path.isfile)
@pytest.mark.parametrize(
    "file_name,csv_config,expected_count,validation_checks",
    [
        # Pipe-separated with complex quotes and newlines (RFC 4180)
        (
            "test_quotes.csv",
            CSVConfig(
                delimiter="|",
                quote_char='"',
                escape_char='"',  # Same as quote_char = use double-quote convention
                encoding="utf-8",
            ),
            3,
            {
                "has_embedded_newlines": lambda r: "Johnson\nIII" in r[0]["last_name"],
                "preserves_escaped_quotes": lambda r: '"Highly recommended"'
                in r[0]["customer_notes"],
                "handles_empty_fields": lambda r: pd.isna(r[1]["last_name"]),
            },
        ),
        # Standard comma-separated with double-quote escaping (RFC 4180)
        (
            "standard_comma.csv",
            CSVConfig(
                delimiter=",",
                quote_char='"',
                escape_char='"',  # Same as quote = double-quote convention
                encoding="utf-8",
            ),
            3,
            {
                "has_embedded_quotes": lambda r: '"Jay"' in r[1]["name"],
                "has_embedded_newlines": lambda r: "\n" in r[2]["name"],
                "preserves_quotes_in_notes": lambda r: '"quotes"' in r[1]["notes"],
            },
        ),
        # Tab-separated with single quotes
        (
            "tab_separated.csv",
            CSVConfig(
                delimiter="\t",
                quote_char="'",
                escape_char="'",  # Double single-quote convention
                encoding="utf-8",
            ),
            3,
            {
                "has_embedded_single_quotes": lambda r: "O'Brien" in r[1]["name"],
                "has_embedded_tabs": lambda r: "\t" in r[2]["name"],
            },
        ),
        # Semicolon-separated with backslash escaping
        (
            "semicolon_backslash.csv",
            CSVConfig(
                delimiter=";",
                quote_char='"',
                escape_char="\\",  # Backslash escape
                encoding="utf-8",
            ),
            3,
            {
                "has_escaped_quotes": lambda r: '"Jay"' in r[1]["name"],
                "has_embedded_semicolon": lambda r: "Bob;Wilson" in r[2]["name"],
            },
        ),
        # No header file
        (
            "no_header.csv",
            CSVConfig(
                delimiter=",",
                quote_char='"',
                escape_char='"',
                has_header=False,
                encoding="utf-8",
            ),
            3,
            {
                "has_expected_column_names": lambda r: "0" in r[0]
                and "1" in r[0]
                and "2" in r[0]
                and "3" in r[0]
                and "4" in r[0],  # Should have string column names "0", "1", "2", "3", "4"
            },
        ),
        # Simple CSV without quotes
        (
            "no_quotes_needed.csv",
            CSVConfig(
                delimiter=",",
                encoding="utf-8",
            ),
            3,
            {
                "reads_simple_values": lambda r: r[0]["name"] == "John"
                and r[1]["name"] == "Jane",
            },
        ),
    ],
)
def test_csv_various_formats(
    mock_s3fs_walk,
    mock_s3fs_open,
    mock_s3fs_is_file,
    file_name,
    csv_config,
    expected_count,
    validation_checks,
):
    """Test CSV reading with various delimiter, quote, and escape configurations.

    This ensures robust handling of different customer CSV formats:
    - Standard comma-separated (RFC 4180)
    - Tab-separated with single quotes
    - Semicolon-separated with backslash escaping
    - Files without headers
    - Simple files without special characters
    """
    fs = fsspec.filesystem("file")

    records = read_file(
        fs,
        f"tests/unit/mock_data/csv_test_bucket/data/{file_name}",
        DatasetFileType.CSV,
        csv_config,
    )

    # Verify correct number of records
    assert len(records) == expected_count, f"Expected {expected_count} records, got {len(records)}"

    # Verify all column names are strings, not integers
    assert_column_names_are_strings(records)

    # Run format-specific validation checks
    for check_name, check_func in validation_checks.items():
        assert check_func(records), f"Validation failed: {check_name}"
