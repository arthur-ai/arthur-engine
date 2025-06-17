import pytest
from arthur_common.aggregations.functions.mean_squared_error import (
    MeanSquaredErrorAggregationFunction,
)
from arthur_common.models.metrics import DatasetReference
from duckdb import DuckDBPyConnection


@pytest.mark.parametrize(
    "city,expected_consumption_mse",
    [
        ("Coruscant", 5.46),
        ("Theed", 5.98),
        ("Mos Eisley", 5.34),
        ("Cloud City", 5.88),
        ("Keren", 5.93),
        ("Iziz", 5.48),
        ("Coronet", 5.46),
        ("Tipoca City", 5.42),
        ("Pau City", 5.50),
        ("Canto Bight", 5.20),
    ],
)
def test_mean_squared_error(
    get_electricity_dataset_conn: tuple[DuckDBPyConnection, DatasetReference],
    city: str,
    expected_consumption_mse: float,
):
    conn, dataset_ref = get_electricity_dataset_conn
    mae_aggregator = MeanSquaredErrorAggregationFunction()

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
    assert metrics[0].name == "squared_error_count"
    assert metrics[1].name == "squared_error_sum"

    # 288 5 minute intervals in a day
    assert len(metrics[0].numeric_series[0].values) == 288
    assert len(metrics[1].numeric_series[0].values) == 288

    squared_error_count = sum([v.value for v in metrics[0].numeric_series[0].values])
    squared_error_sum = sum([v.value for v in metrics[1].numeric_series[0].values])

    assert round(squared_error_sum / squared_error_count, 2) == expected_consumption_mse


def test_mse_with_prompt_version(
    get_equipment_inspection_dataset_conn: tuple[DuckDBPyConnection, DatasetReference],
):
    conn, dataset_ref = get_equipment_inspection_dataset_conn
    mae_aggregator = MeanSquaredErrorAggregationFunction()

    conn.sql(
        f"""
                ALTER TABLE {dataset_ref.dataset_table_name} ADD COLUMN "classification_pred float value" FLOAT;
            """,
    )
    conn.sql(
        f"""
                    ALTER TABLE {dataset_ref.dataset_table_name} ADD COLUMN "classification_gt float value" FLOAT;
                """,
    )
    conn.sql(
        f"""
                UPDATE {dataset_ref.dataset_table_name}
                SET "classification_pred float value" = CASE
                    WHEN "classification_pred" = 'functional' THEN 0.93
                    ELSE 0.85
                END;
            """,
    )
    conn.sql(
        f"""
                    UPDATE {dataset_ref.dataset_table_name}
                    SET "classification_gt float value" = CASE
                        WHEN "classification_gt" = 'functional' THEN 0.93
                        ELSE 0.85
                    END;
                """,
    )

    # make sure aggregation doesn't error
    mae_aggregator.aggregate(
        conn,
        dataset_ref,
        timestamp_col="timestamp",
        prediction_col="classification_pred float value",
        ground_truth_col="classification_gt float value",
    )
