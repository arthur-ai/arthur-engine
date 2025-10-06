from typing import Optional

from arthur_client.api_bindings import (
    AvailableDataset,
    CustomAggregationVersionSpecSchemaAggregateArgsInner,
    Dataset,
    DatasetObjectType,
)
from arthur_common.models.metrics import (
    MetricsColumnSchemaUnion,
    MetricsParameterSchemaUnion,
)
from arthur_common.models.schema_definitions import DType, ScopeSchemaTag
from tools.converters import client_to_common_dataset_schema


def primary_timestamp_col_name(dataset: Dataset | AvailableDataset) -> str:
    """Retrieves name of primary timestamp tagged column, raises error if there is none."""
    missing_col_msg = (
        f"Could not find primary timestamp column in dataset schema. Inference timestamp column should "
        f"have the {ScopeSchemaTag.PRIMARY_TIMESTAMP} tag."
    )
    if not dataset.dataset_schema:
        raise ValueError(missing_col_msg)

    dataset_schema = client_to_common_dataset_schema(dataset.dataset_schema)
    for col in dataset_schema.columns:
        if (
            col.definition
            and col.definition.tag_hints
            and ScopeSchemaTag.PRIMARY_TIMESTAMP in col.definition.tag_hints
        ):
            return col.source_name
    raise ValueError(missing_col_msg)


def get_keys_with_param_type(
    args: (
        list[MetricsParameterSchemaUnion]
        | list[CustomAggregationVersionSpecSchemaAggregateArgsInner]
    ),
    param_type: str,
) -> list[str]:
    """Returns all keys in the list of arguments with the passed parameter type."""
    # parse CustomAggregationSpecSchemaAggregateArgsInner client type objects to actual instance so their fields
    # can be accessed
    for i in range(len(args)):
        arg = args[i]
        if isinstance(arg, CustomAggregationVersionSpecSchemaAggregateArgsInner):
            args[i] = arg.actual_instance
    return [param.parameter_key for param in args if param.parameter_type == param_type]


def get_args_with_tag_hint(
    args: list[MetricsParameterSchemaUnion],
    tag_hint: str,
) -> dict[str, MetricsColumnSchemaUnion]:
    """Returns map from key to arg of all args in the list of arguments with the passed tag hint."""

    return {
        param.parameter_key: param
        for param in args
        if isinstance(param, MetricsColumnSchemaUnion) and tag_hint in param.tag_hints
    }


def _find_dtype_in_object(col_id: str, obj_type: DatasetObjectType):
    """Find dtype for a field ID within an object type"""
    for field_name, field_value in obj_type.object.items():
        field_instance = field_value.actual_instance
        if field_instance.id == col_id and hasattr(field_instance, "dtype"):
            return DType(field_instance.dtype)

        # recurse if nested
        if hasattr(field_instance, "object"):
            result = _find_dtype_in_object(col_id, field_instance)
            if result:
                return result
    return None


def column_scalar_dtype_from_dataset_schema(
    col_id: str,
    dataset: Dataset,
) -> Optional[DType]:
    """Returns the scalar data type of columns including nested columns by column ID"""
    if col_id == "":
        return None

    for column in dataset.dataset_schema.columns:
        # Check top-level columns
        if (
            column.id == col_id
            and column.definition.actual_instance
            and hasattr(column.definition.actual_instance, "dtype")
        ):
            return DType(column.definition.actual_instance.dtype)

        # Check nested columns within DatasetObjectType columns
        if hasattr(column.definition.actual_instance, "object"):
            result = _find_dtype_in_object(col_id, column.definition.actual_instance)
            if result:
                return result

    return None
