import logging
from datetime import datetime, timedelta, timezone

import pandas as pd
from arthur_client.api_bindings import (
    AvailableDataset,
    DatasetsV1Api,
    SchemaInspectionJobSpec,
)
from arthur_common.models.connectors import ConnectorPaginationOptions # TODO: replace when property method fixed in openapi
from arthur_common.models.schema_definitions import SHIELD_SCHEMA
from arthur_common.models.schema_definitions import DatasetSchema as CommonDatasetSchema
from arthur_common.tools.schema_inferer import SchemaInferer
from connectors.connector import Connector
from connectors.shield_connector import ShieldConnector
from tools.connector_constructor import ConnectorConstructor
from tools.converters import common_to_client_put_dataset_schema

INFER_SCHEMA_DATA_LIMIT = 300
INFER_SCHEMA_DATE_RANGE_DAYS = 90


class SchemaInferenceExecutor:
    def __init__(
        self,
        datasets_client: DatasetsV1Api,
        connector_constructor: ConnectorConstructor,
        logger: logging.Logger,
    ) -> None:
        self.datasets_client: DatasetsV1Api = datasets_client
        self.connector_constructor: ConnectorConstructor = connector_constructor
        self.logger: logging.Logger = logger

    def execute(self, job_spec: SchemaInspectionJobSpec) -> None:
        conn: Connector = self.connector_constructor.get_connector_from_spec(
            job_spec.connector_id,
        )
        dataset: AvailableDataset = self.datasets_client.get_available_dataset(
            job_spec.available_dataset_id,
        )

        if isinstance(conn, ShieldConnector):
            schema = SHIELD_SCHEMA()
        else:
            schema = self._infer_schema_from_data(conn, dataset)

        self._put_dataset_schema(job_spec.available_dataset_id, schema)

    def _infer_schema_from_data(
        self,
        conn: Connector,
        dataset: AvailableDataset,
    ) -> CommonDatasetSchema:
        current_time = datetime.now(timezone.utc)
        # connectors will sort data in descending order by default if possible
        data = conn.read(
            dataset,
            start_time=current_time - timedelta(days=INFER_SCHEMA_DATE_RANGE_DAYS),
            end_time=current_time,
            filters=None,
            pagination_options=ConnectorPaginationOptions(
                page_size=INFER_SCHEMA_DATA_LIMIT,
            ),
        )

        if isinstance(data, list):
            data_count = len(data)
        elif isinstance(data, pd.DataFrame):
            if data.empty:
                data_count = 0
            else:
                data_count = len(data.index)
        else:
            raise ValueError(
                f"Unexpected data type {type(data)} returned from connector read function.",
            )

        if data_count == 0:
            error_msg = f"No data found in the last {INFER_SCHEMA_DATE_RANGE_DAYS} days in dataset. Schema could not be inferred."
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        elif data_count < 50:
            self.logger.warning(
                f"Found fewer than 50 inferences for schema inference. Running job anyway with low sample size of {data_count}.",
            )
        else:
            self.logger.info(
                f"Found {data_count} inferences to use for schema inspection job.",
            )

        return SchemaInferer(data).infer_schema()

    def _put_dataset_schema(
        self,
        available_dataset_id: str,
        schema: CommonDatasetSchema,
    ) -> None:
        self.datasets_client.put_available_dataset_schema(
            available_dataset_id=available_dataset_id,
            put_dataset_schema=common_to_client_put_dataset_schema(schema),
        )
