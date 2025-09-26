from datetime import datetime
from logging import Logger
from typing import Any, Callable, Dict, List, Tuple, Union

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
    ConnectorPaginationOptions,
)
from connectors.connector import Connector
from dateutil import parser
from pydantic import SecretStr
from sqlalchemy import (
    URL,
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


class ODBCConnector(Connector):
    """
    A general ODBC connector that can work with various database systems.
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

        # Build connection string based on available fields
        conn_str = self._build_connection_string()
        engine_url, connect_args = self._build_engine_url(conn_str)
        self.engine: Engine = create_engine(
            engine_url,
            echo=False,
            connect_args=connect_args,
        )
        self.metadata = MetaData()
        self.logger = logger

    def _build_engine_url(
        self,
        conn_str: str,
    ) -> Tuple[Union[str, URL], Dict[str, Any]]:
        """
        Build the SQLAlchemy engine URL based on dialect and driver configuration.
        Returns the engine URL and any connect args that need to be passed to the engine.
        """
        dialect_lower = self.dialect.lower()

        # Dictionary mapping dialect patterns to their URL building functions
        # Aligned with schema allowed values
        dialect_handlers = {
            "generic odbc (pyodbc)": self._build_odbc_url,
            "postgresql native (psycopg)": self._build_postgresql_native_url,
            "mysql native (pymysql)": self._build_mysql_native_url,
            "oracle native (cx_oracle)": self._build_oracle_native_url,
        }

        # Find matching dialect handler
        for dialect_pattern, handler_func in dialect_handlers.items():
            if dialect_pattern in dialect_lower:
                if dialect_pattern == "generic odbc (pyodbc)":
                    return handler_func(conn_str)  # type: ignore
                return handler_func()  # type: ignore

        # Default to generic ODBC (pyodbc) - fallback or explicitly chosen
        # This handles cases where no dialect is specified or an invalid dialect is provided
        return self._build_odbc_url(conn_str), {}

    def _build_odbc_url(
        self,
        conn_str: str | None = None,
    ) -> Tuple[Union[str, URL], Dict[str, Any]]:
        """Build ODBC URL using pyodbc."""
        # Build connection string if not provided
        if conn_str is None:
            conn_str = self._build_connection_string()

        if not self.driver:
            # Default to SQL Server if no driver specified
            return f"mssql+pyodbc:///?odbc_connect={conn_str}", {}

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
                return f"{dialect}+pyodbc:///?odbc_connect={conn_str}", {}

        # Default to generic ODBC
        return f"mssql+pyodbc:///?odbc_connect={conn_str}", {}

    def _build_postgresql_native_url(self) -> Tuple[Union[str, URL], Dict[str, Any]]:
        """Build PostgreSQL native URL using psycopg."""
        return self._build_native_url("postgresql+psycopg", "5432")

    def _build_mysql_native_url(self) -> Tuple[Union[str, URL], Dict[str, Any]]:
        """Build MySQL native URL using pymysql."""
        return self._build_native_url("mysql+pymysql", "3306")

    def _build_oracle_native_url(self) -> Tuple[Union[str, URL], Dict[str, Any]]:
        """Build Oracle native URL using cx_oracle."""
        return self._build_native_url("oracle+cx_oracle", "1521")

    def _build_native_url(
        self,
        dialect: str,
        default_port: str,
    ) -> Tuple[Union[str, URL], Dict[str, Any]]:
        """Build native database URL with common logic."""
        if not self.host:
            raise ValueError(f"Host is required for {dialect} native connection")

        port = self.port if self.port else default_port
        username = self.username if self.username else ""
        password = self.password.get_secret_value() if self.password else ""
        database = self.database if self.database else ""

        if username and password:
            return (
                f"{dialect}://{username}:{password}@{self.host}:{port}/{database}",
                {},
            )
        elif username:
            return f"{dialect}://{username}@{self.host}:{port}/{database}", {}
        else:
            return f"{dialect}://{self.host}:{port}/{database}", {}

    def _build_connection_string(self) -> str:
        """
        Build an ODBC connection string based on available configuration fields.
        Supports different database systems with their specific connection string formats.
        """
        parts = []

        if self.driver:
            driver_lower = self.driver.lower()
            if "17" in driver_lower:
                driver = "ODBC Driver 17 for SQL Server"
            elif "18" in driver_lower:
                driver = "ODBC Driver 18 for SQL Server"
            else:
                driver = self.driver
            parts.append(f"DRIVER={{{driver}}}")

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

        # Database-specific schema defaults - aligned with dialect handlers
        if "postgresql native" in dialect_lower:
            return "public"  # PostgreSQL default schema
        elif "mysql native" in dialect_lower:
            return None  # MySQL doesn't use schemas, uses database name directly
        elif "oracle native" in dialect_lower:
            return (
                self.username if self.username else None
            )  # Oracle uses username as default schema
        elif "generic odbc" in dialect_lower:
            # For generic ODBC, try to determine from driver or use None
            driver_lower = self.driver.lower()
            if "mssql" in driver_lower or "sql server" in driver_lower:
                return "dbo"  # SQL Server default schema
            elif "postgresql" in driver_lower or "postgres" in driver_lower:
                return "public"  # PostgreSQL default schema
            else:
                return None  # Generic ODBC - use None
        else:
            # Fallback for unknown dialects
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
