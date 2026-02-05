import os
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
    DATABRICKS_CONNECTOR_CLIENT_ID_FIELD,
    DATABRICKS_CONNECTOR_CLIENT_SECRET_FIELD,
    DATABRICKS_CONNECTOR_HTTP_PATH_FIELD,
    DATABRICKS_CONNECTOR_PAT_FIELD,
    DATABRICKS_CONNECTOR_SERVER_HOSTNAME_FIELD,
    DATABRICKS_DATASET_CATALOG_FIELD,
    DATABRICKS_DATASET_SCHEMA_FIELD,
    ODBC_CONNECTOR_TABLE_NAME_FIELD,
    ConnectorPaginationOptions,
)
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config, oauth_service_principal
from pydantic import SecretStr
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from connectors.connector import Connector
from tools.schema_interpreters import primary_timestamp_col_name

# Authentication method constants
AUTH_METHOD_OAUTH_M2M = "oauth_m2m"
AUTH_METHOD_PAT = "pat"


class DatabricksConnector(Connector):
    """
    Connector for Databricks SQL warehouses and all-purpose compute.
    Uses SQLAlchemy + databricks-sqlalchemy (databricks:// URL).

    Auth: PAT or OAuth M2M (auto-detected based on credentials provided).
    - OAuth M2M: Provide client_id + client_secret
    - PAT: Provide access_token

    All credentials support environment variable fallback:
    - DATABRICKS_HOST, DATABRICKS_HTTP_PATH
    - DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET (OAuth M2M)
    - DATABRICKS_TOKEN (PAT)
    """

    def __init__(self, connector_config: ConnectorSpec, logger: Logger) -> None:
        self.logger = logger
        connector_fields = {f.key: f.value for f in connector_config.fields}

        # Parse connection fields with env var fallback
        self.server_hostname: str = str(
            connector_fields.get(DATABRICKS_CONNECTOR_SERVER_HOSTNAME_FIELD)
            or os.getenv("DATABRICKS_HOST", "")
        )
        self.http_path: str = str(
            connector_fields.get(DATABRICKS_CONNECTOR_HTTP_PATH_FIELD)
            or os.getenv("DATABRICKS_HTTP_PATH", "")
        )

        # Parse credentials with env var fallback
        access_token_raw = connector_fields.get(
            DATABRICKS_CONNECTOR_PAT_FIELD
        ) or os.getenv("DATABRICKS_TOKEN")
        client_id_raw = connector_fields.get(
            DATABRICKS_CONNECTOR_CLIENT_ID_FIELD
        ) or os.getenv("DATABRICKS_CLIENT_ID")
        client_secret_raw = connector_fields.get(
            DATABRICKS_CONNECTOR_CLIENT_SECRET_FIELD
        ) or os.getenv("DATABRICKS_CLIENT_SECRET")

        # Wrap sensitive fields with SecretStr
        self.access_token: Optional[SecretStr] = (
            SecretStr(access_token_raw) if access_token_raw else None
        )
        self.client_id: Optional[SecretStr] = (
            SecretStr(client_id_raw) if client_id_raw else None
        )
        self.client_secret: Optional[SecretStr] = (
            SecretStr(client_secret_raw) if client_secret_raw else None
        )

        # Workspace client for catalog discovery (lazy init)
        self._workspace_client: Optional[WorkspaceClient] = None

        # Determine and validate auth method
        self._auth_method = self._determine_auth_method()
        self._validate_auth_config()

        # Create SQLAlchemy engine
        self._engine: Engine = self._create_sqlalchemy_engine()

    def _determine_auth_method(self) -> str:
        """Determine authentication method based on provided credentials.

        Resolution order:
        1. If client_id AND client_secret provided → OAuth M2M
        2. Else if access_token provided → PAT
        3. Else → Error (no credentials)

        Returns:
            Auth method string: AUTH_METHOD_OAUTH_M2M or AUTH_METHOD_PAT
        """
        if self.client_id and self.client_secret:
            self.logger.info("Using OAuth M2M authentication")
            return AUTH_METHOD_OAUTH_M2M
        elif self.access_token:
            self.logger.info("Using PAT authentication")
            return AUTH_METHOD_PAT
        else:
            raise ValueError(
                "No Databricks credentials provided. "
                "Set either (client_id + client_secret) for OAuth M2M "
                "or access_token for PAT authentication. "
                "Credentials can be provided via connector config or environment variables: "
                "DATABRICKS_CLIENT_ID, DATABRICKS_CLIENT_SECRET, or DATABRICKS_TOKEN"
            )

    def _validate_auth_config(self) -> None:
        """Validate auth config based on detected auth method."""
        if self._auth_method == AUTH_METHOD_OAUTH_M2M:
            if not self.client_id or not self.client_secret:
                raise ValueError(
                    "OAuth M2M requires both client_id and client_secret. "
                    "Provide via connector config or DATABRICKS_CLIENT_ID/DATABRICKS_CLIENT_SECRET env vars."
                )
        elif self._auth_method == AUTH_METHOD_PAT:
            if not self.access_token:
                raise ValueError(
                    "PAT authentication requires access_token. "
                    "Provide via connector config or DATABRICKS_TOKEN env var."
                )

    def _get_access_token(self) -> str:
        """Get access token based on detected auth method."""
        if self._auth_method == AUTH_METHOD_PAT:
            assert self.access_token is not None, "PAT token must be set"
            return self.access_token.get_secret_value()
        elif self._auth_method == AUTH_METHOD_OAUTH_M2M:
            assert self.client_id is not None, "Client ID must be set"
            assert self.client_secret is not None, "Client secret must be set"
            config = Config(
                host=f"https://{self.server_hostname}",
                client_id=self.client_id.get_secret_value(),
                client_secret=self.client_secret.get_secret_value(),
            )
            token: str = oauth_service_principal(config).oauth_token().access_token
            self.logger.debug("Fetched fresh OAuth M2M token")
            return token
        else:
            raise ValueError(f"Unsupported auth method: {self._auth_method}")

    def _create_sqlalchemy_engine(self) -> Engine:
        """Create SQLAlchemy engine with fresh access token."""
        token = self._get_access_token()
        url = (
            f"databricks://token:{quote_plus(token)}@{self.server_hostname}"
            f"?http_path={quote_plus(self.http_path)}"
        )
        return create_engine(url, pool_pre_ping=True, pool_timeout=60)

    def _recreate_engine_if_needed(self, error: Exception) -> bool:
        """Recreate engine with fresh token if auth error detected.

        Only recreates for OAuth M2M (PAT tokens don't expire).

        Args:
            error: The exception that occurred

        Returns:
            True if engine was recreated, False otherwise
        """
        if self._auth_method != AUTH_METHOD_OAUTH_M2M:
            return False

        error_msg = str(error).lower()
        auth_keywords = ["token", "auth", "401", "403", "unauthorized", "forbidden"]
        if any(keyword in error_msg for keyword in auth_keywords):
            self.logger.info("Auth error detected, recreating engine with fresh token")
            self._engine.dispose()
            self._engine = self._create_sqlalchemy_engine()
            return True

        return False

    def _get_workspace_client(self) -> WorkspaceClient:
        """Get or create WorkspaceClient for catalog discovery."""
        if self._workspace_client:
            return self._workspace_client

        # Build Config based on detected auth method
        if self._auth_method == AUTH_METHOD_PAT:
            assert self.access_token is not None, "PAT token must be set"
            config = Config(
                host=f"https://{self.server_hostname}",
                token=self.access_token.get_secret_value(),
            )
        elif self._auth_method == AUTH_METHOD_OAUTH_M2M:
            assert self.client_id is not None, "Client ID must be set"
            assert self.client_secret is not None, "Client secret must be set"
            config = Config(
                host=f"https://{self.server_hostname}",
                client_id=self.client_id.get_secret_value(),
                client_secret=self.client_secret.get_secret_value(),
            )
        else:
            raise ValueError(f"Unsupported auth method: {self._auth_method}")

        self._workspace_client = WorkspaceClient(config=config)
        return self._workspace_client

    @staticmethod
    def _escape_identifier(name: str) -> str:
        """Escape identifier for Databricks SQL (backticks)."""
        escaped = name.replace("`", "\\`")
        return f"`{escaped}`"

    def _build_qualified_table_name(
        self,
        catalog: str,
        schema: str,
        table: str,
    ) -> str:
        """Build fully qualified table name with proper escaping.

        Args:
            catalog: Catalog name
            schema: Schema name
            table: Table name

        Returns:
            Fully qualified and escaped table name: `catalog`.`schema`.`table`
        """
        return ".".join(
            [
                self._escape_identifier(catalog),
                self._escape_identifier(schema),
                self._escape_identifier(table),
            ]
        )

    def _get_qualified_table_name(
        self,
        locator: dict[str, Any],
    ) -> str:
        """Build fully qualified table name from dataset locator.

        All three components (catalog, schema, table) are required in the locator.
        """
        catalog = locator[DATABRICKS_DATASET_CATALOG_FIELD]
        schema = locator[DATABRICKS_DATASET_SCHEMA_FIELD]
        table_name = locator[ODBC_CONNECTOR_TABLE_NAME_FIELD]

        return self._build_qualified_table_name(catalog, schema, table_name)

    @staticmethod
    def _paginate_sql(
        query: str,
        pagination_options: ConnectorPaginationOptions | None,
    ) -> str:
        """Add pagination to SQL query."""
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
        """Build SQL query for reading dataset."""
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
        """Read data from Databricks dataset with automatic token refresh."""
        query = self._build_read_query(
            dataset,
            start_time,
            end_time,
            pagination_options,
        )
        try:
            with self._engine.connect() as conn:
                return pd.read_sql(text(query), conn)
        except Exception as e:
            if self._recreate_engine_if_needed(e):
                self.logger.info("Retrying read with fresh token")
                with self._engine.connect() as conn:
                    return pd.read_sql(text(query), conn)
            raise

    def test_connection(self) -> ConnectorCheckResult:
        """Test connection by verifying we can query at least one accessible table."""
        try:
            # Test basic SQL connectivity
            with self._engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()
                self.logger.info(
                    f"Connected to Databricks version: {version[0] if version else 'Unknown'}"
                )

            # Verify we can query at least one table (proves permissions are correct)
            # Try to find and query an accessible table instead of assuming information_schema access
            workspace_client = self._get_workspace_client()

            # Try to list catalogs and find a queryable table
            test_table_found = False
            try:
                catalogs = list(workspace_client.catalogs.list())
                for catalog in catalogs[:3]:  # Check up to 3 catalogs to avoid slowness
                    if not catalog.name:
                        continue
                    try:
                        schemas = list(
                            workspace_client.schemas.list(catalog_name=catalog.name)
                        )
                        for schema in schemas[:3]:  # Check up to 3 schemas per catalog
                            if not schema.name:
                                continue
                            try:
                                tables = list(
                                    workspace_client.tables.list(
                                        catalog_name=catalog.name,
                                        schema_name=schema.name,
                                    )
                                )
                                # Try to query the first table
                                for table in tables[:3]:  # Try up to 3 tables
                                    if not table.name:
                                        continue
                                    if self._can_query_table(
                                        catalog.name, schema.name, table.name
                                    ):
                                        self.logger.info(
                                            f"Successfully verified query permissions on {catalog.name}.{schema.name}.{table.name}"
                                        )
                                        test_table_found = True
                                        break
                                if test_table_found:
                                    break
                            except Exception as e:
                                self.logger.debug(
                                    f"Cannot access tables in {catalog.name}.{schema.name}: {e}"
                                )
                                continue
                        if test_table_found:
                            break
                    except Exception as e:
                        self.logger.debug(
                            f"Cannot access schemas in {catalog.name}: {e}"
                        )
                        continue
                    if test_table_found:
                        break
            except Exception as e:
                self.logger.warning(f"Cannot list catalogs via WorkspaceClient: {e}")

            if not test_table_found:
                self.logger.warning(
                    "Could not verify query permissions - no accessible tables found. "
                    "Connection works but may have limited permissions."
                )

        except Exception as e:
            self.logger.error("Databricks connection test failed.", exc_info=e)
            error_msg = str(e).lower()

            if "token" in error_msg or "401" in error_msg or "403" in error_msg:
                failure_reason = f"Authentication failed: {e}"
            elif (
                "catalog" in error_msg
                or "schema" in error_msg
                or "permission" in error_msg
            ):
                failure_reason = f"Cannot query tables - check USE CATALOG, USE SCHEMA, and SELECT permissions: {e}"
            else:
                failure_reason = f"Connection failed: {e}"

            return ConnectorCheckResult(
                connection_check_outcome=ConnectorCheckOutcome.FAILED,
                failure_reason=failure_reason,
            )

        return ConnectorCheckResult(
            connection_check_outcome=ConnectorCheckOutcome.SUCCEEDED,
        )

    def _can_query_table(self, catalog: str, schema: str, table: str) -> bool:
        """Test if user has SELECT permission on table using LIMIT 0 query.

        Args:
            catalog: Catalog name
            schema: Schema name
            table: Table name

        Returns:
            True if query succeeds, False otherwise
        """
        try:
            qualified_name = self._build_qualified_table_name(catalog, schema, table)
            query = f"SELECT * FROM {qualified_name} LIMIT 0"
            with self._engine.connect() as conn:
                conn.execute(text(query))
            return True
        except Exception as e:
            self.logger.debug(f"Cannot query {catalog}.{schema}.{table}: {e}")
            return False

    def list_datasets(self) -> PutAvailableDatasets:
        """Discover all queryable datasets across all accessible catalogs."""
        workspace_client = self._get_workspace_client()
        catalogs = list(workspace_client.catalogs.list())

        available_datasets = []
        tables_discovered = 0
        tables_queryable = 0

        for catalog in catalogs:
            if not catalog.name:
                continue
            try:
                schemas = list(workspace_client.schemas.list(catalog_name=catalog.name))
            except Exception as e:
                self.logger.warning(f"Cannot access schemas in {catalog.name}: {e}")
                continue

            for schema in schemas:
                if not schema.name:
                    continue
                try:
                    tables = list(
                        workspace_client.tables.list(
                            catalog_name=catalog.name,
                            schema_name=schema.name,
                        )
                    )
                except Exception as e:
                    self.logger.warning(
                        f"Cannot access tables in {catalog.name}.{schema.name}: {e}"
                    )
                    continue

                for table in tables:
                    if not table.name:
                        continue
                    tables_discovered += 1
                    full_name = f"{catalog.name}.{schema.name}.{table.name}"

                    # Validate query permission with LIMIT 0
                    if not self._can_query_table(catalog.name, schema.name, table.name):
                        self.logger.debug(f"Skipping {full_name} - no query permission")
                        continue

                    tables_queryable += 1
                    available_datasets.append(
                        PutAvailableDataset(
                            name=full_name,
                            dataset_locator=DatasetLocator(
                                fields=[
                                    DatasetLocatorField(
                                        key=DATABRICKS_DATASET_CATALOG_FIELD,
                                        value=catalog.name,
                                    ),
                                    DatasetLocatorField(
                                        key=DATABRICKS_DATASET_SCHEMA_FIELD,
                                        value=schema.name,
                                    ),
                                    DatasetLocatorField(
                                        key=ODBC_CONNECTOR_TABLE_NAME_FIELD,
                                        value=table.name,
                                    ),
                                ],
                            ),
                        )
                    )

        self.logger.info(
            f"Discovered {tables_queryable} queryable datasets out of {tables_discovered} total tables"
        )
        return PutAvailableDatasets(available_datasets=available_datasets)

    def dispose(self) -> None:
        """Dispose of the Databricks SQL engine to clean up connection pool."""
        if hasattr(self, "_engine") and self._engine:
            self._engine.dispose()
            self.logger.info("Databricks engine disposed successfully")
        # WorkspaceClient doesn't need explicit disposal
        self._workspace_client = None

    def __del__(self) -> None:
        """Cleanup method to ensure proper engine disposal."""
        try:
            self.dispose()
        except Exception:
            # Ignore errors during cleanup
            pass
