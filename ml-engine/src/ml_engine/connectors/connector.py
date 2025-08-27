from abc import ABC, abstractmethod
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
from arthur_common.models.connectors import (
    ConnectorPaginationOptions,
)  # TODO: replace when property method fixed in openapi


class Connector(ABC):
    @abstractmethod
    def __init__(self, logger: Logger, connector_config: ConnectorSpec):
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

    @abstractmethod
    def test_connection(self) -> ConnectorCheckResult:
        raise NotImplementedError

    @abstractmethod
    def list_datasets(self) -> PutAvailableDatasets:
        raise NotImplementedError
