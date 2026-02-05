"""
Unit tests for the Databricks connector functionality.
"""

import logging
import os
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
    DATABRICKS_DATASET_CATALOG_FIELD,
    DATABRICKS_DATASET_SCHEMA_FIELD,
    ODBC_CONNECTOR_TABLE_NAME_FIELD,
)
from mock_data.connector_helpers import mock_databricks_connector_spec

from connectors.databricks_connector import DatabricksConnector

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


def _make_dataset_with_timestamp(
    table_name: str = "test_table",
    catalog: str = "test_catalog",
    schema: str = "test_schema",
):
    return Mock(
        spec=Dataset,
        id=str(uuid4()),
        dataset_locator=DatasetLocator(
            fields=[
                DatasetLocatorField(
                    key=DATABRICKS_DATASET_CATALOG_FIELD,
                    value=catalog,
                ),
                DatasetLocatorField(
                    key=DATABRICKS_DATASET_SCHEMA_FIELD,
                    value=schema,
                ),
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


class TestDatabricksConnectorAuthDetection:
    """Test authentication method auto-detection."""

    def test_auth_auto_detection_oauth_m2m(self):
        """Verify OAuth M2M is auto-detected when client_id+secret provided."""
        with patch("connectors.databricks_connector.create_engine") as mock_engine:
            mock_engine.return_value = Mock()
            with patch(
                "connectors.databricks_connector.oauth_service_principal"
            ) as mock_oauth:
                mock_oauth.return_value.oauth_token.return_value.access_token = (
                    "fresh_token"
                )
                spec = _make_connector_spec(
                    access_token=None,
                    client_id="test_client_id",
                    client_secret="test_client_secret",
                )
                conn = DatabricksConnector(spec, logger)
                assert conn._auth_method == "oauth_m2m"
                assert conn.client_id.get_secret_value() == "test_client_id"
                assert conn.client_secret.get_secret_value() == "test_client_secret"

    def test_auth_auto_detection_pat(self):
        """Verify PAT is auto-detected when only access_token provided."""
        with patch("connectors.databricks_connector.create_engine") as mock_engine:
            mock_engine.return_value = Mock()
            spec = _make_connector_spec(
                access_token="test_pat_token",
                client_id=None,
                client_secret=None,
            )
            conn = DatabricksConnector(spec, logger)
            assert conn._auth_method == "pat"
            assert conn.access_token.get_secret_value() == "test_pat_token"

    def test_auth_auto_detection_prefers_oauth_m2m(self):
        """When both credentials provided, OAuth M2M takes precedence."""
        with patch("connectors.databricks_connector.create_engine") as mock_engine:
            mock_engine.return_value = Mock()
            with patch(
                "connectors.databricks_connector.oauth_service_principal"
            ) as mock_oauth:
                mock_oauth.return_value.oauth_token.return_value.access_token = (
                    "fresh_token"
                )
                spec = _make_connector_spec(
                    access_token="test_pat_token",
                    client_id="test_client_id",
                    client_secret="test_client_secret",
                )
                conn = DatabricksConnector(spec, logger)
                assert conn._auth_method == "oauth_m2m"

    def test_no_credentials_raises(self):
        """Verify error when no credentials provided."""
        spec_dict = mock_databricks_connector_spec(access_token=None)
        spec = Mock()
        spec.connector_type = Mock(value="databricks")
        spec.fields = [
            Mock(key=f["key"], value=f["value"]) for f in spec_dict["fields"]
        ]
        with pytest.raises(ValueError, match="No Databricks credentials provided"):
            DatabricksConnector(spec, logger)

    def test_oauth_m2m_missing_client_secret_raises(self):
        """Verify error when client_id without client_secret."""
        spec_dict = mock_databricks_connector_spec(
            access_token=None,
            client_id="test_client_id",
            client_secret=None,
        )
        spec = Mock()
        spec.connector_type = Mock(value="databricks")
        spec.fields = [
            Mock(key=f["key"], value=f["value"]) for f in spec_dict["fields"]
        ]
        with pytest.raises(ValueError, match="OAuth M2M requires both"):
            DatabricksConnector(spec, logger)


class TestDatabricksConnectorEnvVars:
    """Test environment variable fallback."""

    def test_env_var_fallback_for_credentials(self):
        """Test that env vars are used when config fields not provided."""
        with patch.dict(
            os.environ,
            {
                "DATABRICKS_HOST": "env-host.databricks.com",
                "DATABRICKS_HTTP_PATH": "/env/path",
                "DATABRICKS_TOKEN": "env_token",
            },
        ):
            spec_dict = mock_databricks_connector_spec(access_token=None)
            # Remove all credential and connection fields
            spec_dict["fields"] = []
            spec = Mock()
            spec.connector_type = Mock(value="databricks")
            spec.fields = []

            with patch("connectors.databricks_connector.create_engine") as mock_engine:
                mock_engine.return_value = Mock()
                conn = DatabricksConnector(spec, logger)
                assert conn.server_hostname == "env-host.databricks.com"
                assert conn.http_path == "/env/path"
                assert conn.access_token.get_secret_value() == "env_token"
                assert conn._auth_method == "pat"

    def test_env_var_fallback_oauth_m2m(self):
        """Test OAuth M2M env var fallback."""
        with patch.dict(
            os.environ,
            {
                "DATABRICKS_HOST": "env-host.databricks.com",
                "DATABRICKS_HTTP_PATH": "/env/path",
                "DATABRICKS_CLIENT_ID": "env_client_id",
                "DATABRICKS_CLIENT_SECRET": "env_client_secret",
            },
        ):
            spec = Mock()
            spec.connector_type = Mock(value="databricks")
            spec.fields = []

            with patch("connectors.databricks_connector.create_engine") as mock_engine:
                mock_engine.return_value = Mock()
                with patch(
                    "connectors.databricks_connector.oauth_service_principal"
                ) as mock_oauth:
                    mock_oauth.return_value.oauth_token.return_value.access_token = (
                        "fresh_token"
                    )
                    conn = DatabricksConnector(spec, logger)
                    assert conn.client_id.get_secret_value() == "env_client_id"
                    assert (
                        conn.client_secret.get_secret_value() == "env_client_secret"
                    )
                    assert conn._auth_method == "oauth_m2m"


class TestDatabricksConnectorOAuthM2M:
    """Test OAuth M2M token refresh functionality."""

    def test_oauth_m2m_token_refresh(self):
        """Mock oauth_service_principal and verify fresh token fetching."""
        with patch("connectors.databricks_connector.create_engine") as mock_engine:
            mock_engine.return_value = Mock()
            with patch(
                "connectors.databricks_connector.oauth_service_principal"
            ) as mock_oauth:
                mock_token = Mock()
                mock_token.access_token = "fresh_oauth_token"
                mock_oauth.return_value.oauth_token.return_value = mock_token

                spec = _make_connector_spec(
                    access_token=None,
                    client_id="test_client",
                    client_secret="test_secret",
                )
                conn = DatabricksConnector(spec, logger)

                # Verify engine was created with fresh token
                call_args = mock_engine.call_args[0][0]
                assert "token:fresh_oauth_token@" in call_args
                mock_oauth.assert_called_once()

    def test_read_retry_on_auth_failure(self):
        """Mock 401 error, verify engine recreation and retry."""
        with patch("connectors.databricks_connector.create_engine") as mock_engine:
            with patch(
                "connectors.databricks_connector.oauth_service_principal"
            ) as mock_oauth:
                mock_token = Mock()
                mock_token.access_token = "token1"
                mock_oauth.return_value.oauth_token.return_value = mock_token

                spec = _make_connector_spec(
                    access_token=None,
                    client_id="test_client",
                    client_secret="test_secret",
                )

                # First call returns engine that fails with 401
                mock_engine_instance = Mock()
                mock_conn = Mock()
                mock_conn.execute.side_effect = [
                    Exception("401 unauthorized"),
                    Mock(),  # Second attempt succeeds
                ]
                mock_engine_instance.connect.return_value.__enter__ = Mock(
                    return_value=mock_conn
                )
                mock_engine_instance.connect.return_value.__exit__ = Mock(
                    return_value=None
                )
                mock_engine.return_value = mock_engine_instance

                conn = DatabricksConnector(spec, logger)
                dataset = _make_dataset_with_timestamp()

                # Simulate read with fresh token on retry
                mock_token.access_token = "token2"
                with patch("connectors.databricks_connector.pd.read_sql") as mock_read:
                    mock_read.return_value = pd.DataFrame([{"x": 1}])
                    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
                    end = datetime(2025, 1, 2, tzinfo=timezone.utc)
                    conn.read(dataset, start, end)

                # Verify engine was recreated (disposed + new create call)
                assert mock_engine_instance.dispose.called


class TestDatabricksConnectorConnection:
    """Test connection and basic SQL operations."""

    @patch("connectors.databricks_connector.create_engine")
    def test_test_connection_validates_query_access(self, mock_create_engine):
        """Test connection verifies we can query at least one table."""
        mock_engine = Mock()
        mock_conn = Mock()
        # Mock both version query and information_schema query
        mock_conn.execute.side_effect = [
            Mock(fetchone=Mock(return_value=["14.3.0"])),  # version query
            Mock(),  # information_schema query
        ]
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=None)
        mock_create_engine.return_value = mock_engine

        spec = _make_connector_spec()
        conn = DatabricksConnector(spec, logger)
        result = conn.test_connection()
        assert result.connection_check_outcome == ConnectorCheckOutcome.SUCCEEDED

    @patch("connectors.databricks_connector.create_engine")
    def test_test_connection_failure_auth_error(self, mock_create_engine):
        """Test connection failure with auth error message."""
        mock_engine = Mock()
        mock_engine.connect.side_effect = Exception("401 token expired")
        mock_create_engine.return_value = mock_engine

        spec = _make_connector_spec()
        conn = DatabricksConnector(spec, logger)
        result = conn.test_connection()
        assert result.connection_check_outcome == ConnectorCheckOutcome.FAILED
        assert "Authentication failed" in (result.failure_reason or "")

    @patch("connectors.databricks_connector.create_engine")
    def test_test_connection_failure_permission_error(self, mock_create_engine):
        """Test connection failure with permission error message."""
        mock_engine = Mock()
        mock_conn = Mock()
        mock_conn.execute.side_effect = [
            Mock(fetchone=Mock(return_value=["14.3.0"])),
            Exception("permission denied on catalog"),
        ]
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=None)
        mock_create_engine.return_value = mock_engine

        spec = _make_connector_spec()
        conn = DatabricksConnector(spec, logger)
        result = conn.test_connection()
        assert result.connection_check_outcome == ConnectorCheckOutcome.FAILED
        assert "Cannot query tables" in (result.failure_reason or "")


class TestDatabricksConnectorDatasetDiscovery:
    """Test dataset discovery across catalogs."""

    @patch("connectors.databricks_connector.create_engine")
    @patch("connectors.databricks_connector.WorkspaceClient")
    def test_list_datasets_scans_all_catalogs(
        self, mock_workspace_client_class, mock_create_engine
    ):
        """Verify multi-catalog discovery."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        # Setup workspace client mock
        mock_client = Mock()
        mock_workspace_client_class.return_value = mock_client

        # Mock catalog structure
        catalog1 = Mock()
        catalog1.name = "catalog1"
        catalog2 = Mock()
        catalog2.name = "catalog2"
        mock_client.catalogs.list.return_value = [catalog1, catalog2]

        schema1 = Mock()
        schema1.name = "schema1"
        mock_client.schemas.list.return_value = [schema1]

        table1 = Mock()
        table1.name = "table1"
        table2 = Mock()
        table2.name = "table2"
        mock_client.tables.list.return_value = [table1, table2]

        # Mock query permission checks (all succeed)
        mock_conn = Mock()
        mock_conn.execute.return_value = Mock()
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=None)

        spec = _make_connector_spec()
        conn = DatabricksConnector(spec, logger)
        result = conn.list_datasets()

        # Should find 4 tables (2 catalogs × 1 schema × 2 tables)
        assert len(result.available_datasets) == 4

    @patch("connectors.databricks_connector.create_engine")
    @patch("connectors.databricks_connector.WorkspaceClient")
    def test_list_datasets_returns_qualified_names(
        self, mock_workspace_client_class, mock_create_engine
    ):
        """Check catalog.schema.table format."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_client = Mock()
        mock_workspace_client_class.return_value = mock_client

        catalog = Mock()
        catalog.name = "test_catalog"
        mock_client.catalogs.list.return_value = [catalog]

        schema = Mock()
        schema.name = "test_schema"
        mock_client.schemas.list.return_value = [schema]

        table = Mock()
        table.name = "test_table"
        mock_client.tables.list.return_value = [table]

        # Mock successful query permission check
        mock_conn = Mock()
        mock_conn.execute.return_value = Mock()
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=None)

        spec = _make_connector_spec()
        conn = DatabricksConnector(spec, logger)
        result = conn.list_datasets()

        assert len(result.available_datasets) == 1
        assert result.available_datasets[0].name == "test_catalog.test_schema.test_table"

    @patch("connectors.databricks_connector.create_engine")
    @patch("connectors.databricks_connector.WorkspaceClient")
    def test_list_datasets_populates_locator_fields(
        self, mock_workspace_client_class, mock_create_engine
    ):
        """Verify locator has catalog, schema, table_name (all required)."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_client = Mock()
        mock_workspace_client_class.return_value = mock_client

        catalog = Mock()
        catalog.name = "my_catalog"
        mock_client.catalogs.list.return_value = [catalog]

        schema = Mock()
        schema.name = "my_schema"
        mock_client.schemas.list.return_value = [schema]

        table = Mock()
        table.name = "my_table"
        mock_client.tables.list.return_value = [table]

        # Mock successful query permission check
        mock_conn = Mock()
        mock_conn.execute.return_value = Mock()
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=None)

        spec = _make_connector_spec()
        conn = DatabricksConnector(spec, logger)
        result = conn.list_datasets()

        assert len(result.available_datasets) == 1
        locator_fields = {
            f.key: f.value for f in result.available_datasets[0].dataset_locator.fields
        }
        assert locator_fields[DATABRICKS_DATASET_CATALOG_FIELD] == "my_catalog"
        assert locator_fields[DATABRICKS_DATASET_SCHEMA_FIELD] == "my_schema"
        assert locator_fields[ODBC_CONNECTOR_TABLE_NAME_FIELD] == "my_table"

    @patch("connectors.databricks_connector.create_engine")
    @patch("connectors.databricks_connector.WorkspaceClient")
    def test_list_datasets_validates_query_permissions(
        self, mock_workspace_client_class, mock_create_engine
    ):
        """Verify LIMIT 0 query filters unqueryable tables."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        mock_client = Mock()
        mock_workspace_client_class.return_value = mock_client

        catalog = Mock()
        catalog.name = "catalog1"
        mock_client.catalogs.list.return_value = [catalog]

        schema = Mock()
        schema.name = "schema1"
        mock_client.schemas.list.return_value = [schema]

        table1 = Mock()
        table1.name = "queryable_table"
        table2 = Mock()
        table2.name = "forbidden_table"
        mock_client.tables.list.return_value = [table1, table2]

        # Mock query permission checks: first succeeds, second fails
        mock_conn = Mock()
        mock_conn.execute.side_effect = [
            Mock(),  # queryable_table succeeds
            Exception("permission denied"),  # forbidden_table fails
        ]
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=None)

        spec = _make_connector_spec()
        conn = DatabricksConnector(spec, logger)
        result = conn.list_datasets()

        # Only queryable_table should be returned
        assert len(result.available_datasets) == 1
        assert result.available_datasets[0].name == "catalog1.schema1.queryable_table"

    @patch("connectors.databricks_connector.create_engine")
    def test_can_query_table(self, mock_create_engine):
        """Test permission validation helper method."""
        mock_engine = Mock()
        mock_conn = Mock()
        mock_conn.execute.return_value = Mock()
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=None)
        mock_create_engine.return_value = mock_engine

        spec = _make_connector_spec()
        conn = DatabricksConnector(spec, logger)

        # Should succeed
        result = conn._can_query_table("catalog", "schema", "table")
        assert result is True

        # Verify LIMIT 0 query was executed
        mock_conn.execute.assert_called()

    @patch("connectors.databricks_connector.create_engine")
    def test_can_query_table_permission_denied(self, mock_create_engine):
        """Test permission validation returns False on error."""
        mock_engine = Mock()
        mock_conn = Mock()
        mock_conn.execute.side_effect = Exception("permission denied")
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=None)
        mock_create_engine.return_value = mock_engine

        spec = _make_connector_spec()
        conn = DatabricksConnector(spec, logger)

        result = conn._can_query_table("catalog", "schema", "forbidden_table")
        assert result is False


class TestDatabricksConnectorRead:
    """Test data reading functionality."""

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
            spec = _make_connector_spec()
            conn = DatabricksConnector(spec, logger)
            dataset = _make_dataset_with_timestamp()
            start = datetime(2025, 1, 1, tzinfo=timezone.utc)
            end = datetime(2025, 1, 2, tzinfo=timezone.utc)
            result = conn.read(dataset, start, end)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.iloc[0]["x"] == 1


class TestDatabricksConnectorQualifiedNames:
    """Test qualified table name building with proper escaping."""

    @patch("connectors.databricks_connector.create_engine")
    def test_build_qualified_table_name(self, mock_create_engine):
        """Test that _build_qualified_table_name properly escapes identifiers."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        spec = _make_connector_spec()
        conn = DatabricksConnector(spec, logger)

        # Test simple names
        qualified = conn._build_qualified_table_name("catalog1", "schema1", "table1")
        assert qualified == "`catalog1`.`schema1`.`table1`"

    @patch("connectors.databricks_connector.create_engine")
    def test_build_qualified_table_name_with_special_chars(self, mock_create_engine):
        """Test escaping of table names with special characters."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        spec = _make_connector_spec()
        conn = DatabricksConnector(spec, logger)

        # Test names with backticks (should be escaped)
        qualified = conn._build_qualified_table_name("cat`log", "sche`ma", "tab`le")
        assert qualified == "`cat\\`log`.`sche\\`ma`.`tab\\`le`"

    @patch("connectors.databricks_connector.create_engine")
    def test_get_qualified_table_name_from_locator(self, mock_create_engine):
        """Test that _get_qualified_table_name extracts from locator correctly."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        spec = _make_connector_spec()
        conn = DatabricksConnector(spec, logger)

        locator = {
            DATABRICKS_DATASET_CATALOG_FIELD: "my_catalog",
            DATABRICKS_DATASET_SCHEMA_FIELD: "my_schema",
            ODBC_CONNECTOR_TABLE_NAME_FIELD: "my_table",
        }

        qualified = conn._get_qualified_table_name(locator)
        assert qualified == "`my_catalog`.`my_schema`.`my_table`"


class TestDatabricksConnectorConnectionRobust:
    """Test robust connection validation."""

    @patch("connectors.databricks_connector.create_engine")
    @patch("connectors.databricks_connector.WorkspaceClient")
    def test_test_connection_finds_accessible_table(
        self, mock_workspace_client_class, mock_create_engine
    ):
        """Test that test_connection successfully finds and queries an accessible table."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        # Mock version query
        mock_conn = Mock()
        version_result = Mock()
        version_result.fetchone.return_value = ["14.3.0"]
        mock_conn.execute.side_effect = [
            version_result,  # version query
            Mock(),  # can_query_table LIMIT 0 query
        ]
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=None)

        # Mock WorkspaceClient
        mock_client = Mock()
        mock_workspace_client_class.return_value = mock_client

        catalog = Mock()
        catalog.name = "test_catalog"
        mock_client.catalogs.list.return_value = [catalog]

        schema = Mock()
        schema.name = "test_schema"
        mock_client.schemas.list.return_value = [schema]

        table = Mock()
        table.name = "test_table"
        mock_client.tables.list.return_value = [table]

        spec = _make_connector_spec()
        conn = DatabricksConnector(spec, logger)
        result = conn.test_connection()

        assert result.connection_check_outcome == ConnectorCheckOutcome.SUCCEEDED
        # Verify it tried to list catalogs
        mock_client.catalogs.list.assert_called_once()

    @patch("connectors.databricks_connector.create_engine")
    @patch("connectors.databricks_connector.WorkspaceClient")
    def test_test_connection_succeeds_without_queryable_tables(
        self, mock_workspace_client_class, mock_create_engine
    ):
        """Test that connection succeeds even if no queryable tables found (warning logged)."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        # Mock version query succeeds
        mock_conn = Mock()
        version_result = Mock()
        version_result.fetchone.return_value = ["14.3.0"]
        mock_conn.execute.side_effect = [
            version_result,  # version query
            Exception("permission denied"),  # can_query_table fails
        ]
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=None)

        # Mock WorkspaceClient with tables but permission denied on queries
        mock_client = Mock()
        mock_workspace_client_class.return_value = mock_client

        catalog = Mock()
        catalog.name = "test_catalog"
        mock_client.catalogs.list.return_value = [catalog]

        schema = Mock()
        schema.name = "test_schema"
        mock_client.schemas.list.return_value = [schema]

        table = Mock()
        table.name = "test_table"
        mock_client.tables.list.return_value = [table]

        spec = _make_connector_spec()
        conn = DatabricksConnector(spec, logger)
        result = conn.test_connection()

        # Should still succeed (connection works, just no queryable tables)
        assert result.connection_check_outcome == ConnectorCheckOutcome.SUCCEEDED
