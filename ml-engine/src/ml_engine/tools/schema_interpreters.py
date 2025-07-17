from typing import Optional

from arthur_client.api_bindings import AvailableDataset, Dataset
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
    args: list[MetricsParameterSchemaUnion],
    param_type: str,
) -> list[str]:
    """Returns all keys in the list of arguments with the passed parameter type."""
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


def column_scalar_dtype_from_dataset_schema(
    column_name: str,
    dataset: Dataset,
) -> Optional[DType]:
    """Returns the scalar data type of any non-nested columns by the name column_name"""
    for column in dataset.dataset_schema.columns:
        if (
            column.source_name == column_name
            and column.definition.actual_instance
            and hasattr(column.definition.actual_instance, "dtype")
        ):
            return DType(column.definition.actual_instance.dtype)
    return None
