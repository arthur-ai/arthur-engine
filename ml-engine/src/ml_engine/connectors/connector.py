from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from logging import Logger
from typing import Any

import pandas as pd
from arthur_client.api_bindings import (
    AvailableDataset,
    ConnectorCheckResult,
    ConnectorSpec,
    DataResultFilter,
    Dataset,
    PutAvailableDatasets,
)
from arthur_common.models.connectors import ConnectorPaginationOptions


@dataclass(frozen=True)
class ConnectorReadResult:
    rows: list[dict[str, Any]] | pd.DataFrame
    total_count: int | None
    """Rows matching the read's time range and filters across all pages, or None when the source can't report it."""


class Connector(ABC):
    @abstractmethod
    def __init__(self, connector_config: ConnectorSpec, logger: Logger):
        raise NotImplementedError

    @abstractmethod
    def read(
        self,
        dataset: Dataset | AvailableDataset,
        start_time: datetime,
        end_time: datetime,
        filters: list[DataResultFilter] | None = None,
        pagination_options: ConnectorPaginationOptions | None = None,
    ) -> list[dict[str, Any]] | pd.DataFrame:
        raise NotImplementedError

    def read_with_total_count(
        self,
        dataset: Dataset | AvailableDataset,
        start_time: datetime,
        end_time: datetime,
        filters: list[DataResultFilter] | None = None,
        pagination_options: ConnectorPaginationOptions | None = None,
    ) -> ConnectorReadResult:
        return ConnectorReadResult(
            rows=self.read(dataset, start_time, end_time, filters, pagination_options),
            total_count=None,
        )

    @abstractmethod
    def test_connection(self) -> ConnectorCheckResult:
        raise NotImplementedError

    @abstractmethod
    def list_datasets(self) -> PutAvailableDatasets:
        raise NotImplementedError

    @abstractmethod
    def extract_image(self, image_uri: str) -> str:
        raise NotImplementedError
