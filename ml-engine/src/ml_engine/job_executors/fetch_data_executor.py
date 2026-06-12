import json
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from logging import Logger
from typing import Any, Dict, Optional
from uuid import UUID

import numpy as np
import pandas as pd
from arthur_client.api_bindings import (
    DataResultFilter,
    DataRetrievalV1Api,
    DatasetsV1Api,
    FetchDataJobSpec,
    ModelsV1Api,
    PutRetrievedData,
)
from arthur_common.models.connectors import ConnectorPaginationOptions
from arthur_common.models.schema_definitions import DatasetSchema
from arthur_common.tools.functions import uuid_to_base26

from dataset_loader import DatasetLoader
from tools.connector_constructor import ConnectorConstructor
from tools.converters import client_to_common_dataset_schema
from tools.dataset_utils import get_dataset_or_available_dataset_from_id
from tools.image_resolver import ImageResolver
from tools.image_tools import get_image_columns, is_supported_image_uri

MAX_IMAGE_RESOLVER_WORKERS = 50  # same num as in BucketBasedConnector


def preprocess_data(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {key: preprocess_data(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [preprocess_data(item) for item in obj]
    elif isinstance(obj, np.ndarray):
        return _preprocess_ndarray(obj)
    elif isinstance(obj, float):
        return _preprocess_float(obj)
    elif isinstance(obj, pd.Timestamp):
        return _preprocess_timestamp(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, date):
        return obj.isoformat()
    elif isinstance(obj, UUID):
        return str(obj)
    return obj


def _preprocess_ndarray(obj: np.ndarray[Any, Any]) -> Any:
    obj_py = obj.tolist()
    if not isinstance(obj_py, list):  # handles 0-d ndarray
        return preprocess_data(obj_py)
    else:
        return [preprocess_data(item) for item in obj_py]


def _preprocess_float(obj: float) -> str | float:
    if math.isnan(obj):
        return "NaN"
    elif obj == float("inf"):
        return "Infinity"
    elif obj == float("-inf"):
        return "-Infinity"
    return obj


def _preprocess_timestamp(obj: pd.Timestamp) -> Any:
    if obj.tzinfo is None or obj.tzinfo.utcoffset(obj) is None:
        # timestamp is naive
        return obj.isoformat()
    else:
        return obj.astimezone("utc").isoformat()


class FetchDataExecutor:
    def __init__(
        self,
        models_client: ModelsV1Api,
        datasets_client: DatasetsV1Api,
        data_retrieval_client: DataRetrievalV1Api,
        connector_constructor: ConnectorConstructor,
        logger: Logger,
    ):
        self.models_client = models_client
        self.datasets_client = datasets_client
        self.data_retrieval_client = data_retrieval_client
        self.connector_constructor = connector_constructor
        self.logger = logger

    def execute(self, job_spec: FetchDataJobSpec) -> None:
        dataset_id = self._dataset_id_from_job_spec(job_spec)
        self.logger.info(f"Fetching data for dataset {dataset_id}")
        try:
            pagination_options = ConnectorPaginationOptions.model_validate(
                job_spec.pagination_options.model_dump(),
            )
            data = self._load_data(
                dataset_id,
                job_spec.start_timestamp,
                job_spec.end_timestamp,
                job_spec.data_filters,
                pagination_options,
            )
        except Exception as e:
            self.logger.error(
                f"Error fetching data for dataset {dataset_id} - {str(e)}",
            )
            raise e

        if hasattr(job_spec, "operation_id"):
            dataset = get_dataset_or_available_dataset_from_id(
                self.datasets_client,
                dataset_id,
            )
            if dataset.dataset_schema:
                schema = client_to_common_dataset_schema(dataset.dataset_schema)
                image_resolver = ImageResolver(
                    self.connector_constructor,
                    dataset.project_id,
                    self.logger,
                )
                self._resolve_images(data, schema, image_resolver)

            self._store_data(
                job_spec.dataset_id,
                job_spec.available_dataset_id,
                job_spec.operation_id,
                data,
            )

        self.logger.info(f"Fetch data job completed for dataset {dataset_id}")

    def _resolve_images(
        self,
        rows: list[Dict[str, Any]],
        schema: DatasetSchema,
        image_resolver: ImageResolver,
    ) -> None:
        image_cols = get_image_columns(schema)
        if not image_cols:
            return

        with ThreadPoolExecutor(max_workers=MAX_IMAGE_RESOLVER_WORKERS) as executor:
            future_to_cell = {}
            for i, row in enumerate(rows):
                for col in image_cols:
                    cell_value = row.get(col)

                    if not (
                        isinstance(cell_value, str)
                        and is_supported_image_uri(cell_value)
                    ):
                        continue

                    future_to_cell[
                        executor.submit(image_resolver.resolve_image, cell_value)
                    ] = (i, col)

            for future in as_completed(future_to_cell):
                row_idx, col = future_to_cell[future]
                rows[row_idx][col] = future.result()

    @staticmethod
    def _dataset_id_from_job_spec(job_spec: FetchDataJobSpec) -> str:
        if job_spec.dataset_id:
            return str(job_spec.dataset_id)
        elif job_spec.available_dataset_id:
            return str(job_spec.available_dataset_id)
        else:
            raise ValueError("Both Dataset ID and Available Dataset ID cannot be None")

    def _load_data(
        self,
        dataset_id: str,
        start_time: datetime,
        end_time: datetime,
        filters: list[DataResultFilter] | None = None,
        pagination_options: ConnectorPaginationOptions | None = None,
    ) -> list[Dict[str, Any]]:
        dataset_loader = DatasetLoader(
            self.connector_constructor,
            self.datasets_client,
            self.logger,
        )
        duckdb_conn, failed_datasets = dataset_loader.load_datasets(
            [dataset_id],
            start_time,
            end_time,
            filters,
            pagination_options,
        )
        if failed_datasets:
            raise ValueError(f"Could not load data for dataset with id {dataset_id}.")
        table_name = uuid_to_base26(dataset_id)
        # fetch data without converting to dataframe to preserve None values
        result = duckdb_conn.sql(f"select * from {table_name}")
        columns = result.columns
        rows = result.fetchall()
        return [dict(zip(columns, row)) for row in rows]

    @staticmethod
    def _serialize_data(data: list[Dict[str, Any]]) -> str:
        # replace NaNs since they aren't valid JSON
        return json.dumps(preprocess_data(data))

    def _store_data(
        self,
        dataset_id: Optional[str],
        available_dataset_id: Optional[str],
        operation_id: str,
        data: list[Dict[str, Any]],
    ) -> None:
        try:
            data_content = self._serialize_data(data)

            if dataset_id:
                self.data_retrieval_client.put_data_retrieval_data(
                    dataset_id=dataset_id,
                    operation_id=operation_id,
                    put_retrieved_data=PutRetrievedData(
                        content=data_content,
                    ),
                )
                self.logger.info(f"Stored retrieved data for dataset {dataset_id}")
            elif available_dataset_id:
                self.data_retrieval_client.put_available_data_retrieval_data(
                    available_dataset_id=available_dataset_id,
                    operation_id=operation_id,
                    put_retrieved_data=PutRetrievedData(
                        content=data_content,
                    ),
                )
                self.logger.info(
                    f"Stored retrieved data for available dataset {available_dataset_id}",
                )
            else:  # should never happen
                raise ValueError(
                    "dataset_id or available_dataset_id must be set on job spec to retrieve data.",
                )
        except Exception as e:
            if dataset_id:
                self.logger.error(
                    f"Error storing data for dataset {dataset_id} - {str(e)}",
                )
            else:
                self.logger.error(
                    f"Error storing data for available dataset {available_dataset_id} - {str(e)}",
                )
            raise e
