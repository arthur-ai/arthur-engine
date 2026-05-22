import logging
import os
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
import pytz
from arthur_client.api_bindings import ConnectorSpec, DataResultFilter, Dataset
from arthur_common.models.connectors import (
    AZURE_CONNECTOR_CONNECTION_STRING_FIELD,
    ConnectorPaginationOptions,
)
from mock_data.connector_helpers import (
    dataset_locator_happy_path,
    mock_bucket_based_connector_spec,
    mock_expel_tabular_dataset,
    mock_expel_tabular_dataset_no_primary_timestamp_tag,
)

from connectors.azure_blob_connector import (
    AzureBlobConnector,
    _AzureConnectorConfigFields,
)

logger = logging.getLogger("job_logger")

MOCK_AZURE_CONNECTOR_SPEC = mock_bucket_based_connector_spec(
    connector_type=Mock(value="AzureBlob"),
    fields=[
        {
            "key": AZURE_CONNECTOR_CONNECTION_STRING_FIELD,
            "value": "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;",
            "is_sensitive": True,
            "d_type": "string",
        },
        {
            "key": "bucket",
            "value": "./tests/unit/mock_data/expel_tabular_s3_bucket",
            "is_sensitive": False,
            "d_type": "string",
        },
    ],
)


# --- Auth construction tests (call _construct_adlfs_with_auth directly) ---


@patch("adlfs.AzureBlobFileSystem.__init__", return_value=None)
def test_connection_string_auth(mock_init):
    config = _AzureConnectorConfigFields(
        connection_string="DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=mykey;",
        account_name=None,
        account_key=None,
        sas_token=None,
        tenant_id=None,
        client_id=None,
        client_secret=None,
    )
    AzureBlobConnector._construct_adlfs_with_auth(config)
    mock_init.assert_called_once_with(
        connection_string="DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=mykey;",
    )


@patch("adlfs.AzureBlobFileSystem.__init__", return_value=None)
def test_service_principal_auth(mock_init):
    config = _AzureConnectorConfigFields(
        connection_string=None,
        account_name="myaccount",
        account_key=None,
        sas_token=None,
        tenant_id="tenant-123",
        client_id="client-456",
        client_secret="secret-789",
    )
    AzureBlobConnector._construct_adlfs_with_auth(config)
    mock_init.assert_called_once_with(
        account_name="myaccount",
        tenant_id="tenant-123",
        client_id="client-456",
        client_secret="secret-789",
    )


@patch("adlfs.AzureBlobFileSystem.__init__", return_value=None)
def test_sas_token_auth(mock_init):
    config = _AzureConnectorConfigFields(
        connection_string=None,
        account_name="myaccount",
        account_key=None,
        sas_token="?sv=2021-01-01&sig=xxx",
        tenant_id=None,
        client_id=None,
        client_secret=None,
    )
    AzureBlobConnector._construct_adlfs_with_auth(config)
    mock_init.assert_called_once_with(
        account_name="myaccount",
        sas_token="?sv=2021-01-01&sig=xxx",
    )


@patch("adlfs.AzureBlobFileSystem.__init__", return_value=None)
def test_account_key_auth(mock_init):
    config = _AzureConnectorConfigFields(
        connection_string=None,
        account_name="myaccount",
        account_key="myaccountkey==",
        sas_token=None,
        tenant_id=None,
        client_id=None,
        client_secret=None,
    )
    AzureBlobConnector._construct_adlfs_with_auth(config)
    mock_init.assert_called_once_with(
        account_name="myaccount",
        account_key="myaccountkey==",
    )


@patch("adlfs.AzureBlobFileSystem.__init__", return_value=None)
def test_connection_string_priority(mock_init):
    """connection_string takes precedence even when other fields are also set."""
    config = _AzureConnectorConfigFields(
        connection_string="DefaultEndpointsProtocol=https;AccountName=x;AccountKey=y;",
        account_name="myaccount",
        account_key="myaccountkey==",
        sas_token="?sv=2021-01-01&sig=xxx",
        tenant_id="tenant-123",
        client_id="client-456",
        client_secret="secret-789",
    )
    AzureBlobConnector._construct_adlfs_with_auth(config)
    mock_init.assert_called_once_with(
        connection_string="DefaultEndpointsProtocol=https;AccountName=x;AccountKey=y;",
    )


# --- Validation error tests ---


def test_sp_missing_account_name():
    config = _AzureConnectorConfigFields(
        connection_string=None,
        account_name=None,
        account_key=None,
        sas_token=None,
        tenant_id="tenant-123",
        client_id="client-456",
        client_secret="secret-789",
    )
    with pytest.raises(ValueError, match="account_name is required"):
        AzureBlobConnector._construct_adlfs_with_auth(config)


def test_sas_missing_account_name():
    config = _AzureConnectorConfigFields(
        connection_string=None,
        account_name=None,
        account_key=None,
        sas_token="?sv=2021-01-01&sig=xxx",
        tenant_id=None,
        client_id=None,
        client_secret=None,
    )
    with pytest.raises(ValueError, match="account_name is required for SAS token auth"):
        AzureBlobConnector._construct_adlfs_with_auth(config)


def test_no_credentials_raises():
    config = _AzureConnectorConfigFields(
        connection_string=None,
        account_name=None,
        account_key=None,
        sas_token=None,
        tenant_id=None,
        client_id=None,
        client_secret=None,
    )
    with pytest.raises(ValueError, match="At least one auth method is required"):
        AzureBlobConnector._construct_adlfs_with_auth(config)


# --- Read tests (mock filesystem, follow GCS pattern) ---


@patch("adlfs.AzureBlobFileSystem.open", side_effect=open)
@patch("adlfs.AzureBlobFileSystem.walk", side_effect=os.walk)
@patch("adlfs.AzureBlobFileSystem.isfile", side_effect=os.path.isfile)
@patch("adlfs.AzureBlobFileSystem.__init__", return_value=None)
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
        # read without timestamp tag with pagination
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
    ],
)
def test_azure_read_data(
    mock_adlfs_init,
    mock_adlfs_is_file,
    mock_adlfs_walk,
    mock_adlfs_open,
    dataset_spec,
    end_timestamp,
    expected_rows,
    should_error,
    filters,
    pagination_options,
):
    start_timestamp = datetime(2024, 1, 1).astimezone(pytz.timezone("UTC"))
    dataset = Dataset.model_validate(dataset_spec)
    spec = ConnectorSpec.model_validate(MOCK_AZURE_CONNECTOR_SPEC)
    conn = AzureBlobConnector(spec, logger)
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
