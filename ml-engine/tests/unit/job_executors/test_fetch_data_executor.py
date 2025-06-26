from typing import Any

import numpy as np
import pandas as pd
import pytest
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
    ],
)
def test_fetch_data_serialization(
    data: list[dict[str, Any]] | pd.DataFrame,
    expected_json: str,
) -> None:
    actual_json = FetchDataExecutor._serialize_data(data)
    assert expected_json == actual_json
