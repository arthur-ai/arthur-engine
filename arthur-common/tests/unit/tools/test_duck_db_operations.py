import os
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import pandas as pd
import pytest
from arthur_common.models.schema_definitions import (
    DatasetColumn,
    DatasetListType,
    DatasetObjectType,
    DatasetScalarType,
    DatasetSchema,
    DType,
)
from arthur_common.tools.duckdb_data_loader import DuckDBOperator


def test_dataset_joins():
    current_dir = os.path.dirname(__file__)
    inferences_path = os.path.join(current_dir, "../../test_data/balloons/flights.csv")
    gt_path = os.path.join(current_dir, "../../test_data/balloons/ground_truth.csv")
    inferences = pd.read_csv(inferences_path)
    gt = pd.read_csv(gt_path)

    conn = DuckDBOperator.load_data_to_duckdb(inferences, table_name="inferences")
    conn = DuckDBOperator.load_data_to_duckdb(gt, table_name="gt", conn=conn)

    DuckDBOperator.join_tables(
        conn,
        "joined",
        "inferences",
        "gt",
        "flight id",
        "flight id",
        "inner",
    )

    res = conn.sql("SELECT count(*) FROM joined").fetchall()
    assert res[0][0] == 850

    res = conn.sql(
        "SELECT count(*) as c FROM joined group by crashed order by crashed desc",
    ).to_df()
    assert res["c"][0] == 253
    assert res["c"][1] == 597


test_data_1 = {"pk_col": [1, 2, 3], "col_1": ["A", "B", "C"]}
df1 = pd.DataFrame(test_data_1)

test_data_2 = {"pk_col": [2, 3, 4], "col_2": ["W", "X", "Y"]}
df2 = pd.DataFrame(test_data_2)

test_data_3 = {"pk_col": [0, 3, 3], "col_3": ["I", "J", "K"]}
df3 = pd.DataFrame(test_data_2)


@pytest.mark.parametrize(
    "left_df, right_df, join_kind, expected_count",
    [(df1, df2, "inner", 2), (df1, df2, "left_outer", 3), (df1, df3, "inner", 2)],
)
def test_dataset_join_kinds(
    left_df: pd.DataFrame,
    right_df: pd.DataFrame,
    join_kind: str,
    expected_count: int,
):
    conn = DuckDBOperator.load_data_to_duckdb(left_df, table_name="left_table")
    conn = DuckDBOperator.load_data_to_duckdb(
        right_df,
        table_name="right_table",
        conn=conn,
    )

    DuckDBOperator.join_tables(
        conn,
        "joined",
        "left_table",
        "right_table",
        "pk_col",
        "pk_col",
        join_kind,
    )

    res = conn.sql("SELECT count(*) FROM joined").fetchall()
    assert res[0][0] == expected_count


def test_simple_load_data_with_schema():
    schema = DatasetSchema(
        alias_mask={},
        columns=[
            DatasetColumn(
                id=uuid4(),
                source_name="id",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.UUID),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="timestamp",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.TIMESTAMP),
            ),
        ],
    )

    data = [
        {
            "id": "991ff637-2c13-4289-ba17-a23c1c2b20b9",
            "timestamp": "2024-07-29T13:46:12+0000",
        },
        {
            "id": "991ff637-2c13-4289-ba17-a23c1c2b20b8",
            "timestamp": "2024-07-28T13:46:12+0000",
        },
    ]

    conn = DuckDBOperator.load_data_to_duckdb(
        data,
        preprocess_schema=False,
        schema=schema,
    )
    results = conn.sql("SELECT * FROM inferences").fetchall()
    assert len(results) == 2

    # Assert values took on the type defined in the schema, (uuid, datetime) and not the raw types (str, str)
    for row in results:
        assert type(row[0]) == UUID
        assert type(row[1]) == datetime


def test_unstructured_nullable_columns_created():
    schema = DatasetSchema(
        alias_mask={},
        columns=[
            DatasetColumn(
                id=uuid4(),
                source_name="id",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.UUID),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="timestamp",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.TIMESTAMP),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="obj",
                definition=DatasetObjectType(
                    id=uuid4(),
                    object={
                        # use name with dash to test nested column names are properly delimited in duckdb—if they
                        # aren't, this name will cause an error
                        "obj-2": DatasetListType(
                            id=uuid4(),
                            items=DatasetScalarType(id=uuid4(), dtype=DType.INT),
                        ),
                    },
                ),
            ),
        ],
    )
    data = [
        {
            "id": "991ff637-2c13-4289-ba17-a23c1c2b20b9",
            "timestamp": "2024-07-29T13:46:12+0000",
        },
        {
            "id": "991ff637-2c13-4289-ba17-a23c1c2b20b8",
            "timestamp": "2024-07-28T13:46:12+0000",
        },
    ]

    conn = DuckDBOperator.load_data_to_duckdb(
        data,
        preprocess_schema=False,
        schema=schema,
    )
    DuckDBOperator.apply_alias_mask(table_name="inferences", conn=conn, schema=schema)
    # This should return nothing but still be a valid query
    d = conn.sql("SELECT UNNEST(obj) from inferences").df()
    assert d is not None


def test_multitype_list_columns_created():
    schema = DatasetSchema(
        alias_mask={},
        columns=[
            DatasetColumn(
                id=uuid4(),
                source_name="id",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.UUID),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="timestamp",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.TIMESTAMP),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="data",
                definition=DatasetListType(
                    id=uuid4(),
                    items=DatasetListType(
                        id=uuid4(),
                        items=DatasetScalarType(id=uuid4(), dtype=DType.JSON),
                    ),
                ),
            ),
        ],
    )
    data = [
        {
            "id": "991ff637-2c13-4289-ba17-a23c1c2b20b9",
            "timestamp": "2024-07-29T13:46:12+0000",
            "data": [["value1", 2.0], ["value3", 4.0]],
        },
        {
            "id": "991ff637-2c13-4289-ba17-a23c1c2b20b8",
            "timestamp": "2024-07-28T13:46:12+0000",
            "data": [[1.0, "value2"], ["value3", 4.0]],
        },
    ]

    conn = DuckDBOperator.load_data_to_duckdb(
        data,
        preprocess_schema=False,
        schema=schema,
    )
    DuckDBOperator.apply_alias_mask(table_name="inferences", conn=conn, schema=schema)
    d = conn.sql("SELECT UNNEST(data) from inferences").df()
    assert d is not None


def test_cv_schema_with_image_col_loads():
    schema = DatasetSchema(
        alias_mask={},
        columns=[
            DatasetColumn(
                id=uuid4(),
                source_name="prompt_version_id",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.STRING),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="timestamp",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.TIMESTAMP),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="image",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.IMAGE),
            ),
        ],
    )
    data = [
        {
            "id": "991ff637-2c13-4289-ba17-a23c1c2b20b9",
            "timestamp": "2024-07-29T13:46:12+0000",
            "image": "iVBORw0KGgoAAAANSUhEUgAAAOAAAADgCAIAAACVT/22AAADGUlEQVR4nO3doU5cQRiAUbYhQaBJaisRCBKSprLVvEUNpk9TU8MTYNG0rmmCQyD7AGgEahDYltuwe/d+DeeoFTczI778K3ZndzXG2IGqN0sfAJ4jUNIESppASRMoaQIlTaCkCZQ0gZImUNIESppASRMoaQIlTaCkCZQ0gZImUNIESppASRMoaQIlTaCkCZQ0gZImUNIESppASRMoaQIlTaCkCZQ0gZImUNIESppASRMoaQIlTaCkCZQ0gZImUNIESppASRMoaQIlTaCkCZQ0gZImUNIESppASRMoaQIlTaCkCZQ0gZImUNIESppASRMoaQIlTaCkCZQ0gZK2u/QB2Iyjn9dLbX3z4WS+xU1Q0gRKmkBJEyhpAiVNoKQJlDSBkiZQ0gRKmkBJEyhpAiVNoKQJlDSBkuYLy/+Hu73b5x+42tnf1F6fftxvaqn1rcYYS5+BaZOBbtDBw+HW9prkLZ40gZImUNIESppASRMoaQIlTaCkCZQ0gZImUNIESppASRMoaQIlTaCkCZQ0gZImUNIESppASZvl2vHJ+xn/OOdvrn8t9kdBzMcEJW1igv4+O93OOeCPTFDSBEqaQEkTKGkCJc3PL7KuL58/Tj7z9fz7yxY3QUkTKGkCJU2gpAmUNIGSJlDSBEqaQEkTKGmzfNR5cfz26cW7b5dzrM/rYYKSJlDSBEqaQEkTKGkCJU2gpAmUNIGSJlDS3OpkXS++sfkvTFDSBEqaQEkTKGkCJU2gpAmUNIGSJlDSBEqaQEkTKGkCJU2gpAmUNIGSJlDSBEqaQEkTKGkCJU2gpAmUNIGSJlDSBEqaQEkTKGkCJU2gpAmUNIGSJlDSBEqaQEkTKGkCJU2gpAmUNIGSJlDSBEqaQEkTKGkCJU2gpAmUNIGSJlDSBEqaQEkTKGkCJU2gpAmUNIGSJlDSBEqaQElbjTGWPgPT7vZut7bXwcPh1vaaZIKSJlDSBEqaQEkTKGkCJU2gpAmUNIGSJlDSBEqaQEkTKGkCJU2gpAmUNIGSJlDSBEqaQElzaY40E5Q0gZImUNIESppASRMoaY+euCcrkiFutgAAAABJRU5ErkJggg==",
        },
        {
            "id": "991ff637-2c13-4289-ba17-a23c1c2b20b8",
            "timestamp": "2024-07-28T13:46:12+0000",
            "image": "iVBORw0KGgoAAAANSUhEUgAAAOAAAADgCAIAAACVT/22AAADKElEQVR4nO3cMWoVURiA0YmkFAVrGzsrC60tUoS4ALHTTsEduAR3IFhaBhcgpEhhb2HlAtxAxH6sRQgTmJn7+TinfcPcn8fHHRjeu0fzPE9QdWv0AHAdgZImUNIESppASRMoaQIlTaCkCZQ0gZImUNIESppASRMoaQIlTaCkCZQ0gZImUNIESppASRMoaQIlTaCkCZQ0gZImUNIESppASRMoaQIlTaCkCZQ0gZImUNIESppASRMoaQIlTaCkCZQ0gZImUNIESppASRMoaQIlTaCkCZQ0gZImUNIESppASRMoaQIlTaCkCZQ0gZImUNIESppASRMoaQIlTaCkCZQ0gZImUNIESppASRMoaQIlTaCkCZQ0gZImUNIESppASRMoaQIlTaCkCZQ0gZImUNIESppASRMoaQIlTaCkCZS049EDLPXj/HL0CDfw8MXJ6BEOhB2UNIGSJlDSBEqaQEkTKGkCJU2gpAmUNIGSJlDSBEqaQEkTKGkCJU2gpAmUNIGSJlDSBEqaQEkTKGkCJU2gpAmUNIGSJlDSBEqaQEkTKGkCJU2gpAmUNIGSJlDSBEqaQEkTKGkCJU2gpAmUNIGSJlDSBEqaQEkTKGkCJU2gpAmUNIGSJlDSBEqaQEkTKGkCJU2gpAmUNIGSdjx6gHW8Pns5eoS/Xa1/y693f65/0zw7KGkCJU2gpAmUNIGSJlDSBEqaQEkTKGkCJU2gpAmUNIGSJlDSBEqaQEkTKGkCJW38Xz4+PP615LKTd1sPUrfwi9rU2293dl5xfKALXb5/ct3HZ3vNwb484kkTKGkCJU2gpAmUNIGSJlDSBEqaQEkTKGlH8zyPnmEFT6/ujx5hc45fhJz/5sciDPf7y8flF99+9maVRe2gpAmUNIGSJlDSBEqaQEnb/DXTq8+Ptl5imqbpdI9F2J8dlDSBkiZQ0gRKmkBJEyhpAiVNoKQJlDSBkiZQ0gRKmkBJEyhpAiVNoKQJlDSBkiZQ0g7k6JsHF/e2XuLT8+9bL8G/7KCkCZQ0gZImUNIESppASRMoaQfyHpQdrHWq943YQUkTKGkCJU2gpAmUNIGS9gcCZCCbtvyg7QAAAABJRU5ErkJggg==",
        },
    ]

    conn = DuckDBOperator.load_data_to_duckdb(
        data,
        preprocess_schema=False,
        schema=schema,
    )
    DuckDBOperator.apply_alias_mask(table_name="inferences", conn=conn, schema=schema)
    d = conn.sql("SELECT image from inferences").df()
    assert d is not None


def test_tabular_schema():
    current_dir = os.path.dirname(__file__)
    csv_path = os.path.join(current_dir, "../../test_data/balloons/flights.csv")
    data = pd.read_csv(csv_path)
    schema = DatasetSchema(
        alias_mask={},
        columns=[
            DatasetColumn(
                id=uuid4(),
                source_name="flight_id",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.STRING),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="max_altitude",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.INT),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="distance",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.FLOAT),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="flight_start",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.TIMESTAMP),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="flight_end",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.TIMESTAMP),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="customer_feedback",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.STRING),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="weather_conditions",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.STRING),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="night_flight",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.BOOL),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="passenger_count",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.INT),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="max_speed",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.FLOAT),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="loaded_fuel",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.FLOAT),
            ),
        ],
    )

    conn = DuckDBOperator.load_data_to_duckdb(
        data,
        preprocess_schema=False,
        schema=schema,
    )
    DuckDBOperator.apply_alias_mask(table_name="inferences", conn=conn, schema=schema)

    d = conn.sql("SELECT SUM(max_altitude) from inferences").fetchall()
    sum = d[0][0]

    # INT type should have % 1 == 0
    assert sum > 0
    assert sum % 1.0 == 0


special_character_column_name = "id 'with' \"quotes\" 🚀 and spaces"
special_character_column_name2 = "column \"with\" 'apostrophes' 🌟 and emoji"
data_row_1 = {
    special_character_column_name: [1, 2, 3],
    special_character_column_name2: ["A", "B", "C"],
}
data_row_2 = {
    special_character_column_name: [2, 3, 4],
    special_character_column_name2: ["W", "X", "Y"],
}

data_rows = [
    {special_character_column_name: 1, special_character_column_name2: "A"},
    {special_character_column_name: 2, special_character_column_name2: "B"},
    {special_character_column_name: 3, special_character_column_name2: "C"},
]

data_rows_2 = [
    {special_character_column_name: 2, special_character_column_name2: "W"},
    {special_character_column_name: 3, special_character_column_name2: "X"},
    {special_character_column_name: 4, special_character_column_name2: "Y"},
]


@pytest.mark.parametrize(
    "data1,data2",
    [(pd.DataFrame(data_row_1), pd.DataFrame(data_row_2)), (data_rows, data_rows_2)],
)
def test_simple_load_data_with_schema_special_character_names(
    data1: pd.DataFrame | list[dict[str, Any]],
    data2: pd.DataFrame | list[dict[str, Any]],
):
    schema = DatasetSchema(
        alias_mask={},
        columns=[
            DatasetColumn(
                id=uuid4(),
                source_name=special_character_column_name,
                definition=DatasetScalarType(id=uuid4(), dtype=DType.INT),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name=special_character_column_name2,
                definition=DatasetScalarType(id=uuid4(), dtype=DType.STRING),
            ),
        ],
    )

    conn = DuckDBOperator.load_data_to_duckdb(
        data1,
        table_name="left_table",
        schema=schema,
    )
    conn = DuckDBOperator.load_data_to_duckdb(
        data2,
        table_name="right_table",
        conn=conn,
        schema=schema,
    )

    DuckDBOperator.apply_alias_mask(table_name="left_table", conn=conn, schema=schema)
    DuckDBOperator.apply_alias_mask(table_name="right_table", conn=conn, schema=schema)

    DuckDBOperator.join_tables(
        conn,
        "joined",
        "left_table",
        "right_table",
        special_character_column_name,
        special_character_column_name,
        "inner",
    )

    res = conn.sql("SELECT count(*) FROM joined").fetchall()
    assert res[0][0] == 2
