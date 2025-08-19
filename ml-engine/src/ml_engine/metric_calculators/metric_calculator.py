from abc import ABC, abstractmethod
from logging import Logger
from typing import Any, Union
from uuid import UUID

import duckdb
from arthur_client.api_bindings import (
    AggregationSpec,
    CustomAggregationSpecSchema,
    Dataset,
    MetricsArgSpec,
)
from arthur_common.models.metrics import (
    AggregationSpecSchema,
    DatasetReference,
    MetricsColumnSchemaUnion,
    NumericMetric,
    SketchMetric,
)
from arthur_common.models.schema_definitions import ScopeSchemaTag
from arthur_common.tools.duckdb_utils import is_column_possible_segmentation
from arthur_common.tools.functions import uuid_to_base26
from config import Config
from tools.schema_interpreters import (
    column_scalar_dtype_from_dataset_schema,
    get_args_with_tag_hint,
    get_keys_with_param_type,
)


class MetricCalculator(ABC):
    def __init__(
        self,
        conn: duckdb.DuckDBPyConnection,
        logger: Logger,
        agg_schema: Union[CustomAggregationSpecSchema, AggregationSpecSchema],
    ) -> None:
        # TODO: Make conn read only for aggregations? Would have to manually manage table existence across different connections (write for transform, read for aggregate)
        self.conn = conn
        self.agg_schema = agg_schema
        self.logger = logger

    def transform(self) -> None:
        # TODO: One day
        pass

    @abstractmethod
    def aggregate(
        self,
        model_agg_spec: AggregationSpec,
        datasets: list[Dataset],
        init_args: dict[str, Any],
        aggregate_args: dict[str, Any],
    ) -> list[SketchMetric | NumericMetric]:
        """
        Calculates aggregation.
        :param model_agg_spec: AggregationSpec of the aggregation to calculate.
        :param datasets: List of datasets to calculate the aggregation over.
        :param aggregate_args is a mapping from parameter key to parameter value
        :param init_args is a mapping from parameter key to parameter value
        Both of the argument parameters are from the output of process_agg_args
        """
        raise NotImplementedError

    @staticmethod
    def _validate_col_exists(
        col_id: Any,
        all_dataset_columns: dict[str, Any],
        agg_spec: AggregationSpec,
    ) -> None:
        """raises an error if column does not exist in the dataset"""
        if str(col_id) not in all_dataset_columns:
            raise ValueError(
                f"Could not calculate aggregation with id {agg_spec.aggregation_id}. "
                f"At least one parameter ({col_id}) refers to a column in a dataset that could not be loaded."
                f"{all_dataset_columns}",
            )

    def _validate_segmentation_single_column(
        self,
        col_name: str,
        arg_key: Any,
        arg_schema: MetricsColumnSchemaUnion,
        aggregate_args: dict[str, Any],
        ds_map: dict[str, Dataset],
    ) -> None:
        """Validates a single column passes segmentation requirements.

        col_name: name of column to validate
        arg_key: Name of the aggregation argument
        arg_schema: Schema of aggregation argument that includes a segmentation tag hint.
        aggregate_args: dict from argument key to argument value
        ds_map: Dict from dataset ID to dataset object
        """
        dataset_key = arg_schema.source_dataset_parameter_key
        dataset_ref = aggregate_args[dataset_key]
        column_dtype = column_scalar_dtype_from_dataset_schema(
            col_name,
            ds_map[str(dataset_ref.dataset_id)],
        )
        if not column_dtype:
            raise ValueError(
                "Could not fetch scalar column data type for evaluation of segmentation column "
                "requirements. Either the column does not exist or it is an object or list type "
                "or a nested column, which are not supported for segmentation columns.",
            )
        column_can_be_segmented = is_column_possible_segmentation(
            self.conn,
            dataset_ref.dataset_table_name,
            col_name,
            column_dtype,
        )
        if not column_can_be_segmented:
            raise ValueError(
                f"The column {col_name} cannot be applied to the aggregation argument {arg_key} that has "
                f"a {ScopeSchemaTag.POSSIBLE_SEGMENTATION.value} tag hint configured. There is either a "
                f"data type mismatch or the column exceeds the limit of allowed unique values.",
            )

    def _validate_segmentation_args(
        self,
        agg_function_schema: AggregationSpecSchema,
        aggregate_args: dict[str, Any],
        ds_map: dict[str, Dataset],
    ) -> None:
        """If argument requires possible_segmentation tag hints, validates whether the segmentation requirements are met:
        1. If argument is a column list, no more than 3 segmentation columns are configured.
        2. Requirements for data types and limit on unique values are met for the column.

        agg_function_schema: Schema of the aggregate function
        aggregate_args: dict mapping argument keys to argument values
        ds_map: Dict from dataset ID to dataset object
        """
        segmentation_required_arg_schemas = get_args_with_tag_hint(
            agg_function_schema.aggregate_args,
            ScopeSchemaTag.POSSIBLE_SEGMENTATION,
        )

        for arg_key in aggregate_args:
            arg_schema = segmentation_required_arg_schemas.get(arg_key)
            if not arg_schema:
                # arg does not have possible_segmentation tag hint
                continue

            # validate segmentation requirements for multiple column list parameters or single column parameters
            arg_val = aggregate_args[arg_key]
            if isinstance(arg_val, list):
                col_max_count = Config.segmentation_col_count_limit()
                if len(arg_val) > col_max_count:
                    raise ValueError(
                        f"Max {col_max_count} columns can be applied to the aggregation argument {arg_key} that has a "
                        f"{ScopeSchemaTag.POSSIBLE_SEGMENTATION.value} tag hint. Found {len(arg_val)} columns.",
                    )
                for column_name in arg_val:
                    self._validate_segmentation_single_column(
                        column_name,
                        arg_key,
                        arg_schema,
                        aggregate_args,
                        ds_map,
                    )
            else:
                self._validate_segmentation_single_column(
                    arg_val,
                    arg_key,
                    arg_schema,
                    aggregate_args,
                    ds_map,
                )

    @staticmethod
    def _get_col_list_arg_values(
        arg: MetricsArgSpec,
        all_dataset_columns: dict[str, Any],
        agg_spec: AggregationSpec,
    ) -> list[Any]:
        """Validates the argument value of a column list parameter and returns the corresponding list of column names"""
        if not isinstance(arg.arg_value, list):
            raise ValueError(
                f"Column list parameter should be list type, got {type(arg.arg_value)}",
            )
        else:
            # list of column names—validate each column name exists
            for val in arg.arg_value:
                MetricCalculator._validate_col_exists(
                    val,
                    all_dataset_columns,
                    agg_spec,
                )
            return [all_dataset_columns[str(value)] for value in arg.arg_value]

    def process_agg_args(
        self,
        agg_spec: AggregationSpec,
        datasets: list[Dataset],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Performs validations and processes aggregation arguments.

        returns: tuple of (init_args, aggregate_args) for an aggregation.
        These arguments have dict[str, Any] types. This dict represents a mapping from the parameter key of the
        argument (ie. the key by which the argument is referenced in an aggregation) to the value of the argument.
        In the case of literal arguments, the value is a scalar.
        In the case of column arguments, the value is the column name.
        In the case of dataset arguments, the value is the DatasetReference object for this dataset.
        """
        init_args = {
            arg.arg_key: arg.arg_value for arg in agg_spec.aggregation_init_args
        }

        column_parameter_keys = get_keys_with_param_type(
            self.agg_schema.aggregate_args,
            "column",
        )
        column_list_parameter_keys = get_keys_with_param_type(
            self.agg_schema.aggregate_args,
            "column_list",
        )
        dataset_parameter_keys = get_keys_with_param_type(
            self.agg_schema.aggregate_args,
            "dataset",
        )

        ds_map = {ds.id: ds for ds in datasets}
        all_dataset_columns = {}  # column id: column name
        for ds in datasets:
            all_dataset_columns.update(ds.dataset_schema.column_names)

        aggregate_args: dict[str, Any] = {}
        for arg in agg_spec.aggregation_args:
            if arg.arg_key in column_parameter_keys:
                self._validate_col_exists(arg.arg_value, all_dataset_columns, agg_spec)
                aggregate_args[arg.arg_key] = all_dataset_columns[str(arg.arg_value)]
            elif arg.arg_key in column_list_parameter_keys:
                aggregate_args[arg.arg_key] = self._get_col_list_arg_values(
                    arg,
                    all_dataset_columns,
                    agg_spec,
                )
            elif arg.arg_key in dataset_parameter_keys:
                if arg.arg_value not in ds_map:
                    raise ValueError(
                        f"Could not calculate aggregation with id {agg_spec.aggregation_id}. "
                        f"At least one parameter refers to a dataset that could not be loaded.",
                    )
                dataset = ds_map[arg.arg_value]
                aggregate_args[arg.arg_key] = DatasetReference(
                    dataset_name=dataset.name if dataset.name else "",
                    dataset_table_name=uuid_to_base26(dataset.id),
                    dataset_id=UUID(dataset.id),
                )
            else:
                aggregate_args[arg.arg_key] = arg.arg_value

        self._validate_segmentation_args(self.agg_schema, aggregate_args, ds_map)
        return init_args, aggregate_args
