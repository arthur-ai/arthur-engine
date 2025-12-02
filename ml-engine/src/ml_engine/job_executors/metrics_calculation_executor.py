import logging
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from typing import Any, List, Set, Tuple, Union

import pandas as pd
from arthur_client.api_bindings import (
    AggregationKind,
    AggregationSpec,
    AlertCheckJobSpec,
    CustomAggregationsV1Api,
    CustomAggregationTestsV1Api,
    Dataset,
    DatasetsV1Api,
    Job,
    JobsV1Api,
    MetricsCalculationJobSpec,
    MetricsUpload,
    MetricsUploadMetricsInner,
    MetricsV1Api,
    MetricsVersion,
    Model,
    ModelsV1Api,
    PostJob,
    PostJobBatch,
    PostJobKind,
    PostJobSpec,
    PostMetricsVersions,
    TestCustomAggregationJobSpec,
)
from arthur_client.api_bindings.exceptions import NotFoundException
from arthur_common.models.connectors import SHIELD_DATASET_TASK_ID_FIELD
from arthur_common.models.enums import ModelProblemType
from arthur_common.models.metrics import (
    DatasetReference,
    Dimension,
    NumericMetric,
    NumericTimeSeries,
    SketchMetric,
    SketchTimeSeries,
)
from arthur_common.tools.aggregation_loader import AggregationLoader
from duckdb import DuckDBPyConnection
from pydantic import Field

from config import Config
from connectors.shield_connector import ShieldBaseConnector
from dataset_loader import DatasetLoader
from metric_calculators.custom_metric_sql_calculator import CustomMetricSQLCalculator
from metric_calculators.default_metric_calculator import DefaultMetricCalculator
from metric_calculators.metric_calculator import MetricCalculator
from tools.connector_constructor import ConnectorConstructor
from tools.validators import validate_schedule

ML_ENGINE_AGGREGATION_TIMEOUT = Config.aggregation_timeout()

AggCalculationJobSpecTypes = Union[
    MetricsCalculationJobSpec,
    TestCustomAggregationJobSpec,
]


class InternalAggregationKind(str, Enum):
    CUSTOM = "custom"
    DEFAULT = "default"
    CUSTOM_TEST = "custom_test"


class InternalAggregationSpec(AggregationSpec):  # type: ignore[misc]
    internal_aggregation_kind: InternalAggregationKind = Field(
        description="Internal aggregation kind for the spec.",
    )


MAX_POINTS_PER_METRIC_NAME = 25


class AggregationCalculationExecutor(ABC):
    """Abstract class for any jobs that calculate aggregations over datasets"""

    def __init__(
        self,
        models_client: ModelsV1Api,
        datasets_client: DatasetsV1Api,
        metrics_client: MetricsV1Api,
        jobs_client: JobsV1Api,
        custom_aggregations_client: CustomAggregationsV1Api,
        custom_aggregation_tests_client: CustomAggregationTestsV1Api,
        connector_constructor: ConnectorConstructor,
        logger: logging.Logger,
    ):
        self.models_client = models_client
        self.datasets_client = datasets_client
        self.metrics_client = metrics_client
        self.jobs_client = jobs_client
        self.custom_aggregations_client = custom_aggregations_client
        self.custom_aggregation_tests_client = custom_aggregation_tests_client
        self.connector_constructor = connector_constructor
        self.logger = logger
        self.default_aggregations = {
            str(agg_schema.id): (agg_func, agg_schema)
            for agg_schema, agg_func in AggregationLoader.load_aggregations()
        }  # map from schema ID to AggregationFunction and aggregation schema for default aggregations
        self.logger.info(
            f"Loaded {len(self.default_aggregations)} default aggregation functions",
        )

    @abstractmethod
    def _datasets_for_calculation(
        self,
        job_spec: AggCalculationJobSpecTypes,
    ) -> List[Dataset]:
        """Extracts datasets used in the metric calculation from the job spec."""
        raise NotImplementedError

    @abstractmethod
    def _aggregation_specs_for_calculation(
        self,
        job_spec: AggCalculationJobSpecTypes,
    ) -> List[InternalAggregationSpec]:
        """Extracts aggregation specs used for the metric calculation from the job spec.
        Returns object with aggregation spec from the API along with new internal_aggregation_kind field
        """
        raise NotImplementedError

    @abstractmethod
    def _validate_job(self, job: Job, job_spec: AggCalculationJobSpecTypes) -> None:
        """Validates a job against a job spec before execution.

        Used in metrics calculation jobs to validate the model schedule, but is not currently used in
        the custom aggregation test jobs.
        """
        raise NotImplementedError

    @abstractmethod
    def _upload_metrics(
        self,
        job_spec: AggCalculationJobSpecTypes,
        metrics_upload: MetricsUpload,
    ) -> MetricsVersion:
        """Uploads metrics for the job result.
        Can also do any post-job behaviors here, like creating an alert check job.
        """
        raise NotImplementedError

    @staticmethod
    def _convert_to_metrics_upload(
        metrics: list[NumericMetric | SketchMetric],
    ) -> MetricsUpload:
        result = MetricsUpload(metrics=[])
        for m in metrics:
            js = m.model_dump_json()
            result.metrics.append(MetricsUploadMetricsInner.from_json(js))
        return result

    @staticmethod
    @abstractmethod
    def _process_metrics(
        metrics: list[NumericMetric | SketchMetric],
    ) -> list[NumericMetric | SketchMetric]:
        """Processes metrics as needed by the implementer.
        Can include removing null timestamps, limiting the rows returned, etc.
        """
        raise NotImplementedError

    def execute(self, job: Job, job_spec: AggCalculationJobSpecTypes) -> None:
        datasets = self._datasets_for_calculation(job_spec)
        is_agentic = any(
            dataset.model_problem_type == ModelProblemType.AGENTIC_TRACE
            for dataset in datasets
        )

        self._validate_job(job, job_spec)

        # Explicitly run metric computation for agentic datasets, via connector
        if is_agentic:
            for ds in datasets:
                connector_id, task_ids = self._extract_connector_id_and_task_ids(ds)
                if connector_id is not None and task_ids:
                    self._run_agentic_metric_computation(
                        connector_id,
                        job_spec,
                        task_ids,
                    )

        duckdb_conn, failed_to_load_datasets = self._load_data(datasets, job_spec)
        # run metrics calculation on datasets that were successfully loaded only
        loaded_datasets = [
            dataset for dataset in datasets if dataset.id not in failed_to_load_datasets
        ]
        agg_specs = self._aggregation_specs_for_calculation(job_spec)
        metrics, failed_agg_ids = self._calculate_metrics(
            agg_specs,
            loaded_datasets,
            duckdb_conn,
        )
        # process and complete metrics upload
        processed_metrics = self._process_metrics(metrics)
        metrics_upload = self._convert_to_metrics_upload(processed_metrics)
        self.logger.info("Uploading metrics")
        self._upload_metrics(job_spec, metrics_upload)
        self.logger.info("Finished uploading metrics")

        if failed_to_load_datasets:
            # raise exception so job is marked as failed
            raise ValueError(
                f"Error loading dataset(s) with id(s) {', '.join(failed_to_load_datasets)}. Metrics were "
                f"still calculated for any other datasets associated with the model.",
            )
        if failed_agg_ids:
            # raise exception so job is marked as failed
            raise ValueError(
                f"Error calculating aggregation(s) with id(s) {', '.join(failed_agg_ids)}. Metrics were still "
                f"calculated for any other aggregations configured for the model.",
            )

    # Extract task IDs and connector ID from a single dataset
    def _extract_connector_id_and_task_ids(
        self,
        dataset: Dataset,
    ) -> Tuple[str | None, list[str]]:
        if not dataset.connector:
            return None, []

        if not dataset.dataset_locator:
            return dataset.connector.id, []

        task_ids = []
        for field in dataset.dataset_locator.fields:
            if field.key == SHIELD_DATASET_TASK_ID_FIELD:
                task_ids.append(field.value)

        return dataset.connector.id, task_ids

    # Run metric computation agentic models before aggregation
    def _run_agentic_metric_computation(
        self,
        connector_id: str,
        job_spec: MetricsCalculationJobSpec,
        task_ids: list[str],
    ) -> None:
        connector = self.connector_constructor.get_connector_from_spec(connector_id)

        if not isinstance(connector, ShieldBaseConnector):
            raise ValueError(f"Expected ShieldBaseConnector, got {type(connector)}")

        self.logger.info(
            f"Triggered metric computation for connector {connector_id} and agentic task: {task_ids}",
        )
        # Call the metrics endpoint to trigger computation. Ignore the response.
        connector.query_spans_with_metrics(
            task_ids=task_ids,
            start_time=job_spec.start_timestamp,
            end_time=job_spec.end_timestamp,
        )
        self.logger.info(
            f"Finished metric computation for connector {connector_id} and agentic tasks: {task_ids}",
        )

    def _submit_alert_check_job(
        self,
        project_id: str,
        alert_check_batch: PostJobBatch,
    ) -> None:
        self.jobs_client.post_submit_jobs_batch(
            project_id=project_id,
            post_job_batch=alert_check_batch,
        )

    @abstractmethod
    def _load_data(
        self,
        datasets: List[Dataset],
        job_spec: MetricsCalculationJobSpec,
    ) -> Tuple[DuckDBPyConnection, Set[str]]:
        """Returns DuckDB connection and set of datasets that failed to load"""
        raise NotImplementedError

    def _pick_metric_calculator(
        self,
        agg_spec: InternalAggregationSpec,
        duckdb_conn: DuckDBPyConnection,
    ) -> MetricCalculator:
        """Returns the MetricCalculator needed to calculate the aggregation represented by agg_spec.
        :param: agg_spec: AggregationSpec of the aggregation to calculate.
        :param duckdb_conn: DuckDBConnection with loaded dataset.
        """
        # see if agg spec corresponds to a default aggregation function
        match agg_spec.internal_aggregation_kind:
            case InternalAggregationKind.DEFAULT:
                _agg_function_type, agg_function_schema = self.default_aggregations.get(
                    agg_spec.aggregation_id,
                    (None, None),
                )
                if _agg_function_type is None or agg_function_schema is None:
                    raise ValueError(
                        f"No aggregation with id {agg_spec.aggregation_id} could be fetched for execution "
                        f"from the set of default metrics.",
                    )
                return DefaultMetricCalculator(
                    duckdb_conn,
                    self.logger,
                    agg_spec,
                    agg_function_schema,
                    _agg_function_type,
                )
            case InternalAggregationKind.CUSTOM:
                try:
                    custom_agg = self.custom_aggregations_client.get_custom_aggregation(
                        custom_aggregation_id=agg_spec.aggregation_id,
                        version=agg_spec.aggregation_version,
                    )
                except NotFoundException:
                    raise ValueError(
                        f"No aggregation with id {agg_spec.aggregation_id} could be fetched for execution "
                        f"from the set of custom aggregations.",
                    )

                # do not calculate metrics for soft-deleted aggregations. Fail loudly to tell the user the aggregation
                # configured for their model has been deleted.
                if custom_agg.is_deleted:
                    raise ValueError(
                        f"The custom aggregation with id {custom_agg.id} was deleted at "
                        f"{custom_agg.deleted_at.strftime('%Y-%m-%d %H:%M:%S %Z')}. If you still need this aggregation "
                        f"for your model, please recreate it and add the new aggregation to your metric config. "
                        f"Otherwise, please remove the deleted aggregation from your metric config.",
                    )

                # warn user if they're not using the latest version of an aggregation
                if custom_agg.latest_version != agg_spec.aggregation_version:
                    self.logger.warning(
                        f"The aggregation with ID {custom_agg.id} is configured to use version "
                        f"{agg_spec.aggregation_version}. However, the latest version of the aggregation is "
                        f"{custom_agg.latest_version}. Please consider updating your model's metric configuration "
                        f"to pick up the latest version of this custom aggregation.",
                    )

                return CustomMetricSQLCalculator(
                    duckdb_conn,
                    self.logger,
                    agg_spec,
                    custom_agg,
                )
            case InternalAggregationKind.CUSTOM_TEST:
                try:
                    custom_agg_test = self.custom_aggregation_tests_client.get_custom_aggregation_test(
                        custom_aggregation_test_id=agg_spec.aggregation_id,
                    )
                except NotFoundException:
                    raise ValueError(
                        f"No test custom aggregation aggregation with id {agg_spec.aggregation_id} could be fetched for execution "
                        f"from the set of custom aggregation tests.",
                    )
                return CustomMetricSQLCalculator(
                    duckdb_conn,
                    self.logger,
                    agg_spec,
                    custom_agg_test,
                )
            case _:
                raise ValueError(
                    f"Aggregation type {agg_spec.aggregation_kind} not supported for execution.",
                )

    def _calculate_metrics(
        self,
        aggregation_specs: List[InternalAggregationSpec],
        datasets: list[Dataset],
        duckdb_conn: DuckDBPyConnection,
    ) -> Tuple[list[NumericMetric | SketchMetric], List[str]]:
        """Returns list of metrics and list of IDs of any aggregations that failed to be calculated."""
        metrics: list[NumericMetric | SketchMetric] = []
        calculator = None
        failed_aggregation_ids = []
        for agg_spec in aggregation_specs:
            try:
                calculator = self._pick_metric_calculator(agg_spec, duckdb_conn)
                self.logger.info(
                    f"Calculating aggregation with name {calculator.agg_name}",
                )
                init_args, aggregate_args = calculator.process_agg_args(
                    datasets,
                )

                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        calculator.aggregate,
                        init_args,
                        aggregate_args,
                    )
                    metrics_to_add = future.result(
                        timeout=ML_ENGINE_AGGREGATION_TIMEOUT,
                    )

                self._add_dimensions_to_metrics(
                    metrics_to_add,
                    aggregate_args,
                    agg_spec,
                )
                metrics.extend(metrics_to_add)
            except Exception as exc:
                # continue with future metrics calculations in case they're successful and log an error
                if isinstance(exc, TimeoutError):
                    error_msg = f"Aggregation calculation timed out for {agg_spec.aggregation_id}"
                else:
                    error_msg = (
                        f"Failed to process aggregation {agg_spec.aggregation_id}"
                    )

                if calculator and calculator.agg_name:
                    error_msg += f" - {calculator.agg_name}"
                self.logger.error(
                    error_msg,
                    exc_info=exc,
                )
                failed_aggregation_ids.append(agg_spec.aggregation_id)
        return metrics, failed_aggregation_ids

    def _add_dimensions_to_metrics(
        self,
        metrics_to_add: list[NumericMetric | SketchMetric],
        aggregate_args: dict[str, Any],
        agg_spec: AggregationSpec,
    ) -> None:
        """
        If the aggregate args contain a dataset reference, this function adds dataset_name and dataset_id
        dimensions to the metrics in the list of metrics_to_add.
        It updates the metrics in the list in-place.
        """
        dimensions_to_add = []

        # find the dataset reference in the aggregate_args
        dataset_ref = None
        for arg_name, arg_value in aggregate_args.items():
            if isinstance(arg_value, DatasetReference):
                dataset_ref = arg_value
                break

        if dataset_ref is not None:
            dimensions_to_add.extend(
                [
                    Dimension(name="dataset_name", value=dataset_ref.dataset_name),
                    Dimension(name="dataset_id", value=str(dataset_ref.dataset_id)),
                ],
            )

        # add dimensions to the metrics
        dimensions_to_add.append(
            Dimension(name="aggregation_id", value=str(agg_spec.aggregation_id)),
        )

        if agg_spec.aggregation_version is not None:
            dimensions_to_add.append(
                Dimension(
                    name="aggregation_version",
                    value=str(agg_spec.aggregation_version),
                ),
            )

        for metric in metrics_to_add:
            series_list: list[NumericTimeSeries] | list[SketchTimeSeries] = []
            if isinstance(metric, NumericMetric):
                series_list = metric.numeric_series
            elif isinstance(metric, SketchMetric):
                series_list = metric.sketch_series
            else:
                self.logger.warning(
                    f"Unknown metric type: {metric.__class__.__name__} when attempting to add metric dataset dimensions",
                )

            for series in series_list:
                series.dimensions.extend(dimensions_to_add)


def _create_alert_check_job(
    model: Model,
    job_spec: MetricsCalculationJobSpec,
) -> PostJobBatch:
    return PostJobBatch(
        jobs=[
            PostJob(
                kind=PostJobKind.ALERT_CHECK,
                job_spec=PostJobSpec(
                    AlertCheckJobSpec(
                        scope_model_id=model.id,
                        check_range_start_timestamp=job_spec.start_timestamp,
                        check_range_end_timestamp=job_spec.end_timestamp,
                    ),
                ),
            ),
        ],
    )


def _filter_numeric_series(numeric_series: NumericTimeSeries) -> NumericTimeSeries:
    new_numeric_series = NumericTimeSeries(
        dimensions=numeric_series.dimensions,
        values=[],
    )
    for numeric_point in numeric_series.values:
        if numeric_point.timestamp is not None and not pd.isna(numeric_point.timestamp):
            new_numeric_series.values.append(numeric_point)
    return new_numeric_series


def _filter_sketch_series(sketch_series: SketchTimeSeries) -> SketchTimeSeries:
    new_sketch_series = SketchTimeSeries(dimensions=sketch_series.dimensions, values=[])
    for sketch_point in sketch_series.values:
        if sketch_point.timestamp is not None and not pd.isna(sketch_point.timestamp):
            new_sketch_series.values.append(sketch_point)
    return new_sketch_series


def filter_metric_null_timestamps(
    metrics: list[NumericMetric | SketchMetric],
) -> list[NumericMetric | SketchMetric]:
    # Naming is all hyper-specific to make mypy happy
    for m in metrics:
        if isinstance(m, NumericMetric):
            m.numeric_series = [
                _filter_numeric_series(numeric_series)
                for numeric_series in m.numeric_series
            ]
        elif isinstance(m, SketchMetric):
            m.sketch_series = [
                _filter_sketch_series(sketch_series)
                for sketch_series in m.sketch_series
            ]
    return metrics


class MetricsCalculationExecutor(AggregationCalculationExecutor):
    """Implements metrics calculation job spec-specific extraction logic."""

    def _datasets_for_calculation(
        self,
        job_spec: MetricsCalculationJobSpec,
    ) -> List[Dataset]:
        model = self.models_client.get_model(job_spec.scope_model_id)
        datasets = []
        for dsr in model.datasets:
            datasets.append(self.datasets_client.get_dataset(dsr.dataset_id))
        return datasets

    def _aggregation_specs_for_calculation(
        self,
        job_spec: MetricsCalculationJobSpec,
    ) -> List[InternalAggregationSpec]:
        model = self.models_client.get_model(job_spec.scope_model_id)
        agg_specs = []
        for agg_spec in model.metric_config.aggregation_specs:
            agg_specs.append(
                InternalAggregationSpec(
                    internal_aggregation_kind=agg_spec.aggregation_kind,
                    aggregation_id=agg_spec.aggregation_id,
                    aggregation_init_args=agg_spec.aggregation_init_args,
                    aggregation_args=agg_spec.aggregation_args,
                    aggregation_kind=agg_spec.aggregation_kind,
                    aggregation_version=agg_spec.aggregation_version,
                ),
            )
        return agg_specs

    def _validate_job(self, job: Job, job_spec: MetricsCalculationJobSpec) -> None:
        model = self.models_client.get_model(job_spec.scope_model_id)
        if job.schedule_id:
            validate_schedule(model, job.schedule_id)

    def _upload_metrics(
        self,
        job_spec: MetricsCalculationJobSpec,
        metrics_upload: MetricsUpload,
    ) -> None:
        """Uploads metrics to model metrics endpoint, creates new version, and creates alert check job
        to run over newly uploaded metrics."""
        model = self.models_client.get_model(job_spec.scope_model_id)
        mv = self.metrics_client.post_model_metrics_version(
            model_id=model.id,
            post_metrics_versions=PostMetricsVersions(
                range_start=job_spec.start_timestamp,
                range_end=job_spec.end_timestamp,
            ),
        )

        self.metrics_client.post_model_metrics_by_version(
            model_id=model.id,
            metric_version_num=mv.version_num,
            metrics_upload=metrics_upload,
        )
        alert_check_batch = _create_alert_check_job(model, job_spec)
        self._submit_alert_check_job(model.project_id, alert_check_batch)

    @staticmethod
    def _process_metrics(
        metrics: list[NumericMetric | SketchMetric],
    ) -> list[NumericMetric | SketchMetric]:
        """Filters null timestamps"""
        return filter_metric_null_timestamps(metrics)

    def _load_data(
        self,
        datasets: List[Dataset],
        job_spec: MetricsCalculationJobSpec,
    ) -> Tuple[DuckDBPyConnection, Set[str]]:
        """Returns DuckDB connection and set of datasets that failed to load"""
        dataset_loader = DatasetLoader(
            self.connector_constructor,
            self.datasets_client,
            self.logger,
        )
        return dataset_loader.load_datasets(
            [ds.id for ds in datasets],
            job_spec.start_timestamp,
            job_spec.end_timestamp,
        )


def _group_metrics_by_name_and_type(
    metrics: list[NumericMetric | SketchMetric],
) -> tuple[dict[str, list[NumericMetric]], dict[str, list[SketchMetric]]]:
    """Groups metrics by name and separates by type (numeric vs sketch)."""
    numeric_metrics_by_name: dict[str, list[NumericMetric]] = {}
    sketch_metrics_by_name: dict[str, list[SketchMetric]] = {}

    for metric in metrics:
        metric_name = metric.name
        if isinstance(metric, NumericMetric):
            if metric_name not in numeric_metrics_by_name:
                numeric_metrics_by_name[metric_name] = []
            numeric_metrics_by_name[metric_name].append(metric)
        elif isinstance(metric, SketchMetric):
            if metric_name not in sketch_metrics_by_name:
                sketch_metrics_by_name[metric_name] = []
            sketch_metrics_by_name[metric_name].append(metric)

    return numeric_metrics_by_name, sketch_metrics_by_name


def _limit_numeric_metric_points(
    metric_name: str,
    metric_list: list[NumericMetric],
    max_points: int,
) -> NumericMetric | None:
    """Limits the total number of points across all series for a numeric metric name group."""
    total_points_collected = 0
    limited_series = []

    for metric in metric_list:
        if total_points_collected >= max_points:
            break

        for series in metric.numeric_series:
            if total_points_collected >= max_points:
                break

            remaining_points = max_points - total_points_collected
            limited_values = series.values[:remaining_points]
            total_points_collected += len(limited_values)

            if limited_values:
                limited_series.append(
                    NumericTimeSeries(
                        dimensions=series.dimensions,
                        values=limited_values,
                    ),
                )

    if not limited_series:
        return None

    return NumericMetric(
        name=metric_name,
        numeric_series=limited_series,
    )


def _limit_sketch_metric_points(
    metric_name: str,
    metric_list: list[SketchMetric],
    max_points: int,
) -> SketchMetric | None:
    """Limits the total number of points across all series for a sketch metric name group."""
    total_points_collected = 0
    limited_series = []

    for metric in metric_list:
        if total_points_collected >= max_points:
            break

        for series in metric.sketch_series:
            if total_points_collected >= max_points:
                break

            remaining_points = max_points - total_points_collected
            limited_values = series.values[:remaining_points]
            total_points_collected += len(limited_values)

            if limited_values:
                limited_series.append(
                    SketchTimeSeries(
                        dimensions=series.dimensions,
                        values=limited_values,
                    ),
                )

    if not limited_series:
        return None

    return SketchMetric(
        name=metric_name,
        sketch_series=limited_series,
    )


def _limit_metrics_by_name(
    metrics: list[NumericMetric | SketchMetric],
    max_points_per_name: int,
) -> list[NumericMetric | SketchMetric]:
    """Limits the number of points per metric name across all metrics."""
    grouped = _group_metrics_by_name_and_type(metrics)
    numeric_metrics_by_name: dict[str, list[NumericMetric]] = grouped[0]
    sketch_metrics_by_name: dict[str, list[SketchMetric]] = grouped[1]

    limited_metrics: list[NumericMetric | SketchMetric] = []

    # Limit points for each numeric metric name group
    for metric_name, metric_list in numeric_metrics_by_name.items():
        limited_numeric_metric = _limit_numeric_metric_points(
            metric_name,
            metric_list,
            max_points_per_name,
        )
        if limited_numeric_metric is not None:
            limited_metrics.append(limited_numeric_metric)

    # Limit points for each sketch metric name group
    for metric_name, sketch_metric_list in sketch_metrics_by_name.items():
        limited_sketch_metric = _limit_sketch_metric_points(
            metric_name,
            sketch_metric_list,
            max_points_per_name,
        )
        if limited_sketch_metric is not None:
            limited_metrics.append(limited_sketch_metric)

    return limited_metrics


class CustomAggregationTestExecutor(AggregationCalculationExecutor):
    """Implements custom aggregation test job spec-specific extraction logic."""

    def _datasets_for_calculation(
        self,
        job_spec: TestCustomAggregationJobSpec,
    ) -> List[Dataset]:
        custom_agg_test = (
            self.custom_aggregation_tests_client.get_custom_aggregation_test(
                job_spec.test_custom_aggregation_id,
            )
        )
        return [self.datasets_client.get_dataset(custom_agg_test.dataset_id)]

    def _aggregation_specs_for_calculation(
        self,
        job_spec: TestCustomAggregationJobSpec,
    ) -> List[InternalAggregationSpec]:
        custom_agg_test = (
            self.custom_aggregation_tests_client.get_custom_aggregation_test(
                job_spec.test_custom_aggregation_id,
            )
        )
        return [
            InternalAggregationSpec(
                aggregation_id=job_spec.test_custom_aggregation_id,
                aggregation_init_args=[],
                aggregation_args=custom_agg_test.aggregation_arg_configuration,
                aggregation_kind=AggregationKind.CUSTOM,
                internal_aggregation_kind=InternalAggregationKind.CUSTOM_TEST,
                aggregation_version=None,
            ),
        ]

    def _validate_job(self, job: Job, job_spec: TestCustomAggregationJobSpec) -> None:
        # no validations needed for custom aggregation test jobs today
        pass

    @staticmethod
    def _process_metrics(
        metrics: list[NumericMetric | SketchMetric],
    ) -> list[NumericMetric | SketchMetric]:
        """Applies limits to number returned and filters null timestamps."""
        # Filter null timestamps first
        filtered_metrics = filter_metric_null_timestamps(metrics)

        # Limit points per metric name
        return _limit_metrics_by_name(filtered_metrics, MAX_POINTS_PER_METRIC_NAME)

    def _upload_metrics(
        self,
        job_spec: TestCustomAggregationJobSpec,
        metrics_upload: MetricsUpload,
    ) -> None:
        """Upload metric to custom aggregation test result endpoint"""
        self.custom_aggregation_tests_client.post_custom_aggregation_test_results(
            custom_aggregation_test_id=job_spec.test_custom_aggregation_id,
            metrics_upload=metrics_upload,
        )

    def _load_data(
        self,
        datasets: List[Dataset],
        job_spec: TestCustomAggregationJobSpec,
    ) -> Tuple[DuckDBPyConnection, Set[str]]:
        """Returns DuckDB connection and set of datasets that failed to load"""
        custom_agg_test = (
            self.custom_aggregation_tests_client.get_custom_aggregation_test(
                job_spec.test_custom_aggregation_id,
            )
        )
        dataset_loader = DatasetLoader(
            self.connector_constructor,
            self.datasets_client,
            self.logger,
        )
        return dataset_loader.load_datasets(
            [ds.id for ds in datasets],
            custom_agg_test.start_timestamp,
            custom_agg_test.end_timestamp,
        )
