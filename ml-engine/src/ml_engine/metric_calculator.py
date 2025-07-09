from typing import Any, Union

import duckdb
from arthur_common.aggregations import AggregationFunction
from arthur_common.models.metrics import NumericMetric, SketchMetric


class MetricCalculator:
    # TODO: Expand to multiple datasets eventually
    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self.conn = conn

    def transform(self) -> None:
        # TODO: One day
        pass

    def aggregate(
        self,
        aggregation_function: AggregationFunction,
        aggregate_args: dict[str, Any],
    ) -> Union[list[SketchMetric], list[NumericMetric]]:
        # TODO: Make conn read only for aggregations? Would have to manually manage table existence across different connections (write for transform, read for aggregate)
        return aggregation_function.aggregate(self.conn, **aggregate_args)
