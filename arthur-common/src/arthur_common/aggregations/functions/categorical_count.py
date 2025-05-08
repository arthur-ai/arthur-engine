from typing import Annotated
from uuid import UUID

from arthur_common.aggregations.aggregator import NumericAggregationFunction
from arthur_common.models.metrics import DatasetReference, NumericMetric
from arthur_common.models.schema_definitions import (
    DType,
    MetricColumnParameterAnnotation,
    MetricDatasetParameterAnnotation,
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
    ) -> list[NumericMetric]:
        timestamp_col_escaped = escape_identifier(timestamp_col)
        categorical_col_escaped = escape_identifier(categorical_col)
        categorical_col_name_escaped = escape_str_literal(categorical_col)
        count_query = f" \
            select time_bucket(INTERVAL '5 minutes', {timestamp_col_escaped}) as ts, \
            count(*) as count, \
            {categorical_col_escaped} as category, \
            {categorical_col_name_escaped} as column_name \
            from {dataset.dataset_table_name} \
            where ts is not null \
            group by ts, category  \
        "
        results = ddb_conn.sql(count_query).df()

        series = self.group_query_results_to_numeric_metrics(
            results,
            "count",
            ["column_name", "category"],
            timestamp_col="ts",
        )
        metric = self.series_to_metric(self.METRIC_NAME, series)
        return [metric]
