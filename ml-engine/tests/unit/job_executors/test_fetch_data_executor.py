import logging
from datetime import date, datetime
from typing import Any
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest
from arthur_client.api_bindings import PutRetrievedData

from job_executors.fetch_data_executor import FetchDataExecutor


@pytest.mark.parametrize(
    "data, expected_json",
    [
        (
            [
                {"Column1": 1, "Column2": np.inf, "Column3": 5},
                {"Column1": 2, "Column2": -np.inf, "Column3": np.nan},
                {"Column1": np.nan, "Column2": 3, "Column3": np.inf},
                {"Column1": 4, "Column2": 4, "Column3": -np.inf},
                {
                    "Column1": float("nan"),
                    "Column2": float("inf"),
                    "Column3": float("-inf"),
                },
            ],
            '[{"Column1": 1, "Column2": "Infinity", "Column3": 5}, {"Column1": 2, "Column2": "-Infinity", "Column3": "NaN"}, {"Column1": "NaN", "Column2": 3, "Column3": "Infinity"}, {"Column1": 4, "Column2": 4, "Column3": "-Infinity"}, {"Column1": "NaN", "Column2": "Infinity", "Column3": "-Infinity"}]',
        ),
        (
            [
                {
                    "date_col": date(2024, 1, 15),
                    "datetime_col": datetime(2024, 1, 15, 10, 30, 45),
                    "pd_timestamp_col": pd.Timestamp("2024-01-15 10:30:45"),
                },
            ],
            '[{"date_col": "2024-01-15", "datetime_col": "2024-01-15T10:30:45", "pd_timestamp_col": "2024-01-15T10:30:45"}]',
        ),
    ],
)
def test_fetch_data_serialization(
    data: list[dict[str, Any]] | pd.DataFrame,
    expected_json: str,
) -> None:
    actual_json = FetchDataExecutor._serialize_data(data)
    assert expected_json == actual_json


@pytest.mark.parametrize(
    "dataset_id, available_dataset_id, put_method",
    [
        ("dataset-id", None, "put_data_retrieval_data"),
        (None, "available-dataset-id", "put_available_data_retrieval_data"),
    ],
)
@pytest.mark.parametrize("total_count", [137, None])
def test_store_data_sends_total_count(
    dataset_id: str | None,
    available_dataset_id: str | None,
    put_method: str,
    total_count: int | None,
) -> None:
    data_retrieval_client = Mock()
    executor = FetchDataExecutor(
        models_client=Mock(),
        datasets_client=Mock(),
        data_retrieval_client=data_retrieval_client,
        connector_constructor=Mock(),
        logger=logging.getLogger(__name__),
    )

    executor._store_data(
        dataset_id,
        available_dataset_id,
        "operation-id",
        [{"a": 1}],
        total_count,
    )

    sent: PutRetrievedData = getattr(
        data_retrieval_client,
        put_method,
    ).call_args.kwargs["put_retrieved_data"]
    assert sent.content == '[{"a": 1}]'
    assert sent.total_count == total_count
