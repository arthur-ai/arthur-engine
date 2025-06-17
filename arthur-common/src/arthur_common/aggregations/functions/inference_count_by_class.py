from typing import Annotated
from uuid import UUID

from arthur_common.aggregations.aggregator import NumericAggregationFunction
from arthur_common.models.datasets import ModelProblemType
from arthur_common.models.metrics import DatasetReference, NumericMetric
from arthur_common.models.schema_definitions import (
    DType,
    MetricColumnParameterAnnotation,
    MetricDatasetParameterAnnotation,
    MetricLiteralParameterAnnotation,
    ScalarType,
    ScopeSchemaTag,
)
from arthur_common.tools.duckdb_data_loader import escape_identifier
from duckdb import DuckDBPyConnection


class BinaryClassifierCountByClassAggregationFunction(NumericAggregationFunction):
    @staticmethod
    def id() -> UUID:
        return UUID("00000000-0000-0000-0000-00000000001f")

    @staticmethod
    def display_name() -> str:
        return "Binary Classification Count by Class - Class Label"

    @staticmethod
    def description() -> str:
        return "Aggregation that counts the number of predictions by class for a binary classifier. Takes boolean, integer, or string prediction values and groups them by time bucket to show prediction distribution over time."

    @staticmethod
    def _metric_name() -> str:
        return "binary_classifier_count_by_class"

    def aggregate(
        self,
        ddb_conn: DuckDBPyConnection,
        dataset: Annotated[
            DatasetReference,
            MetricDatasetParameterAnnotation(
                friendly_name="Dataset",
                description="The dataset containing binary classifier prediction values.",
                model_problem_type=ModelProblemType.BINARY_CLASSIFICATION,
            ),
        ],
        timestamp_col: Annotated[
            str,
            MetricColumnParameterAnnotation(
                source_dataset_parameter_key="dataset",
                tag_hints=[ScopeSchemaTag.PRIMARY_TIMESTAMP],
                allowed_column_types=[
                    ScalarType(dtype=DType.TIMESTAMP),
                ],
                friendly_name="Timestamp Column",
                description="A column containing timestamp values to bucket by.",
            ),
        ],
        prediction_col: Annotated[
            str,
            MetricColumnParameterAnnotation(
                source_dataset_parameter_key="dataset",
                allowed_column_types=[
                    ScalarType(dtype=DType.BOOL),
                    ScalarType(dtype=DType.INT),
                    ScalarType(dtype=DType.STRING),
                ],
                tag_hints=[ScopeSchemaTag.PREDICTION],
                friendly_name="Prediction Column",
                description="A column containing boolean, integer, or string labelled prediction values.",
            ),
        ],
    ) -> list[NumericMetric]:
        escaped_timestamp_col = escape_identifier(timestamp_col)
        escaped_pred_col = escape_identifier(prediction_col)
        dims = ["prediction"]
        if self.has_col_by_name(
            ddb_conn,
            dataset.dataset_table_name,
            "prompt_version_id",
        ):
            query = f"""
                SELECT
                    time_bucket(INTERVAL '5 minutes', {escaped_timestamp_col}) as ts,
                    {escaped_pred_col} as prediction,
                    COUNT(*) as count,
                    prompt_version_id
                FROM {dataset.dataset_table_name}
                GROUP BY
                    ts,
                    -- group by raw column name instead of alias in select
                    -- in case table has a column called 'prediction'
                    {escaped_pred_col},
                    prompt_version_id
                ORDER BY ts
            """
            dims.append("prompt_version_id")
        else:
            query = f"""
                SELECT
                    time_bucket(INTERVAL '5 minutes', {escaped_timestamp_col}) as ts,
                    {escaped_pred_col} as prediction,
                    COUNT(*) as count
                FROM {dataset.dataset_table_name}
                GROUP BY
                    ts,
                    -- group by raw column name instead of alias in select
                    -- in case table has a column called 'prediction'
                    {escaped_pred_col}
                ORDER BY ts
            """

        result = ddb_conn.sql(query).df()

        series = self.group_query_results_to_numeric_metrics(
            result,
            "count",
            dims,
            "ts",
        )
        metric = self.series_to_metric(self._metric_name(), series)
        return [metric]


class BinaryClassifierCountThresholdClassAggregationFunction(
    NumericAggregationFunction,
):
    @staticmethod
    def id() -> UUID:
        return UUID("00000000-0000-0000-0000-000000000020")

    @staticmethod
    def display_name() -> str:
        return "Binary Classification Count by Class - Probability Threshold"

    @staticmethod
    def description() -> str:
        return "Aggregation that counts the number of predictions by class for a binary classifier using a probability threshold. Takes float prediction values and a threshold value to classify predictions, then groups them by time bucket to show prediction distribution over time."

    @staticmethod
    def _metric_name() -> str:
        return "binary_classifier_count_by_class"

    def aggregate(
        self,
        ddb_conn: DuckDBPyConnection,
        dataset: Annotated[
            DatasetReference,
            MetricDatasetParameterAnnotation(
                friendly_name="Dataset",
                description="The dataset containing binary classifier prediction values.",
                model_problem_type=ModelProblemType.BINARY_CLASSIFICATION,
            ),
        ],
        timestamp_col: Annotated[
            str,
            MetricColumnParameterAnnotation(
                source_dataset_parameter_key="dataset",
                tag_hints=[ScopeSchemaTag.PRIMARY_TIMESTAMP],
                allowed_column_types=[
                    ScalarType(dtype=DType.TIMESTAMP),
                ],
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
                description="A column containing float prediction values.",
            ),
        ],
        threshold: Annotated[
            float,
            MetricLiteralParameterAnnotation(
                parameter_dtype=DType.FLOAT,
                friendly_name="Threshold",
                description="The threshold to classify predictions to 0 or 1. 0 will result in the 'False Label' being assigned and 1 to the 'True Label' being assigned.",
            ),
        ],
        true_label: Annotated[
            str,
            MetricLiteralParameterAnnotation(
                parameter_dtype=DType.STRING,
                friendly_name="True Label",
                description="The label denoting a positive classification.",
            ),
        ],
        false_label: Annotated[
            str,
            MetricLiteralParameterAnnotation(
                parameter_dtype=DType.STRING,
                friendly_name="False Label",
                description="The label denoting a negative classification.",
            ),
        ],
    ) -> list[NumericMetric]:
        escaped_timestamp_col = escape_identifier(timestamp_col)
        escaped_prediction_col = escape_identifier(prediction_col)
        dims = ["prediction"]
        if self.has_col_by_name(
            ddb_conn,
            dataset.dataset_table_name,
            "prompt_version_id",
        ):
            query = f"""
                SELECT
                    time_bucket(INTERVAL '5 minutes', {escaped_timestamp_col}) as ts,
                    CASE WHEN {escaped_prediction_col} >= {threshold} THEN '{true_label}' ELSE '{false_label}' END as prediction,
                    COUNT(*) as count,
                    prompt_version_id
                FROM {dataset.dataset_table_name}
                GROUP BY
                    ts,
                    -- group by raw column name instead of alias in select
                    -- in case table has a column called 'prediction'
                    {escaped_prediction_col},
                    prompt_version_id
                ORDER BY ts
            """
            dims.append("prompt_version_id")
        else:
            query = f"""
                SELECT
                    time_bucket(INTERVAL '5 minutes', {escaped_timestamp_col}) as ts,
                    CASE WHEN {escaped_prediction_col} >= {threshold} THEN '{true_label}' ELSE '{false_label}' END as prediction,
                    COUNT(*) as count
                FROM {dataset.dataset_table_name}
                GROUP BY
                    ts,
                    -- group by raw column name instead of alias in select
                    -- in case table has a column called 'prediction'
                    {escaped_prediction_col}
                ORDER BY ts
            """

        result = ddb_conn.sql(query).df()

        series = self.group_query_results_to_numeric_metrics(
            result,
            "count",
            dims,
            "ts",
        )
        metric = self.series_to_metric(self._metric_name(), series)
        return [metric]
