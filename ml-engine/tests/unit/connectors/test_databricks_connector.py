"""
Unit tests for the Databricks connector functionality.
"""

import logging
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from uuid import uuid4

import pandas as pd
import pytest
from arthur_client.api_bindings import (
    ConnectorCheckOutcome,
    ConnectorSpec,
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
)
from arthur_common.models.enums import (
    DatabricksConnectorAuthenticatorMethods,
)
from mock_data.connector_helpers import mock_databricks_connector_spec

from connectors.databricks_connector import (
    CONNECTION_METHOD_ODBC,
    CONNECTION_METHOD_SQL_CONNECTOR,
    DatabricksConnector,
)

logger = logging.getLogger("databricks_test_logger")


def _make_connector_spec(**overrides):
    """Build a ConnectorSpec-like object for Databricks (Mock with .fields and .connector_type)."""
    spec = mock_databricks_connector_spec(
        **{k: v for k, v in overrides.items() if k != "fields"},
    )
    if "fields" in overrides:
        spec["fields"] = overrides["fields"]
    # ConnectorSpec expects .connector_type and .fields; .fields items have .key and .value
    mock_spec = Mock(spec=ConnectorSpec)
    mock_spec.connector_type = Mock(value="databricks")
    mock_spec.fields = [Mock(key=f["key"], value=f["value"]) for f in spec["fields"]]
    return mock_spec


def _make_dataset_with_timestamp(table_name: str = "test_table"):
    return Mock(
        spec=Dataset,
        id=str(uuid4()),
        dataset_locator=DatasetLocator(
            fields=[
                DatasetLocatorField(
                    key=ODBC_CONNECTOR_TABLE_NAME_FIELD,
                    value=table_name,
                ),
            ],
        ),
        dataset_schema=DatasetSchema(
            alias_mask={},
            columns=[
                DatasetColumn(
                    id=str(uuid4()),
                    source_name="ts",
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
            column_names={"ts": "ts"},
        ),
    )


class TestDatabricksConnectorConfig:
    """Test config parsing and validation."""

    def test_init_sql_connector_pat(self):
        with patch("connectors.databricks_connector.create_engine") as mock_engine:
            mock_engine.return_value = Mock()
            spec = _make_connector_spec(
                connection_method=CONNECTION_METHOD_SQL_CONNECTOR,
                authenticator=DatabricksConnectorAuthenticatorMethods.DATABRICKS_PAT,
                access_token="token123",
            )
            conn = DatabricksConnector(spec, logger)
            assert conn.connection_method == CONNECTION_METHOD_SQL_CONNECTOR
            assert conn.access_token == "token123"
            assert conn.server_hostname == "dbc-xxx.cloud.databricks.com"
            assert conn.http_path == "/sql/1.0/warehouses/yyy"

    def test_init_oauth_token_passthrough(self):
        with patch("connectors.databricks_connector.create_engine") as mock_engine:
            mock_engine.return_value = Mock()
            spec = _make_connector_spec(
                authenticator=DatabricksConnectorAuthenticatorMethods.DATABRICKS_OAUTH_TOKEN_PASSTHROUGH,
                access_token="oauth_token_xyz",
            )
            conn = DatabricksConnector(spec, logger)
            assert (
                conn.authenticator
                == DatabricksConnectorAuthenticatorMethods.DATABRICKS_OAUTH_TOKEN_PASSTHROUGH
            )
            assert conn.access_token == "oauth_token_xyz"

    def test_init_missing_access_token_succeeds(self):
        """Test that connector can be created without access_token (will use env vars)."""
        with patch("connectors.databricks_connector.create_engine") as mock_engine:
            mock_engine.return_value = Mock()
            spec_dict = mock_databricks_connector_spec(access_token="token")
            spec_dict["fields"] = [
                f for f in spec_dict["fields"] if f["key"] != "access_token"
            ]
            spec = Mock()
            spec.connector_type = Mock(value="databricks")
            spec.fields = [
                Mock(key=f["key"], value=f["value"]) for f in spec_dict["fields"]
            ]
            conn = DatabricksConnector(spec, logger)
            assert conn.access_token is None
            # Verify the connection string was created without token (will use env vars)
            mock_engine.assert_called_once()

    def test_init_invalid_authenticator_raises(self):
        spec_dict = mock_databricks_connector_spec()
        for f in spec_dict["fields"]:
            if f["key"] == "authenticator":
                f["value"] = "invalid_auth"
                break
        spec = Mock()
        spec.connector_type = Mock(value="databricks")
        spec.fields = [
            Mock(key=f["key"], value=f["value"]) for f in spec_dict["fields"]
        ]
        with pytest.raises(ValueError, match="Authenticator must be"):
            DatabricksConnector(spec, logger)

    def test_sqlalchemy_connection_string_with_token(self):
        """Test that SQLAlchemy connection string includes token when provided."""
        with patch("connectors.databricks_connector.create_engine") as mock_engine:
            mock_engine.return_value = Mock()
            spec = _make_connector_spec(
                connection_method=CONNECTION_METHOD_SQL_CONNECTOR,
                access_token="test_token_123",
            )
            DatabricksConnector(spec, logger)
            # Verify connection string includes token
            call_args = mock_engine.call_args[0][0]
            assert "token:test_token_123@" in call_args

    def test_sqlalchemy_connection_string_without_token(self):
        """Test that SQLAlchemy connection string omits token when not provided."""
        with patch("connectors.databricks_connector.create_engine") as mock_engine:
            mock_engine.return_value = Mock()
            spec_dict = mock_databricks_connector_spec(access_token="token")
            spec_dict["fields"] = [
                f for f in spec_dict["fields"] if f["key"] != "access_token"
            ]
            spec = Mock()
            spec.connector_type = Mock(value="databricks")
            spec.fields = [
                Mock(key=f["key"], value=f["value"]) for f in spec_dict["fields"]
            ]
            DatabricksConnector(spec, logger)
            # Verify connection string does NOT include token part
            call_args = mock_engine.call_args[0][0]
            assert "token:" not in call_args
            assert call_args.startswith("databricks://dbc-")


class TestDatabricksConnectorSQLBackend:
    """Test SQL connector backend (SQLAlchemy)."""

    @patch("connectors.databricks_connector.create_engine")
    def test_test_connection_success(self, mock_create_engine):
        mock_engine = Mock()
        mock_conn = Mock()
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=None)
        mock_create_engine.return_value = mock_engine

        spec = _make_connector_spec(connection_method=CONNECTION_METHOD_SQL_CONNECTOR)
        conn = DatabricksConnector(spec, logger)
        result = conn.test_connection()
        assert result.connection_check_outcome == ConnectorCheckOutcome.SUCCEEDED

    @patch("connectors.databricks_connector.create_engine")
    def test_test_connection_failure(self, mock_create_engine):
        mock_engine = Mock()
        mock_engine.connect.side_effect = Exception("Connection refused")
        mock_create_engine.return_value = mock_engine

        spec = _make_connector_spec(connection_method=CONNECTION_METHOD_SQL_CONNECTOR)
        conn = DatabricksConnector(spec, logger)
        result = conn.test_connection()
        assert result.connection_check_outcome == ConnectorCheckOutcome.FAILED
        assert "Connection refused" in (result.failure_reason or "")

    @patch("connectors.databricks_connector.create_engine")
    def test_read_builds_query_and_returns_dataframe(self, mock_create_engine):
        mock_engine = Mock()
        mock_conn = Mock()
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=None)
        mock_create_engine.return_value = mock_engine

        expected_df = pd.DataFrame([{"ts": datetime.now(timezone.utc), "x": 1}])
        with patch(
            "connectors.databricks_connector.pd.read_sql",
            return_value=expected_df,
        ):
            spec = _make_connector_spec(
                connection_method=CONNECTION_METHOD_SQL_CONNECTOR,
            )
            conn = DatabricksConnector(spec, logger)
            dataset = _make_dataset_with_timestamp()
            start = datetime(2025, 1, 1, tzinfo=timezone.utc)
            end = datetime(2025, 1, 2, tzinfo=timezone.utc)
            result = conn.read(dataset, start, end)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.iloc[0]["x"] == 1

    @patch("connectors.databricks_connector.create_engine")
    def test_list_datasets_returns_put_available_datasets(self, mock_create_engine):
        mock_engine = Mock()
        mock_inspector = Mock()
        mock_inspector.get_table_names.return_value = ["t1", "t2"]
        with patch(
            "connectors.databricks_connector.inspect",
            return_value=mock_inspector,
        ):
            mock_create_engine.return_value = mock_engine
            spec = _make_connector_spec(
                connection_method=CONNECTION_METHOD_SQL_CONNECTOR,
            )
            conn = DatabricksConnector(spec, logger)
            result = conn.list_datasets()
        assert len(result.available_datasets) == 2
        names = {d.name for d in result.available_datasets}
        assert names == {"t1", "t2"}
        for d in result.available_datasets:
            locator_fields = {f.key: f.value for f in d.dataset_locator.fields}
            assert ODBC_CONNECTOR_TABLE_NAME_FIELD in locator_fields


class TestDatabricksConnectorODBCBackend:
    """Test ODBC backend (pyodbc)."""

    @patch("pyodbc.connect")
    def test_test_connection_success(self, mock_pyodbc_connect):
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)
        mock_pyodbc_connect.return_value = mock_conn

        spec = _make_connector_spec(connection_method=CONNECTION_METHOD_ODBC)
        conn = DatabricksConnector(spec, logger)
        result = conn.test_connection()
        assert result.connection_check_outcome == ConnectorCheckOutcome.SUCCEEDED

    @patch("pyodbc.connect")
    def test_test_connection_failure(self, mock_pyodbc_connect):
        mock_pyodbc_connect.side_effect = Exception("ODBC error")

        spec = _make_connector_spec(connection_method=CONNECTION_METHOD_ODBC)
        conn = DatabricksConnector(spec, logger)
        result = conn.test_connection()
        assert result.connection_check_outcome == ConnectorCheckOutcome.FAILED
        assert "ODBC error" in (result.failure_reason or "")

    @patch("pyodbc.connect")
    def test_read_returns_dataframe(self, mock_pyodbc_connect):
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.description = [("ts",), ("x",)]
        mock_cursor.fetchall.return_value = [(datetime.now(timezone.utc), 1)]
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)
        mock_pyodbc_connect.return_value = mock_conn

        spec = _make_connector_spec(connection_method=CONNECTION_METHOD_ODBC)
        conn = DatabricksConnector(spec, logger)
        dataset = _make_dataset_with_timestamp()
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 2, tzinfo=timezone.utc)
        result = conn.read(dataset, start, end)
        assert isinstance(result, pd.DataFrame)
        assert list(result.columns) == ["ts", "x"]
        assert len(result) == 1

    @patch("pyodbc.connect")
    def test_list_datasets_returns_put_available_datasets(self, mock_pyodbc_connect):
        mock_conn = Mock()
        mock_cursor = Mock()
        # cursor.tables() returns TABLE_CAT, TABLE_SCHEM, TABLE_NAME, TABLE_TYPE, REMARKS
        mock_cursor.fetchall.return_value = [
            ("cat", "schema_a", "table1", "TABLE", None),
            ("cat", "schema_a", "table2", "TABLE", None),
        ]
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)
        mock_pyodbc_connect.return_value = mock_conn

        spec = _make_connector_spec(connection_method=CONNECTION_METHOD_ODBC)
        conn = DatabricksConnector(spec, logger)
        result = conn.list_datasets()
        assert len(result.available_datasets) == 2
        names = {d.name for d in result.available_datasets}
        assert names == {"table1", "table2"}
        for d in result.available_datasets:
            locator_fields = {f.key: f.value for f in d.dataset_locator.fields}
            assert ODBC_CONNECTOR_TABLE_NAME_FIELD in locator_fields
