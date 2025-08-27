import concurrent.futures
import json
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from logging import Logger
from typing import Any, Optional

import pandas as pd
import pyarrow.parquet as pq
import pytz
from _pydatetime import tzinfo
from arthur_client.api_bindings import (
    AvailableDataset,
    ConnectorCheckOutcome,
    ConnectorCheckResult,
    ConnectorSpec,
    DataResultFilter,
    Dataset,
    PutAvailableDatasets,
    ScopeSchemaTag,
)
from arthur_common.models.connectors import (  # TODO: replace when property method fixed in openapi
    BUCKET_BASED_CONNECTOR_BUCKET_FIELD,
    BUCKET_BASED_DATASET_FILE_PREFIX_FIELD,
    BUCKET_BASED_DATASET_FILE_SUFFIX_FIELD,
    BUCKET_BASED_DATASET_FILE_TYPE_FIELD,
    BUCKET_BASED_DATASET_TIMESTAMP_TIME_ZONE_FIELD,
    ConnectorPaginationOptions,
)
from arthur_common.tools.time_utils import (
    check_datetime_tz_aware,
    find_smallest_timedelta,
)
from connectors.connector import Connector
from dateutil import parser
from fsspec import AbstractFileSystem
from tools.connector_read_filters import apply_filters_to_retrieved_inferences
from tools.schema_interpreters import primary_timestamp_col_name

from common_client.arthur_common_generated.models import DatasetFileType

DEFAULT_PAGE_SIZE = 250
DEFAULT_LIMIT = 500


"""
Read inference from a file
"""


def read_file(
    fs: AbstractFileSystem,
    file_name: str,
    file_type: DatasetFileType,
) -> list[dict[str, Any]]:
    inferences: list[dict[str, Any]] = []
    match file_type:
        case DatasetFileType.JSON:
            with fs.open(file_name, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    inferences.append(data)
                elif isinstance(data, list):
                    inferences.extend(data)
                else:
                    raise Exception(
                        f"Unexpected type: {type(data)}. Data could not be read.",
                    )
        case DatasetFileType.PARQUET:
            with fs.open(file_name, "rb") as f:
                return pq.ParquetFile(f).read().to_pylist()  # type: ignore
        case _:
            raise NotImplementedError(
                f"read_file not supported for file type {file_type}.",
            )
    return inferences


@dataclass()
class _BucketBasedDatasetLocatorFields:
    file_prefix: str
    file_suffix: str | None
    file_type: DatasetFileType
    timezone: tzinfo


class BucketBasedConnector(Connector, ABC):
    def __init__(self, logger: Logger, connector_config: ConnectorSpec) -> None:
        connector_fields = {f.key: f.value for f in connector_config.fields}
        self.bucket_name = connector_fields.get(BUCKET_BASED_CONNECTOR_BUCKET_FIELD)
        self.logger = logger

    @property
    @abstractmethod
    def file_system(self) -> AbstractFileSystem:
        """Returns fsspec file system for connection"""
        raise NotImplementedError

    def test_connection(self) -> ConnectorCheckResult:
        try:
            # list files in bucket
            self.file_system.ls(self.bucket_name)
        except Exception as e:
            self.logger.error(
                f"Failed to connect to bucket {self.bucket_name}",
                exc_info=e,
            )
            return ConnectorCheckResult(
                connection_check_outcome=ConnectorCheckOutcome.FAILED,
                failure_reason=f"Could not connect to bucket: {self.bucket_name}",
            )
        else:
            return ConnectorCheckResult(
                connection_check_outcome=ConnectorCheckOutcome.SUCCEEDED,
            )

    def _render_file_prefix_for_timestamp(
        self,
        tz_adjusted_time: datetime,
        file_prefix: str,
    ) -> str:
        """Renders file prefix with tz_adjusted_time. tz_adjusted_time is the timestamp adjusted to the data storage
        timezone. File prefix should not have leading /."""
        rendered_timestamp_prefix = tz_adjusted_time.strftime(file_prefix)
        return f"{self.bucket_name}/{rendered_timestamp_prefix}"

    @staticmethod
    def _secondary_filter_primary_timestamp(
        timestamp_col: str,
        inferences: list[dict[str, Any]],
        start_time: datetime,
        end_time: datetime,
        tz: tzinfo,
    ) -> list[dict[str, Any]]:
        """Filters on primary timestamp column for inferences in range  [start_time, end_time). Datetimes in range
        must be tz-aware. tz-naive timestamps in the data will be cast to the specified timezone.
        """
        if not check_datetime_tz_aware(start_time) or not check_datetime_tz_aware(
            end_time,
        ):
            raise Exception(
                f"Datetimes in range must be timezone-aware, got {start_time} and {end_time}.",
            )

        filtered_inferences = []
        for inference in inferences:
            timestamp = inference[timestamp_col]
            timestamp_dt = parser.parse(timestamp)
            if not check_datetime_tz_aware(timestamp_dt):
                # timestamp in data is naive - assume it should have the passed timezone
                timestamp_dt = timestamp_dt.astimezone(tz)
            if start_time <= timestamp_dt < end_time:
                filtered_inferences.append(inference)
        return filtered_inferences

    @staticmethod
    def _pagination_limits_met(
        inferences: list[dict[str, Any]],
        pagination_options: ConnectorPaginationOptions | None,
    ) -> bool:
        if not pagination_options:
            return False

        """Should be checked after column name filters have been applied to inferences"""
        page, page_size = pagination_options.page_params
        # adjust for use of 1-indexed pagination by API
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        if len(inferences) >= end_idx:
            return True

        return False

    @staticmethod
    def _paginate_inferences(
        inferences: list[dict[str, Any]],
        pagination_options: ConnectorPaginationOptions,
    ) -> list[dict[str, Any]]:
        """Applies pagination to inferences if pagination filters are present"""
        page, page_size = pagination_options.page_params
        # adjust for use of 1-indexed pagination by API
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        if start_idx >= len(inferences):
            # page starts beyond present data - return empty list
            return []
        elif len(inferences) >= end_idx:
            # return complete page
            return inferences[start_idx:end_idx]
        else:  # start_idx < len(inferences) and len(inferences) < end_idx
            # return incomplete page
            return inferences[start_idx:]

    def _filter_inferences(
        self,
        inferences: list[dict[str, Any]],
        timestamp_col: str | None,
        start_time_tz_aware: datetime,
        end_time_tz_aware: datetime,
        timezone: tzinfo,
        filters: list[DataResultFilter] | None,
    ) -> list[dict[str, Any]]:
        """Performs time range filtering and data result filtering by column name."""
        # filter inferences for [start_time, end_time) range. Covers edge case where timedelta causes data plane
        # to pull inferences outside the range (e.g. the last time range pulled has a timedelta that exceeds the
        # specified end_time)
        if timestamp_col is None:
            # this case happens if the dataset does not have a primary timestamp tag
            # it is ok to skip the filter here because the presence of the tag is validated in read()
            # before calling this method if it is required
            time_filtered_inferences = inferences
        else:
            time_filtered_inferences = self._secondary_filter_primary_timestamp(
                timestamp_col,
                inferences,
                start_time_tz_aware,
                end_time_tz_aware,
                timezone,
            )

        # remove pagination filters from being considered as column name filters
        if filters:
            filters = [
                data_filter
                for data_filter in filters
                if data_filter.field_name not in ["limit", "page", "page_size"]
            ]
        filter_applied_inferences = apply_filters_to_retrieved_inferences(
            time_filtered_inferences,
            filters,
        )

        return filter_applied_inferences

    def _validate_timestamp_col(
        self,
        dataset: Dataset | AvailableDataset,
        pagination_options: ConnectorPaginationOptions | None,
    ) -> str | None:
        """
        Extracts and validates if a timestamp_col is required for this read operation. Raises a ValueError
        if the timestamp_col is not found and is required.
        """
        try:
            return primary_timestamp_col_name(dataset)
        except ValueError:
            if not pagination_options:
                raise ValueError(
                    f"Could not find primary timestamp column with {ScopeSchemaTag.PRIMARY_TIMESTAMP} tag "
                    f"in dataset schema to do time range filtering, and no limit is set. Connector does "
                    f"not allow retrieving all data in a dataset.",
                )
            # timestamp column not found, but limit was set - warn user
            self.logger.warning(
                f"Primary timestamp column with {ScopeSchemaTag.PRIMARY_TIMESTAMP} tag not found, "
                f"but page_size is set. Will load data without timestamp filtering up to the amount in the page.",
            )
            return None

    @staticmethod
    def _extract_dataset_locator_fields(
        dataset: Dataset | AvailableDataset,
    ) -> _BucketBasedDatasetLocatorFields:
        if not dataset.dataset_locator:
            raise ValueError(
                f"Dataset {dataset.id} has no dataset locator, cannot read from BigQuery.",
            )
        dataset_locator_fields = {
            f.key: f.value for f in dataset.dataset_locator.fields
        }
        file_prefix = str(
            dataset_locator_fields[BUCKET_BASED_DATASET_FILE_PREFIX_FIELD],
        )
        # strip leading / from file_prefix if present & allow the connector to handle it
        if file_prefix.startswith("/"):
            file_prefix = file_prefix[1:]
        file_suffix = dataset_locator_fields.get(BUCKET_BASED_DATASET_FILE_SUFFIX_FIELD)
        if file_suffix:
            file_suffix = str(file_suffix)
            # make file_suffix regex enforce "suffix" constraint
            if not file_suffix.endswith("$"):
                file_suffix += "$"
        file_type = DatasetFileType(
            dataset_locator_fields[BUCKET_BASED_DATASET_FILE_TYPE_FIELD],
        )
        timezone = pytz.timezone(
            dataset_locator_fields[BUCKET_BASED_DATASET_TIMESTAMP_TIME_ZONE_FIELD],
        )
        return _BucketBasedDatasetLocatorFields(
            file_prefix=file_prefix,
            file_suffix=file_suffix,
            file_type=file_type,
            timezone=timezone,
        )

    def _get_matching_files(
        self,
        rendered_file_search_str: str,
        file_suffix: Optional[str],
    ) -> list[str]:
        # file search string should already have rendered timestamp information
        matching_files = []
        for root, dirs, files in self.file_system.walk(rendered_file_search_str):
            for file in files:
                file_path = os.path.join(root, file)
                if file_suffix and not re.search(file_suffix, file_path):
                    # file doesn't match requirements
                    continue
                matching_files.append(file_path)
        return matching_files

    def read(
        self,
        dataset: Dataset | AvailableDataset,
        start_time: datetime,
        end_time: datetime,
        filters: list[DataResultFilter] | None = None,
        pagination_options: ConnectorPaginationOptions | None = None,
    ) -> list[dict[str, Any]] | pd.DataFrame:
        """Reads data from the bucket. By default, will fetch all data between start/end matching the filters.
        Supports page, page_size, and limit filters. Starts from end_time and works backward.
        """
        timestamp_col: str | None = self._validate_timestamp_col(
            dataset,
            pagination_options,
        )
        inferences: list[dict[str, Any]] = []
        locator_fields = self._extract_dataset_locator_fields(dataset)

        # adjust start_time and end_time to the file timezones. if the timestamps are naive local tz will be assumed
        start_time_tz_aware = start_time.astimezone(locator_fields.timezone)
        end_time_tz_aware = end_time.astimezone(locator_fields.timezone)

        # extract smallest supported timedelta from time partition in file prefix
        smallest_timedelta = find_smallest_timedelta(locator_fields.file_prefix)
        if not smallest_timedelta:
            raise Exception(
                f"Timestamp partition in file prefix must have at least as small as a day time unit present. "
                f"Got {locator_fields.file_prefix}.",
            )

        # include listing files at end_time even though range is exclusive so that if the end_time timestamp is, for
        # example, +10:00, and the timedelta is days, we list inferences up to +10:00 using the rendered string for
        # end_time timestamp
        timestamp = end_time_tz_aware
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            # need to include one extra loop so that if the timedelta takes us from files after start_time to files
            # before start_time, we still render the search string for files that will hold inferences taken at
            # start_time
            while timestamp >= start_time_tz_aware - smallest_timedelta:
                # list matching files in dataset
                rendered_file_search_str = self._render_file_prefix_for_timestamp(
                    timestamp,
                    locator_fields.file_prefix,
                )
                try:
                    matching_files = self._get_matching_files(
                        rendered_file_search_str,
                        locator_fields.file_suffix,
                    )
                except FileNotFoundError:
                    # no files for this time range, move to next
                    self.logger.info(
                        f"Found no files that match prefix {rendered_file_search_str}. Moving to next time range.",
                    )
                    timestamp -= smallest_timedelta
                    continue
                self.logger.info(
                    f"Found {len(matching_files)} files that match prefix {rendered_file_search_str}. Reading files.",
                )

                # read files, store inferences in memory. order must be deterministic to support pagination
                future_to_file = {
                    executor.submit(
                        read_file,
                        self.file_system,
                        file_name,
                        locator_fields.file_type,
                    ): file_name
                    for file_name in matching_files
                }
                results = []
                for future in concurrent.futures.as_completed(future_to_file):
                    file_name = future_to_file[future]
                    result = future.result()
                    results.append((file_name, result))

                # sort results by file name and add to inferences
                for _, result in sorted(results, key=lambda x: x[0], reverse=True):
                    inferences += result

                # perform filtering now to optimize paginated queries
                inferences = self._filter_inferences(
                    inferences,
                    timestamp_col,
                    start_time_tz_aware,
                    end_time_tz_aware,
                    locator_fields.timezone,
                    filters,
                )
                if self._pagination_limits_met(inferences, pagination_options):
                    break

                timestamp -= smallest_timedelta

        if timestamp_col:
            # sort by descending timestamp by default
            inferences = sorted(
                inferences,
                key=lambda x: x[timestamp_col],
                reverse=True,
            )

        return (
            self._paginate_inferences(inferences, pagination_options)
            if pagination_options
            else inferences
        )

    def list_datasets(self) -> PutAvailableDatasets:
        raise NotImplementedError(
            "List datasets not implemented for bucket-based connectors.",
        )
