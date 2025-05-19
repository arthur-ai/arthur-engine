from typing import Annotated
from uuid import UUID

from arthur_common.aggregations.aggregator import NumericAggregationFunction
from arthur_common.models.datasets import ModelProblemType
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


class MeanAbsoluteErrorAggregationFunction(NumericAggregationFunction):
    @staticmethod
    def id() -> UUID:
        return UUID("00000000-0000-0000-0000-00000000000e")

    @staticmethod
    def display_name() -> str:
        return "Mean Absolute Error"

    @staticmethod
    def description() -> str:
        return "Metric that sums the absolute error of a prediction and ground truth column. It omits any rows where either the prediction or ground truth are null. It reports the count of non-null rows used in the calculation in a second metric."

    def aggregate(
        self,
        ddb_conn: DuckDBPyConnection,
        dataset: Annotated[
            DatasetReference,
            MetricDatasetParameterAnnotation(
                friendly_name="Dataset",
                description="The dataset containing the inference data.",
                model_problem_type=ModelProblemType.REGRESSION,
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
        prediction_col: Annotated[
            str,
            MetricColumnParameterAnnotation(
                source_dataset_parameter_key="dataset",
                allowed_column_types=[
                    ScalarType(dtype=DType.FLOAT),
                ],
                tag_hints=[ScopeSchemaTag.PREDICTION],
                friendly_name="Prediction Column",
                description="A column containing float typed prediction values.",
            ),
        ],
        ground_truth_col: Annotated[
            str,
            MetricColumnParameterAnnotation(
                source_dataset_parameter_key="dataset",
                allowed_column_types=[
                    ScalarType(dtype=DType.FLOAT),
                ],
                tag_hints=[ScopeSchemaTag.GROUND_TRUTH],
                friendly_name="Ground Truth Column",
                description="A column containing float typed ground truth values.",
            ),
        ],
    ) -> list[NumericMetric]:
        escaped_timestamp_col = escape_identifier(timestamp_col)
        escaped_prediction_col = escape_identifier(prediction_col)
        escaped_ground_truth_col = escape_identifier(ground_truth_col)
        count_query = f" \
            SELECT time_bucket(INTERVAL '5 minutes', {escaped_timestamp_col}) as ts, \
            SUM(ABS({escaped_prediction_col} - {escaped_ground_truth_col})) as ae, \
            COUNT(*) as count \
            FROM {dataset.dataset_table_name} \
            WHERE {escaped_prediction_col} IS NOT NULL \
            AND {escaped_ground_truth_col} IS NOT NULL \
            GROUP BY ts order by ts desc \
        "

        results = ddb_conn.sql(count_query).df()
        count_series = self.dimensionless_query_results_to_numeric_metrics(
            results,
            "count",
            "ts",
        )
        absolute_error_series = self.dimensionless_query_results_to_numeric_metrics(
            results,
            "ae",
            "ts",
        )

        count_metric = self.series_to_metric("absolute_error_count", [count_series])
        absolute_error_metric = self.series_to_metric(
            "absolute_error_sum",
            [absolute_error_series],
        )

        return [count_metric, absolute_error_metric]
