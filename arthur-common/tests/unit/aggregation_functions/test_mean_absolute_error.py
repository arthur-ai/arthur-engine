import pytest
from arthur_common.aggregations.functions.mean_absolute_error import (
    MeanAbsoluteErrorAggregationFunction,
)
from arthur_common.models.metrics import DatasetReference
from duckdb import DuckDBPyConnection


@pytest.mark.parametrize(
    "city,expected_consumption_mae",
    [
        ("Coruscant", 1.82),
        ("Theed", 1.90),
        ("Mos Eisley", 1.81),
        ("Cloud City", 1.89),
        ("Keren", 1.90),
        ("Iziz", 1.83),
        ("Coronet", 1.83),
        ("Tipoca City", 1.80),
        ("Pau City", 1.85),
        ("Canto Bight", 1.79),
    ],
)
def test_mean_absolute_error(
    get_electricity_dataset_conn: tuple[DuckDBPyConnection, DatasetReference],
    city: str,
    expected_consumption_mae: float,
):
    conn, dataset_ref = get_electricity_dataset_conn
    mae_aggregator = MeanAbsoluteErrorAggregationFunction()

    # This will be handy for segmentation later on to test for each city, for now just delete the irrelevant ones
    conn.sql(
        f"""
        DELETE FROM {dataset_ref.dataset_table_name} where city != '{city}' OR city is null;
    """,
    )

    metrics = mae_aggregator.aggregate(
        conn,
        dataset_ref,
        timestamp_col="timestamp",
        prediction_col="expected energy consumption",
        ground_truth_col="energy usage consumption",
    )

    assert len(metrics) == 2
    assert metrics[0].name == "absolute_error_count"
    assert metrics[1].name == "absolute_error_sum"

    # 288 5 minute intervals in a day
    assert len(metrics[0].numeric_series[0].values) == 288
    assert len(metrics[1].numeric_series[0].values) == 288

    absolute_error_count = sum([v.value for v in metrics[0].numeric_series[0].values])
    absolute_error_sum = sum([v.value for v in metrics[1].numeric_series[0].values])

    assert (
        round(absolute_error_sum / absolute_error_count, 2) == expected_consumption_mae
    )
