from arthur_common.aggregations.functions.inference_count import (
    InferenceCountAggregationFunction,
)
from arthur_common.models.metrics import DatasetReference
from duckdb import DuckDBPyConnection


def test_inference_count(
    get_balloons_dataset_conn: tuple[DuckDBPyConnection, DatasetReference],
    get_equipment_inspection_dataset_conn: tuple[DuckDBPyConnection, DatasetReference],
):
    # run test on balloons dataset
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

    # run test on dataset with prompt_version_id
    conn, dataset_ref = get_equipment_inspection_dataset_conn
    inference_counter = InferenceCountAggregationFunction()
    metrics = inference_counter.aggregate(conn, dataset_ref, "timestamp")
    assert len(metrics) == 1
    assert metrics[0].name == "inference_count"
    results = metrics[0].numeric_series
    total_count = 0
    found_prompt_version_ids = set()
    for group in results:
        dims = {r.name: r.value for r in group.dimensions}
        assert "prompt_version_id" in dims
        found_prompt_version_ids.add(dims["prompt_version_id"])
        for point in group.values:
            total_count += point.value

    assert found_prompt_version_ids == {"0", "1", "2"}
    assert total_count == 1000

    # customize segmentation columns for balloon dataset
    conn, dataset_ref = get_balloons_dataset_conn
    inference_counter = InferenceCountAggregationFunction()
    metrics = inference_counter.aggregate(
        conn,
        dataset_ref,
        "flight start",
        ["weather conditions"],
    )
    assert len(metrics) == 1
    assert metrics[0].name == "inference_count"
    results = metrics[0].numeric_series
    total_count = 0
    weather_conditions = set()
    for group in results:
        dims = {r.name: r.value for r in group.dimensions}
        assert "weather conditions" in dims
        weather_conditions.add(dims["weather conditions"])
        for point in group.values:
            total_count += point.value

    assert weather_conditions == {"Sunny", "Cloudy", "Rainy", "Windy", "null"}
    assert total_count == 850
