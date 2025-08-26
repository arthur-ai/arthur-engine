from logging import Logger

from arthur_client.api_bindings import (
    ConnectorCheckOutcome,
    ConnectorCheckResult,
    ConnectorSpec,
)
from arthur_common.models.connectors import (
    SNOWFLAKE_CONNECTOR_ACCOUNT_FIELD,
    SNOWFLAKE_CONNECTOR_AUTHENTICATOR_FIELD,
    SNOWFLAKE_CONNECTOR_PRIVATE_KEY_FIELD,
    SNOWFLAKE_CONNECTOR_PRIVATE_KEY_PASSPHRASE_FIELD,
    SNOWFLAKE_CONNECTOR_ROLE_FIELD,
    SNOWFLAKE_CONNECTOR_SCHEMA_FIELD,
    SNOWFLAKE_CONNECTOR_WAREHOUSE_FIELD,
)
from connectors.odbc_connector import ODBCConnector
from snowflake.sqlalchemy import URL
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


class SnowflakeConnector(ODBCConnector):
    """
    A specialized connector for Snowflake that extends the ODBCConnector.
    Handles Snowflake-specific connection parameters and authentication methods.
    """

    def __init__(self, connector_config: ConnectorSpec, logger: Logger) -> None:
        connector_fields = {f.key: f.value for f in connector_config.fields}

        # Validate required Snowflake fields first
        if not connector_fields.get("username"):
            raise ValueError("Username is required for Snowflake connection")
        if not connector_fields.get("database"):
            raise ValueError("Database is required for Snowflake connection")

        # Store Snowflake-specific configuration
        self.account = connector_fields.get(
            SNOWFLAKE_CONNECTOR_ACCOUNT_FIELD,
            "account",
        )

        if not self.account or self.account == "account":
            raise ValueError("Snowflake account identifier is required")

        self.schema = connector_fields.get(SNOWFLAKE_CONNECTOR_SCHEMA_FIELD, "PUBLIC")
        self.warehouse = connector_fields.get(
            SNOWFLAKE_CONNECTOR_WAREHOUSE_FIELD,
            "COMPUTE_WH",
        )
        self.role = connector_fields.get(SNOWFLAKE_CONNECTOR_ROLE_FIELD)
        self.authenticator = connector_fields.get(
            SNOWFLAKE_CONNECTOR_AUTHENTICATOR_FIELD,
            "snowflake",
        )
        self.private_key = connector_fields.get(SNOWFLAKE_CONNECTOR_PRIVATE_KEY_FIELD)
        self.private_key_passphrase = connector_fields.get(
            SNOWFLAKE_CONNECTOR_PRIVATE_KEY_PASSPHRASE_FIELD,
        )

        if "host" not in connector_fields:
            connector_config.fields.append(
                type(
                    "Field",
                    (),
                    {
                        "key": "host",
                        "value": self.account,
                        "is_sensitive": False,
                        "d_type": "STRING",
                    },
                )(),
            )

        if "dialect" not in connector_fields:
            connector_config.fields.append(
                type(
                    "Field",
                    (),
                    {
                        "key": "dialect",
                        "value": "snowflake native (snowflake-connector-python)",
                        "is_sensitive": False,
                        "d_type": "STRING",
                    },
                )(),
            )

        # Call parent constructor to set up basic ODBC connection
        super().__init__(connector_config, logger)

        # Override the engine with Snowflake-specific configuration
        self.engine = self._create_snowflake_engine()

    def _create_snowflake_engine(self) -> Engine:
        """Create a Snowflake-specific SQLAlchemy engine following official documentation."""
        connection_params = {
            "account": self.account,
            "user": self.username,
            "database": self.database,
            "schema": self.schema,
            "warehouse": self.warehouse,
        }

        if self.authenticator == "private_key":
            if not self.private_key:
                raise ValueError(
                    "Private key is required when using 'private_key' authenticator",
                )
            connection_params["authenticator"] = "private_key"
            connection_params["private_key"] = self.private_key
            if self.private_key_passphrase:
                connection_params["private_key_passphrase"] = (
                    self.private_key_passphrase
                )
        elif self.authenticator == "snowflake":
            connection_params["authenticator"] = "snowflake"
            if self.password:
                connection_params["password"] = self.password.get_secret_value()
        else:
            self.logger.warning(
                f"Unsupported authenticator '{self.authenticator}', defaulting to 'snowflake'",
            )
            connection_params["authenticator"] = "snowflake"
            if self.password:
                connection_params["password"] = self.password.get_secret_value()

        if self.role:
            connection_params["role"] = self.role

        # Add optional connection optimization parameters with sensible defaults
        connection_params.update(
            {
                "client_session_keep_alive": True,
                "client_session_keep_alive_heartbeat_frequency": 3600,  # 1 hour
                "login_timeout": 60,  # 60 seconds
                "network_timeout": 60,  # 60 seconds
            },
        )

        if hasattr(self, "session_parameters") and self.session_parameters:
            connection_params["session_parameters"] = self.session_parameters

        snowflake_url = URL(**connection_params)
        return create_engine(snowflake_url, echo=False)

    def _get_default_schema(self) -> str:
        """Override to return Snowflake's default schema."""
        return self.schema or "PUBLIC"

    def test_connection(self) -> ConnectorCheckResult:
        """Test Snowflake connection using list_datasets for comprehensive validation."""
        try:
            # Test basic connectivity first
            connection = self.engine.connect()
            try:
                result = connection.execute(text("SELECT CURRENT_VERSION()"))
                version = result.fetchone()
                self.logger.info(
                    f"Connected to Snowflake version: {version[0] if version else 'Unknown'}",
                )

                # Test database access
                if self.database:
                    connection.execute(text(f"USE DATABASE {self.database}"))
                    self.logger.info(f"Successfully accessed database: {self.database}")

                # Test warehouse access
                if self.warehouse:
                    connection.execute(text(f"USE WAREHOUSE {self.warehouse}"))
                    self.logger.info(
                        f"Successfully switched to warehouse: {self.warehouse}",
                    )

            finally:
                connection.close()

            datasets = self.list_datasets()
            self.logger.info(
                f"Successfully listed {len(datasets.available_datasets)} datasets",
            )

        except Exception as e:
            self.logger.error("Snowflake connection test failed.", exc_info=e)
            return ConnectorCheckResult(
                connection_check_outcome=ConnectorCheckOutcome.FAILED,
                failure_reason=f"Snowflake connection failed: {e}",
            )

        return ConnectorCheckResult(
            connection_check_outcome=ConnectorCheckOutcome.SUCCEEDED,
        )

    def dispose(self) -> None:
        """Dispose of the Snowflake engine following official documentation."""
        if hasattr(self, "engine") and self.engine:
            self.engine.dispose()
            self.logger.info("Snowflake engine disposed successfully")

    def get_connection_info(self) -> dict:
        """Get connection information for debugging purposes."""
        return {
            "account": self.account,
            "user": self.username,
            "database": self.database,
            "schema": self.schema,
            "warehouse": self.warehouse,
            "role": self.role,
            "authenticator": self.authenticator,
            "has_private_key": bool(self.private_key),
            "has_password": bool(self.password),
        }

    def __del__(self) -> None:
        """Cleanup method to ensure proper engine disposal."""
        self.dispose()
