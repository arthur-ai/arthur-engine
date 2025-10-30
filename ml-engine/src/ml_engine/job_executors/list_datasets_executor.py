import logging

from arthur_client.api_bindings import DatasetsV1Api, ListDatasetsJobSpec

from connectors.connector import Connector
from tools.connector_constructor import ConnectorConstructor


class ListDatasetsExecutor:
    def __init__(
        self,
        datasets_client: DatasetsV1Api,
        connector_constructor: ConnectorConstructor,
        logger: logging.Logger,
    ) -> None:
        self.datasets_client: DatasetsV1Api = datasets_client
        self.connector_constructor: ConnectorConstructor = connector_constructor
        self.logger: logging.Logger = logger

    def execute(self, job_spec: ListDatasetsJobSpec) -> None:
        self.logger.info(
            f"Executing list datasets job for connector {job_spec.connector_id}",
        )

        conn: Connector = self.connector_constructor.get_connector_from_spec(
            job_spec.connector_id,
        )
        available_datasets = conn.list_datasets()

        self.logger.info(
            f"Found {len(available_datasets.available_datasets)} datasets for connector {job_spec.connector_id}",
        )

        self.datasets_client.put_connector_available_datasets(
            connector_id=job_spec.connector_id,
            put_available_datasets=available_datasets,
        )
        self.logger.info(
            f"List datasets job completed for connector {job_spec.connector_id}",
        )
