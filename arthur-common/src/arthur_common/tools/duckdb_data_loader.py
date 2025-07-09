import json
from typing import Any

import duckdb
import pandas as pd
from arthur_common.models.datasets import DatasetJoinKind
from arthur_common.models.schema_definitions import (
    DatasetListType,
    DatasetObjectType,
    DatasetScalarType,
    DatasetSchema,
    DType,
)
from dateutil.parser import parse
from fsspec import filesystem
from pydantic import BaseModel


class ColumnFormat(BaseModel):
    source_name: str
    alias: str
    format: str


class DuckDBOperator:
    """
    Loads data into a DuckDB table.

    If no schema is supplied, the output table will contain columns with names equal to the source names in the data.
    If a schema is applied, the column names in the output table will be aliases equal to the column id from the schema.
    This allows for consistent column naming across different data sources.
    """

    @staticmethod
    def load_data_to_duckdb(
        data: list[dict[str, Any]] | pd.DataFrame,
        preprocess_schema: bool = False,
        table_name: str = "inferences",
        conn: duckdb.DuckDBPyConnection | None = None,
        schema: DatasetSchema | None = None,
    ) -> duckdb.DuckDBPyConnection:
        if not conn:
            conn = duckdb.connect()

        if type(data) == list:
            DuckDBOperator._load_unstructured_data(data, table_name, conn, schema)
        elif type(data) == pd.DataFrame:
            DuckDBOperator._load_structured_data(
                data,
                preprocess_schema,
                table_name,
                conn,
                schema,
            )
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")
        return conn

    """
    Rename columns from ids to their friendly names based on schema.column_names
    """

    @staticmethod
    def apply_alias_mask(
        table_name: str,
        conn: duckdb.DuckDBPyConnection,
        schema: DatasetSchema,
    ) -> None:
        old_new_mask = {
            str(col_id): schema.column_names[col_id] for col_id in schema.column_names
        }
        DuckDBOperator._apply_alias_mask(table_name, conn, old_new_mask)

    @staticmethod
    def _apply_alias_mask(
        table_name: str,
        conn: duckdb.DuckDBPyConnection,
        old_new_mask: dict[str, str],
    ) -> None:
        for old, new in old_new_mask.items():
            # Don't quote the join column names, since they're already quoted as part of escape_identifier's output
            alter_query = f"ALTER TABLE {table_name} RENAME COLUMN {escape_identifier(old)} TO {escape_identifier(new)}"
            conn.sql(alter_query)

    @staticmethod
    def _load_unstructured_data(
        data: list[dict[str, Any]],
        table_name: str,
        conn: duckdb.DuckDBPyConnection,
        schema: DatasetSchema | None,
    ) -> None:
        with filesystem("memory").open(f"inferences.json", "w") as file:
            file.write(json.dumps(data))
        conn.register_filesystem(filesystem("memory"))

        if schema:
            column_formats = make_duckdb_dataset_schema(schema)

            key_value_pairs = [
                f"{escape_identifier(col.source_name)}: '{col.format}'"
                for col in column_formats
            ]
            stringified_schema = ", ".join([f"{kv}" for kv in key_value_pairs])
            stringified_schema = f"{{ {stringified_schema} }}"

            read_stmt = f"read_json('memory://inferences.json', format='array', columns={stringified_schema})"
        else:
            read_stmt = "read_json_auto('memory://inferences.json')"

        conn.sql(
            f"CREATE OR REPLACE TEMP TABLE {table_name} AS SELECT * FROM {read_stmt}",
        )

        if schema:
            old_new_mask = {}
            for col in column_formats:
                old_new_mask[col.source_name] = col.alias
            DuckDBOperator._apply_alias_mask(table_name, conn, old_new_mask)

    @staticmethod
    def _load_structured_data(
        data: pd.DataFrame,
        preprocess_schema: bool,
        table_name: str,
        conn: duckdb.DuckDBPyConnection,
        schema: DatasetSchema | None,
    ) -> None:
        if preprocess_schema:
            data = DuckDBOperator._preprocess_dataframe_schema_inference(data)

        if schema:
            column_formats = make_duckdb_dataset_schema(schema)

            key_value_pairs = [
                f"{escape_identifier(col.source_name)} {col.format}"
                for col in column_formats
            ]
            stringified_schema = ", ".join([f"{kv}" for kv in key_value_pairs])
            create_table_stmt = (
                f"CREATE OR REPLACE TEMP TABLE {table_name} ({stringified_schema});"
            )
            conn.sql(create_table_stmt)
            conn.sql(f"INSERT INTO {table_name} SELECT * FROM data")

            old_new_mask = {}
            for col in column_formats:
                old_new_mask[col.source_name] = col.alias
            DuckDBOperator._apply_alias_mask(table_name, conn, old_new_mask)

        else:
            conn.sql(f"CREATE OR REPLACE TEMP TABLE {table_name} AS SELECT * FROM data")

    """
        Preprocess to make smarter type inferences. Pandas and json recognize very little beyond primitives out of the box. We can support a little more with a little effort like:
        1. Datetimes

        Modifies the input data in place to have smarter types than pandas will natively infer
    """

    @staticmethod
    def _preprocess_dataframe_schema_inference(data: pd.DataFrame) -> pd.DataFrame:
        datetime_columns = _infer_dataframe_datetime_columns(data)
        for column in datetime_columns:
            try:
                data[column] = pd.to_datetime(data[column])
            except Exception:
                # we're using best-effort to infer datetime columns, but just in case we got it wrong, move on
                continue

        return data

    @staticmethod
    def join_tables(
        conn: duckdb.DuckDBPyConnection,
        table_name: str,
        table_1: str,
        table_2: str,
        table_1_join_key: str,
        table_2_join_key: str,
        join_kind: DatasetJoinKind = DatasetJoinKind.INNER,
    ) -> None:
        match join_kind:
            case DatasetJoinKind.INNER:
                join = "INNER"
            case DatasetJoinKind.LEFT_OUTER:
                join = "LEFT"
            case DatasetJoinKind.RIGHT_OUTER:
                join = "RIGHT"
            case DatasetJoinKind.OUTER:
                join = "FULL OUTER"
            case _:
                raise NotImplementedError(f"Join kind {join_kind} is not supported.")

        # Don't quote the join column names, since they're already quoted as part of escape_identifier's output
        join_query = f"""
        CREATE TABLE {table_name} AS
        SELECT *
        FROM {table_1} a
        {join} JOIN {table_2} b
        ON a.{escape_identifier(table_1_join_key)} = b.{escape_identifier(table_2_join_key)}
        """

        conn.sql(join_query)


def _infer_dataframe_datetime_columns(df: pd.DataFrame, n: int = 100) -> list[str]:
    """
    Infer datetime columns in a pandas DataFrame by parsing non-null values in the first n rows. Return the column names believed to be datetime type

    Parameters:
        df (pandas.DataFrame): Input DataFrame.
        n (int): Number of non-null rows to consider for each column. Default is 100.

    Returns:
        datetime_columns (list): List of column names inferred to be datetime.
    """
    datetime_columns = []

    for column in df.columns:
        non_null_values = df[column].dropna().head(n)
        if non_null_values.empty:
            continue

        # Try parsing each non-null value in the column
        try:
            parsed_values = non_null_values.apply(lambda x: parse(x))

            # If parsing succeeds for all values, consider the column as datetime
            if parsed_values.notnull().all():
                datetime_columns.append(column)
        except:
            # If parsing fails for any value, move to the next column
            continue

    return datetime_columns


"""
Returns a list of ColumnFormat. Depending on structure / unstructured data, we need to format the root columns differently, so return the raw forms.

See the subtle differences between

CREATE TABLE users (
    userID BIGINT,
    userName VARCHAR,
    hobbies ARRAY<VARCHAR>
);

and

SELECT *
FROM read_json('todos.json',
               format = 'array',
               columns = {userId: 'UBIGINT',
                          userName: 'VARCHAR',
                          hobbies: 'ARRAY<VARCHAR>'});

"""


def make_duckdb_dataset_schema(schema: DatasetSchema) -> list[ColumnFormat]:
    details = []
    for col in schema.columns:
        format = _make_schema(col.definition)
        details.append(
            ColumnFormat(source_name=col.source_name, alias=str(col.id), format=format),
        )

    return details


def _make_schema(
    schema_node: DatasetObjectType | DatasetListType | DatasetScalarType,
) -> str:
    if isinstance(schema_node, DatasetObjectType):
        details = {}
        for col, value in schema_node.object.items():
            details[col] = _make_schema(value)
        key_value_pairs = [
            f"{escape_identifier(col)} {value}" for col, value in details.items()
        ]
        return f"STRUCT({', '.join(key_value_pairs)})"

    elif isinstance(schema_node, DatasetListType):
        return f"{_make_schema(schema_node.items)}[]"
    elif isinstance(schema_node, DatasetScalarType):
        match schema_node.dtype:
            case DType.INT:
                return "BIGINT"
            case DType.FLOAT:
                return "DOUBLE"
            case DType.BOOL:
                return "BOOLEAN"
            case DType.STRING | DType.IMAGE:
                return "VARCHAR"
            case DType.UUID:
                return "UUID"
            case DType.TIMESTAMP:
                return "TIMESTAMP"
            case DType.JSON:
                return "JSON"
            case _:
                raise ValueError(f"Unknown mapping for DType {schema_node.dtype}")
    else:
        raise NotImplementedError(
            f"Schema conversion not implemented for node type {type(schema_node)}",
        )


def escape_identifier(identifier: str) -> str:
    """
    Escape an identifier (e.g., column name) for use in a SQL query.
    This method handles special characters and ensures proper quoting.
    """
    # Replace any double quotes with two double quotes
    escaped = identifier.replace('"', '""')
    # Wrap the entire identifier in double quotes and return
    return f'"{escaped}"'


def escape_str_literal(literal: str) -> str:
    """
    Escape a duckDB string literal for use in a SQL query.
    https://duckdb.org/docs/stable/sql/data_types/literal_types.html#escape-string-literals
    """
    # replace any single quotes with two single quotes
    escaped = literal.replace("'", "''")
    # Wrap the entire identifier in single quotes and return
    return f"'{escaped}'"
