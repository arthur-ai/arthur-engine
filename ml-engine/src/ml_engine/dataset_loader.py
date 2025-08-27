from datetime import datetime
from logging import Logger
from typing import Set, Tuple

import duckdb
from arthur_client.api_bindings import (
    AvailableDataset,
    DataResultFilter,
    Dataset,
    DatasetsV1Api,
)
from arthur_client.api_bindings.exceptions import NotFoundException
from common_client.arthur_common_generated.models import DatasetJoinKind
from arthur_common.models.connectors import ConnectorPaginationOptions # TODO: replace when property method fixed in openapi
from arthur_common.tools.duckdb_data_loader import DuckDBOperator
from arthur_common.tools.functions import uuid_to_base26
from duckdb import DuckDBPyConnection
from tools.connector_constructor import ConnectorConstructor
from tools.converters import client_to_common_dataset_schema


class DatasetLoader:
    def __init__(
        self,
        connector_constructor: ConnectorConstructor,
        datasets_client: DatasetsV1Api,
        logger: Logger,
    ):
        self.conn = duckdb.connect()
        self.connector_constructor = connector_constructor
        self.datasets_client = datasets_client
        self.logger = logger

    def _dataset_or_available_dataset_from_id(
        self,
        dataset_id: str,
    ) -> Dataset | AvailableDataset:
        try:
            return self.datasets_client.get_dataset(dataset_id)
        except NotFoundException:
            return self.datasets_client.get_available_dataset(dataset_id)

    """
    Obtain a list of all physical datasets in the list. These might be at the root level, or nested within join specs, so do so recursively
    """

    def _get_physical_datasets(
        self,
        dataset_ids: list[str],
    ) -> list[Dataset | AvailableDataset]:
        physical_datasets: list[Dataset | AvailableDataset] = []

        for dataset_id in dataset_ids:
            dataset = self._dataset_or_available_dataset_from_id(dataset_id)
            if dataset.join_spec:
                ds1 = self.datasets_client.get_dataset(
                    dataset.join_spec.left_joined_dataset.id,
                )
                ds2 = self.datasets_client.get_dataset(
                    dataset.join_spec.right_joined_dataset.id,
                )
                physical_datasets.extend(self._get_physical_datasets([ds1.id, ds2.id]))
            else:
                physical_datasets.append(dataset)
        return physical_datasets

    def load_physical_dataset(
        self,
        conn: DuckDBPyConnection,
        dataset: Dataset | AvailableDataset,
        start_time: datetime,
        end_time: datetime,
        filters: list[DataResultFilter] | None = None,
        pagination_options: ConnectorPaginationOptions | None = None,
    ) -> str:
        if isinstance(dataset, Dataset):
            if not dataset.connector:
                raise ValueError(
                    f"Cannot load virtual dataset {dataset.id} using load_physical_dataset.",
                )
            else:
                connector_id = dataset.connector.id
        elif not dataset.connector_id:  # dataset is available dataset
            raise ValueError(
                f"Cannot load virtual dataset {dataset.id} using load_physical_dataset.",
            )
        else:
            connector_id = dataset.connector_id
        connector = self.connector_constructor.get_connector_from_spec(connector_id)
        data = connector.read(
            dataset,
            start_time,
            end_time,
            filters,
            pagination_options,
        )
        self.logger.info(f"Retrieved {len(data)} inferences for dataset {dataset.id}")
        schema = (
            client_to_common_dataset_schema(dataset.dataset_schema)
            if dataset.dataset_schema
            else None
        )
        table_name = uuid_to_base26(dataset.id)

        DuckDBOperator.load_data_to_duckdb(
            data,
            table_name=table_name,
            conn=conn,
            schema=schema,
        )

        return table_name

    """
        Perform joins / virtual table creation after all physical tables have been created.
        Unavailable_datasets corresponds to set of all physical tables that could not be loaded.
    """

    def resolve_dataset(
        self,
        conn: DuckDBPyConnection,
        dataset: Dataset | AvailableDataset,
        unavailable_datasets: Set[str],
    ) -> None:
        if dataset.id in unavailable_datasets:
            raise ValueError(
                f"Could not resolve dataset with id {dataset.id} because it was not loaded.",
            )

        if dataset.join_spec:
            ds1 = self.datasets_client.get_dataset(
                dataset.join_spec.left_joined_dataset.id,
            )
            ds2 = self.datasets_client.get_dataset(
                dataset.join_spec.right_joined_dataset.id,
            )
            if ds1.id in unavailable_datasets:
                # technically these cases are handled by the base case, but this will raise a more clear error so
                # users aren't surprised by a dataset ID that isn't in their top-level datasets
                raise ValueError(
                    f"Could not resolve dataset with id {dataset.id} because its left joined dataset with "
                    f"id {ds1.id} could not be loaded.",
                )
            elif ds2.id in unavailable_datasets:
                raise ValueError(
                    f"Could not resolve dataset with id {dataset.id} because its right joined dataset "
                    f"with id {ds2.id} could not be loaded.",
                )
            self.resolve_dataset(conn, ds1, unavailable_datasets)
            self.resolve_dataset(conn, ds2, unavailable_datasets)

            DuckDBOperator.join_tables(
                conn,
                uuid_to_base26(dataset.id),
                uuid_to_base26(ds1.id),
                uuid_to_base26(ds2.id),
                dataset.join_spec.left_joined_dataset.column_id,
                dataset.join_spec.right_joined_dataset.column_id,
                (
                    dataset.join_spec.join_type
                    if dataset.join_spec.join_type
                    else DatasetJoinKind.INNER
                ),
            )

            return
        else:
            return

    """
    Load all physical datasets, then resolve all virtual datasets. Once all datasets are resolved, apply alias masks to convert to final column names.
    Returns DuckDB connection with datasets that loaded successfully, and set of dataset ids that could not be loaded.
    """

    def load_datasets(
        self,
        dataset_ids: list[str],
        start_time: datetime,
        end_time: datetime,
        filters: list[DataResultFilter] | None = None,
        pagination_options: ConnectorPaginationOptions | None = None,
    ) -> Tuple[DuckDBPyConnection, Set[str]]:
        conn = duckdb.connect()
        physical_datasets = self._get_physical_datasets(dataset_ids)
        unloaded_datasets = set()

        for dataset in physical_datasets:
            try:
                self.load_physical_dataset(
                    conn,
                    dataset,
                    start_time,
                    end_time,
                    filters,
                    pagination_options,
                )
            except Exception as e:
                unloaded_datasets.add(dataset.id)
                self.logger.error(
                    f"Error loading dataset with id {dataset.id}.",
                    exc_info=e,
                )

        # Once all datasets are loaded, resolve to solve for joins
        for dataset_id in dataset_ids:
            dataset = self._dataset_or_available_dataset_from_id(dataset_id)
            try:
                self.resolve_dataset(conn, dataset, unloaded_datasets)
            except Exception as e:
                unloaded_datasets.add(dataset.id)
                self.logger.error(
                    f"Error resolving dataset with id {dataset.id}.",
                    exc_info=e,
                )
                continue
            if dataset.dataset_schema:
                schema = client_to_common_dataset_schema(dataset.dataset_schema)
                DuckDBOperator.apply_alias_mask(
                    table_name=uuid_to_base26(dataset.id),
                    conn=conn,
                    schema=schema,
                )
        return conn, unloaded_datasets
