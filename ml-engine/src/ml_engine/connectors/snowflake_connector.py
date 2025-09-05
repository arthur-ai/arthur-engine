from logging import Logger

from arthur_client.api_bindings import (
    ConnectorCheckOutcome,
    ConnectorCheckResult,
    ConnectorSpec,
    ConnectorSpecField,
)
from arthur_common.models.connectors import (
    ODBC_CONNECTOR_HOST_FIELD,
    SNOWFLAKE_CONNECTOR_ACCOUNT_FIELD,
    SNOWFLAKE_CONNECTOR_AUTHENTICATOR_FIELD,
    SNOWFLAKE_CONNECTOR_PRIVATE_KEY_FIELD,
    SNOWFLAKE_CONNECTOR_PRIVATE_KEY_PASSPHRASE_FIELD,
    SNOWFLAKE_CONNECTOR_ROLE_FIELD,
    SNOWFLAKE_CONNECTOR_SCHEMA_FIELD,
    SNOWFLAKE_CONNECTOR_WAREHOUSE_FIELD,
)
from connectors.odbc_connector import ODBCConnector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from pydantic import SecretStr
from snowflake.sqlalchemy import URL
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


class SnowflakeConnector(ODBCConnector):
    """
    A specialized connector for Snowflake that extends the ODBCConnector.
    Handles Snowflake-specific connection parameters and authentication methods.
    """

    def __init__(self, connector_config: ConnectorSpec, logger: Logger) -> None:
        self.logger = logger
        connector_fields = {f.key: f.value for f in connector_config.fields}

        # Store Snowflake-specific configuration
        self.account = connector_fields.get(
            SNOWFLAKE_CONNECTOR_ACCOUNT_FIELD,
            "account",
        )

        # Add host field to connector_config.fields for parent constructor
        if "host" not in connector_fields:
            connector_config.fields.append(
                ConnectorSpecField(
                    key=ODBC_CONNECTOR_HOST_FIELD,
                    value=self.account,
                    is_sensitive=False,
                    d_type="STRING",
                ),
            )
            self.logger.info(f"Added host field to connector config: {self.account}")
        else:
            self.logger.info(f"Host field already exists in connector config")

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
        if self.authenticator == "snowflake_jwt":
            self.private_key_passphrase = SecretStr(
                connector_fields.get(SNOWFLAKE_CONNECTOR_PRIVATE_KEY_PASSPHRASE_FIELD),
            )
            self.private_key = SecretStr(
                connector_fields.get(SNOWFLAKE_CONNECTOR_PRIVATE_KEY_FIELD),
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

        if self.role:
            connection_params["role"] = self.role

        if self.authenticator == "snowflake":
            connection_params["authenticator"] = "snowflake"
            if self.password:
                connection_params["password"] = self.password.get_secret_value()

        elif self.authenticator == "snowflake_jwt":

            connection_params["authenticator"] = "snowflake_jwt"

            pem_text = self.private_key.get_secret_value()

            p_key = serialization.load_pem_private_key(
                pem_text.encode(),
                password=self.private_key_passphrase.get_secret_value().encode(),
                backend=default_backend(),  # optional in modern cryptography
            )

            pkb = p_key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )

            try:
                private_key_URL = URL(**connection_params)
                engine = create_engine(
                    private_key_URL,
                    connect_args={"private_key": pkb},
                )
            except Exception as e:
                self.logger.error(f"Failed to create Snowflake engine: {e}")
                raise
        else:
            self.logger.warning(
                f"Unsupported authenticator '{self.authenticator}', defaulting to 'snowflake'",
            )
            connection_params["authenticator"] = "snowflake"
            if self.password:
                connection_params["password"] = self.password.get_secret_value()

        if self.authenticator != "key_pair":
            try:
                snowflake_url = URL(**connection_params)
                engine = create_engine(snowflake_url, echo=False)
            except Exception as e:
                self.logger.error(f"Failed to create Snowflake engine: {e}")
                raise

        return engine

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
            "has_password": bool(self.password),
        }

    def __del__(self) -> None:
        """Cleanup method to ensure proper engine disposal."""
        self.dispose()
