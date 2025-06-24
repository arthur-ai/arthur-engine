from typing import Annotated, Optional
from uuid import UUID

from arthur_common.aggregations.functions.inference_count_by_class import (
    BinaryClassifierCountByClassAggregationFunction,
)
from arthur_common.models.datasets import ModelProblemType
from arthur_common.models.metrics import DatasetReference, NumericMetric
from arthur_common.models.schema_definitions import (
    DType,
    MetricColumnParameterAnnotation,
    MetricDatasetParameterAnnotation,
    MetricMultipleColumnParameterAnnotation,
    ScalarType,
    ScopeSchemaTag,
)
from duckdb import DuckDBPyConnection


class MulticlassClassifierCountByClassAggregationFunction(
    BinaryClassifierCountByClassAggregationFunction,
):
    """
    This class simply exposes the same calculation as the BinaryClassifierCountByClassAggregationFunction
    but using the MULTICLASS_CLASSIFICATION tags
    """

    @staticmethod
    def id() -> UUID:
        return UUID("64a338fb-6c99-4c40-ba39-81ab8baa8687")

    @staticmethod
    def display_name() -> str:
        return "Multiclass Classification Count by Class - Class Label"

    @staticmethod
    def description() -> str:
        return (
            "Aggregation that counts the number of predictions by class for a multiclass classifier. "
            "Takes boolean, integer, or string prediction values and groups them by time bucket "
            "to show prediction distribution over time."
        )

    @staticmethod
    def _metric_name() -> str:
        return "multiclass_classifier_count_by_class"

    def aggregate(
        self,
        ddb_conn: DuckDBPyConnection,
        dataset: Annotated[
            DatasetReference,
            MetricDatasetParameterAnnotation(
                friendly_name="Dataset",
                description="The dataset containing multiclass classifier prediction values.",
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
                    ScalarType(dtype=DType.BOOL),
                    ScalarType(dtype=DType.INT),
                    ScalarType(dtype=DType.STRING),
                ],
                tag_hints=[ScopeSchemaTag.PREDICTION],
                friendly_name="Prediction Column",
                description="A column containing boolean, integer, or string labelled prediction values.",
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
        return super().aggregate(
            ddb_conn=ddb_conn,
            dataset=dataset,
            timestamp_col=timestamp_col,
            prediction_col=prediction_col,
            segmentation_cols=segmentation_cols,
        )
