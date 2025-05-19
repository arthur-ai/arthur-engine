from arthur_common.aggregations.functions.multiclass_inference_count_by_class import (
    MulticlassClassifierCountByClassAggregationFunction,
)
from arthur_common.models.metrics import DatasetReference
from duckdb import DuckDBPyConnection


def test_multiclass_str_count_by_class(
    get_vehicle_dataset_conn: tuple[DuckDBPyConnection, DatasetReference],
):
    conn, dataset_ref = get_vehicle_dataset_conn
    cm_aggregator = MulticlassClassifierCountByClassAggregationFunction()
    metrics = cm_aggregator.aggregate(
        conn,
        dataset_ref,
        timestamp_col="Timestamp",
        prediction_col="PredictedLabel",
    )
    assert len(metrics) == 1
    assert metrics[0].name == "multiclass_classifier_count_by_class"

    expected_counts = {
        "Car": 142,
        "Truck": 25,
        "Motorcycle": 33,
    }

    for series in metrics[0].numeric_series:
        # find the dimension for the prediction label
        for dimension in series.dimensions:
            if dimension.name == "prediction":
                predicted_label = dimension.value
                break
        else:
            assert (
                False
            ), f"could not find dimension prediction in dimensions {series.dimensions}"

        # verify sum of series matches the expected count for that label
        assert sum([v.value for v in series.values]) == expected_counts[predicted_label]
