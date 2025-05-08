from arthur_common.aggregations.functions.inference_count import (
    InferenceCountAggregationFunction,
)
from arthur_common.models.metrics import DatasetReference
from duckdb import DuckDBPyConnection


def test_inference_count(
    get_balloons_dataset_conn: tuple[DuckDBPyConnection, DatasetReference],
):
    conn, dataset_ref = get_balloons_dataset_conn
    inference_counter = InferenceCountAggregationFunction()
    metrics = inference_counter.aggregate(conn, dataset_ref, "flight start")
    assert len(metrics) == 1
    assert metrics[0].name == "inference_count"
    results = metrics[0].numeric_series
    total_count = 0
    for group in results:
        for point in group.values:
            total_count += point.value

    assert total_count == 850
