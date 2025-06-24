from arthur_common.aggregations.functions.categorical_count import (
    CategoricalCountAggregationFunction,
)
from arthur_common.models.metrics import DatasetReference
from duckdb import DuckDBPyConnection


def test_string_categorical_count(
    get_balloons_dataset_conn: tuple[DuckDBPyConnection, DatasetReference],
):
    conn, dataset_ref = get_balloons_dataset_conn
    cat_counter = CategoricalCountAggregationFunction()

    metric = cat_counter.aggregate(
        conn,
        dataset_ref,
        timestamp_col="flight start",
        categorical_col="customer feedback",
    )
    assert len(metric) == 1
    assert metric[0].name == "categorical_count"
    # Four possibilities + null
    results = metric[0].numeric_series
    assert len(results) == 5
    # assert dimensions match
    found_categories = set()
    for res in results:
        dims = {r.name: r.value for r in res.dimensions}
        assert "column_name" in dims
        assert dims["column_name"] == "customer feedback"
        assert "category" in dims
        found_categories.add(dims["category"])

    assert found_categories == {
        "Positive",
        "Neutral",
        "Negative",
        "Highly Negative",
        "null",
    }


def test_cv_categorical_count_with_dimensions(
    get_equipment_inspection_dataset_conn: tuple[DuckDBPyConnection, DatasetReference],
):
    conn, dataset_ref = get_equipment_inspection_dataset_conn
    cat_counter = CategoricalCountAggregationFunction()

    metric = cat_counter.aggregate(
        conn,
        dataset_ref,
        timestamp_col="timestamp",
        categorical_col="classification_pred",
        segmentation_cols=["prompt_version_id"],
    )
    assert len(metric) == 1
    assert metric[0].name == "categorical_count"
    # three possibilities for categorical dimensions * 3 possibilities for prompt version dimensions
    results = metric[0].numeric_series
    assert len(results) == 3 * 3
    # assert dimensions match
    found_categories = set()
    found_prompt_version_ids = set()
    for res in results:
        dims = {r.name: r.value for r in res.dimensions}
        assert "column_name" in dims
        assert dims["column_name"] == "classification_pred"
        assert "category" in dims
        assert "prompt_version_id" in dims
        found_categories.add(dims["category"])
        found_prompt_version_ids.add(dims["prompt_version_id"])

    assert found_categories == {
        "needs_repair_soon",
        "functional",
        "broken",
    }

    assert found_prompt_version_ids == {"0", "1", "2"}
