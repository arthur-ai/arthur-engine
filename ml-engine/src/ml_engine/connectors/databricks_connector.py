from datetime import datetime
from logging import Logger
from typing import Any, Optional
from urllib.parse import quote_plus

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
    ScopeSchemaTag,
)
from arthur_common.models.connectors import (
    DATABRICKS_CONNECTOR_ACCESS_TOKEN_FIELD,
    DATABRICKS_CONNECTOR_AUTHENTICATOR_FIELD,
    DATABRICKS_CONNECTOR_CATALOG_FIELD,
    DATABRICKS_CONNECTOR_HTTP_PATH_FIELD,
    DATABRICKS_CONNECTOR_SCHEMA_FIELD,
    DATABRICKS_CONNECTOR_SERVER_HOSTNAME_FIELD,
    DATABRICKS_DATASET_CATALOG_FIELD,
    DATABRICKS_DATASET_SCHEMA_FIELD,
    ODBC_CONNECTOR_TABLE_NAME_FIELD,
    ConnectorPaginationOptions,
)
from arthur_common.models.enums import DatabricksConnectorAuthenticatorMethods
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from connectors.connector import Connector
from tools.schema_interpreters import primary_timestamp_col_name


class DatabricksConnector(Connector):
    """
    Connector for Databricks SQL warehouses and all-purpose compute.
    Uses SQLAlchemy + databricks-sqlalchemy (databricks:// URL).

    Auth: PAT or OAuth token pass-through (both use access_token).
    If access_token is not provided, falls back to environment variables:
    - DATABRICKS_ACCESS_TOKEN or DATABRICKS_TOKEN (for PAT)
    - DATABRICKS_SERVER_HOSTNAME, DATABRICKS_HTTP_PATH
    """

    def __init__(self, connector_config: ConnectorSpec, logger: Logger) -> None:
        self.logger = logger
        connector_fields = {f.key: f.value for f in connector_config.fields}

        self.server_hostname: str = connector_fields[
            DATABRICKS_CONNECTOR_SERVER_HOSTNAME_FIELD
        ]
        self.http_path: str = connector_fields[DATABRICKS_CONNECTOR_HTTP_PATH_FIELD]
        self.authenticator: str = connector_fields[
            DATABRICKS_CONNECTOR_AUTHENTICATOR_FIELD
        ]
        self.access_token: Optional[str] = connector_fields.get(
            DATABRICKS_CONNECTOR_ACCESS_TOKEN_FIELD,
        )
        self.catalog: Optional[str] = connector_fields.get(
            DATABRICKS_CONNECTOR_CATALOG_FIELD,
        )
        self.schema: Optional[str] = connector_fields.get(
            DATABRICKS_CONNECTOR_SCHEMA_FIELD,
        )

        self._validate_auth_config()
        self._engine: Engine = self._create_sqlalchemy_engine()

    def _authenticator_value(self) -> str:
        """Return authenticator as string (API may send enum or string)."""
        return (
            getattr(self.authenticator, "value", self.authenticator)
            if self.authenticator is not None
            else ""
        )

    def _validate_auth_config(self) -> None:
        allowed = (
            DatabricksConnectorAuthenticatorMethods.DATABRICKS_PAT.value,
            DatabricksConnectorAuthenticatorMethods.DATABRICKS_OAUTH_TOKEN_PASSTHROUGH.value,
        )
        if self._authenticator_value() not in allowed:
            raise ValueError(
                f"Authenticator must be {DatabricksConnectorAuthenticatorMethods.DATABRICKS_PAT.value} "
                f"or {DatabricksConnectorAuthenticatorMethods.DATABRICKS_OAUTH_TOKEN_PASSTHROUGH.value}, "
                f"got {self.authenticator}.",
            )
        # access_token is optional - if not provided, the Databricks SDK will fall back to
        # environment variables (DATABRICKS_ACCESS_TOKEN, DATABRICKS_TOKEN) similar to
        # AWS boto3 and Google Cloud SDK behavior

    def _create_sqlalchemy_engine(self) -> Engine:
        # If access_token is provided: databricks://token:{access_token}@{server_hostname}?http_path={http_path}&catalog={catalog}&schema={schema}
        # If not provided: databricks://{server_hostname}?http_path={http_path}&catalog={catalog}&schema={schema}
        # When token is omitted, the SDK will use DATABRICKS_ACCESS_TOKEN or DATABRICKS_TOKEN env var
        if self.access_token:
            token = quote_plus(self.access_token)
            url = (
                f"databricks://token:{token}@{self.server_hostname}"
                f"?http_path={quote_plus(self.http_path)}"
            )
        else:
            url = (
                f"databricks://{self.server_hostname}"
                f"?http_path={quote_plus(self.http_path)}"
            )
        if self.catalog:
            url += f"&catalog={quote_plus(self.catalog)}"
        if self.schema:
            url += f"&schema={quote_plus(self.schema)}"
        return create_engine(url, pool_pre_ping=True, pool_timeout=60)

    @staticmethod
    def _escape_identifier(name: str) -> str:
        """Escape identifier for Databricks SQL (backticks)."""
        escaped = name.replace("`", "\\`")
        return f"`{escaped}`"

    def _get_qualified_table_name(
        self,
        locator: dict[str, Any],
    ) -> str:
        table_name = locator[ODBC_CONNECTOR_TABLE_NAME_FIELD]
        catalog = locator.get(DATABRICKS_DATASET_CATALOG_FIELD)
        schema = locator.get(DATABRICKS_DATASET_SCHEMA_FIELD)
        parts = []
        if catalog:
            parts.append(self._escape_identifier(catalog))
        if schema:
            parts.append(self._escape_identifier(schema))
        parts.append(self._escape_identifier(table_name))
        return ".".join(parts)

    @staticmethod
    def _paginate_sql(
        query: str,
        pagination_options: ConnectorPaginationOptions | None,
    ) -> str:
        if not pagination_options:
            return query
        if pagination_options.page < 1:
            raise ValueError(
                "Arthur pagination is 1-indexed. Please provide a page number >= 1.",
            )
        limit = pagination_options.page_size
        offset = (pagination_options.page - 1) * pagination_options.page_size
        return query + f" LIMIT {limit} OFFSET {offset}"

    def _build_read_query(
        self,
        dataset: Dataset | AvailableDataset,
        start_time: datetime,
        end_time: datetime,
        pagination_options: ConnectorPaginationOptions | None,
    ) -> str:
        if not dataset.dataset_locator:
            raise ValueError(
                f"Dataset {dataset.id} has no dataset locator, cannot read from Databricks.",
            )
        locator = {f.key: f.value for f in dataset.dataset_locator.fields}
        qualified = self._get_qualified_table_name(locator)
        query = f"SELECT * FROM {qualified}"

        try:
            ts_col = primary_timestamp_col_name(dataset)
            query += (
                f" WHERE {self._escape_identifier(ts_col)} >= '{start_time}'"
                f" AND {self._escape_identifier(ts_col)} < '{end_time}'"
            )
            query += f" ORDER BY {self._escape_identifier(ts_col)} DESC"
        except ValueError:
            self.logger.warning(
                f"Primary timestamp column with {ScopeSchemaTag.PRIMARY_TIMESTAMP} tag not found. "
                "Using pagination only.",
            )
            if not pagination_options:
                raise ValueError(
                    "Pagination options not provided and timestamp range not set. "
                    "Cannot fetch all data without a limit or time range.",
                ) from None

        query = self._paginate_sql(query, pagination_options)
        return query

    def read(
        self,
        dataset: Dataset | AvailableDataset,
        start_time: datetime,
        end_time: datetime,
        filters: list[DataResultFilter] | None = None,
        pagination_options: ConnectorPaginationOptions | None = None,
    ) -> list[dict[str, Any]] | pd.DataFrame:
        query = self._build_read_query(
            dataset,
            start_time,
            end_time,
            pagination_options,
        )
        with self._engine.connect() as conn:
            return pd.read_sql(text(query), conn)

    def test_connection(self) -> ConnectorCheckResult:
        try:
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as e:
            self.logger.error("Databricks connection test failed.", exc_info=e)
            return ConnectorCheckResult(
                connection_check_outcome=ConnectorCheckOutcome.FAILED,
                failure_reason=f"Databricks connection failed: {e}",
            )
        return ConnectorCheckResult(
            connection_check_outcome=ConnectorCheckOutcome.SUCCEEDED,
        )

    def list_datasets(self) -> PutAvailableDatasets:
        inspector = inspect(self._engine)
        schema_name = self.schema or "default"
        try:
            tables = inspector.get_table_names(schema=schema_name)
        except Exception:
            tables = []
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

    def dispose(self) -> None:
        """Dispose of the Databricks SQL engine to clean up connection pool."""
        if hasattr(self, "_engine") and self._engine:
            self._engine.dispose()
            self.logger.info("Databricks engine disposed successfully")

    def __del__(self) -> None:
        """Cleanup method to ensure proper engine disposal."""
        try:
            self.dispose()
        except Exception:
            # Ignore errors during cleanup
            pass
