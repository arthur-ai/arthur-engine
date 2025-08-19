from logging import Logger
from typing import Any

import duckdb
import pandas as pd
from arthur_client.api_bindings import (
    AggregationMetricType,
    AggregationSpec,
    CustomAggregationSpecSchema,
    Dataset,
)
from arthur_common.aggregations import (
    NumericAggregationFunction,
    SketchAggregationFunction,
)
from arthur_common.models.metrics import (
    NumericMetric,
    ReportedCustomAggregation,
    SketchMetric,
)
from arthur_common.tools.duckdb_data_loader import escape_identifier
from metric_calculators.metric_calculator import MetricCalculator


class CustomMetricSQLCalculator(MetricCalculator):
    def __init__(
        self,
        conn: duckdb.DuckDBPyConnection,
        logger: Logger,
        agg_spec_schema: CustomAggregationSpecSchema,
    ) -> None:
        """
        :param conn: DuckDB Connection with datasets loaded to calculate aggregations over.
        :param agg_function_type: The AggregationFunction to execute.
        :param agg_function_schema: The schema of the aggregation function to execute.
        """
        super().__init__(conn, logger, agg_spec_schema)
        # enforce CustomAggregationSpecSchema type for agg_schema field
        self.agg_schema: CustomAggregationSpecSchema = agg_spec_schema

    @staticmethod
    def _calculate_time_series(
        results: pd.DataFrame,
        reported_agg: ReportedCustomAggregation,
    ) -> NumericMetric | SketchMetric:
        """Returns the time series for a reported aggregation in the dataset represented in the results DataFrame."""
        match reported_agg.metric_kind:
            case AggregationMetricType.NUMERIC:
                numeric_series = (
                    NumericAggregationFunction.group_query_results_to_numeric_metrics(
                        results,
                        reported_agg.value_column,
                        reported_agg.dimension_columns,
                        reported_agg.timestamp_column,
                    )
                )
                return NumericAggregationFunction.series_to_metric(
                    metric_name=reported_agg.metric_name,
                    series=numeric_series,
                )
            case AggregationMetricType.SKETCH:
                sketch_series = (
                    SketchAggregationFunction.group_query_results_to_sketch_metrics(
                        results,
                        reported_agg.value_column,
                        reported_agg.dimension_columns,
                        reported_agg.timestamp_column,
                    )
                )
                return SketchAggregationFunction.series_to_metric(
                    reported_agg.metric_name,
                    sketch_series,
                )
            case _:
                raise ValueError(
                    f"Unsupported metric kind for custom aggregations: {reported_agg.metric_kind}.",
                )

    @staticmethod
    def _evaluate_arg_value(
        key_to_parameter_type: dict[str, str],
        arg_key: str,
        arg_val: Any,
    ) -> Any:
        """Returns the value that a parameter should be filled in with based on the parameter type.
        :param key_to_parameter_type: Map from argument key name to argument parameter type.
        :param arg_key: Argument key
        :param arg_val: Argument value returned by process_agg_args.
        """
        parameter_type = key_to_parameter_type[arg_key]
        match parameter_type:
            case "literal":
                return arg_val
            case "dataset":
                return arg_val.dataset_table_name
            case "column":
                return escape_identifier(arg_val)
            case _:
                raise ValueError(
                    f"Parameter type {parameter_type} not supported for custom metrics SQL calculator.",
                )

    def _construct_sql(self, aggregate_args: dict[str, Any]) -> str:
        """Constructs SQL string for the custom aggregation.
        :param aggregate_args: Map from parameter key to parameter value returned by process_agg_args.

        Replaces all variables in the SQL string indicated by {{}} with the needed value for SQL execution.
        """
        aggregate_arg_map_key_to_parameter_type = {
            arg.parameter_key: arg.parameter_type
            for arg in self.agg_schema.aggregate_args
        }
        constructed_sql: str = self.agg_schema.sql
        for arg_key, arg_val in aggregate_args.items():
            # replace all variables with format {{}} with their values in aggregate_args
            new_val = self._evaluate_arg_value(
                aggregate_arg_map_key_to_parameter_type,
                arg_key,
                arg_val,
            )
            constructed_sql = constructed_sql.replace(f"{{{{{arg_key}}}}}", new_val)

        return constructed_sql

    def aggregate(
        self,
        model_agg_spec: AggregationSpec,
        datasets: list[Dataset],
        init_args: dict[str, Any],
        aggregate_args: dict[str, Any],
    ) -> list[SketchMetric | NumericMetric]:
        constructed_sql = self._construct_sql(aggregate_args)
        self.logger.info(f"Executing SQL: {constructed_sql}")
        results = self.conn.sql(constructed_sql).df()

        time_series: list[SketchMetric | NumericMetric] = []
        for reported_agg in self.agg_schema.reported_aggregations:
            time_series.append(self._calculate_time_series(results, reported_agg))
        return time_series
