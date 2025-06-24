import pytest
from arthur_common.aggregations.functions.multiclass_confusion_matrix import (
    MulticlassClassifierStringLabelSingleClassConfusionMatrixAggregationFunction,
)
from arthur_common.models.metrics import DatasetReference
from duckdb import DuckDBPyConnection

from .helpers import *


@pytest.mark.parametrize(
    "positive_label,expected_tp,expected_fp,expected_tn,expected_fn",
    [
        ("Truck", 10, 15, 172, 3),
        ("Car", 141, 1, 27, 31),
        ("Motorcycle", 15, 18, 167, 0),
    ],
)
def test_multiclass_single_class_confusion_matrix(
    get_vehicle_dataset_conn: tuple[DuckDBPyConnection, DatasetReference],
    positive_label: str,
    expected_tp: int,
    expected_fp: int,
    expected_tn: int,
    expected_fn: int,
):
    conn, dataset_ref = get_vehicle_dataset_conn
    cm_aggregator = (
        MulticlassClassifierStringLabelSingleClassConfusionMatrixAggregationFunction()
    )
    metrics = cm_aggregator.aggregate(
        conn,
        dataset_ref,
        timestamp_col="Timestamp",
        prediction_col="PredictedLabel",
        gt_values_col="TrueLabel",
        positive_class_label=positive_label,
    )
    assert len(metrics) == 4
    assert (
        metrics[0].name
        == "multiclass_confusion_matrix_single_class_true_positive_count"
    )
    assert (
        metrics[1].name
        == "multiclass_confusion_matrix_single_class_false_positive_count"
    )
    assert (
        metrics[2].name
        == "multiclass_confusion_matrix_single_class_false_negative_count"
    )
    assert (
        metrics[3].name
        == "multiclass_confusion_matrix_single_class_true_negative_count"
    )

    for metric in metrics:
        for series in metric.numeric_series:
            for dimension in series.dimensions:
                if dimension.name == "class_label":
                    assert dimension.value == positive_label
                    break
            else:
                assert (
                    False
                ), f"class_label dimension not found in dimensions {series.dimensions}"

    assert sum([v.value for v in metrics[0].numeric_series[0].values]) == expected_tp
    assert sum([v.value for v in metrics[1].numeric_series[0].values]) == expected_fp
    assert sum([v.value for v in metrics[2].numeric_series[0].values]) == expected_fn
    assert sum([v.value for v in metrics[3].numeric_series[0].values]) == expected_tn


def test_multiclass_with_segmentation(
    get_equipment_inspection_dataset_conn: tuple[DuckDBPyConnection, DatasetReference],
):
    conn, dataset_ref = get_equipment_inspection_dataset_conn
    cm_aggregator = (
        MulticlassClassifierStringLabelSingleClassConfusionMatrixAggregationFunction()
    )
    metrics = cm_aggregator.aggregate(
        conn,
        dataset_ref,
        timestamp_col="timestamp",
        prediction_col="classification_pred",
        gt_values_col="classification_gt",
        positive_class_label="functional",
        segmentation_cols=["prompt_version_id"],
    )
    assert_dimension_in_metric(metrics[0], "prompt_version_id")
