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
from arthur_common.tools.duckdb_data_loader import escape_identifier
from duckdb import DuckDBPyConnection


class ConfusionMatrixAggregationFunction(NumericAggregationFunction):
    def generate_confusion_matrix_metrics(
        self,
        ddb_conn: DuckDBPyConnection,
        timestamp_col: str,
        prediction_col: str,
        gt_values_col: str,
        prediction_normalization_case: str,
        gt_normalization_case: str,
        dataset: DatasetReference,
        segmentation_cols: list[str],
    ) -> list[NumericMetric]:
        """
        Generate a SQL query to compute confusion matrix metrics over time.

        Args:
            timestamp_col: Column name containing timestamps
            prediction_col: Column name containing predictions
            gt_values_col: Column name containing ground truth values
            prediction_normalization_case: SQL CASE statement for normalizing predictions to 0 / 1 / null using 'value' as the target column name
            gt_normalization_case: SQL CASE statement for normalizing ground truth values to 0 / 1 / null using 'value' as the target column name
            dataset: DatasetReference containing dataset metadata
            segmentation_cols: list of columns to segment by

        Returns:
            str: SQL query that computes confusion matrix metrics
            Without segmentation, this is the query:
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
                    SUM(CASE WHEN prediction = actual_value AND actual_value = 1 THEN 1 ELSE 0 END) AS true_positive_count,
                    SUM(CASE WHEN prediction != actual_value AND actual_value = 0 THEN 1 ELSE 0 END) AS false_positive_count,
                    SUM(CASE WHEN prediction != actual_value AND actual_value = 1 THEN 1 ELSE 0 END) AS false_negative_count,
                    SUM(CASE WHEN prediction = actual_value AND actual_value = 0 THEN 1 ELSE 0 END) AS true_negative_count
                FROM normalized_data
                GROUP BY ts
                ORDER BY ts
        """
        segmentation_cols = [] if not segmentation_cols else segmentation_cols
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
            "SUM(CASE WHEN prediction = actual_value AND actual_value = 1 THEN 1 ELSE 0 END) AS true_positive_count",
            "SUM(CASE WHEN prediction != actual_value AND actual_value = 0 THEN 1 ELSE 0 END) AS false_positive_count",
            "SUM(CASE WHEN prediction != actual_value AND actual_value = 1 THEN 1 ELSE 0 END) AS false_negative_count",
            "SUM(CASE WHEN prediction = actual_value AND actual_value = 0 THEN 1 ELSE 0 END) AS true_negative_count",
        ] + escaped_segmentation_cols
        second_subquery_group_by_cols = ["ts"] + escaped_segmentation_cols

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
            dim_columns=segmentation_cols,
            timestamp_col="ts",
        )
        fp = self.group_query_results_to_numeric_metrics(
            results,
            "false_positive_count",
            dim_columns=segmentation_cols,
            timestamp_col="ts",
        )
        fn = self.group_query_results_to_numeric_metrics(
            results,
            "false_negative_count",
            dim_columns=segmentation_cols,
            timestamp_col="ts",
        )
        tn = self.group_query_results_to_numeric_metrics(
            results,
            "true_negative_count",
            dim_columns=segmentation_cols,
            timestamp_col="ts",
        )
        tp_metric = self.series_to_metric("confusion_matrix_true_positive_count", tp)
        fp_metric = self.series_to_metric("confusion_matrix_false_positive_count", fp)
        fn_metric = self.series_to_metric("confusion_matrix_false_negative_count", fn)
        tn_metric = self.series_to_metric("confusion_matrix_true_negative_count", tn)
        return [tp_metric, fp_metric, fn_metric, tn_metric]


class BinaryClassifierIntBoolConfusionMatrixAggregationFunction(
    ConfusionMatrixAggregationFunction,
):
    @staticmethod
    def id() -> UUID:
        return UUID("00000000-0000-0000-0000-00000000001c")

    @staticmethod
    def display_name() -> str:
        return "Binary Classification Confusion Matrix - Int/Bool Prediction"

    @staticmethod
    def description() -> str:
        return "Aggregation that takes in boolean or integer prediction and ground truth values and calculates the confusion matrix (True Positives, False Positives, False Negatives, True Negatives) for a binary set of predictions and values."

    def aggregate(
        self,
        ddb_conn: DuckDBPyConnection,
        dataset: Annotated[
            DatasetReference,
            MetricDatasetParameterAnnotation(
                friendly_name="Dataset",
                description="The dataset containing the prediction and ground truth values.",
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
                ],
                tag_hints=[ScopeSchemaTag.PREDICTION],
                friendly_name="Prediction Column",
                description="A column containing boolean or integer prediction values.",
            ),
        ],
        gt_values_col: Annotated[
            str,
            MetricColumnParameterAnnotation(
                source_dataset_parameter_key="dataset",
                allowed_column_types=[
                    ScalarType(dtype=DType.BOOL),
                    ScalarType(dtype=DType.INT),
                ],
                tag_hints=[ScopeSchemaTag.GROUND_TRUTH],
                friendly_name="Ground Truth Column",
                description="A column containing boolean or integer ground truth values.",
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
        escaped_prediction_col = escape_identifier(prediction_col)
        # Get the type of prediction column
        type_query = f"SELECT typeof({escaped_prediction_col}) as col_type FROM {dataset.dataset_table_name} LIMIT 1"
        res = ddb_conn.sql(type_query).fetchone()
        # As long as this column exists, we should be able to get the type. This is here to make mypy happy.
        if not res:
            raise ValueError(f"No results found for type query: {type_query}")
        col_type = res[0].lower()

        match col_type:
            case "boolean":
                normalization_case = """
                CASE
                    WHEN value THEN 1
                    ELSE 0
                END
                """
            case "integer" | "bigint":
                normalization_case = """
                CASE
                    WHEN value = 1 THEN 1
                    WHEN value = 0 THEN 0
                    ELSE NULL
                END
                """
            case _:
                raise ValueError(f"Unsupported column type: {col_type}")

        return self.generate_confusion_matrix_metrics(
            ddb_conn,
            timestamp_col,
            prediction_col,
            gt_values_col,
            normalization_case,
            normalization_case,
            dataset,
            segmentation_cols,
        )


class BinaryClassifierStringLabelConfusionMatrixAggregationFunction(
    ConfusionMatrixAggregationFunction,
):
    @staticmethod
    def id() -> UUID:
        return UUID("00000000-0000-0000-0000-00000000001d")

    @staticmethod
    def display_name() -> str:
        return "Binary Classification Confusion Matrix - String Class Label Prediction"

    @staticmethod
    def description() -> str:
        return "Aggregation that takes in string labelled prediction and ground truth values and calculates the confusion matrix (True Positives, False Positives, False Negatives, True Negatives) for a binary set of predictions and values."

    def aggregate(
        self,
        ddb_conn: DuckDBPyConnection,
        dataset: Annotated[
            DatasetReference,
            MetricDatasetParameterAnnotation(
                friendly_name="Dataset",
                description="The dataset containing the prediction and ground truth values.",
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
                    ScalarType(dtype=DType.STRING),
                ],
                tag_hints=[ScopeSchemaTag.PREDICTION],
                friendly_name="Prediction Column",
                description="A column containing string labelled prediction values.",
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
                description="A column containing string labelled ground truth values.",
            ),
        ],
        true_label: Annotated[
            str,
            MetricLiteralParameterAnnotation(
                parameter_dtype=DType.STRING,
                friendly_name="True Label",
                description="The label indicating a positive classification to normalize to 1.",
            ),
        ],
        false_label: Annotated[
            str,
            MetricLiteralParameterAnnotation(
                parameter_dtype=DType.STRING,
                friendly_name="False Label",
                description="The label indicating a negative classification to normalize to 0.",
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
        normalization_case = f"""
                CASE
                    WHEN value = '{true_label}' THEN 1
                    WHEN value = '{false_label}' THEN 0
                    ELSE NULL
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
            segmentation_cols,
        )


class BinaryClassifierProbabilityThresholdConfusionMatrixAggregationFunction(
    ConfusionMatrixAggregationFunction,
):
    @staticmethod
    def id() -> UUID:
        return UUID("00000000-0000-0000-0000-00000000001e")

    @staticmethod
    def display_name() -> str:
        return "Binary Classification Confusion Matrix - Probability Threshold"

    @staticmethod
    def description() -> str:
        return "Aggregation that takes in a float prediction column, a ground truth values column, and a probability threshold and calculates the confusion matrix (True Positives, False Positives, False Negatives, True Negatives) for a binary set of predictions and values where the predictions are calculated using the probability threshold."

    def aggregate(
        self,
        ddb_conn: DuckDBPyConnection,
        dataset: Annotated[
            DatasetReference,
            MetricDatasetParameterAnnotation(
                friendly_name="Dataset",
                description="The dataset containing the prediction and ground truth values.",
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
        gt_values_col: Annotated[
            str,
            MetricColumnParameterAnnotation(
                source_dataset_parameter_key="dataset",
                allowed_column_types=[
                    ScalarType(dtype=DType.BOOL),
                    ScalarType(dtype=DType.INT),
                ],
                tag_hints=[ScopeSchemaTag.GROUND_TRUTH],
                friendly_name="Ground Truth Column",
                description="A column containing boolean or integer ground truth values.",
            ),
        ],
        threshold: Annotated[
            float,
            MetricLiteralParameterAnnotation(
                parameter_dtype=DType.FLOAT,
                friendly_name="Threshold",
                description="The threshold to classify predictions to 0 or 1.",
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
        escaped_gt_values_col = escape_identifier(gt_values_col)
        prediction_normalization_case = f"""
                CASE
                    WHEN value >= {threshold} THEN 1
                    WHEN value < {threshold} THEN 0
                    ELSE NULL
                END
                """

        type_query = f"SELECT typeof({escaped_gt_values_col}) as col_type FROM {dataset.dataset_table_name} LIMIT 1"
        res = ddb_conn.sql(type_query).fetchone()
        # As long as this column exists, we should be able to get the type. This is here to make mypy happy.
        if not res:
            raise ValueError(f"No results found for type query: {type_query}")
        col_type = res[0].lower()

        match col_type:
            case "boolean":
                gt_normalization_case = """
                CASE
                    WHEN value THEN 1
                    ELSE 0
                END
                """
            case "integer" | "bigint":
                gt_normalization_case = """
                CASE
                    WHEN value = 1 THEN 1
                    WHEN value = 0 THEN 0
                    ELSE NULL
                END
                """
            case _:
                raise ValueError(f"Unsupported column type: {col_type}")

        return self.generate_confusion_matrix_metrics(
            ddb_conn,
            timestamp_col,
            prediction_col,
            gt_values_col,
            prediction_normalization_case,
            gt_normalization_case,
            dataset,
            segmentation_cols,
        )
