from typing import Annotated, Optional
from uuid import UUID

from arthur_common.aggregations.aggregator import NumericAggregationFunction
from arthur_common.models.datasets import ModelProblemType
from arthur_common.models.metrics import DatasetReference, NumericMetric
from arthur_common.models.schema_definitions import (
    DType,
    MetricColumnParameterAnnotation,
    MetricDatasetParameterAnnotation,
    MetricLiteralParameterAnnotation,
    MetricMultipleColumnParameterAnnotation,
    ScalarType,
    ScopeSchemaTag,
)
from arthur_common.tools.duckdb_data_loader import escape_identifier, escape_str_literal
from duckdb import DuckDBPyConnection


class MulticlassClassifierStringLabelSingleClassConfusionMatrixAggregationFunction(
    NumericAggregationFunction,
):
    @staticmethod
    def id() -> UUID:
        return UUID("dc728927-6928-4a3b-b174-8c1ec8b58d62")

    @staticmethod
    def display_name() -> str:
        return "Multiclass Classification Confusion Matrix Single Class - String Class Label Prediction"

    @staticmethod
    def description() -> str:
        return (
            "Aggregation that takes in the string label for the positive class, "
            "and calculates the confusion matrix (True Positives, False Positives, "
            "False Negatives, True Negatives) for that class compared to all others."
        )

    def aggregate(
        self,
        ddb_conn: DuckDBPyConnection,
        dataset: Annotated[
            DatasetReference,
            MetricDatasetParameterAnnotation(
                friendly_name="Dataset",
                description="The dataset containing the prediction and ground truth values.",
                model_problem_type=ModelProblemType.MULTICLASS_CLASSIFICATION,
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
                    ScalarType(dtype=DType.STRING),
                ],
                tag_hints=[ScopeSchemaTag.PREDICTION],
                friendly_name="Prediction Column",
                description="A column containing the predicted string class label.",
            ),
        ],
        gt_values_col: Annotated[
            str,
            MetricColumnParameterAnnotation(
                source_dataset_parameter_key="dataset",
                allowed_column_types=[
                    ScalarType(dtype=DType.STRING),
                ],
                tag_hints=[ScopeSchemaTag.GROUND_TRUTH],
                friendly_name="Ground Truth Column",
                description="A column containing the ground truth string class label.",
            ),
        ],
        positive_class_label: Annotated[
            str,
            MetricLiteralParameterAnnotation(
                parameter_dtype=DType.STRING,
                friendly_name="Positive Class Label",
                description="The label indicating a positive class.",
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
        segmentation_cols = [] if not segmentation_cols else segmentation_cols
        escaped_positive_class_label = escape_str_literal(positive_class_label)
        normalization_case = f"""
                CASE
                    WHEN value = {escaped_positive_class_label} THEN 1
                    ELSE 0
                END
                """
        return self.generate_confusion_matrix_metrics(
            ddb_conn,
            timestamp_col,
            prediction_col,
            gt_values_col,
            normalization_case,
            normalization_case,
            dataset,
            escaped_positive_class_label,
            segmentation_cols,
        )

    def generate_confusion_matrix_metrics(
        self,
        ddb_conn: DuckDBPyConnection,
        timestamp_col: str,
        prediction_col: str,
        gt_values_col: str,
        prediction_normalization_case: str,
        gt_normalization_case: str,
        dataset: DatasetReference,
        escaped_positive_class_label: str,
        segmentation_cols: list[str],
    ) -> list[NumericMetric]:
        """
        Generate a SQL query to compute confusion matrix metrics over time.

        Args:
            ddb_conn: duck DB connection
            timestamp_col: Column name containing timestamps
            prediction_col: Column name containing predictions
            gt_values_col: Column name containing ground truth values
            prediction_normalization_case: SQL CASE statement for normalizing predictions to 0 / 1 / null using 'value' as the target column name
            gt_normalization_case: SQL CASE statement for normalizing ground truth values to 0 / 1 / null using 'value' as the target column name
            dataset: DatasetReference containing dataset metadata
            escaped_positive_class_label: escaped label for the class to include in the dimensions
            segmentation_cols: List of columns to segment by

        Returns:
            str: SQL query that computes confusion matrix metrics
            Returns the following SQL with no segmentation:
            WITH normalized_data AS (
                    SELECT
                        {escaped_timestamp_col} AS timestamp,
                        {prediction_normalization_case.replace('value', escaped_prediction_col)} AS prediction,
                        {gt_normalization_case.replace('value', escaped_gt_values_col)} AS actual_value
                    FROM {dataset.dataset_table_name}
                    WHERE {escaped_timestamp_col} IS NOT NULL
                )
                SELECT
                    time_bucket(INTERVAL '5 minutes', timestamp) AS ts,
                    SUM(CASE WHEN prediction = 1 AND actual_value = 1 THEN 1 ELSE 0 END) AS true_positive_count,
                    SUM(CASE WHEN prediction = 1 AND actual_value = 0 THEN 1 ELSE 0 END) AS false_positive_count,
                    SUM(CASE WHEN prediction = 0 AND actual_value = 1 THEN 1 ELSE 0 END) AS false_negative_count,
                    SUM(CASE WHEN prediction = 0 AND actual_value = 0 THEN 1 ELSE 0 END) AS true_negative_count,
                    any_value({escaped_positive_class_label}) as class_label
                FROM normalized_data
                GROUP BY ts
                ORDER BY ts

        """
        escaped_timestamp_col = escape_identifier(timestamp_col)
        escaped_prediction_col = escape_identifier(prediction_col)
        escaped_gt_values_col = escape_identifier(gt_values_col)

        # build query components with segmentation columns
        escaped_segmentation_cols = [
            escape_identifier(col) for col in segmentation_cols
        ]
        first_subquery_select_cols = [
            f"{escaped_timestamp_col} AS timestamp",
            f"{prediction_normalization_case.replace('value', escaped_prediction_col)} AS prediction",
            f"{gt_normalization_case.replace('value', escaped_gt_values_col)} AS actual_value",
        ] + escaped_segmentation_cols
        second_subquery_select_cols = [
            "time_bucket(INTERVAL '5 minutes', timestamp) AS ts",
            "SUM(CASE WHEN prediction = 1 AND actual_value = 1 THEN 1 ELSE 0 END) AS true_positive_count",
            "SUM(CASE WHEN prediction = 1 AND actual_value = 0 THEN 1 ELSE 0 END) AS false_positive_count",
            "SUM(CASE WHEN prediction = 0 AND actual_value = 1 THEN 1 ELSE 0 END) AS false_negative_count",
            "SUM(CASE WHEN prediction = 0 AND actual_value = 0 THEN 1 ELSE 0 END) AS true_negative_count",
            f"any_value({escaped_positive_class_label}) as class_label",
        ] + escaped_segmentation_cols
        second_subquery_group_by_cols = ["ts"] + escaped_segmentation_cols
        extra_dims = ["class_label"]

        # build query
        confusion_matrix_query = f"""
        WITH normalized_data AS (
            SELECT {", ".join(first_subquery_select_cols)}
            FROM {dataset.dataset_table_name}
            WHERE {escaped_timestamp_col} IS NOT NULL
        )
        SELECT {", ".join(second_subquery_select_cols)}
        FROM normalized_data
        GROUP BY {", ".join(second_subquery_group_by_cols)}
        ORDER BY ts
"""

        results = ddb_conn.sql(confusion_matrix_query).df()

        tp = self.group_query_results_to_numeric_metrics(
            results,
            "true_positive_count",
            dim_columns=segmentation_cols + extra_dims,
            timestamp_col="ts",
        )
        fp = self.group_query_results_to_numeric_metrics(
            results,
            "false_positive_count",
            dim_columns=segmentation_cols + extra_dims,
            timestamp_col="ts",
        )
        fn = self.group_query_results_to_numeric_metrics(
            results,
            "false_negative_count",
            dim_columns=segmentation_cols + extra_dims,
            timestamp_col="ts",
        )
        tn = self.group_query_results_to_numeric_metrics(
            results,
            "true_negative_count",
            dim_columns=segmentation_cols + extra_dims,
            timestamp_col="ts",
        )
        tp_metric = self.series_to_metric(
            "multiclass_confusion_matrix_single_class_true_positive_count",
            tp,
        )
        fp_metric = self.series_to_metric(
            "multiclass_confusion_matrix_single_class_false_positive_count",
            fp,
        )
        fn_metric = self.series_to_metric(
            "multiclass_confusion_matrix_single_class_false_negative_count",
            fn,
        )
        tn_metric = self.series_to_metric(
            "multiclass_confusion_matrix_single_class_true_negative_count",
            tn,
        )
        return [tp_metric, fp_metric, fn_metric, tn_metric]
