from datetime import datetime
from logging import Logger
from typing import List

import pandas as pd
from arthur_client.api_bindings import (
    AvailableDataset,
    ConnectorCheckOutcome,
    ConnectorCheckResult,
    ConnectorSpec,
    DataResultFilter,
    Dataset,
    DatasetLocator,
    DatasetLocatorField,
    PutAvailableDataset,
    PutAvailableDatasets,
)
from arthur_common.models.connectors import (
    ODBC_CONNECTOR_TABLE_NAME_FIELD,
    SNOWFLAKE_CONNECTOR_AUTHENTICATOR_FIELD,
    SNOWFLAKE_CONNECTOR_PRIVATE_KEY_FIELD,
    SNOWFLAKE_CONNECTOR_PRIVATE_KEY_PASSPHRASE_FIELD,
    SNOWFLAKE_CONNECTOR_ROLE_FIELD,
    SNOWFLAKE_CONNECTOR_SCHEMA_FIELD,
    SNOWFLAKE_CONNECTOR_WAREHOUSE_FIELD,
    ConnectorPaginationOptions,
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
        # Extract Snowflake-specific fields
        connector_fields = {f.key: f.value for f in connector_config.fields}

        # Store Snowflake-specific configuration
        self.schema = connector_fields.get(SNOWFLAKE_CONNECTOR_SCHEMA_FIELD, "PUBLIC")
        self.warehouse = connector_fields.get(SNOWFLAKE_CONNECTOR_WAREHOUSE_FIELD)
        self.role = connector_fields.get(SNOWFLAKE_CONNECTOR_ROLE_FIELD)
        self.authenticator = connector_fields.get(
            SNOWFLAKE_CONNECTOR_AUTHENTICATOR_FIELD,
            "snowflake",
        )
        self.private_key = connector_fields.get(SNOWFLAKE_CONNECTOR_PRIVATE_KEY_FIELD)
        self.private_key_passphrase = connector_fields.get(
            SNOWFLAKE_CONNECTOR_PRIVATE_KEY_PASSPHRASE_FIELD,
        )

        # Call parent constructor to set up basic ODBC connection
        super().__init__(connector_config, logger)

        # Override the engine with Snowflake-specific configuration
        self.engine = self._create_snowflake_engine()

    def _create_snowflake_engine(self) -> Engine:
        """Create a Snowflake-specific SQLAlchemy engine using snowflake.sqlalchemy.URL."""
        # Build Snowflake connection parameters
        connection_params = {
            "account": self.host,
            "user": self.username,
            "database": self.database,
            "schema": self.schema,
            "warehouse": self.warehouse,
            "authenticator": self.authenticator,
        }

        # Add optional parameters if provided
        if self.role:
            connection_params["role"] = self.role
        if self.password:
            connection_params["password"] = self.password.get_secret_value()
        if self.private_key:
            connection_params["private_key"] = self.private_key
        if self.private_key_passphrase:
            connection_params["private_key_passphrase"] = self.private_key_passphrase

        # Create Snowflake URL and engine using the proper snowflake.sqlalchemy.URL
        snowflake_url = URL(**connection_params)
        return create_engine(snowflake_url)

    def _get_default_schema(self) -> str:
        """Override to return Snowflake's default schema."""
        return self.schema or "PUBLIC"

    def list_datasets(self) -> PutAvailableDatasets:
        """Override to handle Snowflake-specific dataset listing."""
        inspector = self.engine.inspect(self.engine)
        schema = self._get_default_schema()

        # Get tables from the specified schema
        tables = inspector.get_table_names(schema=schema)

        return PutAvailableDatasets(
            available_datasets=[
                PutAvailableDataset(
                    name=tbl,
                    dataset_locator=DatasetLocator(
                        fields=[
                            DatasetLocatorField(
                                key=ODBC_CONNECTOR_TABLE_NAME_FIELD,
                                value=tbl,
                            ),
                        ],
                    ),
                )
                for tbl in tables
            ],
        )

    def test_connection(self) -> ConnectorCheckResult:
        """Override to test Snowflake-specific connection."""
        try:
            with self.engine.connect() as conn:
                # Test with a simple Snowflake query
                conn.execute(text("SELECT CURRENT_VERSION()"))

                # If warehouse is specified, test warehouse access
                if self.warehouse:
                    conn.execute(text(f"USE WAREHOUSE {self.warehouse}"))

        except Exception as e:
            self.logger.error("Snowflake connection test failed.", exc_info=e)
            return ConnectorCheckResult(
                connection_check_outcome=ConnectorCheckOutcome.FAILED,
                failure_reason=f"Snowflake connection failed: {e}",
            )

        return ConnectorCheckResult(
            connection_check_outcome=ConnectorCheckOutcome.SUCCEEDED,
        )

    def read(
        self,
        dataset: Dataset | AvailableDataset,
        start_time: datetime,
        end_time: datetime,
        filters: List[DataResultFilter] | None = None,
        pagination_options: ConnectorPaginationOptions | None = None,
    ) -> pd.DataFrame:
        """Override to handle Snowflake-specific data reading."""
        # Use the parent ODBCConnector's read method
        return super().read(dataset, start_time, end_time, filters, pagination_options)
