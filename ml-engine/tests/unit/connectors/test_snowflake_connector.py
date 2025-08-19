import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
import pytz
from arthur_client.api_bindings import (
    ConnectorCheckOutcome,
    ConnectorFieldDataType,
    ConnectorSpec,
    ConnectorType,
    DatasetColumn,
    DatasetLocator,
    DatasetLocatorField,
    DatasetScalarType,
    DatasetSchema,
    Definition,
    ScopeSchemaTag,
)
from arthur_common.models.connectors import (  # Snowflake-specific fields
    ODBC_CONNECTOR_DATABASE_FIELD,
    ODBC_CONNECTOR_DIALECT_FIELD,
    ODBC_CONNECTOR_HOST_FIELD,
    ODBC_CONNECTOR_PASSWORD_FIELD,
    ODBC_CONNECTOR_TABLE_NAME_FIELD,
    ODBC_CONNECTOR_USERNAME_FIELD,
    SNOWFLAKE_CONNECTOR_AUTHENTICATOR_FIELD,
    SNOWFLAKE_CONNECTOR_PRIVATE_KEY_FIELD,
    SNOWFLAKE_CONNECTOR_PRIVATE_KEY_PASSPHRASE_FIELD,
    SNOWFLAKE_CONNECTOR_ROLE_FIELD,
    SNOWFLAKE_CONNECTOR_SCHEMA_FIELD,
    SNOWFLAKE_CONNECTOR_WAREHOUSE_FIELD,
    ConnectorPaginationOptions,
)
from arthur_common.models.datasets import ModelProblemType

logger = logging.getLogger("snowflake_test_logger")

# Mock ConnectorSpec for Snowflake using ODBC connector
MOCK_SNOWFLAKE_CONNECTOR_SPEC = {
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
    "id": str(uuid4()),
    "connector_type": ConnectorType.ODBC,
    "name": "Mock Snowflake Connector Spec",
    "temporary": False,
    "fields": [
        {
            "key": "host",
            "value": "test-account",
            "is_sensitive": False,
            "d_type": ConnectorFieldDataType.STRING.value,
        },
        {
            "key": "username",
            "value": "testuser",
            "is_sensitive": False,
            "d_type": ConnectorFieldDataType.STRING.value,
        },
        {
            "key": "password",
            "value": "testpass",
            "is_sensitive": True,
            "d_type": ConnectorFieldDataType.STRING.value,
        },
        {
            "key": "database",
            "value": "testdb",
            "is_sensitive": False,
            "d_type": ConnectorFieldDataType.STRING.value,
        },
        {
            "key": "dialect",
            "value": "Snowflake Native (snowflake-connector-python)",
            "is_sensitive": False,
            "d_type": ConnectorFieldDataType.STRING.value,
        },
        {
            "key": "schema",
            "value": "PUBLIC",
            "is_sensitive": False,
            "d_type": ConnectorFieldDataType.STRING.value,
        },
        {
            "key": "warehouse",
            "value": "test_warehouse",
            "is_sensitive": False,
            "d_type": ConnectorFieldDataType.STRING.value,
        },
        {
            "key": "role",
            "value": "test_role",
            "is_sensitive": False,
            "d_type": ConnectorFieldDataType.STRING.value,
        },
        {
            "key": "authenticator",
            "value": "snowflake",
            "is_sensitive": False,
            "d_type": ConnectorFieldDataType.STRING.value,
        },
    ],
    "last_updated_by_user": None,
    "connector_check_result": None,
    "project_id": str(uuid4()),
    "data_plane_id": str(uuid4()),
}

# Construct mock dataset definitions
BASE_DATASET = {
    "id": str(uuid4()),
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
    "project_id": str(uuid4()),
    "connector_id": str(uuid4()),
    "data_plane_id": str(uuid4()),
    "dataset_locator": DatasetLocator(
        fields=[
            DatasetLocatorField(
                key=ODBC_CONNECTOR_TABLE_NAME_FIELD,
                value="test_table",
            ),
        ],
    ),
    "model_problem_type": ModelProblemType.BINARY_CLASSIFICATION.value,
    "dataset_schema": DatasetSchema(
        alias_mask={},
        columns=[
            DatasetColumn(
                id=str(uuid4()),
                source_name="id",
                definition=Definition(
                    DatasetScalarType(
                        tag_hints=[],
                        nullable=False,
                        id=str(uuid4()),
                        dtype="uuid",
                    ),
                ),
            ),
            DatasetColumn(
                id=str(uuid4()),
                source_name="timestamp",
                definition=Definition(
                    DatasetScalarType(
                        tag_hints=[ScopeSchemaTag.PRIMARY_TIMESTAMP],
                        nullable=False,
                        id=str(uuid4()),
                        dtype="timestamp",
                    ),
                ),
            ),
        ],
        column_names={"id": "id", "timestamp": "timestamp"},
    ),
}

# Duplicate without timestamp tag
NO_TS_DATASET = dict(BASE_DATASET)
NO_TS_DATASET["dataset_schema"] = BASE_DATASET["dataset_schema"].model_copy(
    update={
        "columns": [
            BASE_DATASET["dataset_schema"].columns[0],
            # timestamp column without tag
            DatasetColumn(
                id=str(uuid4()),
                source_name="timestamp",
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
    },
)

start_timestamp = datetime(2024, 1, 1, tzinfo=pytz.UTC)
end_timestamp = start_timestamp + timedelta(days=1)


class TestSnowflakeConnectorInitialization:
    """Test Snowflake connector initialization using ODBC connector with Snowflake dialect."""

    @patch("ml_engine.connectors.odbc_connector.create_engine")
    def test_connector_initialization_success(self, mock_create_engine):
        """Test successful connector initialization with all required fields."""
        from ml_engine.connectors.odbc_connector import ODBCConnector

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        spec = ConnectorSpec.model_validate(MOCK_SNOWFLAKE_CONNECTOR_SPEC)
        connector = ODBCConnector(spec, logger)

        assert connector.host == "test-account"
        assert connector.username == "testuser"
        assert connector.password.get_secret_value() == "testpass"
        assert connector.database == "testdb"
        assert connector.dialect == "Snowflake Native (snowflake-connector-python)"
        assert connector.schema == "PUBLIC"
        assert connector.warehouse == "test_warehouse"
        assert connector.role == "test_role"
        assert connector.authenticator == "snowflake"
        assert connector.engine == mock_engine
        assert connector.logger == logger

    @patch("ml_engine.connectors.odbc_connector.create_engine")
    def test_connector_initialization_minimal_fields(self, mock_create_engine):
        """Test connector initialization with only required fields (should use defaults)."""
        from ml_engine.connectors.odbc_connector import ODBCConnector

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        # Create spec with only required fields
        minimal_spec = MOCK_SNOWFLAKE_CONNECTOR_SPEC.copy()
        minimal_spec["fields"] = [
            {
                "key": "host",
                "value": "minimal-account",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "username",
                "value": "minimaluser",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "database",
                "value": "minimaldb",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "dialect",
                "value": "Snowflake Native (snowflake-connector-python)",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
        ]

        spec = ConnectorSpec.model_validate(minimal_spec)
        connector = ODBCConnector(spec, logger)

        # Should use defaults for missing optional fields
        assert connector.host == "minimal-account"
        assert connector.username == "minimaluser"
        assert connector.database == "minimaldb"
        assert connector.dialect == "Snowflake Native (snowflake-connector-python)"
        assert connector.schema == "PUBLIC"  # default
        assert connector.warehouse == ""  # default
        assert connector.role == ""  # default
        assert connector.authenticator == "snowflake"  # default

    @patch("ml_engine.connectors.odbc_connector.create_engine")
    def test_connector_initialization_with_private_key_auth(self, mock_create_engine):
        """Test connector initialization with private key authentication."""
        from ml_engine.connectors.odbc_connector import ODBCConnector

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        # Create spec with private key authentication
        private_key_spec = MOCK_SNOWFLAKE_CONNECTOR_SPEC.copy()
        private_key_spec["fields"] = [
            {
                "key": "host",
                "value": "key-account",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "username",
                "value": "keyuser",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "database",
                "value": "keydb",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "dialect",
                "value": "Snowflake Native (snowflake-connector-python)",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "authenticator",
                "value": "snowflake_jwt",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "private_key",
                "value": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...",
                "is_sensitive": True,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "private_key_passphrase",
                "value": "passphrase123",
                "is_sensitive": True,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
        ]

        spec = ConnectorSpec.model_validate(private_key_spec)
        connector = ODBCConnector(spec, logger)

        assert connector.authenticator == "snowflake_jwt"
        assert (
            connector.private_key
            == "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC..."
        )
        assert connector.private_key_passphrase == "passphrase123"

    @patch("ml_engine.connectors.odbc_connector.create_engine")
    def test_connector_initialization_missing_required_field(self, mock_create_engine):
        """Test connector initialization with missing required field raises KeyError."""
        from ml_engine.connectors.odbc_connector import ODBCConnector

        # Create spec missing host field (required)
        invalid_spec = MOCK_SNOWFLAKE_CONNECTOR_SPEC.copy()
        invalid_spec["fields"] = [
            {
                "key": "username",
                "value": "testuser",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "database",
                "value": "testdb",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
        ]

        spec = ConnectorSpec.model_validate(invalid_spec)

        with pytest.raises(KeyError, match="host"):
            ODBCConnector(spec, logger)


class TestSnowflakeConnectorConnection:
    """Test Snowflake connector connection functionality using ODBC connector."""

    @patch("ml_engine.connectors.odbc_connector.create_engine")
    def test_connection_test_success(self, mock_create_engine):
        """Test successful connection test."""
        from ml_engine.connectors.odbc_connector import ODBCConnector

        mock_engine = Mock()
        mock_connection = Mock()
        mock_connection.__enter__ = Mock(return_value=mock_connection)
        mock_connection.__exit__ = Mock(return_value=None)
        mock_connection.execute = Mock()
        mock_engine.connect.return_value = mock_connection
        mock_create_engine.return_value = mock_engine

        spec = ConnectorSpec.model_validate(MOCK_SNOWFLAKE_CONNECTOR_SPEC)
        connector = ODBCConnector(spec, logger)

        result = connector.test_connection()

        assert result.connection_check_outcome == ConnectorCheckOutcome.SUCCEEDED
        assert result.failure_reason is None

    @patch("ml_engine.connectors.odbc_connector.create_engine")
    def test_connection_test_with_warehouse(self, mock_create_engine):
        """Test connection test with warehouse specified."""
        from ml_engine.connectors.odbc_connector import ODBCConnector

        mock_engine = Mock()
        mock_connection = Mock()
        mock_connection.__enter__ = Mock(return_value=mock_connection)
        mock_connection.__exit__ = Mock(return_value=None)
        mock_connection.execute = Mock()
        mock_engine.connect.return_value = mock_connection
        mock_create_engine.return_value = mock_engine

        spec = ConnectorSpec.model_validate(MOCK_SNOWFLAKE_CONNECTOR_SPEC)
        connector = ODBCConnector(spec, logger)

        result = connector.test_connection()

        # Should be called 4 times: SELECT 1, USE WAREHOUSE, USE DATABASE, USE SCHEMA
        assert mock_connection.execute.call_count == 4
        assert result.connection_check_outcome == ConnectorCheckOutcome.SUCCEEDED


class TestSnowflakeConnectorURLBuilding:
    """Test Snowflake connector URL building functionality using ODBC connector."""

    @patch("ml_engine.connectors.odbc_connector.create_engine")
    def test_build_snowflake_url_with_password(self, mock_create_engine):
        """Test engine URL building with password authentication."""
        from ml_engine.connectors.odbc_connector import ODBCConnector

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        spec = ConnectorSpec.model_validate(MOCK_SNOWFLAKE_CONNECTOR_SPEC)
        connector = ODBCConnector(spec, logger)

        # Verify the URL format
        mock_create_engine.assert_called_once()
        call_args = mock_create_engine.call_args[0][0]
        assert "snowflake://testuser:testpass@test-account" in call_args
        assert "/testdb" in call_args
        assert "warehouse=test_warehouse" in call_args
        assert "role=test_role" in call_args

    @patch("ml_engine.connectors.odbc_connector.create_engine")
    def test_build_snowflake_url_without_password(self, mock_create_engine):
        """Test engine URL building without password (for OAuth/JWT)."""
        from ml_engine.connectors.odbc_connector import ODBCConnector

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        # Create spec without password
        no_password_spec = MOCK_SNOWFLAKE_CONNECTOR_SPEC.copy()
        no_password_spec["fields"] = [
            {
                "key": "host",
                "value": "no-pass-account",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "username",
                "value": "nopassuser",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "database",
                "value": "nopassdb",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "dialect",
                "value": "Snowflake Native (snowflake-connector-python)",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
        ]

        spec = ConnectorSpec.model_validate(no_password_spec)
        connector = ODBCConnector(spec, logger)

        # Verify the URL format without password
        mock_create_engine.assert_called_once()
        call_args = mock_create_engine.call_args[0][0]
        assert "snowflake://nopassuser@no-pass-account" in call_args
        assert "/nopassdb" in call_args

    @patch("ml_engine.connectors.odbc_connector.create_engine")
    def test_build_snowflake_url_with_private_key(self, mock_create_engine):
        """Test engine URL building with private key authentication."""
        from ml_engine.connectors.odbc_connector import ODBCConnector

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        # Create spec with private key
        private_key_spec = MOCK_SNOWFLAKE_CONNECTOR_SPEC.copy()
        private_key_spec["fields"] = [
            {
                "key": "host",
                "value": "key-account",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "username",
                "value": "keyuser",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "database",
                "value": "keydb",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "dialect",
                "value": "Snowflake Native (snowflake-connector-python)",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "authenticator",
                "value": "snowflake_jwt",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "private_key",
                "value": "test_private_key",
                "is_sensitive": True,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "private_key_passphrase",
                "value": "test_passphrase",
                "is_sensitive": True,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
        ]

        spec = ConnectorSpec.model_validate(private_key_spec)
        connector = ODBCConnector(spec, logger)

        # Verify the URL format with private key
        mock_create_engine.assert_called_once()
        call_args = mock_create_engine.call_args[0][0]
        assert "snowflake://keyuser@key-account" in call_args
        assert "/keydb" in call_args
        assert "authenticator=snowflake_jwt" in call_args
        assert "private_key=test_private_key" in call_args
        assert "private_key_passphrase=test_passphrase" in call_args
