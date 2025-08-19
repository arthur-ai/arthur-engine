from datetime import datetime
from enum import Enum
from logging import Logger
from typing import Any, Callable, List

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
    ODBC_CONNECTOR_DATABASE_FIELD,
    ODBC_CONNECTOR_DIALECT_FIELD,
    ODBC_CONNECTOR_DRIVER_FIELD,
    ODBC_CONNECTOR_HOST_FIELD,
    ODBC_CONNECTOR_PASSWORD_FIELD,
    ODBC_CONNECTOR_PORT_FIELD,
    ODBC_CONNECTOR_TABLE_NAME_FIELD,
    ODBC_CONNECTOR_USERNAME_FIELD,
    SNOWFLAKE_CONNECTOR_AUTHENTICATOR_FIELD,
    SNOWFLAKE_CONNECTOR_PRIVATE_KEY_FIELD,
    SNOWFLAKE_CONNECTOR_PRIVATE_KEY_PASSPHRASE_FIELD,
    SNOWFLAKE_CONNECTOR_ROLE_FIELD,
    SNOWFLAKE_CONNECTOR_SCHEMA_FIELD,
    SNOWFLAKE_CONNECTOR_WAREHOUSE_FIELD,
    ConnectorPaginationOptions,
)
from connectors.connector import Connector
from dateutil import parser
from pydantic import SecretStr
from sqlalchemy import (
    Column,
    MetaData,
    Table,
    and_,
    create_engine,
    desc,
    inspect,
    select,
    text,
)
from sqlalchemy.engine import Engine
from sqlalchemy.sql import Select
from sqlalchemy.sql.elements import BinaryExpression
from tools.schema_interpreters import primary_timestamp_col_name


class DialectType(Enum):
    """Enum for database dialect types to avoid string duplication."""

    GENERIC_ODBC = "generic odbc"
    GENERIC_ODBC_PYODBC = "generic odbc (pyodbc)"
    POSTGRESQL_NATIVE = "postgresql native"
    POSTGRESQL_NATIVE_PSYCOPG = "postgresql native (psycopg)"
    MYSQL_NATIVE = "mysql native"
    MYSQL_NATIVE_PYMYSQL = "mysql native (pymysql)"
    ORACLE_NATIVE = "oracle native"
    ORACLE_NATIVE_CX_ORACLE = "oracle native (cx_oracle)"
    SNOWFLAKE_NATIVE = "snowflake native"
    SNOWFLAKE_NATIVE_CONNECTOR = "snowflake native (snowflake-connector-python)"


class ODBCConnector(Connector):
    """
    A universal database connector that can work with various database systems including Snowflake.
    Supports different connection string formats and database-specific configurations.
    """

    def __init__(self, connector_config: ConnectorSpec, logger: Logger) -> None:
        connector_fields = {f.key: f.value for f in connector_config.fields}

        self.host: str = connector_fields[ODBC_CONNECTOR_HOST_FIELD]
        self.port: str = connector_fields.get(ODBC_CONNECTOR_PORT_FIELD, "")
        self.database: str = connector_fields.get(ODBC_CONNECTOR_DATABASE_FIELD, "")
        self.username: str = connector_fields.get(ODBC_CONNECTOR_USERNAME_FIELD, "")
        self.password: SecretStr = SecretStr(
            connector_fields.get(ODBC_CONNECTOR_PASSWORD_FIELD, ""),
        )
        self.driver: str = connector_fields.get(ODBC_CONNECTOR_DRIVER_FIELD, "")
        self.dialect: str = connector_fields.get(ODBC_CONNECTOR_DIALECT_FIELD, "")

        # Snowflake-specific fields
        self.schema: str = connector_fields.get(
            SNOWFLAKE_CONNECTOR_SCHEMA_FIELD,
            "PUBLIC",
        )
        self.warehouse: str = connector_fields.get(
            SNOWFLAKE_CONNECTOR_WAREHOUSE_FIELD,
            "",
        )
        self.role: str = connector_fields.get(SNOWFLAKE_CONNECTOR_ROLE_FIELD, "")
        self.authenticator: str = connector_fields.get(
            SNOWFLAKE_CONNECTOR_AUTHENTICATOR_FIELD,
            "snowflake",
        )
        self.private_key: str = connector_fields.get(
            SNOWFLAKE_CONNECTOR_PRIVATE_KEY_FIELD,
            "",
        )
        self.private_key_passphrase: str = connector_fields.get(
            SNOWFLAKE_CONNECTOR_PRIVATE_KEY_PASSPHRASE_FIELD,
            "",
        )

        # Build connection string based on available fields
        conn_str = self._build_connection_string()
        engine_url = self._build_engine_url(conn_str)
        self.engine: Engine = create_engine(engine_url)
        self.metadata = MetaData()
        self.logger = logger

    def _build_engine_url(self, conn_str: str) -> str:
        """
        Build the SQLAlchemy engine URL based on dialect and driver configuration.
        """
        dialect_lower = self.dialect.lower()

        # Dictionary mapping dialect patterns to their URL building functions
        # Aligned with schema allowed values
        dialect_handlers = {
            DialectType.GENERIC_ODBC_PYODBC.value: self._build_odbc_url,
            DialectType.POSTGRESQL_NATIVE_PSYCOPG.value: self._build_postgresql_native_url,
            DialectType.MYSQL_NATIVE_PYMYSQL.value: self._build_mysql_native_url,
            DialectType.ORACLE_NATIVE_CX_ORACLE.value: self._build_oracle_native_url,
            DialectType.SNOWFLAKE_NATIVE_CONNECTOR.value: self._build_snowflake_url,
        }

        # Find matching dialect handler
        for dialect_pattern, handler_func in dialect_handlers.items():
            if dialect_pattern in dialect_lower:
                if dialect_pattern == DialectType.GENERIC_ODBC_PYODBC.value:
                    return handler_func(conn_str)  # type: ignore
                return handler_func()  # type: ignore

        # Default to generic ODBC (pyodbc) - fallback or explicitly chosen
        # This handles cases where no dialect is specified or an invalid dialect is provided
        return self._build_odbc_url(conn_str)

    def _build_odbc_url(self, conn_str: str | None = None) -> str:
        """Build ODBC URL using pyodbc."""
        # Build connection string if not provided
        if conn_str is None:
            conn_str = self._build_connection_string()

        if not self.driver:
            # Default to SQL Server if no driver specified
            return f"mssql+pyodbc:///?odbc_connect={conn_str}"

        driver_lower = self.driver.lower()

        # Map driver to SQLAlchemy dialect
        driver_mapping = {
            "sql server": "mssql",
            "mssql": "mssql",
            "mysql": "mysql",
            "postgresql": "postgresql",
            "postgres": "postgresql",
            "psql": "postgresql",
            "oracle": "oracle",
        }

        # Find matching dialect based on driver
        for driver_key, dialect in driver_mapping.items():
            if driver_key in driver_lower:
                return f"{dialect}+pyodbc:///?odbc_connect={conn_str}"

        # Default to generic ODBC
        return f"mssql+pyodbc:///?odbc_connect={conn_str}"

    def _build_postgresql_native_url(self) -> str:
        """Build PostgreSQL native URL using psycopg."""
        return self._build_native_url("postgresql+psycopg", "5432")

    def _build_mysql_native_url(self) -> str:
        """Build MySQL native URL using pymysql."""
        return self._build_native_url("mysql+pymysql", "3306")

    def _build_oracle_native_url(self) -> str:
        """Build Oracle native URL using cx_oracle."""
        return self._build_native_url("oracle+cx_oracle", "1521")

    def _build_snowflake_url(self) -> str:
        """Build Snowflake URL using snowflake-connector-python."""
        if not self.host:
            raise ValueError("Host is required for Snowflake connection.")

        username = self.username if self.username else ""
        password = self.password.get_secret_value() if self.password else ""
        account = self.host  # Use host as account identifier

        # Build authentication part
        if password:
            url_parts = [f"snowflake://{username}:{password}@{account}"]
        else:
            url_parts = [f"snowflake://{username}@{account}"]

        # Add database and schema
        if self.database:
            url_parts.append(f"/{self.database}")
            if self.schema:
                url_parts.append(f"/{self.schema}")

        # Build query parameters
        query_params = []
        if self.warehouse:
            query_params.append(f"warehouse={self.warehouse}")
        if self.role:
            query_params.append(f"role={self.role}")
        if self.authenticator != "snowflake":
            query_params.append(f"authenticator={self.authenticator}")
        if self.private_key:
            query_params.append(f"private_key={self.private_key}")
            if self.private_key_passphrase:
                query_params.append(
                    f"private_key_passphrase={self.private_key_passphrase}",
                )

        # Combine URL parts
        url = "".join(url_parts)
        if query_params:
            url += "?" + "&".join(query_params)

        return url

    def _build_native_url(self, dialect: str, default_port: str) -> str:
        """Build native database URL with common logic."""
        if not self.host:
            raise ValueError(f"Host is required for {dialect} native connection")

        port = self.port if self.port else default_port
        username = self.username if self.username else ""
        password = self.password.get_secret_value() if self.password else ""
        database = self.database if self.database else ""

        if username and password:
            return f"{dialect}://{username}:{password}@{self.host}:{port}/{database}"
        elif username:
            return f"{dialect}://{username}@{self.host}:{port}/{database}"
        else:
            return f"{dialect}://{self.host}:{port}/{database}"

    def _build_connection_string(self) -> str:
        """
        Build an ODBC connection string based on available configuration fields.
        Supports different database systems with their specific connection string formats.
        """
        parts = []

        if self.driver:
            parts.append(f"DRIVER={{{self.driver}}}")

        if self.host:
            if self.port:
                parts.append(f"SERVER={self.host},{self.port}")
            else:
                parts.append(f"SERVER={self.host}")

        if self.database:
            parts.append(f"DATABASE={self.database}")

        if self.username:
            parts.append(f"UID={self.username}")

        if self.password:
            parts.append(f"PWD={self.password.get_secret_value()}")

        return ";".join(parts) + ";"

    def _get_default_schema(self) -> str | None:
        """Get the default schema based on the database dialect."""
        dialect_lower = self.dialect.lower()

        # Use a mapping approach to reduce cognitive complexity
        schema_handlers = {
            DialectType.POSTGRESQL_NATIVE.value: self._get_postgresql_schema,
            DialectType.MYSQL_NATIVE.value: self._get_mysql_schema,
            DialectType.ORACLE_NATIVE.value: self._get_oracle_schema,
            DialectType.SNOWFLAKE_NATIVE.value: self._get_snowflake_schema,
            DialectType.GENERIC_ODBC.value: self._get_generic_odbc_schema,
        }

        # Find the appropriate handler for the dialect
        for dialect_pattern, handler in schema_handlers.items():
            if dialect_pattern in dialect_lower:
                return handler()

        # Fallback for unknown dialects
        return None

    def _get_postgresql_schema(self) -> str:
        """Get PostgreSQL default schema."""
        return "public"

    def _get_mysql_schema(self) -> None:
        """Get MySQL schema (MySQL doesn't use schemas)."""
        return None

    def _get_oracle_schema(self) -> str | None:
        """Get Oracle default schema."""
        return self.username if self.username else None

    def _get_snowflake_schema(self) -> str:
        """Get Snowflake default schema."""
        return self.schema if self.schema else "PUBLIC"

    def _get_generic_odbc_schema(self) -> str | None:
        """Get generic ODBC schema based on driver."""
        driver_lower = self.driver.lower()

        driver_schema_map = {
            "mssql": "dbo",
            "sql server": "dbo",
            "postgresql": "public",
            "postgres": "public",
        }

        for driver_pattern, schema in driver_schema_map.items():
            if driver_pattern in driver_lower:
                return schema

        return None

    def _paginate_query(
        self,
        stmt: Select[Any],
        pagination_options: ConnectorPaginationOptions | None = None,
    ) -> Select[Any]:
        if not pagination_options:
            return stmt
        if pagination_options.page < 1:
            raise ValueError(
                "Arthur pagination is 1-indexed. Please provide a page number >= 1.",
            )

        return stmt.offset(
            (pagination_options.page - 1) * pagination_options.page_size,
        ).limit(pagination_options.page_size)

    def _get_filter_condition(self, col: Column[Any], op: str, val: Any) -> Any | None:
        """Apply a single filter operation to a column."""
        # Handle type conversion for timestamp columns
        converted_val = self._convert_filter_value(col, val)

        op_handlers: dict[str, Callable[[], BinaryExpression[Any]]] = {
            "equals": lambda: col == converted_val,
            "not_equals": lambda: col != converted_val,
            "less_than": lambda: col < converted_val,
            "less_than_or_equal": lambda: col <= converted_val,
            "greater_than": lambda: col > converted_val,
            "greater_than_or_equal": lambda: col >= converted_val,
            "in": lambda: col.in_(
                converted_val if isinstance(converted_val, list) else [converted_val],
            ),
            "not_in": lambda: col.notin_(
                converted_val if isinstance(converted_val, list) else [converted_val],
            ),
        }

        handler = op_handlers.get(op.lower())
        if handler is None:
            self.logger.warning(f"Unsupported filter operator: {op}")
            return None

        return handler()

    def _convert_filter_value(self, col: Column[Any], val: Any) -> Any:
        """Convert filter value to appropriate type based on column type."""
        if val is None:
            return val

        # Get column type information
        col_type = getattr(col.type, "__class__", None)
        if col_type is None:
            return val

        col_type_name = col_type.__name__.lower()

        # Handle timestamp/date types
        if any(
            timestamp_type in col_type_name
            for timestamp_type in ["timestamp", "datetime", "date"]
        ):
            if isinstance(val, str):
                try:
                    # Parse string timestamp to datetime
                    return parser.parse(val)
                except (ValueError, TypeError) as e:
                    self.logger.warning(
                        f"Could not parse timestamp string '{val}': {e}",
                    )
                    return val
            elif isinstance(val, list):
                # Handle list of values (for IN/NOT_IN operations)
                return [self._convert_filter_value(col, item) for item in val]

        return val

    def _apply_filters(
        self,
        table: Table,
        stmt: Select[Any],
        filters: List[DataResultFilter],
    ) -> Select[Any]:
        conditions = []
        skipped_filters = 0

        for f in filters:
            col = table.c.get(f.field_name)
            if col is None:
                self.logger.warning(
                    f"Filter field '{f.field_name}' not found in table '{table.name}'; skipping filter",
                )
                skipped_filters += 1
                continue

            condition = self._get_filter_condition(col, f.op, f.value)
            if condition is not None:
                conditions.append(condition)
            else:
                skipped_filters += 1

        if conditions:
            stmt = stmt.where(and_(*conditions))

        if skipped_filters > 0:
            self.logger.info(
                f"Applied {len(conditions)} filters, skipped {skipped_filters} filters on table '{table.name}'",
            )

        return stmt

    def _build_fetch_stmt(
        self,
        table: Table,
        timestamp_col: str,
        start_time: datetime,
        end_time: datetime,
        filters: List[DataResultFilter] | None = None,
        pagination_options: ConnectorPaginationOptions | None = None,
    ) -> Select[Any]:
        col = table.c[timestamp_col]
        stmt = (
            select(table)
            .where(and_(col >= start_time, col < end_time))
            .order_by(desc(col))
        )
        if filters:
            stmt = self._apply_filters(table, stmt, filters)
        stmt = self._paginate_query(stmt, pagination_options)
        return stmt

    def read(
        self,
        dataset: Dataset | AvailableDataset,
        start_time: datetime,
        end_time: datetime,
        filters: List[DataResultFilter] | None = None,
        pagination_options: ConnectorPaginationOptions | None = None,
    ) -> pd.DataFrame:
        if not dataset.dataset_locator:
            raise ValueError(f"Dataset {dataset.id} has no locator.")

        locator = {f.key: f.value for f in dataset.dataset_locator.fields}
        table_name = locator[ODBC_CONNECTOR_TABLE_NAME_FIELD]

        # For Snowflake, use schema if specified
        if DialectType.SNOWFLAKE_NATIVE.value in self.dialect.lower() and self.schema:
            table = Table(
                table_name,
                self.metadata,
                schema=self.schema,
                autoload_with=self.engine,
            )
        else:
            table = Table(table_name, self.metadata, autoload_with=self.engine)

        try:
            ts_col_name = primary_timestamp_col_name(dataset)
            # Timestamp column found - use timestamp range filtering
            stmt = self._build_fetch_stmt(
                table,
                ts_col_name,
                start_time,
                end_time,
                filters,
                pagination_options,
            )
        except ValueError:
            # No timestamp column found - use fallback logic with pagination
            self.logger.warning(
                "Primary timestamp column not found; using filters/pagination only.",
            )
            if not pagination_options:
                raise ValueError(
                    "Pagination options not provided and timestamp range not set. Cannot fetch all data "
                    "without providing a limit or time range.",
                )
            stmt = select(table)

            if filters:
                stmt = self._apply_filters(table, stmt, filters)
            stmt = self._paginate_query(stmt, pagination_options)

        df = pd.read_sql(stmt, self.engine)
        return df

    def test_connection(self) -> ConnectorCheckResult:
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))

                # For Snowflake, test additional setup commands
                if DialectType.SNOWFLAKE_NATIVE.value in self.dialect.lower():
                    # Test warehouse access if specified
                    if self.warehouse:
                        conn.execute(text(f"USE WAREHOUSE {self.warehouse}"))

                    # Test database access if specified
                    if self.database:
                        conn.execute(text(f"USE DATABASE {self.database}"))

                    # Test schema access if specified
                    if self.schema:
                        conn.execute(text(f"USE SCHEMA {self.schema}"))

        except Exception as e:
            self.logger.error("Connection test failed.", exc_info=e)
            return ConnectorCheckResult(
                connection_check_outcome=ConnectorCheckOutcome.FAILED,
                failure_reason=f"ODBC connection failed: {e}",
            )
        return ConnectorCheckResult(
            connection_check_outcome=ConnectorCheckOutcome.SUCCEEDED,
        )

    def list_datasets(
        self,
    ) -> PutAvailableDatasets:
        inspector = inspect(self.engine)
        schema = self._get_default_schema()

        # For Snowflake, use the schema field if specified
        if DialectType.SNOWFLAKE_NATIVE.value in self.dialect.lower() and self.schema:
            schema = self.schema

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
