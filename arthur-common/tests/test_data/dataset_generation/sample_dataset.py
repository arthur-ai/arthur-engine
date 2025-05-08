from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Tuple


class SampleDataset(ABC):
    @property
    @abstractmethod
    def inferences_per_file(self) -> int:
        """Inferences per file in dataset. relevant for s3 and local filesystem only."""
        raise NotImplementedError

    @staticmethod
    def generate_prediction_range_from_timestamp(
        timestamp: datetime,
    ) -> Tuple[float, float]:
        """generates a range [range_start, range_end] between [0, 1] based on inference timestamp so prediction line
        doesn't flatten over time"""
        date_int = (
            int(timestamp.year)
            + int(timestamp.month)
            + int(timestamp.day)
            + int(timestamp.hour)
        )
        prediction_range_end = float(f"0.{date_int % 11}") if date_int % 11 != 10 else 1
        prediction_range_start = (
            prediction_range_end - 0.1 if prediction_range_end >= 0.1 else 0
        )
        return prediction_range_start, prediction_range_end

    @abstractmethod
    def generate_sample(self, timestamp: datetime) -> Dict[str, Any]:
        """generate sample dataset"""
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def format_row_as_json(data: Dict[str, Any]) -> Dict[str, Any]:
        """formats a row in json-compatible format for writing to bigquery:
        https://cloud.google.com/python/docs/reference/bigquery/latest/google.cloud.bigquery.client.Client#google_cloud_bigquery_client_Client_insert_rows_json
        """
        raise NotImplementedError

    @abstractmethod
    def file_name(self, date: datetime) -> str:
        """returns name of file in bucket that should contain the inferences for a given datetime"""
        raise NotImplementedError
