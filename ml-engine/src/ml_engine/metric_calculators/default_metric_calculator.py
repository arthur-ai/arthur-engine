from logging import Logger
from typing import Any, List, Type

import duckdb
from arthur_client.api_bindings import AggregationSpec
from arthur_common.aggregations import AggregationFunction
from arthur_common.models.metrics import (
    AggregationSpecSchema,
    MetricsParameterSchemaUnion,
    NumericMetric,
    SketchMetric,
)
from metric_calculators.metric_calculator import MetricCalculator


class DefaultMetricCalculator(MetricCalculator):
    def __init__(
        self,
        conn: duckdb.DuckDBPyConnection,
        logger: Logger,
        agg_spec: AggregationSpec,
        agg_schema: AggregationSpecSchema,
        agg_function_type: Type[AggregationFunction],
    ) -> None:
        """
        :param conn: DuckDB Connection with datasets loaded to calculate aggregations over.
        :param agg_function_type: The AggregationFunction to execute.
        :param agg_schema: The schema of the aggregation function to execute.
        """
        super().__init__(conn, logger, agg_spec)
        self.agg_schema = agg_schema
        self._agg_function_type = agg_function_type

    @property
    def aggregate_args_schemas(self) -> List[MetricsParameterSchemaUnion]:
        return self.agg_schema.aggregate_args

    def aggregate(
        self,
        init_args: dict[str, Any],
        aggregate_args: dict[str, Any],
    ) -> list[SketchMetric | NumericMetric]:
        agg_function = self._agg_function_type(**init_args)
        # underlying aggregates in arthur-common return type is list[SketchMetric] | list[NumericMetric]
        # mypy can't figure out that that's a sub-type of list[SketchMetric | NumericMetric]
        return agg_function.aggregate(self.conn, **aggregate_args)  # type: ignore
