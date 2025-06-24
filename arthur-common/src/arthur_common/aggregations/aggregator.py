from abc import ABC, abstractmethod
from base64 import b64encode
from typing import Any, Type, Union

import pandas as pd
from arthur_common.models.metrics import *
from datasketches import kll_floats_sketch
from duckdb import DuckDBPyConnection


class AggregationFunction(ABC):
    @staticmethod
    @abstractmethod
    def id() -> UUID:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def display_name() -> str:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def description() -> str:
        raise NotImplementedError

    @abstractmethod
    def aggregation_type(self) -> Type[SketchMetric] | Type[NumericMetric]:
        raise NotImplementedError

    @abstractmethod
    def aggregate(
        self,
        ddb_conn: DuckDBPyConnection,
        *args: Any,
        **kwargs: Any,
    ) -> Union[list[SketchMetric], list[NumericMetric]]:
        raise NotImplementedError

    @staticmethod
    def string_to_dimension(name: str, value: str | None) -> Dimension:
        if value is None:
            value = "null"
        return Dimension(name=name, value=str(value))


class NumericAggregationFunction(AggregationFunction, ABC):
    def aggregation_type(self) -> Type[NumericMetric]:
        return NumericMetric

    @abstractmethod
    def aggregate(
        self,
        ddb_conn: DuckDBPyConnection,
        *args: Any,
        **kwargs: Any,
    ) -> list[NumericMetric]:
        raise NotImplementedError

    @staticmethod
    def group_query_results_to_numeric_metrics(
        data: pd.DataFrame,
        value_col: str,
        dim_columns: list[str],
        timestamp_col: str,
    ) -> list[NumericTimeSeries]:
        """
        Convert a grouped dataframe with repeated dimensions to internal numeric metric definition.

        At a high level, the query results are already grouped, however,
        the order isn't guaranteed that groups are sequential (this requires an explicit ORDER BY on the source query.)
        What this function does is group by the indicated dimensions list, and from each group extract the dimension values once.
        From there, iterate over the group turning each data point to a *Point. At the end, this single instance of the group metrics
        and the list of points (values) are merged to one *TimeSeries
        """
        if not dim_columns:
            return [
                NumericAggregationFunction._dimensionless_query_results_to_numeric_metrics(
                    data,
                    value_col,
                    timestamp_col,
                ),
            ]

        calculated_metrics: list[NumericTimeSeries] = []
        # make sure dropna is False or rows with "null" as a dimension value will be dropped
        groups = data.groupby(dim_columns, dropna=False)
        for _, group in groups:
            dimensions: list[Dimension] = []
            # Get the first row of the group to determine the group level dimensions
            dims_row = group.iloc[0]
            for dim in dim_columns:
                d = AggregationFunction.string_to_dimension(
                    name=dim,
                    value=dims_row[dim],
                )
                dimensions.append(d)

            values: list[NumericPoint] = []
            for _, row in group.iterrows():
                values.append(
                    NumericPoint(timestamp=row[timestamp_col], value=row[value_col]),
                )
            calculated_metrics.append(
                NumericTimeSeries(values=values, dimensions=dimensions),
            )

        return calculated_metrics

    @staticmethod
    def _dimensionless_query_results_to_numeric_metrics(
        data: pd.DataFrame,
        value_col: str,
        timestamp_col: str,
    ) -> NumericTimeSeries:
        """
        Convert a dimensionless time / value series to internal numeric metric definition.
        """
        values: list[NumericPoint] = []
        for _, row in data.iterrows():
            values.append(
                NumericPoint(timestamp=row[timestamp_col], value=row[value_col]),
            )
        return NumericTimeSeries(values=values, dimensions=[])

    def series_to_metric(
        self,
        metric_name: str,
        series: list[NumericTimeSeries],
    ) -> NumericMetric:
        return NumericMetric(name=metric_name, numeric_series=series)


class SketchAggregationFunction(AggregationFunction, ABC):
    def aggregation_type(self) -> Type[SketchMetric]:
        return SketchMetric

    @abstractmethod
    def aggregate(
        self,
        ddb_conn: DuckDBPyConnection,
        *args: Any,
        **kwargs: Any,
    ) -> list[SketchMetric]:
        raise NotImplementedError

    def group_query_results_to_sketch_metrics(
        self,
        data: pd.DataFrame,
        value_col: str,
        dim_columns: list[str],
        timestamp_col: str,
    ) -> list[SketchTimeSeries]:
        """
        Convert a grouped dataframe with repeated dimensions to internal sketch metric definition.

        For sketch data, what we're doing is grouping the raw row data into the dimensions we care about.
        Within each group, we extract the dimensions once. Within this single dimension group,
        we group the data into 5min intervals. Within each interval, the data point we care to sketch is added to the sketch.

        """

        calculated_metrics: list[SketchTimeSeries] = []
        # make sure dropna is False or rows with "null" as a dimension value will be dropped
        groups = data.groupby(dim_columns, dropna=False)
        for _, group in groups:
            calculated_metrics.append(
                self._group_to_series(group, timestamp_col, dim_columns, value_col),
            )

        return calculated_metrics

    @staticmethod
    def _group_to_series(
        group: pd.DataFrame,
        timestamp_col: str,
        dim_columns: list[str],
        value_col: str,
    ) -> SketchTimeSeries:
        def to_sketch(col: pd.Series) -> Optional[kll_floats_sketch]:
            if not len(col):
                return None
            s = kll_floats_sketch()
            for v in col.values:
                s.update(v)
            return s

        dimensions: list[Dimension] = []
        # Get the first row of the group to determine the group level dimensions
        dims_row = group.iloc[0]
        for dim in dim_columns:
            d = AggregationFunction.string_to_dimension(name=dim, value=dims_row[dim])
            dimensions.append(d)

        values: list[SketchPoint] = []

        # Group query results into 5min buckets
        group[timestamp_col] = pd.to_datetime(group[timestamp_col])
        group.set_index(timestamp_col, inplace=True)
        # make sure dropna is False or rows with "null" as a dimension value will be dropped
        time_bucketed_groups = group.groupby(pd.Grouper(freq="5min"), dropna=False)

        for group_timestamp, time_bucket_group in time_bucketed_groups:
            # Don't generate metrics on empty buckets
            if time_bucket_group.empty:
                continue
            sketch = to_sketch(time_bucket_group[value_col])
            if sketch is not None:
                values.append(
                    SketchPoint(
                        timestamp=group_timestamp,
                        value=b64encode(sketch.serialize()).decode(),
                    ),
                )

        return SketchTimeSeries(values=values, dimensions=dimensions)

    def series_to_metric(
        self,
        metric_name: str,
        series: list[SketchTimeSeries],
    ) -> SketchMetric:
        return SketchMetric(name=metric_name, sketch_series=series)
