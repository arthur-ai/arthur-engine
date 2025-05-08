from typing import Any
from uuid import uuid4

import pandas as pd
from arthur_common.models.schema_definitions import (
    DatasetColumn,
    DatasetListType,
    DatasetObjectType,
    DatasetScalarType,
    DatasetSchema,
    DType,
    ScopeSchemaTag,
)
from arthur_common.tools.duckdb_data_loader import DuckDBOperator, escape_identifier


class SchemaInferer:
    def __init__(self, data: list[dict[str, Any]] | pd.DataFrame):
        self.conn = DuckDBOperator.load_data_to_duckdb(
            data,
            preprocess_schema=True,
            table_name="root",
        )

    def infer_schema(self) -> DatasetSchema:
        columns = self._infer_schema()
        schema = DatasetSchema(columns=[], alias_mask={})
        for key, definition in columns.object.items():
            schema.columns.append(
                DatasetColumn(id=uuid4(), source_name=key, definition=definition),
            )
        # Close connection to destroy all temp tables and free up memory
        self.conn.close()
        return schema

    def _infer_nested_schema(self, col_name: str, table: str) -> DatasetObjectType:
        escaped_col = escape_identifier(col_name)
        self.conn.sql(
            f"CREATE OR REPLACE TEMP TABLE {escaped_col} AS SELECT UNNEST({escaped_col}) as {escaped_col} FROM {table}",
        )
        return self._infer_schema(escaped_col)

    def _infer_schema(self, table: str = "root") -> DatasetObjectType:
        ddb_schema: list[tuple[Any, Any, Any]] = self.conn.sql(
            f"DESCRIBE {table}",
        ).fetchall()

        obj = DatasetObjectType(id=uuid4(), object={}, nullable=False)
        timestamp_cols = []

        for column in ddb_schema:
            col_type, col_name, col_nullable = (
                str(column[1]),
                str(column[0]),
                str(column[2]) == "YES",
            )
            col_is_list = col_type[-2:] == "[]"
            col_type = col_type.replace("[]", "")

            # Handle structs / lists recursively
            if col_is_list:
                schema = self._infer_nested_schema(col_name, table)
                obj.object[col_name] = DatasetListType(
                    id=uuid4(),
                    items=schema[col_name],
                    nullable=col_nullable,
                )
            elif "STRUCT" in col_type:
                schema = self._infer_nested_schema(col_name, table)
                schema.nullable = col_nullable
                obj.object[col_name] = schema
            else:
                scalar_schema = DatasetScalarType(id=uuid4(), dtype=DType.UNDEFINED)
                match col_type:
                    case "UUID":
                        scalar_schema.dtype = DType.UUID
                    case "VARCHAR":
                        scalar_schema.dtype = DType.STRING
                    case "BIGINT" | "INTEGER":
                        scalar_schema.dtype = DType.INT
                    case "DOUBLE" | "FLOAT":
                        scalar_schema.dtype = DType.FLOAT
                    case "BOOLEAN":
                        scalar_schema.dtype = DType.BOOL
                    case "JSON":
                        # keep duckDB's json type in case the customer's data doesn't fit in well-structured types
                        # an example is a JSON list like ["str", 0.234], because arrays can only have a single type
                        # in duckDB
                        scalar_schema.dtype = DType.JSON
                    case "DATE":
                        scalar_schema.dtype = DType.DATE
                    case "TIMESTAMP_NS" | "TIMESTAMP WITH TIME ZONE" | "TIMESTAMP":
                        scalar_schema.dtype = DType.TIMESTAMP
                        timestamp_cols.append(scalar_schema)
                    case _:
                        raise NotImplementedError(f"Type {col_type} not mappable.")
                obj.object[col_name] = scalar_schema

        # auto assign primary timestamp tag if there's only one timestamp column
        if len(timestamp_cols) == 1:
            timestamp_col = timestamp_cols[0]
            timestamp_col.tag_hints.append(ScopeSchemaTag.PRIMARY_TIMESTAMP)

        return obj
