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
    ) -> list[NumericMetric]:
        escaped_timestamp_col = escape_identifier(timestamp_col)
        dims = []
        if self.has_col_by_name(
            ddb_conn,
            dataset.dataset_table_name,
            "prompt_version_id",
        ):
            count_query = f" \
                select time_bucket(INTERVAL '5 minutes', {escaped_timestamp_col}) as ts, \
                count(*) as count, \
                prompt_version_id \
                from {dataset.dataset_table_name} \
                group by ts, prompt_version_id \
            "
            dims.append("prompt_version_id")
        else:
            count_query = f" \
                select time_bucket(INTERVAL '5 minutes', {escaped_timestamp_col}) as ts, \
                count(*) as count \
                from {dataset.dataset_table_name} \
                group by ts \
            "
        results = ddb_conn.sql(count_query).df()
        series = self.group_query_results_to_numeric_metrics(
            results,
            "count",
            dims,
            "ts",
        )
        metric = self.series_to_metric(self.METRIC_NAME, series)
        return [metric]
