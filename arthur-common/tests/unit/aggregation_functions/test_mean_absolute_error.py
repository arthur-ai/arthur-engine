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


def test_mae_with_prompt_version(
    get_equipment_inspection_dataset_conn: tuple[DuckDBPyConnection, DatasetReference],
):
    conn, dataset_ref = get_equipment_inspection_dataset_conn
    mae_aggregator = MeanAbsoluteErrorAggregationFunction()

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
