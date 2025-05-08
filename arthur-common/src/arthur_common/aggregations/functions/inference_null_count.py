from typing import Annotated
from uuid import UUID

from arthur_common.aggregations.aggregator import NumericAggregationFunction
from arthur_common.models.metrics import DatasetReference, Dimension, NumericMetric
from arthur_common.models.schema_definitions import (
    DType,
    MetricColumnParameterAnnotation,
    MetricDatasetParameterAnnotation,
    ScalarType,
    ScopeSchemaTag,
)
from arthur_common.tools.duckdb_data_loader import escape_identifier
from duckdb import DuckDBPyConnection


class InferenceNullCountAggregationFunction(NumericAggregationFunction):
    METRIC_NAME = "null_count"

    @staticmethod
    def id() -> UUID:
        return UUID("00000000-0000-0000-0000-00000000000b")

    @staticmethod
    def display_name() -> str:
        return "Null Value Count"

    @staticmethod
    def description() -> str:
        return "Metric that counts the number of null values in the column per time window."

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
        nullable_col: Annotated[
            str,
            MetricColumnParameterAnnotation(
                source_dataset_parameter_key="dataset",
                allow_any_column_type=True,
                friendly_name="Nullable Column",
                description="A column containing nullable values to count.",
            ),
        ],
    ) -> list[NumericMetric]:
        escaped_timestamp_col = escape_identifier(timestamp_col)
        escaped_nullable_col = escape_identifier(nullable_col)
        count_query = f" \
            select time_bucket(INTERVAL '5 minutes', {escaped_timestamp_col}) as ts, \
            count(*) as count \
            from {dataset.dataset_table_name} where {escaped_nullable_col} is null \
            group by ts \
        "
        results = ddb_conn.sql(count_query).df()

        series = self.dimensionless_query_results_to_numeric_metrics(
            results,
            "count",
            "ts",
        )
        series.dimensions = [Dimension(name="column_name", value=nullable_col)]

        metric = self.series_to_metric(self.METRIC_NAME, [series])
        return [metric]
