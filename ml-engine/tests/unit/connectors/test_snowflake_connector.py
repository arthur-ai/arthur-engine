"""
Unit tests for the Snowflake connector functionality.
"""

from datetime import datetime, timezone
from unittest.mock import Mock, patch
from uuid import uuid4

from arthur_client.api_bindings import (
    ConnectorFieldDataType,
    ConnectorSpec,
    ConnectorType,
)
from arthur_common.models.enums import SnowflakeConnectorAuthenticatorMethods
from ml_engine.connectors.snowflake_connector import SnowflakeConnector

# Mock ConnectorSpec for Snowflake testing
MOCK_SNOWFLAKE_CONNECTOR_SPEC = {
    "created_at": datetime.now(timezone.utc),
    "updated_at": datetime.now(timezone.utc),
    "id": str(uuid4()),
    "connector_type": ConnectorType.SNOWFLAKE,
    "name": "Mock Snowflake Connector Spec",
    "temporary": False,
    "fields": [
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
        {
            "key": "role",
            "value": "TEST_ROLE",
            "is_sensitive": False,
            "d_type": ConnectorFieldDataType.STRING.value,
        },
        {
            "key": "authenticator",
            "value": SnowflakeConnectorAuthenticatorMethods.SNOWFLAKE_PASSWORD,
            "is_sensitive": False,
            "d_type": ConnectorFieldDataType.STRING.value,
        },
    ],
    "last_updated_by_user": None,
    "connector_check_result": None,
    "project_id": str(uuid4()),
    "data_plane_id": str(uuid4()),
}


class TestSnowflakeConnector:
    """Test cases for SnowflakeConnector."""

    @patch("ml_engine.connectors.odbc_connector.create_engine")
    def test_snowflake_connector_defaults(self, mock_create_engine):
        """Test that Snowflake connector uses correct default values."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        # Create spec with minimal fields (no warehouse, role, schema)
        minimal_spec = MOCK_SNOWFLAKE_CONNECTOR_SPEC.copy()
        minimal_spec["fields"] = [
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
                "key": "authenticator",
                "value": SnowflakeConnectorAuthenticatorMethods.SNOWFLAKE_PASSWORD,
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
        ]

        spec = ConnectorSpec.model_validate(minimal_spec)
        logger = Mock()

        connector = SnowflakeConnector(spec, logger)

        assert connector.schema == "PUBLIC"
        assert connector.warehouse is "COMPUTE_WH"
        assert connector.role is None
        assert (
            connector.authenticator
            == SnowflakeConnectorAuthenticatorMethods.SNOWFLAKE_PASSWORD
        )

    @patch("ml_engine.connectors.odbc_connector.create_engine")
    def test_get_default_schema(self, mock_create_engine):
        """Test that Snowflake connector returns correct custom schema."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine

        # Create spec with custom schema
        custom_schema_spec = MOCK_SNOWFLAKE_CONNECTOR_SPEC.copy()
        custom_schema_spec["fields"] = [
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
                "key": "schema",
                "value": "CUSTOM_SCHEMA",
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
            {
                "key": "authenticator",
                "value": SnowflakeConnectorAuthenticatorMethods.SNOWFLAKE_PASSWORD,
                "is_sensitive": False,
                "d_type": ConnectorFieldDataType.STRING.value,
            },
        ]

        spec = ConnectorSpec.model_validate(custom_schema_spec)
        logger = Mock()

        connector = SnowflakeConnector(spec, logger)

        assert connector._get_default_schema() == "CUSTOM_SCHEMA"
