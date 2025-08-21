"""
Unit tests for the connector factory functionality.
"""

from datetime import datetime, timezone
from unittest.mock import Mock, patch
from uuid import uuid4

from arthur_client.api_bindings import (
    ConnectorFieldDataType,
    ConnectorSpec,
    ConnectorType,
)
from ml_engine.connectors.connector_factory import ConnectorFactory
from ml_engine.connectors.odbc_connector import ODBCConnector
from ml_engine.connectors.snowflake_connector import SnowflakeConnector

# Mock ConnectorSpec for testing
MOCK_CONNECTOR_SPEC = {
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
    "id": str(uuid4()),
    "connector_type": ConnectorType.ODBC,
    "name": "Mock Connector Spec",
    "temporary": False,
    "fields": [
        {
            "key": "host",
            "value": "test-db.com",
            "is_sensitive": False,
            "d_type": ConnectorFieldDataType.STRING.value,
        },
        {
            "key": "database",
            "value": "test_db",
            "is_sensitive": False,
            "d_type": ConnectorFieldDataType.STRING.value,
        },
        {
            "key": "username",
            "value": "test_user",
            "is_sensitive": False,
            "d_type": ConnectorFieldDataType.STRING.value,
        },
        {
            "key": "password",
            "value": "test_pass",
            "is_sensitive": True,
            "d_type": ConnectorFieldDataType.STRING.value,
        },
        {
            "key": "dialect",
            "value": "generic odbc (pyodbc)",
            "is_sensitive": False,
            "d_type": ConnectorFieldDataType.STRING.value,
        },
    ],
    "last_updated_by_user": None,
    "connector_check_result": None,
    "project_id": str(uuid4()),
    "data_plane_id": str(uuid4()),
}


class TestConnectorFactory:
    """Test cases for ConnectorFactory."""

    @patch("ml_engine.connectors.odbc_connector.create_engine")
    def test_create_odbc_connector(self, mock_create_engine):
        """Test that factory creates ODBC connector for generic ODBC dialect."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        spec = ConnectorSpec.model_validate(MOCK_CONNECTOR_SPEC)
        logger = Mock()

        connector = ConnectorFactory.create_connector(spec, logger)

        assert isinstance(connector, ODBCConnector)

    @patch("ml_engine.connectors.snowflake_connector.create_engine")
    def test_create_snowflake_connector(self, mock_create_engine):
        """Test that factory creates Snowflake connector for Snowflake connector type."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        # Create spec with Snowflake connector type
        snowflake_spec = MOCK_CONNECTOR_SPEC.copy()
        snowflake_spec["connector_type"] = ConnectorType.SNOWFLAKE
        snowflake_spec["fields"] = [
            {
                "key": "host",
                "value": "test.snowflakecomputing.com",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "database",
                "value": "TEST_DB",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "username",
                "value": "test_user",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "password",
                "value": "test_pass",
                "is_sensitive": True,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "warehouse",
                "value": "TEST_WH",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "schema",
                "value": "PUBLIC",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
        ]

        spec = ConnectorSpec.model_validate(snowflake_spec)
        logger = Mock()

        connector = ConnectorFactory.create_connector(spec, logger)

        assert isinstance(connector, SnowflakeConnector)

    @patch("ml_engine.connectors.odbc_connector.create_engine")
    def test_create_default_connector(self, mock_create_engine):
        """Test that factory defaults to ODBC connector when connector type not found."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        # Create spec with unregistered connector type
        unknown_type_spec = MOCK_CONNECTOR_SPEC.copy()
        unknown_type_spec["connector_type"] = ConnectorType.SHIELD

        spec = ConnectorSpec.model_validate(unknown_type_spec)
        logger = Mock()

        connector = ConnectorFactory.create_connector(spec, logger)

        assert isinstance(connector, ODBCConnector)

    def test_get_available_connectors(self):
        """Test that factory returns correct mml_engineing of available connectors."""
        available = ConnectorFactory.get_available_connectors()

        assert "snowflake" in available
        assert "odbc" in available
        assert available["snowflake"] == "SnowflakeConnector"
        assert available["odbc"] == "ODBCConnector"

    def test_register_new_connector(self):
        """Test that new connectors can be registered with the factory."""

        class TestConnector(ODBCConnector):
            pass

        ConnectorFactory.register_connector(ConnectorType.SHIELD, TestConnector)

        available = ConnectorFactory.get_available_connectors()
        assert "shield" in available
        assert available["shield"] == "TestConnector"

        # Clean up
        del ConnectorFactory._connector_registry[ConnectorType.SHIELD]

    def test_factory_registry_structure(self):
        """Test that the factory registry has the expected structure."""
        registry = ConnectorFactory._connector_registry

        # Check that key connector types are present
        assert ConnectorType.SNOWFLAKE in registry
        assert ConnectorType.ODBC in registry

        # Check that they map to the right classes
        assert registry[ConnectorType.SNOWFLAKE] == SnowflakeConnector
        assert registry[ConnectorType.ODBC] == ODBCConnector
