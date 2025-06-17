import pytest
from arthur_common.aggregations.functions.confusion_matrix import (
    BinaryClassifierIntBoolConfusionMatrixAggregationFunction,
    BinaryClassifierProbabilityThresholdConfusionMatrixAggregationFunction,
    BinaryClassifierStringLabelConfusionMatrixAggregationFunction,
)
from arthur_common.models.metrics import DatasetReference
from duckdb import DuckDBPyConnection

HIGH_ACCURACY_COUNTS = (477, 266, 24256, 1)
LOW_ACCURACY_COUNTS = (9, 0, 24522, 469)


def _add_int_cols_to_equipment_dataset(
    conn: DuckDBPyConnection,
    dataset_ref: DatasetReference,
) -> None:
    conn.sql(
        f"""
                    ALTER TABLE {dataset_ref.dataset_table_name} ADD COLUMN "classification_pred int value" INT;
                """,
    )
    conn.sql(
        f"""
                        ALTER TABLE {dataset_ref.dataset_table_name} ADD COLUMN "classification_gt int value" INT;
                    """,
    )
    conn.sql(
        f"""
                    UPDATE {dataset_ref.dataset_table_name}
                    SET "classification_pred int value" = CASE
                        WHEN "classification_pred" = 'functional' THEN 1
                        ELSE 0
                    END;
                """,
    )
    conn.sql(
        f"""
                        UPDATE {dataset_ref.dataset_table_name}
                        SET "classification_gt int value" = CASE
                            WHEN "classification_gt" = 'functional' THEN 1
                            ELSE 0
                        END;
                    """,
    )


@pytest.mark.parametrize(
    "prediction_col,tp,fp,tn,fn",
    [
        ("pred high accuracy malicious", *HIGH_ACCURACY_COUNTS),
        ("pred low accuracy malicious", *LOW_ACCURACY_COUNTS),
    ],
)
def test_int_bool_confusion_matrix(
    get_networking_dataset_conn: tuple[DuckDBPyConnection, DatasetReference],
    prediction_col: str,
    tp: int,
    fp: int,
    tn: int,
    fn: int,
):
    conn, dataset_ref = get_networking_dataset_conn
    cm_aggregator = BinaryClassifierIntBoolConfusionMatrixAggregationFunction()
    metrics = cm_aggregator.aggregate(
        conn,
        dataset_ref,
        timestamp_col="sent timestamp",
        prediction_col=prediction_col,
        gt_values_col="malicious",
    )
    assert len(metrics) == 4
    assert metrics[0].name == "confusion_matrix_true_positive_count"
    assert metrics[1].name == "confusion_matrix_false_positive_count"
    assert metrics[2].name == "confusion_matrix_false_negative_count"
    assert metrics[3].name == "confusion_matrix_true_negative_count"

    assert sum([v.value for v in metrics[0].numeric_series[0].values]) == tp
    assert sum([v.value for v in metrics[1].numeric_series[0].values]) == fp
    assert sum([v.value for v in metrics[2].numeric_series[0].values]) == fn
    assert sum([v.value for v in metrics[3].numeric_series[0].values]) == tn


def test_int_bool_confusion_matrix_with_prompt_version(
    get_equipment_inspection_dataset_conn: tuple[DuckDBPyConnection, DatasetReference],
):
    conn, dataset_ref = get_equipment_inspection_dataset_conn
    _add_int_cols_to_equipment_dataset(conn, dataset_ref)

    # make sure aggregation doesn't error
    cm_aggregator = BinaryClassifierIntBoolConfusionMatrixAggregationFunction()
    cm_aggregator.aggregate(
        conn,
        dataset_ref,
        timestamp_col="timestamp",
        prediction_col="classification_pred int value",
        gt_values_col="classification_gt int value",
    )


@pytest.mark.parametrize(
    "prediction_col,tp,fp,tn,fn",
    [
        ("pred high accuracy malicious", *HIGH_ACCURACY_COUNTS),
        ("pred low accuracy malicious", *LOW_ACCURACY_COUNTS),
    ],
)
def test_str_label_confusion_matrix(
    get_networking_dataset_conn: tuple[DuckDBPyConnection, DatasetReference],
    prediction_col: str,
    tp: int,
    fp: int,
    tn: int,
    fn: int,
):
    conn, dataset_ref = get_networking_dataset_conn
    # First add the column
    conn.sql(
        f"""
        ALTER TABLE {dataset_ref.dataset_table_name} ADD COLUMN "malicious str label" VARCHAR;
    """,
    )

    # Then update it
    conn.sql(
        f"""
        UPDATE {dataset_ref.dataset_table_name}
        SET "malicious str label" = CASE
            WHEN malicious = true THEN 'MALICIOUS'
            ELSE 'NOT_MALICIOUS'
        END;
    """,
    )

    conn.sql(
        f"""
        ALTER TABLE {dataset_ref.dataset_table_name} ADD COLUMN "{prediction_col} str label" VARCHAR;
    """,
    )

    # Then update it
    conn.sql(
        f"""
        UPDATE {dataset_ref.dataset_table_name}
        SET "{prediction_col} str label" = CASE
            WHEN "{prediction_col}" = true THEN 'MALICIOUS'
            ELSE 'NOT_MALICIOUS'
        END;
    """,
    )

    cm_aggregator = BinaryClassifierStringLabelConfusionMatrixAggregationFunction()
    metrics = cm_aggregator.aggregate(
        conn,
        dataset_ref,
        timestamp_col="sent timestamp",
        prediction_col=f"{prediction_col} str label",
        gt_values_col="malicious str label",
        true_label="MALICIOUS",
        false_label="NOT_MALICIOUS",
    )
    assert len(metrics) == 4
    assert metrics[0].name == "confusion_matrix_true_positive_count"
    assert metrics[1].name == "confusion_matrix_false_positive_count"
    assert metrics[2].name == "confusion_matrix_false_negative_count"
    assert metrics[3].name == "confusion_matrix_true_negative_count"

    assert sum([v.value for v in metrics[0].numeric_series[0].values]) == tp
    assert sum([v.value for v in metrics[1].numeric_series[0].values]) == fp
    assert sum([v.value for v in metrics[2].numeric_series[0].values]) == fn
    assert sum([v.value for v in metrics[3].numeric_series[0].values]) == tn


def test_str_label_confusion_matrix_with_prompt_version(
    get_equipment_inspection_dataset_conn: tuple[DuckDBPyConnection, DatasetReference],
):
    conn, dataset_ref = get_equipment_inspection_dataset_conn
    # make sure aggregation doesn't error
    cm_aggregator = BinaryClassifierStringLabelConfusionMatrixAggregationFunction()
    cm_aggregator.aggregate(
        conn,
        dataset_ref,
        timestamp_col="timestamp",
        prediction_col=f"classification_pred",
        gt_values_col="classification_gt",
        true_label="functional",
        false_label="broken",
    )


@pytest.mark.parametrize(
    "prediction_col,tp,fp,tn,fn",
    [
        ("pred high accuracy malicious", *HIGH_ACCURACY_COUNTS),
        ("pred low accuracy malicious", *LOW_ACCURACY_COUNTS),
    ],
)
def test_prediction_threshold_confusion_matrix(
    get_networking_dataset_conn: tuple[DuckDBPyConnection, DatasetReference],
    prediction_col: str,
    tp: int,
    fp: int,
    tn: int,
    fn: int,
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

    cm_aggregator = (
        BinaryClassifierProbabilityThresholdConfusionMatrixAggregationFunction()
    )
    metrics = cm_aggregator.aggregate(
        conn,
        dataset_ref,
        timestamp_col="sent timestamp",
        prediction_col=f"{prediction_col} float value",
        gt_values_col="malicious",
        threshold=0.93,
    )
    assert len(metrics) == 4
    assert metrics[0].name == "confusion_matrix_true_positive_count"
    assert metrics[1].name == "confusion_matrix_false_positive_count"
    assert metrics[2].name == "confusion_matrix_false_negative_count"
    assert metrics[3].name == "confusion_matrix_true_negative_count"

    assert sum([v.value for v in metrics[0].numeric_series[0].values]) == tp
    assert sum([v.value for v in metrics[1].numeric_series[0].values]) == fp
    assert sum([v.value for v in metrics[2].numeric_series[0].values]) == fn
    assert sum([v.value for v in metrics[3].numeric_series[0].values]) == tn


def test_pred_threshold_confusion_matrix_with_prompt_version(
    get_equipment_inspection_dataset_conn: tuple[DuckDBPyConnection, DatasetReference],
):
    conn, dataset_ref = get_equipment_inspection_dataset_conn
    conn.sql(
        f"""
                        ALTER TABLE {dataset_ref.dataset_table_name} ADD COLUMN "classification_pred float value" FLOAT;
                    """,
    )
    conn.sql(
        f"""
                            ALTER TABLE {dataset_ref.dataset_table_name} ADD COLUMN "classification_gt int value" INT;
                        """,
    )
    conn.sql(
        f"""
                        UPDATE {dataset_ref.dataset_table_name}
                        SET "classification_pred float value" = CASE
                            WHEN "classification_pred" = 'functional' THEN 0.94
                            ELSE 0.2
                        END;
                    """,
    )
    conn.sql(
        f"""
                            UPDATE {dataset_ref.dataset_table_name}
                            SET "classification_gt int value" = CASE
                                WHEN "classification_gt" = 'functional' THEN 1
                                ELSE 0
                            END;
                        """,
    )
    # make sure aggregation doesn't error
    cm_aggregator = (
        BinaryClassifierProbabilityThresholdConfusionMatrixAggregationFunction()
    )

    cm_aggregator.aggregate(
        conn,
        dataset_ref,
        timestamp_col="timestamp",
        prediction_col=f"classification_pred float value",
        gt_values_col="classification_gt int value",
        threshold=0.93,
    )
