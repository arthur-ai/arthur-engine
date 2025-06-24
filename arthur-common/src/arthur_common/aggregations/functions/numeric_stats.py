from typing import Annotated, Optional
from uuid import UUID

from arthur_common.aggregations.aggregator import SketchAggregationFunction
from arthur_common.models.metrics import DatasetReference, SketchMetric
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


class NumericSketchAggregationFunction(SketchAggregationFunction):
    METRIC_NAME = "numeric_sketch"

    @staticmethod
    def id() -> UUID:
        return UUID("00000000-0000-0000-0000-00000000000d")

    @staticmethod
    def display_name() -> str:
        return "Numeric Distribution"

    @staticmethod
    def description() -> str:
        return (
            "Metric that calculates a distribution (data sketch) on a numeric column."
        )

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
                description="A column containing numeric values to calculate a data sketch on.",
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
    ) -> list[SketchMetric]:
        """Executed SQL with no segmentation columns:
                    select {escaped_timestamp_col_id} as ts, \
                       {escaped_numeric_col_id}, \
                       {numeric_col_name_str} as column_name \
                from {dataset.dataset_table_name} \
                where {escaped_numeric_col_id} is not null \
        """
        segmentation_cols = [] if not segmentation_cols else segmentation_cols
        escaped_timestamp_col_id = escape_identifier(timestamp_col)
        escaped_numeric_col_id = escape_identifier(numeric_col)
        numeric_col_name_str = escape_str_literal(numeric_col)

        # build query components with segmentation columns
        escaped_segmentation_cols = [
            escape_identifier(col) for col in segmentation_cols
        ]
        all_select_clause_cols = [
            f"{escaped_timestamp_col_id} as ts",
            f"{escaped_numeric_col_id}",
            f"{numeric_col_name_str} as column_name",
        ] + escaped_segmentation_cols
        extra_dims = ["column_name"]

        # build query
        data_query = f"""
                    select {", ".join(all_select_clause_cols)}
                    from {dataset.dataset_table_name}
                    where {escaped_numeric_col_id} is not null
                """

        results = ddb_conn.sql(data_query).df()

        series = self.group_query_results_to_sketch_metrics(
            results,
            numeric_col,
            segmentation_cols + extra_dims,
            "ts",
        )

        metric = self.series_to_metric(self.METRIC_NAME, series)
        return [metric]
