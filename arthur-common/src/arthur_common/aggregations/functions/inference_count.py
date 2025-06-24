from typing import Annotated, Optional
from uuid import UUID

from arthur_common.aggregations.aggregator import NumericAggregationFunction
from arthur_common.models.metrics import DatasetReference, NumericMetric
from arthur_common.models.schema_definitions import (
    DType,
    MetricColumnParameterAnnotation,
    MetricDatasetParameterAnnotation,
    MetricMultipleColumnParameterAnnotation,
    ScalarType,
    ScopeSchemaTag,
)
from arthur_common.tools.duckdb_data_loader import escape_identifier
from duckdb import DuckDBPyConnection


class InferenceCountAggregationFunction(NumericAggregationFunction):
    METRIC_NAME = "inference_count"

    @staticmethod
    def id() -> UUID:
        return UUID("00000000-0000-0000-0000-00000000000a")

    @staticmethod
    def display_name() -> str:
        return "Inference Count"

    @staticmethod
    def description() -> str:
        return "Metric that counts the number of inferences per time window."

    def aggregate(
        self,
        ddb_conn: DuckDBPyConnection,
        dataset: Annotated[
            DatasetReference,
            MetricDatasetParameterAnnotation(
                friendly_name="Dataset",
                description="The dataset containing the inference data.",
            ),
        ],
        timestamp_col: Annotated[
            str,
            MetricColumnParameterAnnotation(
                source_dataset_parameter_key="dataset",
                allowed_column_types=[
                    ScalarType(dtype=DType.TIMESTAMP),
                ],
                tag_hints=[ScopeSchemaTag.PRIMARY_TIMESTAMP],
                friendly_name="Timestamp Column",
                description="A column containing timestamp values to bucket by.",
            ),
        ],
        segmentation_cols: Annotated[
            Optional[list[str]],
            MetricMultipleColumnParameterAnnotation(
                source_dataset_parameter_key="dataset",
                allowed_column_types=[
                    ScalarType(dtype=DType.INT),
                    ScalarType(dtype=DType.BOOL),
                    ScalarType(dtype=DType.STRING),
                    ScalarType(dtype=DType.UUID),
                ],
                tag_hints=[],
                friendly_name="Segmentation Columns",
                description="All columns to include as dimensions for segmentation.",
                optional=True,
            ),
        ] = None,
    ) -> list[NumericMetric]:
        """Executed SQL with no segmentation columns:
            select time_bucket(INTERVAL '5 minutes', {escaped_timestamp_col}) as ts, \
                    count(*) as count \
                    from {dataset.dataset_table_name} \
                    group by ts \
        """
        segmentation_cols = [] if not segmentation_cols else segmentation_cols
        escaped_timestamp_col = escape_identifier(timestamp_col)

        # build query components with segmentation columns
        escaped_segmentation_cols = [
            escape_identifier(col) for col in segmentation_cols
        ]
        all_select_clause_cols = [
            f"time_bucket(INTERVAL '5 minutes', {escaped_timestamp_col}) as ts",
            f"count(*) as count",
        ] + escaped_segmentation_cols
        all_group_by_cols = ["ts"] + escaped_segmentation_cols

        # build query
        count_query = f"""
            select {", ".join(all_select_clause_cols)}
            from {dataset.dataset_table_name}
            group by {", ".join(all_group_by_cols)}
        """

        results = ddb_conn.sql(count_query).df()
        series = self.group_query_results_to_numeric_metrics(
            results,
            "count",
            segmentation_cols,
            "ts",
        )
        metric = self.series_to_metric(self.METRIC_NAME, series)
        return [metric]
