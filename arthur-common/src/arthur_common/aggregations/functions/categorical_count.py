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
from arthur_common.tools.duckdb_data_loader import escape_identifier, escape_str_literal
from duckdb import DuckDBPyConnection


class CategoricalCountAggregationFunction(NumericAggregationFunction):
    METRIC_NAME = "categorical_count"

    @staticmethod
    def id() -> UUID:
        return UUID("00000000-0000-0000-0000-00000000000c")

    @staticmethod
    def display_name() -> str:
        return "Category Count"

    @staticmethod
    def description() -> str:
        return "Metric that counts the number of discrete values of each category in a string column. Creates a separate dimension for each category and the values are the count of occurrences of that category in the time window."

    def aggregate(
        self,
        ddb_conn: DuckDBPyConnection,
        dataset: Annotated[
            DatasetReference,
            MetricDatasetParameterAnnotation(
                friendly_name="Dataset",
                description="The dataset containing some categorical data.",
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
        categorical_col: Annotated[
            str,
            MetricColumnParameterAnnotation(
                source_dataset_parameter_key="dataset",
                allowed_column_types=[
                    ScalarType(dtype=DType.STRING),
                    ScalarType(dtype=DType.INT),
                ],
                tag_hints=[ScopeSchemaTag.CATEGORICAL],
                friendly_name="Categorical Column",
                description="A column containing categorical values to count.",
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
            select time_bucket(INTERVAL '5 minutes', {timestamp_col_escaped}) as ts, \
                count(*) as count, \
                {categorical_col_escaped} as category, \
                {categorical_col_name_escaped} as column_name \
                from {dataset.dataset_table_name} \
                where ts is not null \
                group by ts, category
        """
        segmentation_cols = [] if not segmentation_cols else segmentation_cols
        timestamp_col_escaped = escape_identifier(timestamp_col)
        categorical_col_escaped = escape_identifier(categorical_col)
        categorical_col_name_escaped = escape_str_literal(categorical_col)

        # build query components with segmentation columns
        escaped_segmentation_cols = [
            escape_identifier(col) for col in segmentation_cols
        ]
        all_select_clause_cols = [
            f"time_bucket(INTERVAL '5 minutes', {timestamp_col_escaped}) as ts",
            f"count(*) as count",
            f"{categorical_col_escaped} as category",
            f"{categorical_col_name_escaped} as column_name",
        ] + escaped_segmentation_cols
        all_group_by_cols = ["ts", "category"] + escaped_segmentation_cols
        extra_dims = ["column_name", "category"]

        # build query
        count_query = f"""
            select {", ".join(all_select_clause_cols)}
            from {dataset.dataset_table_name}
            where ts is not null
            group by {", ".join(all_group_by_cols)}
        """

        results = ddb_conn.sql(count_query).df()

        series = self.group_query_results_to_numeric_metrics(
            results,
            "count",
            segmentation_cols + extra_dims,
            timestamp_col="ts",
        )
        metric = self.series_to_metric(self.METRIC_NAME, series)
        return [metric]
