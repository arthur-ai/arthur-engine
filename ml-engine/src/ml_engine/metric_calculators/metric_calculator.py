from abc import ABC, abstractmethod
from logging import Logger
from typing import Any, Dict, List, Tuple
from uuid import UUID

import duckdb
from arthur_client.api_bindings import (
    AggregationSpec,
    CustomAggregationVersionSpecSchemaAggregateArgsInner,
    Dataset,
    DatasetObjectType,
    MetricsArgSpec,
)
from arthur_common.models.metrics import (
    DatasetReference,
    MetricsColumnSchemaUnion,
    MetricsParameterSchemaUnion,
    NumericMetric,
    SketchMetric,
)
from arthur_common.models.schema_definitions import ScopeSchemaTag
from arthur_common.tools.duckdb_data_loader import (
    escape_identifier,
)
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
        agg_spec: AggregationSpec,
    ) -> None:
        # TODO: Make conn read only for aggregations? Would have to manually manage table existence across different connections (write for transform, read for aggregate)
        self.conn = conn
        self.agg_spec = agg_spec
        self.logger = logger

    def transform(self) -> None:
        # TODO: One day
        pass

    @abstractmethod
    def aggregate(
        self,
        init_args: dict[str, Any],
        aggregate_args: dict[str, Any],
    ) -> list[SketchMetric | NumericMetric]:
        """
        Calculates aggregation.
        :param aggregate_args is a mapping from parameter key to parameter value
        :param init_args is a mapping from parameter key to parameter value
        Both of the argument parameters are from the output of process_agg_args
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def aggregate_args_schemas(
        self,
    ) -> (
        List[CustomAggregationVersionSpecSchemaAggregateArgsInner]
        | List[MetricsParameterSchemaUnion]
    ):
        """Returns the schema for the arguments for the aggregation.
        This will likely be done by accessing the agg_spec_schema field.
        """
        raise NotImplementedError

    def _validate_col_exists(
        self,
        col_id: Any,
        all_dataset_columns: dict[str, Any],
    ) -> None:
        """raises an error if column does not exist in the dataset"""
        if str(col_id) not in all_dataset_columns:
            raise ValueError(
                f"Could not calculate aggregation with id {self.agg_spec.aggregation_id}. "
                f"At least one parameter ({col_id}) refers to a column in a dataset that could not be loaded."
                f"{all_dataset_columns}",
            )

    def _validate_segmentation_single_column(
        self,
        col_id: str,
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
            col_id,
            ds_map[str(dataset_ref.dataset_id)],
        )
        if not column_dtype:
            raise ValueError(
                "Could not fetch scalar column data type for evaluation of segmentation column "
                "requirements. Either the column does not exist or it is an object or list type.",
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
        col_names_to_id: dict[str, str],
        aggregate_args: dict[str, Any],
        ds_map: dict[str, Dataset],
    ) -> None:
        """If argument requires possible_segmentation tag hints, validates whether the segmentation requirements are met:
        1. If argument is a column list, no more than 3 segmentation columns are configured.
        2. Requirements for data types and limit on unique values are met for the column.

        aggregate_args: dict mapping argument keys to argument values
        ds_map: Dict from dataset ID to dataset object
        """
        segmentation_required_arg_schemas = get_args_with_tag_hint(
            self.aggregate_args_schemas,
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
                        col_names_to_id.get(column_name, ""),
                        column_name,
                        arg_key,
                        arg_schema,
                        aggregate_args,
                        ds_map,
                    )
            else:
                self._validate_segmentation_single_column(
                    col_names_to_id.get(column_name, ""),
                    arg_val,
                    arg_key,
                    arg_schema,
                    aggregate_args,
                    ds_map,
                )

    def _get_col_list_arg_values(
        self,
        arg: MetricsArgSpec,
        all_dataset_columns: dict[str, Any],
    ) -> list[Any]:
        """Validates the argument value of a column list parameter and returns the corresponding list of column names"""
        if not isinstance(arg.arg_value, list):
            raise ValueError(
                f"Column list parameter should be list type, got {type(arg.arg_value)}",
            )
        else:
            # list of column names—validate each column name exists
            for val in arg.arg_value:
                self._validate_col_exists(
                    val,
                    all_dataset_columns,
                )
            return [all_dataset_columns[str(value)] for value in arg.arg_value]

    def _field_names_from_object_type_column(
        self,
        obj_type: DatasetObjectType,
        base_name: str = "",
    ) -> Dict[str, str]:
        """Returns map from column ID to column name of all columns nested in a DatasetObjectType typed column.

        This usually means obj_type refers to a struct column.
        The column names returned in the maps have escape identifiers applied as needed to the struct fields.

        base_name: Used for recursion. Refers to the name of any parent column. For example, if this DatasetObjectType
        typed column is already a nested field in a top-level column called "parent_column", the base_name should be
        "parent_column", including the double-quoted escape identifiers.
        """
        nested_object = obj_type.object
        field_names = {}
        for key, value in nested_object.items():
            # key is the name of the nested field
            # value is the next DatasetObjectType or DatasetScalarType, etc.

            if not isinstance(value, DatasetObjectType):
                # base case - next field is not also an object type
                if base_name:
                    col_name = f"{base_name}.{escape_identifier(key)}"
                else:
                    col_name = key

                field_names[value.actual_instance.id] = col_name
            else:
                # next field is also an object/struct type; recurse to get the names of the nested fields
                field_names.update(
                    self._field_names_from_object_type_column(value, base_name),
                )
                # there's some weirdness where the DatasetObjectType itself has an ID, but not a source name.
                # the ID & source name of the column live in the DatasetColumn object.
        return field_names

    def _all_dataset_columns(
        self,
        datasets: List[Dataset],
    ) -> Tuple[Dict[str, str], Dict[str, str]]:
        """
        This function is used to create two dictionaries, one from column ID to column name
        for every column in the list of datasets, and one from column name back to column ID.

        Notes:
          - This includes nested column names using dot syntax ("parent_column_name"."nested_column_name").
          - Nested column names are not included in column_names so we cannot just use that property from the Dataset object here.
          - Escape identifiers are included in the names.

        Parameters:
            datasets (List[Dataset]): list of datasets to process

        Returns:
            all_dataset_columns (Dict[str, str]): dict from column ID to column name for every column in the list of datasets.
            col_names_to_id (Dict[str, str]): dict from column name to column ID for every column in the list of datasets.
        """
        all_dataset_columns = {}
        col_names_to_id = {}

        for ds in datasets:
            # first, use the column_names property. We need to do this instead of iterating over the parent-level
            # column names & adding them ourselves because this property applies alias masks as needed to the
            # top-level column names.
            top_level_col_names = ds.dataset_schema.column_names.copy()
            for col_id, col_name in top_level_col_names.items():
                # add escape identifier to column name
                escaped_col_name = escape_identifier(col_name)
                top_level_col_names[col_id] = escaped_col_name
                col_names_to_id[escaped_col_name] = col_id

            all_dataset_columns.update(top_level_col_names)

            # then, iterate over any object type columns to include the nested column names in the dict
            for column in ds.dataset_schema.columns:
                if isinstance(column.definition.actual_instance, DatasetObjectType):
                    nested_fields = self._field_names_from_object_type_column(
                        column.definition.actual_instance,
                        escape_identifier(column.source_name),
                    )
                    all_dataset_columns.update(nested_fields)
                    for field_id, field_name in nested_fields.items():
                        col_names_to_id[field_name] = field_id

        return all_dataset_columns, col_names_to_id

    def process_agg_args(
        self,
        datasets: list[Dataset],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Performs validations and processes aggregation arguments.

        returns: tuple of (init_args, aggregate_args) for an aggregation.
        These arguments have dict[str, Any] types. This dict represents a mapping from the parameter key of the
        argument (ie. the key by which the argument is referenced in an aggregation) to the value of the argument.
        In the case of literal arguments, the value is a scalar.
        In the case of column arguments, the value is the column name. The name includes the escape identifiers
            needed to execute the query.
        In the case of dataset arguments, the value is the DatasetReference object for this dataset.
        """
        init_args = {
            arg.arg_key: arg.arg_value for arg in self.agg_spec.aggregation_init_args
        }

        column_parameter_keys = get_keys_with_param_type(
            self.aggregate_args_schemas,
            "column",
        )
        column_list_parameter_keys = get_keys_with_param_type(
            self.aggregate_args_schemas,
            "column_list",
        )
        dataset_parameter_keys = get_keys_with_param_type(
            self.aggregate_args_schemas,
            "dataset",
        )

        ds_map = {ds.id: ds for ds in datasets}
        all_dataset_columns, col_names_to_id = self._all_dataset_columns(
            datasets,
        )  # column id: escaped column name

        aggregate_args: dict[str, Any] = {}
        for arg in self.agg_spec.aggregation_args:
            if arg.arg_key in column_parameter_keys:
                self._validate_col_exists(arg.arg_value, all_dataset_columns)
                aggregate_args[arg.arg_key] = all_dataset_columns[str(arg.arg_value)]
            elif arg.arg_key in column_list_parameter_keys:
                aggregate_args[arg.arg_key] = self._get_col_list_arg_values(
                    arg,
                    all_dataset_columns,
                )
            elif arg.arg_key in dataset_parameter_keys:
                if arg.arg_value not in ds_map:
                    raise ValueError(
                        f"Could not calculate aggregation with id {self.agg_spec.aggregation_id}. "
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

        self._validate_segmentation_args(col_names_to_id, aggregate_args, ds_map)
        return init_args, aggregate_args
