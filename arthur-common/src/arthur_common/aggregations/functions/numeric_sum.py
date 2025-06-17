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


class NumericSumAggregationFunction(NumericAggregationFunction):
    METRIC_NAME = "numeric_sum"

    @staticmethod
    def id() -> UUID:
        return UUID("00000000-0000-0000-0000-00000000000f")

    @staticmethod
    def display_name() -> str:
        return "Numeric Sum"

    @staticmethod
    def description() -> str:
        return "Metric that reports the sum of the numeric column per time window."

    def aggregate(
        self,
        ddb_conn: DuckDBPyConnection,
        dataset: Annotated[
            DatasetReference,
            MetricDatasetParameterAnnotation(
                friendly_name="Dataset",
                description="The dataset containing the numeric data.",
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
        numeric_col: Annotated[
            str,
            MetricColumnParameterAnnotation(
                source_dataset_parameter_key="dataset",
                allowed_column_types=[
                    ScalarType(dtype=DType.INT),
                    ScalarType(dtype=DType.FLOAT),
                ],
                tag_hints=[ScopeSchemaTag.CONTINUOUS],
                friendly_name="Numeric Column",
                description="A column containing numeric values to sum.",
            ),
        ],
    ) -> list[NumericMetric]:
        escaped_timestamp_col = escape_identifier(timestamp_col)
        escaped_numeric_col = escape_identifier(numeric_col)
        dims = []
        if self.has_col_by_name(
            ddb_conn,
            dataset.dataset_table_name,
            "prompt_version_id",
        ):
            count_query = f" \
                select time_bucket(INTERVAL '5 minutes', {escaped_timestamp_col}) as ts, \
                sum({escaped_numeric_col}) as sum, \
                prompt_version_id \
                from {dataset.dataset_table_name} \
                where {escaped_numeric_col} is not null \
                group by ts, prompt_version_id \
            "
        else:
            count_query = f" \
                select time_bucket(INTERVAL '5 minutes', {escaped_timestamp_col}) as ts, \
                sum({escaped_numeric_col}) as sum \
                from {dataset.dataset_table_name} \
                where {escaped_numeric_col} is not null \
                group by ts \
            "
        results = ddb_conn.sql(count_query).df()

        series = self.group_query_results_to_numeric_metrics(
            results,
            "sum",
            dims,
            "ts",
        )
        # preserve dimension that identifies the name of the numeric column used for the aggregation
        for point in series:
            point.dimensions.append(Dimension(name="column_name", value=numeric_col))

        metric = self.series_to_metric(self.METRIC_NAME, series)
        return [metric]
