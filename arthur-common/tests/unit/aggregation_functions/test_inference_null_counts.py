import pytest
from arthur_common.aggregations.functions.inference_null_count import (
    InferenceNullCountAggregationFunction,
)
from arthur_common.models.metrics import DatasetReference
from duckdb import DuckDBPyConnection


@pytest.mark.parametrize(
    "column_name, expected_null_count",
    [
        ("flight id", 0),
        ("max altitude", 38),
        ("distance", 36),
        ("flight start", 31),
        ("flight end", 33),
        ("customer feedback", 33),
        ("weather conditions", 35),
        ("night flight", 0),
        ("passenger count", 0),
        ("max speed", 34),
        ("loaded fuel", 32),
    ],
)
def test_inference_null_count(
    get_balloons_dataset_conn: tuple[DuckDBPyConnection, DatasetReference],
    column_name: str,
    expected_null_count: int,
):
    inference_null_counter = InferenceNullCountAggregationFunction()
    conn, dataset_ref = get_balloons_dataset_conn

    metrics = inference_null_counter.aggregate(
        conn,
        dataset_ref,
        timestamp_col="flight start",
        nullable_col=column_name,
    )
    assert len(metrics) == 1
    assert metrics[0].name == "null_count"

    results = metrics[0].numeric_series
    # Only one set of dimensions from this function
    result = results[0]
    assert result.dimensions[0].value == column_name
    assert result.dimensions[0].name == "column_name"
    total_count = sum([point.value for point in result.values])
    assert total_count == expected_null_count
