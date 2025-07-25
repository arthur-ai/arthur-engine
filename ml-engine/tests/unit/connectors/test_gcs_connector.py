import logging
import os

import pytz
from arthur_client.api_bindings import ConnectorSpec, DataResultFilter, Dataset
from arthur_common.models.connectors import ConnectorPaginationOptions
from connectors.gcs_connector import GCSConnector
from mock_data.connector_helpers import *

logger = logging.getLogger("job_logger")


MOCK_GCS_CONNECTOR_SPEC = mock_bucket_based_connector_spec(
    connector_type=ConnectorType.GCS,
    fields=[
        {
            "key": "credentials",
            "value": json.dumps(
                {
                    "refresh_token": "some_refresh_token",
                    "client_secret": "some_client_secret",
                    "client_id": "some_client_id",
                    "token_uri": "https://oauth2.googleapis.com/token",
                },
            ),
            "is_sensitive": True,
            "d_type": ConnectorFieldDataType.STRING.value,
        },
        {
            "key": "bucket",
            "value": "./tests/unit/mock_data/expel_tabular_s3_bucket",
            "is_sensitive": False,
            "d_type": ConnectorFieldDataType.STRING.value,
        },
        {
            "key": "project_id",
            "value": "some-project-id",
            "is_sensitive": False,
            "d_type": ConnectorFieldDataType.STRING.value,
        },
    ],
)


# mocks gcsfs.ls and gcsfs.open as local directory calls
@patch("gcsfs.GCSFileSystem.open", side_effect=open)
@patch("gcsfs.GCSFileSystem.walk", side_effect=os.walk)
@patch("gcsfs.GCSFileSystem.isfile", side_effect=os.path.isfile)
@pytest.mark.parametrize(
    "dataset_spec,end_timestamp,expected_rows,should_error,filters,pagination_options",
    [
        # UTC timezone, should read all 40 inferences in the time range
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
            None,
            ConnectorPaginationOptions(page_size=8),
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
            ConnectorPaginationOptions(limit=3),
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
def test_gcs_read_data(
    mock_gcsfs_walk,
    mock_gcsfs_open,
    mock_gcsfs_is_file,
    dataset_spec,
    end_timestamp,
    expected_rows,
    should_error,
    filters,
    pagination_options,
):
    start_timestamp = datetime(2024, 1, 1).astimezone(pytz.timezone("UTC"))
    dataset = Dataset.model_validate(dataset_spec)
    spec = ConnectorSpec.model_validate(MOCK_GCS_CONNECTOR_SPEC)
    conn = GCSConnector(spec, logger)
    filters = (
        [
            DataResultFilter(field_name=k, op="equals", value=v)
            for k, v in filters.items()
        ]
        if filters
        else []
    )

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
