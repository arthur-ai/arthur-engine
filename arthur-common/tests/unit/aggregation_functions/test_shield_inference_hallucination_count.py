from arthur_common.aggregations.functions.shield_aggregations import (
    ShieldInferenceHallucinationCountAggregation,
)
from arthur_common.models.metrics import DatasetReference
from duckdb import DuckDBPyConnection


def test_shield_inference_hallucination_count(
    get_shield_dataset_conn: tuple[DuckDBPyConnection, DatasetReference],
):
    conn, dataset_ref = get_shield_dataset_conn

    hallucination_count_aggregator = ShieldInferenceHallucinationCountAggregation()
    metrics = hallucination_count_aggregator.aggregate(
        conn,
        dataset_ref,
        shield_response_column="shield_response",
    )

    # validate there's a single hallucination count metric
    hallucination_count_metrics = [
        m for m in metrics if m.name == "hallucination_count"
    ]
    assert len(hallucination_count_metrics) == 1
    assert len(hallucination_count_metrics[0].numeric_series) == 1

    # validate expected hallucination case: 1 Fail out of 3 total cases
    total_hallucination_count = sum(
        v.value for v in hallucination_count_metrics[0].numeric_series[0].values
    )
    assert (
        total_hallucination_count == 1
    ), f"Expected 1 hallucination count, got {total_hallucination_count}"
