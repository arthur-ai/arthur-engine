import pytest
from arthur_common.aggregations.functions.inference_count_by_class import (
    BinaryClassifierCountByClassAggregationFunction,
    BinaryClassifierCountThresholdClassAggregationFunction,
)
from arthur_common.models.metrics import DatasetReference, Dimension
from duckdb import DuckDBPyConnection

HIGH_ACCURACY_COUNTS = (743, 24257)
LOW_ACCURACY_COUNTS = (9, 24991)


@pytest.mark.parametrize(
    "prediction_col,true_count,false_count",
    [
        ("pred high accuracy malicious", *HIGH_ACCURACY_COUNTS),
        ("pred low accuracy malicious", *LOW_ACCURACY_COUNTS),
    ],
)
def test_int_bool_count_by_class(
    get_networking_dataset_conn: tuple[DuckDBPyConnection, DatasetReference],
    prediction_col: str,
    true_count: int,
    false_count: int,
):
    conn, dataset_ref = get_networking_dataset_conn
    cm_aggregator = BinaryClassifierCountByClassAggregationFunction()
    metrics = cm_aggregator.aggregate(
        conn,
        dataset_ref,
        timestamp_col="sent timestamp",
        prediction_col=prediction_col,
    )
    assert len(metrics) == 1
    assert metrics[0].name == "binary_classifier_count_by_class"

    assert sum([v.value for v in metrics[0].numeric_series[0].values]) == false_count
    assert metrics[0].numeric_series[0].dimensions == [
        Dimension(name="prediction", value="False"),
    ]

    assert sum([v.value for v in metrics[0].numeric_series[1].values]) == true_count
    assert metrics[0].numeric_series[1].dimensions == [
        Dimension(name="prediction", value="True"),
    ]


@pytest.mark.parametrize(
    "prediction_col,true_count,false_count",
    [
        ("pred high accuracy malicious", *HIGH_ACCURACY_COUNTS),
        ("pred low accuracy malicious", *LOW_ACCURACY_COUNTS),
    ],
)
def test_prediction_threshold_count_by_class(
    get_networking_dataset_conn: tuple[DuckDBPyConnection, DatasetReference],
    prediction_col: str,
    true_count: int,
    false_count: int,
):
    conn, dataset_ref = get_networking_dataset_conn
    conn.sql(
        f"""
        ALTER TABLE {dataset_ref.dataset_table_name} ADD COLUMN "{prediction_col} float value" FLOAT;
    """,
    )

    # Then update it
    conn.sql(
        f"""
        UPDATE {dataset_ref.dataset_table_name}
        SET "{prediction_col} float value" = CASE
            WHEN "{prediction_col}" = true THEN 0.93
            ELSE 0.85
        END;
    """,
    )

    cm_aggregator = BinaryClassifierCountThresholdClassAggregationFunction()
    metrics = cm_aggregator.aggregate(
        conn,
        dataset_ref,
        timestamp_col="sent timestamp",
        prediction_col=f"{prediction_col} float value",
        threshold=0.93,
        true_label="yeetyeetyes",
        false_label="no",
    )

    assert len(metrics) == 1
    assert metrics[0].name == "binary_classifier_count_by_class"

    assert sum([v.value for v in metrics[0].numeric_series[0].values]) == false_count
    assert metrics[0].numeric_series[0].dimensions == [
        Dimension(name="prediction", value="no"),
    ]

    assert sum([v.value for v in metrics[0].numeric_series[1].values]) == true_count
    assert metrics[0].numeric_series[1].dimensions == [
        Dimension(name="prediction", value="yeetyeetyes"),
    ]
