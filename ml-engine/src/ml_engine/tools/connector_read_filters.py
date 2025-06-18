from typing import Any, Iterable

import pandas as pd
from arthur_client.api_bindings import DataResultFilter, DataResultFilterOp


def _apply_pd_filters(
    data: pd.DataFrame,
    filters: list[DataResultFilter],
) -> pd.DataFrame:
    for data_filter in filters:
        match data_filter.op:
            case DataResultFilterOp.GREATER_THAN:
                data = data[data[data_filter.field_name] > data_filter.value]
            case DataResultFilterOp.LESS_THAN:
                data = data[data[data_filter.field_name] < data_filter.value]
            case DataResultFilterOp.EQUALS:
                data = data[data[data_filter.field_name] == data_filter.value]
            case DataResultFilterOp.NOT_EQUALS:
                data = data[data[data_filter.field_name] != data_filter.value]
            case DataResultFilterOp.GREATER_THAN_OR_EQUAL:
                data = data[data[data_filter.field_name] >= data_filter.value]
            case DataResultFilterOp.LESS_THAN_OR_EQUAL:
                data = data[data[data_filter.field_name] <= data_filter.value]
            case DataResultFilterOp.IN:
                iterable_value = _value_to_iterable(data_filter.value)
                data = data[data[data_filter.field_name].isin(iterable_value)]
            case DataResultFilterOp.NOT_IN:
                iterable_value = _value_to_iterable(data_filter.value)
                data = data[~data[data_filter.field_name].isin(iterable_value)]
        return data


def _value_to_iterable(value: Any) -> Iterable[Any]:
    return value if isinstance(value, Iterable) else [value]


def _apply_dict_filter(data: dict[str, Any], data_filter: DataResultFilter) -> bool:
    value = data.get(data_filter.field_name, None)

    if not value:
        return False

    match data_filter.op:
        case DataResultFilterOp.GREATER_THAN:
            return bool(value > data_filter.value)
        case DataResultFilterOp.LESS_THAN:
            return bool(value < data_filter.value)
        case DataResultFilterOp.EQUALS:
            return bool(value == data_filter.value)
        case DataResultFilterOp.NOT_EQUALS:
            return bool(value != data_filter.value)
        case DataResultFilterOp.GREATER_THAN_OR_EQUAL:
            return bool(value >= data_filter.value)
        case DataResultFilterOp.LESS_THAN_OR_EQUAL:
            return bool(value <= data_filter.value)
        case DataResultFilterOp.IN:
            iterable_value = _value_to_iterable(data_filter.value)
            return bool(value in iterable_value)
        case DataResultFilterOp.NOT_IN:
            iterable_value = _value_to_iterable(data_filter.value)
            return bool(value not in iterable_value)

    return False


def apply_filters_to_retrieved_inferences(
    inferences: list[dict[str, Any]] | pd.DataFrame,
    filters: list[DataResultFilter] | None,
) -> list[dict[str, Any]] | pd.DataFrame:
    """Apply dataset filters to retrieved inferences"""
    if not filters:
        return inferences

    if isinstance(inferences, pd.DataFrame):
        data = _apply_pd_filters(inferences, filters)
    elif isinstance(inferences, list):
        data = [
            item
            for item in inferences
            if all(_apply_dict_filter(item, filter) for filter in filters)
        ]
    else:
        raise NotImplementedError(f"Unsupported inference type: {type(inferences)}")
    return data
