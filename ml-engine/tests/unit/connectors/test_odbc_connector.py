import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from uuid import uuid4

import pandas as pd
import pytest
import pytz
from arthur_client.api_bindings import (
    ConnectorCheckOutcome,
    ConnectorFieldDataType,
    ConnectorSpec,
    ConnectorType,
    DataResultFilter,
    Dataset,
    DatasetColumn,
    DatasetLocator,
    DatasetLocatorField,
    DatasetScalarType,
    DatasetSchema,
    Definition,
    ScopeSchemaTag,
)
from arthur_common.models.connectors import (
    ODBC_CONNECTOR_TABLE_NAME_FIELD,
    ConnectorPaginationOptions,
)
from arthur_common.models import ModelProblemType
from sqlalchemy import Column, Integer, MetaData, String
from sqlalchemy import Table as SQLATable

logger = logging.getLogger("odbc_test_logger")

# Mock ConnectorSpec for ODBC
MOCK_ODBC_CONNECTOR_SPEC = {
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
    "id": str(uuid4()),
    "connector_type": ConnectorType.ODBC,
    "name": "Mock ODBC Connector Spec",
    "temporary": False,
    "fields": [
        {
            "key": "host",
            "value": "localhost",
            "is_sensitive": False,
            "d_type": ConnectorFieldDataType.STRING.value,
        },
        {
            "key": "port",
            "value": "1433",
            "is_sensitive": False,
            "d_type": ConnectorFieldDataType.STRING.value,
        },
        {
            "key": "database",
            "value": "testdb",
            "is_sensitive": False,
            "d_type": ConnectorFieldDataType.STRING.value,
        },
        {
            "key": "username",
            "value": "user",
            "is_sensitive": False,
            "d_type": ConnectorFieldDataType.STRING.value,
        },
        {
            "key": "password",
            "value": "pass",
            "is_sensitive": True,
            "d_type": ConnectorFieldDataType.STRING.value,
        },
        {
            "key": "driver",
            "value": "ODBC Driver 17 for SQL Server",
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


class TestODBCConnectorInitialization:
    """Test ODBC connector initialization and configuration."""

    @patch("ml_engine.connectors.odbc_connector.create_engine")
    def test_connector_initialization_success(self, mock_create_engine):
        """Test successful connector initialization with all required fields."""
        from ml_engine.connectors.odbc_connector import ODBCConnector

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        spec = ConnectorSpec.model_validate(MOCK_ODBC_CONNECTOR_SPEC)
        connector = ODBCConnector(spec, logger)

        assert connector.host == "localhost"
        assert connector.port == "1433"
        assert connector.database == "testdb"
        assert connector.username == "user"
        assert connector.password.get_secret_value() == "pass"
        assert connector.driver == "ODBC Driver 17 for SQL Server"
        assert connector.engine == mock_engine
        assert connector.logger == logger

    @patch("ml_engine.connectors.odbc_connector.create_engine")
    def test_connector_initialization_missing_optional_fields(self, mock_create_engine):
        """Test connector initialization with missing optional fields (should use defaults)."""
        from ml_engine.connectors.odbc_connector import ODBCConnector

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        # Create spec with only required fields
        minimal_spec = MOCK_ODBC_CONNECTOR_SPEC.copy()
        minimal_spec["fields"] = [
            {
                "key": "host",
                "value": "testhost",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "database",
                "value": "testdb",
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
        ]

        spec = ConnectorSpec.model_validate(minimal_spec)
        connector = ODBCConnector(spec, logger)

        # Should use defaults for missing optional fields
        assert connector.host == "testhost"
        assert connector.port == ""  # default
        assert connector.database == "testdb"
        assert connector.username == "testuser"
        assert connector.password.get_secret_value() == "testpass"
        assert connector.driver == ""

    @patch("ml_engine.connectors.odbc_connector.create_engine")
    def test_connector_initialization_with_custom_driver(self, mock_create_engine):
        """Test connector initialization with custom driver field."""
        from ml_engine.connectors.odbc_connector import ODBCConnector

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        # Create spec with custom driver
        custom_driver_spec = MOCK_ODBC_CONNECTOR_SPEC.copy()
        custom_driver_spec["fields"] = [
            {
                "key": "host",
                "value": "testhost",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "database",
                "value": "testdb",
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
                "key": "driver",
                "value": "ODBC Driver 18 for SQL Server",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
        ]

        spec = ConnectorSpec.model_validate(custom_driver_spec)
        connector = ODBCConnector(spec, logger)

        # Verify custom driver is used in connection string
        mock_create_engine.assert_called_once()
        call_args = mock_create_engine.call_args[0][0]
        assert "ODBC Driver 18 for SQL Server" in call_args
        assert "mssql+pyodbc:///?odbc_connect=" in call_args

    @patch("ml_engine.connectors.odbc_connector.create_engine")
    def test_connector_initialization_driver_default(self, mock_create_engine):
        """Test connector initialization uses default driver when not specified."""
        from ml_engine.connectors.odbc_connector import ODBCConnector

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        # Create spec without driver field
        no_driver_spec = MOCK_ODBC_CONNECTOR_SPEC.copy()
        no_driver_spec["fields"] = [
            {
                "key": "host",
                "value": "testhost",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "database",
                "value": "testdb",
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
        ]

        spec = ConnectorSpec.model_validate(no_driver_spec)
        connector = ODBCConnector(spec, logger)

        # Verify default driver is used
        mock_create_engine.assert_called_once()
        call_args = mock_create_engine.call_args[0][0]
        assert "mssql+pyodbc:///?odbc_connect=" in call_args
        # Should not contain driver in connection string when not specified
        assert "DRIVER=" not in call_args

    @pytest.mark.parametrize(
        "dialect_config",
        [
            {
                "name": "PostgreSQL Native",
                "dialect": "PostgreSQL Native (psycopg)",
                "host": "postgres.example.com",
                "port": "5432",
                "database": "mydb",
                "username": "postgres",
                "password": "secret",
                "expected_url": "postgresql+psycopg://postgres:secret@postgres.example.com:5432/mydb",
            },
            {
                "name": "MySQL Native",
                "dialect": "MySQL Native (pymysql)",
                "host": "mysql.example.com",
                "port": "3306",
                "database": "mydb",
                "username": "mysql_user",
                "password": "secret",
                "expected_url": "mysql+pymysql://mysql_user:secret@mysql.example.com:3306/mydb",
            },
            {
                "name": "Oracle Native",
                "dialect": "Oracle Native (cx_oracle)",
                "host": "oracle.example.com",
                "port": "1521",
                "database": "XE",
                "username": "system",
                "password": "secret",
                "expected_url": "oracle+cx_oracle://system:secret@oracle.example.com:1521/XE",
            },
            {
                "name": "Generic ODBC",
                "dialect": "Generic ODBC (pyodbc)",
                "host": "server.example.com",
                "port": "1433",
                "database": "mydb",
                "username": "user",
                "password": "secret",
                "driver": "ODBC Driver 17 for SQL Server",
                "expected_url": "mssql+pyodbc:///?odbc_connect=",
            },
        ],
    )
    @patch("ml_engine.connectors.odbc_connector.create_engine")
    def test_connector_initialization_with_dialects(
        self,
        mock_create_engine,
        dialect_config,
    ):
        """Test connector initialization with different dialects."""
        from ml_engine.connectors.odbc_connector import ODBCConnector

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        # Create spec with the specified dialect
        spec_data = MOCK_ODBC_CONNECTOR_SPEC.copy()
        spec_data["fields"] = [
            {
                "key": "host",
                "value": dialect_config["host"],
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "port",
                "value": dialect_config["port"],
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "database",
                "value": dialect_config["database"],
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "username",
                "value": dialect_config["username"],
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "password",
                "value": dialect_config["password"],
                "is_sensitive": True,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "dialect",
                "value": dialect_config["dialect"],
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
        ]

        # Add driver if specified
        if "driver" in dialect_config:
            spec_data["fields"].append(
                {
                    "key": "driver",
                    "value": dialect_config["driver"],
                    "is_sensitive": False,
                    "d_type": ConnectorFieldDataType.STRING.value,
                },
            )

        spec = ConnectorSpec.model_validate(spec_data)
        connector = ODBCConnector(spec, logger)

        # Verify the expected URL is used
        mock_create_engine.assert_called_once()
        call_args = mock_create_engine.call_args[0][0]
        assert dialect_config["expected_url"] in call_args

    def test_connector_initialization_missing_required_field(self):
        """Test connector initialization with missing required field raises KeyError."""
        from ml_engine.connectors.odbc_connector import ODBCConnector

        # Create spec missing host field (required)
        invalid_spec = MOCK_ODBC_CONNECTOR_SPEC.copy()
        invalid_spec["fields"] = [
            {
                "key": "database",
                "value": "testdb",
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
        ]

        spec = ConnectorSpec.model_validate(invalid_spec)

        with pytest.raises(KeyError, match="host"):
            ODBCConnector(spec, logger)


class TestODBCConnectorConnection:
    """Test ODBC connector connection functionality."""

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

        spec = ConnectorSpec.model_validate(MOCK_ODBC_CONNECTOR_SPEC)
        connector = ODBCConnector(spec, logger)

        result = connector.test_connection()

        assert result.connection_check_outcome == ConnectorCheckOutcome.SUCCEEDED
        assert result.failure_reason is None


class TestODBCConnectorDatasetListing:
    """Test ODBC connector dataset listing functionality."""

    @patch("ml_engine.connectors.odbc_connector.create_engine")
    @patch("ml_engine.connectors.odbc_connector.inspect")
    def test_list_datasets_success(self, mock_inspect, mock_create_engine):
        """Test successful dataset listing."""
        from ml_engine.connectors.odbc_connector import ODBCConnector

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_inspector = Mock()
        mock_inspector.get_table_names.return_value = ["table1", "table2", "table3"]
        mock_inspect.return_value = mock_inspector

        spec = ConnectorSpec.model_validate(MOCK_ODBC_CONNECTOR_SPEC)
        connector = ODBCConnector(spec, logger)

        result = connector.list_datasets()

        assert len(result.available_datasets) == 3
        assert result.available_datasets[0].name == "table1"
        assert (
            result.available_datasets[0].dataset_locator.fields[0].key
            == ODBC_CONNECTOR_TABLE_NAME_FIELD
        )
        assert result.available_datasets[0].dataset_locator.fields[0].value == "table1"

    @patch("ml_engine.connectors.odbc_connector.create_engine")
    @patch("ml_engine.connectors.odbc_connector.inspect")
    def test_list_datasets_empty(self, mock_inspect, mock_create_engine):
        """Test dataset listing with no tables."""
        from ml_engine.connectors.odbc_connector import ODBCConnector

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_inspector = Mock()
        mock_inspector.get_table_names.return_value = []
        mock_inspect.return_value = mock_inspector

        spec = ConnectorSpec.model_validate(MOCK_ODBC_CONNECTOR_SPEC)
        connector = ODBCConnector(spec, logger)

        result = connector.list_datasets()

        assert len(result.available_datasets) == 0


class TestODBCConnectorDataReading:
    """Test ODBC connector data reading functionality."""

    @patch("ml_engine.connectors.odbc_connector.create_engine")
    @patch("ml_engine.connectors.odbc_connector.pd.read_sql")
    @patch("ml_engine.connectors.odbc_connector.primary_timestamp_col_name")
    def test_read_with_timestamp_column(
        self,
        mock_primary_timestamp,
        mock_read_sql,
        mock_create_engine,
    ):
        """Test reading data with timestamp column."""
        from ml_engine.connectors.odbc_connector import ODBCConnector

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_primary_timestamp.return_value = "timestamp"
        mock_read_sql.return_value = pd.DataFrame(
            {"id": [1, 2], "timestamp": ["2024-01-01", "2024-01-02"]},
        )

        # Create a real SQLAlchemy Table
        metadata = MetaData()
        table = SQLATable(
            "test_table",
            metadata,
            Column("id", Integer),
            Column("timestamp", String),
        )

        spec = ConnectorSpec.model_validate(MOCK_ODBC_CONNECTOR_SPEC)
        connector = ODBCConnector(spec, logger)
        connector.metadata = metadata

        # Patch Table autoload to return our table
        with patch("ml_engine.connectors.odbc_connector.Table", return_value=table):
            dataset = Dataset.model_validate(BASE_DATASET)
            result = connector.read(dataset, start_timestamp, end_timestamp)

        assert isinstance(result, pd.DataFrame)
        mock_read_sql.assert_called_once()

    @patch("ml_engine.connectors.odbc_connector.create_engine")
    @patch("ml_engine.connectors.odbc_connector.pd.read_sql")
    @patch("ml_engine.connectors.odbc_connector.primary_timestamp_col_name")
    def test_read_without_timestamp_column(
        self,
        mock_primary_timestamp,
        mock_read_sql,
        mock_create_engine,
    ):
        """Test reading data without timestamp column."""
        from ml_engine.connectors.odbc_connector import ODBCConnector

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_primary_timestamp.side_effect = ValueError("No timestamp column")
        mock_read_sql.return_value = pd.DataFrame({"id": [1, 2]})

        # Create a real SQLAlchemy Table
        metadata = MetaData()
        table = SQLATable(
            "test_table",
            metadata,
            Column("id", Integer),
        )

        spec = ConnectorSpec.model_validate(MOCK_ODBC_CONNECTOR_SPEC)
        connector = ODBCConnector(spec, logger)
        connector.metadata = metadata

        # Patch Table autoload to return our table
        with patch("ml_engine.connectors.odbc_connector.Table", return_value=table):
            dataset = Dataset.model_validate(NO_TS_DATASET)
            # Add pagination options since no timestamp column
            pagination = ConnectorPaginationOptions(page=1, page_size=10)
            result = connector.read(
                dataset,
                start_timestamp,
                end_timestamp,
                pagination_options=pagination,
            )

        assert isinstance(result, pd.DataFrame)
        mock_read_sql.assert_called_once()

    @patch("ml_engine.connectors.odbc_connector.create_engine")
    def test_read_missing_dataset_locator(self, mock_create_engine):
        """Test reading data with missing dataset locator."""
        from ml_engine.connectors.odbc_connector import ODBCConnector

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        spec = ConnectorSpec.model_validate(MOCK_ODBC_CONNECTOR_SPEC)
        connector = ODBCConnector(spec, logger)

        # Create dataset without locator
        invalid_dataset = BASE_DATASET.copy()
        invalid_dataset["dataset_locator"] = None
        dataset = Dataset.model_validate(invalid_dataset)

        with pytest.raises(ValueError, match="has no locator"):
            connector.read(dataset, start_timestamp, end_timestamp)

    @patch("ml_engine.connectors.odbc_connector.create_engine")
    @patch("ml_engine.connectors.odbc_connector.pd.read_sql")
    @patch("ml_engine.connectors.odbc_connector.primary_timestamp_col_name")
    def test_read_with_pagination(
        self,
        mock_primary_timestamp,
        mock_read_sql,
        mock_create_engine,
    ):
        """Test reading data with pagination."""
        from ml_engine.connectors.odbc_connector import ODBCConnector

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_primary_timestamp.return_value = "timestamp"
        mock_read_sql.return_value = pd.DataFrame({"id": [1, 2]})

        # Create a real SQLAlchemy Table
        metadata = MetaData()
        table = SQLATable(
            "test_table",
            metadata,
            Column("id", Integer),
            Column("timestamp", String),
        )

        spec = ConnectorSpec.model_validate(MOCK_ODBC_CONNECTOR_SPEC)
        connector = ODBCConnector(spec, logger)
        connector.metadata = metadata

        # Patch Table autoload to return our table
        with patch("ml_engine.connectors.odbc_connector.Table", return_value=table):
            dataset = Dataset.model_validate(BASE_DATASET)
            pagination = ConnectorPaginationOptions(page=2, page_size=10)
            result = connector.read(
                dataset,
                start_timestamp,
                end_timestamp,
                pagination_options=pagination,
            )

        assert isinstance(result, pd.DataFrame)
        mock_read_sql.assert_called_once()

    @patch("ml_engine.connectors.odbc_connector.create_engine")
    @patch("ml_engine.connectors.odbc_connector.pd.read_sql")
    @patch("ml_engine.connectors.odbc_connector.primary_timestamp_col_name")
    def test_read_with_filters(
        self,
        mock_primary_timestamp,
        mock_read_sql,
        mock_create_engine,
    ):
        """Test reading data with filters."""
        from ml_engine.connectors.odbc_connector import ODBCConnector

        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_primary_timestamp.return_value = "timestamp"
        mock_read_sql.return_value = pd.DataFrame({"id": [1], "status": ["active"]})

        # Create a real SQLAlchemy Table
        metadata = MetaData()
        table = SQLATable(
            "test_table",
            metadata,
            Column("id", Integer),
            Column("timestamp", String),
            Column("status", String),
        )

        spec = ConnectorSpec.model_validate(MOCK_ODBC_CONNECTOR_SPEC)
        connector = ODBCConnector(spec, logger)
        connector.metadata = metadata

        # Patch Table autoload to return our table
        with patch("ml_engine.connectors.odbc_connector.Table", return_value=table):
            dataset = Dataset.model_validate(BASE_DATASET)
            filters = [
                DataResultFilter(field_name="status", op="equals", value="active"),
                DataResultFilter(field_name="id", op="greater_than", value=0),
            ]
            result = connector.read(
                dataset,
                start_timestamp,
                end_timestamp,
                filters=filters,
            )

        assert isinstance(result, pd.DataFrame)
        mock_read_sql.assert_called_once()

    @patch("ml_engine.connectors.odbc_connector.create_engine")
    def test_engine_creation_failure(self, mock_create_engine):
        """Test handling of engine creation failure."""
        from ml_engine.connectors.odbc_connector import ODBCConnector

        mock_create_engine.side_effect = Exception("Engine creation failed")

        spec = ConnectorSpec.model_validate(MOCK_ODBC_CONNECTOR_SPEC)

        with pytest.raises(Exception, match="Engine creation failed"):
            ODBCConnector(spec, logger)
