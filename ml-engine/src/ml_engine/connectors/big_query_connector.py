import json
from datetime import datetime
from logging import Logger
from typing import Any, List, Tuple

import pandas as pd
from arthur_client.api_bindings import (
    AvailableDataset,
    ConnectorCheckOutcome,
    ConnectorCheckResult,
    ConnectorSpec,
    DataResultFilter,
    Dataset,
    DatasetLocator,
    DatasetLocatorField,
    PutAvailableDataset,
    PutAvailableDatasets,
    ScopeSchemaTag,
)
from arthur_common.models.connectors import (
    BIG_QUERY_DATASET_DATASET_ID_FIELD,
    BIG_QUERY_DATASET_TABLE_NAME_FIELD,
    GOOGLE_CONNECTOR_CREDENTIALS_FIELD,
    GOOGLE_CONNECTOR_LOCATION_FIELD,
    GOOGLE_CONNECTOR_PROJECT_ID_FIELD,
    ConnectorPaginationOptions,
)
from connectors.connector import Connector
from google.auth import load_credentials_from_dict
from google.cloud import bigquery
from google.cloud.bigquery import SchemaField
from tools.schema_interpreters import primary_timestamp_col_name


class BigQueryConnector(Connector):
    def __init__(self, connector_config: ConnectorSpec, logger: Logger):
        connector_fields = {f.key: f.value for f in connector_config.fields}
        creds_json = connector_fields.get(GOOGLE_CONNECTOR_CREDENTIALS_FIELD)
        if creds_json:
            bq_creds = load_credentials_from_dict(json.loads(creds_json))[0]  # type: ignore
        else:
            bq_creds = None

        location = connector_fields.get(GOOGLE_CONNECTOR_LOCATION_FIELD)
        self.project_id = connector_fields[GOOGLE_CONNECTOR_PROJECT_ID_FIELD]
        self.client = bigquery.Client(
            credentials=bq_creds,
            project=self.project_id,
            location=location,
        )
        self.logger = logger

    @staticmethod
    def _paginate_query(
        query_str: str,
        pagination_options: ConnectorPaginationOptions | None = None,
    ) -> str:
        if not pagination_options:
            return query_str

        if pagination_options.page < 1:
            raise ValueError(
                "Arthur pagination is 1-indexed. Please provide a page number >= 1.",
            )
        limit = pagination_options.page_size
        offset = (pagination_options.page - 1) * pagination_options.page_size
        return query_str + f" LIMIT {limit} OFFSET {offset}"

    @staticmethod
    def _escape_identifier(str_to_escape: str) -> str:
        # replace any backticks in the identifier with \`
        # https://cloud.google.com/bigquery/docs/reference/standard-sql/lexical#string_and_bytes_literals
        escaped = str_to_escape.replace("`", "\\`")
        # wrap in backticks to fully quote it
        # https://cloud.google.com/bigquery/docs/reference/standard-sql/lexical
        return f"`{escaped}`"

    def _build_fetch_data_query(
        self,
        dataset: Dataset | AvailableDataset,
        start_time: datetime,
        end_time: datetime,
        pagination_options: ConnectorPaginationOptions | None = None,
    ) -> str:
        if not dataset.dataset_locator:
            raise ValueError(
                f"Dataset {dataset.id} has no dataset locator, cannot read from BigQuery.",
            )

        dataset_locator_fields = {
            f.key: f.value for f in dataset.dataset_locator.fields
        }

        table_name = dataset_locator_fields[BIG_QUERY_DATASET_TABLE_NAME_FIELD]
        dataset_id = dataset_locator_fields[BIG_QUERY_DATASET_DATASET_ID_FIELD]
        full_bq_table_name = f"{self.project_id}.{dataset_id}.{table_name}"
        basic_query = f"SELECT * FROM {self._escape_identifier(full_bq_table_name)}"

        try:
            timestamp_col = primary_timestamp_col_name(dataset)
            basic_query += (
                f" WHERE {self._escape_identifier(timestamp_col)} >= '{start_time}' AND "
                f"{self._escape_identifier(timestamp_col)} < '{end_time}'"
            )
            basic_query += f" ORDER BY {self._escape_identifier(timestamp_col)} DESC"
        except ValueError:
            # timestamp column not found
            self.logger.warning(
                f"Primary timestamp column with {ScopeSchemaTag.PRIMARY_TIMESTAMP} tag not found. "
                f"Defaulting to ignoring specified time range filter and using requested pagination.",
            )
            if not pagination_options:
                raise ValueError(
                    "Pagination options not provided and timestamp range not set. Cannot fetch all data "
                    "without providing a limit or time range.",
                )

        basic_query = self._paginate_query(basic_query, pagination_options)
        return basic_query

    def read(
        self,
        dataset: Dataset | AvailableDataset,
        start_time: datetime,
        end_time: datetime,
        filters: list[DataResultFilter] | None = None,
        pagination_options: ConnectorPaginationOptions | None = None,
    ) -> list[dict[str, Any]] | pd.DataFrame:
        """
        Reads data from the table. By default, will fetch all data between start/end matching. Column filters are not
        currently supported. Starts from end_time and works backward.
        """
        basic_query = self._build_fetch_data_query(
            dataset,
            start_time,
            end_time,
            pagination_options,
        )
        results = self.client.query_and_wait(basic_query)
        # we should use the db-dtypes package and just cast the results to a dataframe (.to_dataframe()) once the
        # package supports python 3.13: https://cloud.google.com/bigquery/docs/samples/bigquery-query-results-dataframe
        # this is a hack for now & has noticeably worse performance
        # open issue: https://github.com/googleapis/python-db-dtypes-pandas/issues/298
        col_names = []
        for schema_field in results.schema:
            if not isinstance(schema_field, SchemaField):
                # schema is Dict[str, Any] compatible with from_api_rep
                col_names.append(SchemaField.from_api_repr(schema_field).name)
            else:
                col_names.append(schema_field.name)

        return pd.DataFrame(
            data=[dict(row.items()) for row in results],
            columns=col_names,
        )

    def test_connection(self) -> ConnectorCheckResult:
        try:
            list(self.client.list_datasets(max_results=10))
        except Exception as e:
            self.logger.error(
                f"Could not connect to BigQuery project {self.project_id}. Failed to list datasets.",
                exc_info=e,
            )
            return ConnectorCheckResult(
                connection_check_outcome=ConnectorCheckOutcome.FAILED,
                failure_reason=f"Could not connect to BigQuery project {self.project_id}. Failed to list datasets. Error: {e}",
            )
        else:
            return ConnectorCheckResult(
                connection_check_outcome=ConnectorCheckOutcome.SUCCEEDED,
            )

    def list_datasets(self) -> PutAvailableDatasets:
        """
        BigQuery is structured as: project -> datasets -> tables. We'll consider each table to be an available dataset.
        """
        bq_datasets = list(self.client.list_datasets())
        if not bq_datasets:
            return PutAvailableDatasets(available_datasets=[])

        table_ids: List[Tuple[str, str]] = []  # tuple of dataset_id, table_id
        for bq_dataset in bq_datasets:
            tables_in_dataset = list(self.client.list_tables(bq_dataset.dataset_id))
            table_ids += [
                (bq_dataset.dataset_id, table.table_id) for table in tables_in_dataset
            ]

        return PutAvailableDatasets(
            available_datasets=[
                PutAvailableDataset(
                    name=f"{table_id[0]}.{table_id[1]}",
                    dataset_locator=DatasetLocator(
                        fields=[
                            DatasetLocatorField(
                                key=BIG_QUERY_DATASET_DATASET_ID_FIELD,
                                value=table_id[0],
                            ),
                            DatasetLocatorField(
                                key=BIG_QUERY_DATASET_TABLE_NAME_FIELD,
                                value=table_id[1],
                            ),
                        ],
                    ),
                )
                for table_id in table_ids
            ],
        )
