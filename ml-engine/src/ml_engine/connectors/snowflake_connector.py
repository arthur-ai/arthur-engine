from logging import Logger
from typing import Any, Dict, Tuple, Union

from arthur_client.api_bindings import (
    ConnectorCheckOutcome,
    ConnectorCheckResult,
    ConnectorSpec,
)
from arthur_common.models.connectors import (
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
from sqlalchemy import text


class SnowflakeConnector(ODBCConnector):
    """
    A specialized connector for Snowflake that extends the ODBCConnector.
    Handles Snowflake-specific connection parameters and authentication methods.
    """

    def __init__(self, connector_config: ConnectorSpec, logger: Logger) -> None:
        self.logger = logger
        connector_fields = {f.key: f.value for f in connector_config.fields}

        self.schema = connector_fields.get(SNOWFLAKE_CONNECTOR_SCHEMA_FIELD, "PUBLIC")
        self.warehouse = connector_fields.get(
            SNOWFLAKE_CONNECTOR_WAREHOUSE_FIELD,
            "COMPUTE_WH",
        )
        self.role = connector_fields.get(SNOWFLAKE_CONNECTOR_ROLE_FIELD)
        self.authenticator = connector_fields[SNOWFLAKE_CONNECTOR_AUTHENTICATOR_FIELD]

        private_key_passphrase = connector_fields.get(
            SNOWFLAKE_CONNECTOR_PRIVATE_KEY_PASSPHRASE_FIELD,
        )
        self.private_key_passphrase = (
            SecretStr(private_key_passphrase) if private_key_passphrase else None
        )

        private_key = connector_fields.get(SNOWFLAKE_CONNECTOR_PRIVATE_KEY_FIELD)
        self.private_key = SecretStr(private_key) if private_key else None

        # Call parent constructor to set up basic ODBC connection
        super().__init__(connector_config, logger)

        # validate snowflake config
        self._validate_snowflake_auth_config()

    def _validate_snowflake_auth_config(self) -> None:
        """Validates the expected fields are set for the authenticator methods"""
        match self.authenticator:
            case "snowflake_jwt":
                if not self.private_key or not self.username:
                    raise ValueError(
                        f"Private key and username must be specified when the authentication method is snowflake_jwt.",
                    )
            case "snowflake":
                if not self.username or not self.password:
                    raise ValueError(
                        f"Username and password must be specified when the authentication method is snowflake.",
                    )
            case _:
                raise ValueError(
                    f"Authenticator method {self.authenticator} is not recognized.",
                )

    def _build_engine_url(
        self,
        conn_str: str = "",
    ) -> Tuple[Union[str, URL], Dict[str, Any]]:
        """Overrides _build_engine_url to create a Snowflake-specific SQLAlchemy engine URL following official documentation.

        https://docs.snowflake.com/en/developer-guide/python-connector/sqlalchemy#:~:text=role%3Dmyrole%27%0A)-,For,-convenience%2C%20you%20can
        """

        connection_params = {
            "account": self.host,
            "user": self.username,
            "database": self.database,
            "schema": self.schema,
            "warehouse": self.warehouse,
        }

        if self.role:
            connection_params["role"] = self.role

        connect_args = {}

        if self.authenticator == "snowflake":
            if self.password:
                connection_params["password"] = self.password.get_secret_value()

        elif self.authenticator == "snowflake_jwt":
            # https://docs.snowflake.com/en/developer-guide/python-connector/sqlalchemy#key-pair-authentication-support

            pem_text = self.private_key.get_secret_value()

            p_key = serialization.load_pem_private_key(
                pem_text.encode(),
                password=(
                    self.private_key_passphrase.get_secret_value().encode()
                    if self.private_key_passphrase
                    else None
                ),
                backend=default_backend(),  # optional in modern cryptography
            )

            pkb = p_key.private_bytes(
                encoding=serialization.Encoding.DER,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            connect_args["private_key"] = pkb
        else:
            raise ValueError(
                f"Unsupported authenticator '{self.authenticator}'.",
            )

        snowflake_url = URL(**connection_params)
        return snowflake_url, connect_args

    def _get_default_schema(self) -> str:
        """Override ODBC connector method to return Snowflake's schema."""
        return self.schema

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
                f"Successfully discovered {len(datasets.available_datasets)} datasets",
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
        """Dispose of the Snowflake engine following official documentation.
        https://docs.snowflake.com/en/developer-guide/python-connector/sqlalchemy#opening-and-closing-a-connection
        """
        if hasattr(self, "engine") and self.engine:
            self.engine.dispose()
            self.logger.info("Snowflake engine disposed successfully")

    def __del__(self) -> None:
        """Cleanup method to ensure proper engine disposal."""
        self.dispose()
