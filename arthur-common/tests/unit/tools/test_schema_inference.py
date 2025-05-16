import os
from uuid import uuid4

import pandas as pd
from arthur_common.models.schema_definitions import (
    DatasetColumn,
    DatasetListType,
    DatasetObjectType,
    DatasetScalarType,
    DatasetSchema,
    DType,
)
from arthur_common.tools.schema_inferer import SchemaInferer


def test_schema_inference():
    data = [{"name": "first_name", "age": 23}]

    schema = SchemaInferer(data).infer_schema()
    expected_schema = DatasetSchema(
        alias_mask={},
        columns=[
            DatasetColumn(
                id=uuid4(),
                source_name="name",
                definition=DatasetScalarType(
                    id=uuid4(),
                    dtype=DType.STRING,
                    nullable=True,
                ),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="age",
                definition=DatasetScalarType(
                    id=uuid4(),
                    dtype=DType.INT,
                    nullable=True,
                ),
            ),
        ],
    )

    assert set(hash(col) for col in schema.columns) == set(
        hash(col) for col in expected_schema.columns
    )


def test_col_names_with_spaces_schema_inference():
    data = [
        {
            "MA History": {
                "Past Acquisition Activity": 10,
                "Collaboration History": 20,
                "Regulatory Hurdles": 30,
            },
        },
    ]

    schema = SchemaInferer(data).infer_schema()
    expected_schema = DatasetSchema(
        alias_mask={},
        columns=[
            DatasetColumn(
                id=uuid4(),
                source_name="MA History",
                definition=DatasetListType(
                    id=uuid4(),
                    items=DatasetObjectType(
                        id=uuid4(),
                        object={
                            "Past Acquisition Activity": DatasetScalarType(
                                id=uuid4(),
                                dtype=DType.INT,
                                nullable=True,
                            ),
                            "Collaboration History": DatasetScalarType(
                                id=uuid4(),
                                dtype=DType.INT,
                                nullable=True,
                            ),
                            "Regulatory Hurdles": DatasetScalarType(
                                id=uuid4(),
                                dtype=DType.INT,
                                nullable=True,
                            ),
                        },
                    ),
                    nullable=True,
                ),
            ),
        ],
    )

    assert set(hash(col) for col in schema.columns) == set(
        hash(col) for col in expected_schema.columns
    )


def test_nested_schema_inference():
    data = [
        {
            "model": "t",
            "engine_options": [
                {"capacity": "4L", "power": {"torque": 10, "hp": 14.3}},
                {"capacity": "3L", "power": {"torque": 5, "hp": 7.1}},
            ],
            "successors": ["A", "U"],
            "is_cool": True,
        },
    ]

    expected_schema = DatasetSchema(
        alias_mask={},
        columns=[
            DatasetColumn(
                id=uuid4(),
                source_name="model",
                definition=DatasetScalarType(
                    id=uuid4(),
                    dtype=DType.STRING,
                    nullable=True,
                ),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="engine_options",
                definition=DatasetListType(
                    id=uuid4(),
                    items=DatasetObjectType(
                        id=uuid4(),
                        object={
                            "capacity": DatasetScalarType(
                                id=uuid4(),
                                dtype=DType.STRING,
                                nullable=True,
                            ),
                            "power": DatasetObjectType(
                                id=uuid4(),
                                object={
                                    "torque": DatasetScalarType(
                                        id=uuid4(),
                                        dtype=DType.INT,
                                        nullable=True,
                                    ),
                                    "hp": DatasetScalarType(
                                        id=uuid4(),
                                        dtype=DType.FLOAT,
                                        nullable=True,
                                    ),
                                },
                                nullable=True,
                            ),
                        },
                    ),
                    nullable=True,
                ),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="successors",
                definition=DatasetListType(
                    id=uuid4(),
                    items=DatasetScalarType(
                        id=uuid4(),
                        dtype=DType.STRING,
                        nullable=True,
                    ),
                    nullable=True,
                ),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="is_cool",
                definition=DatasetScalarType(
                    id=uuid4(),
                    dtype=DType.BOOL,
                    nullable=True,
                ),
            ),
        ],
    )

    schema = SchemaInferer(data).infer_schema()

    assert set(hash(col) for col in schema.columns) == set(
        hash(col) for col in expected_schema.columns
    )


def test_multivalue_list_schema_inference():
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

    expected_schema = DatasetSchema(
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
                definition=DatasetScalarType(id=uuid4(), dtype=DType.STRING),
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

    schema = SchemaInferer(data).infer_schema()
    print(schema)

    assert set(hash(col) for col in schema.columns) == set(
        hash(col) for col in expected_schema.columns
    )


def test_tabular_schema():
    current_dir = os.path.dirname(__file__)
    csv_path = os.path.join(current_dir, "../../test_data/balloons/flights.csv")
    data = pd.read_csv(csv_path)
    schema = SchemaInferer(data).infer_schema()

    expected_schema = DatasetSchema(
        alias_mask={},
        columns=[
            DatasetColumn(
                id=uuid4(),
                source_name="flight id",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.STRING),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="max altitude",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.FLOAT),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="distance",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.FLOAT),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="flight start",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.TIMESTAMP),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="flight end",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.TIMESTAMP),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="customer feedback",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.STRING),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="weather conditions",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.STRING),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="night flight",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.BOOL),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="passenger count",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.INT),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="max speed",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.FLOAT),
            ),
            DatasetColumn(
                id=uuid4(),
                source_name="loaded fuel",
                definition=DatasetScalarType(id=uuid4(), dtype=DType.FLOAT),
            ),
        ],
    )

    assert set(hash(col) for col in schema.columns) == set(
        hash(col) for col in expected_schema.columns
    )
