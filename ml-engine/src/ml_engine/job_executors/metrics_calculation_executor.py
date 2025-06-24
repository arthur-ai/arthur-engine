import logging
from typing import Any, Set, Tuple
from uuid import UUID

import pandas as pd
from arthur_client.api_bindings import (
    AggregationSpec,
    AlertCheckJobSpec,
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
)
from arthur_common.models.metrics import (
    AggregationSpecSchema,
    DatasetReference,
    Dimension,
    NumericMetric,
    NumericTimeSeries,
    SketchMetric,
    SketchTimeSeries,
)
from arthur_common.tools.aggregation_loader import AggregationLoader
from arthur_common.tools.functions import uuid_to_base26
from dataset_loader import DatasetLoader
from duckdb import DuckDBPyConnection
from metric_calculator import MetricCalculator
from tools.connector_constructor import ConnectorConstructor
from tools.validators import validate_schedule


class MetricsCalculationExecutor:
    def __init__(
        self,
        models_client: ModelsV1Api,
        datasets_client: DatasetsV1Api,
        metrics_client: MetricsV1Api,
        jobs_client: JobsV1Api,
        connector_constructor: ConnectorConstructor,
        logger: logging.Logger,
    ):
        self.models_client = models_client
        self.datasets_client = datasets_client
        self.metrics_client = metrics_client
        self.jobs_client = jobs_client
        self.connector_constructor = connector_constructor
        self.logger = logger

    def execute(self, job: Job, job_spec: MetricsCalculationJobSpec) -> None:
        model = self.models_client.get_model(job_spec.scope_model_id)
        datasets = []
        for dsr in model.datasets:
            datasets.append(self.datasets_client.get_dataset(dsr.dataset_id))

        if job.schedule_id:
            validate_schedule(model, job.schedule_id)

        duckdb_conn, failed_to_load_datasets = self._load_data(model, job_spec)
        # run metrics calculation on datasets that were successfully loaded only
        loaded_datasets = [
            dataset for dataset in datasets if dataset.id not in failed_to_load_datasets
        ]
        metrics = self._calculate_metrics(model, loaded_datasets, duckdb_conn)
        mv = self._upload_metrics(model, job_spec, metrics)
        alert_check_batch = _create_alert_check_job(model, job_spec, mv)
        self._submit_alert_check_job(model.project_id, alert_check_batch)

        if failed_to_load_datasets:
            # raise exception so job is marked as failed
            raise ValueError(
                f"Error loading dataset(s) with id(s) {', '.join(failed_to_load_datasets)}. Metrics were "
                f"still calculated for any other datasets associated with the model.",
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

    def _load_data(
        self,
        model: Model,
        job_spec: MetricsCalculationJobSpec,
    ) -> Tuple[DuckDBPyConnection, Set[str]]:
        """Returns DuckDB connection and set of datasets that failed to load"""
        dataset_loader = DatasetLoader(
            self.connector_constructor,
            self.datasets_client,
            self.logger,
        )
        return dataset_loader.load_datasets(
            [ds.dataset_id for ds in model.datasets],
            job_spec.start_timestamp,
            job_spec.end_timestamp,
        )

    def _calculate_metrics(
        self,
        model: Model,
        datasets: list[Dataset],
        duckdb_conn: DuckDBPyConnection,
    ) -> list[NumericMetric | SketchMetric]:
        metrics: list[NumericMetric | SketchMetric] = []
        calculator = MetricCalculator(duckdb_conn)
        agg_functions = {
            str(agg_schema.id): (agg_func, agg_schema)
            for agg_schema, agg_func in AggregationLoader.load_aggregations()
        }

        self.logger.info(f"Loaded {len(agg_functions)} aggregation functions")

        for agg_spec in model.metric_config.aggregation_specs:
            try:
                _agg_function_type, agg_function_schema = agg_functions[
                    agg_spec.aggregation_id
                ]
            except KeyError:
                self.logger.error(f"Unknown aggregation ID: {agg_spec.aggregation_id}")
                continue

            try:
                init_args, aggregate_args = process_agg_args(
                    agg_spec,
                    agg_function_schema,
                    datasets,
                )
                agg_function = _agg_function_type(**init_args)

                self.logger.info(f"Calculating function {agg_function.display_name()}")
                metrics_to_add = calculator.aggregate(agg_function, aggregate_args)
                self._add_dataset_dimensions_to_metrics(metrics_to_add, aggregate_args)
                metrics.extend(metrics_to_add)
            except Exception as e:
                self.logger.error(
                    f"Failed to process aggregation {agg_spec.aggregation_id} - {agg_function_schema.name}",
                    exc_info=e,
                )
        return metrics

    def _add_dataset_dimensions_to_metrics(
        self,
        metrics_to_add: list[NumericMetric] | list[SketchMetric],
        aggregate_args: dict[str, Any],
    ) -> None:
        """
        If the aggregate args contain a dataset reference, this function adds dataset_name and dataset_id
        dimensions to the metrics in the list of metrics_to_add.
        It updates the metrics in the list in-place.
        """
        # find the dataset reference in the aggregate_args
        for arg_name, arg_value in aggregate_args.items():
            if isinstance(arg_value, DatasetReference):
                dataset_ref = arg_value
                break
        else:
            # no dataset arg found, metric isn't tied to a dataset
            return

        # add the dataset dimensions to the metrics
        dimensions_to_add = [
            Dimension(name="dataset_name", value=dataset_ref.dataset_name),
            Dimension(name="dataset_id", value=str(dataset_ref.dataset_id)),
        ]

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

    def _upload_metrics(
        self,
        model: Model,
        job_spec: MetricsCalculationJobSpec,
        metrics: list[NumericMetric | SketchMetric],
    ) -> MetricsVersion:
        metrics = filter_metric_null_timestamps(metrics)
        result = MetricsUpload(metrics=[])
        for m in metrics:
            js = m.model_dump_json()
            result.metrics.append(MetricsUploadMetricsInner.from_json(js))

        self.logger.info("Uploading metrics")
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
            metrics_upload=result,
        )
        return mv


def _create_alert_check_job(
    model: Model,
    job_spec: MetricsCalculationJobSpec,
    mv: MetricsVersion,
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


def process_agg_args(
    agg_spec: AggregationSpec,
    agg_function_schema: AggregationSpecSchema,
    datasets: list[Dataset],
) -> tuple[dict[str, Any], dict[str, Any]]:
    init_args = {arg.arg_key: arg.arg_value for arg in agg_spec.aggregation_init_args}

    column_parameter_keys = [
        param.parameter_key
        for param in agg_function_schema.aggregate_args
        if param.parameter_type == "column"
    ]
    dataset_parameter_keys = [
        param.parameter_key
        for param in agg_function_schema.aggregate_args
        if param.parameter_type == "dataset"
    ]
    ds_map = {ds.id: ds for ds in datasets}
    all_dataset_columns = {}
    for ds in datasets:
        all_dataset_columns.update(ds.dataset_schema.column_names)

    aggregate_args: dict[str, Any] = {}
    for arg in agg_spec.aggregation_args:
        if arg.arg_key in column_parameter_keys:
            if arg.arg_value not in all_dataset_columns:
                raise ValueError(
                    f"Could not calculate aggregation with id {agg_spec.aggregation_id}. "
                    f"At least one parameter refers to a column in a dataset that could not be loaded.",
                )
            aggregate_args[arg.arg_key] = all_dataset_columns[arg.arg_value]
        elif arg.arg_key in dataset_parameter_keys:
            if arg.arg_value not in ds_map:
                raise ValueError(
                    f"Could not calculate aggregation with id {agg_spec.aggregation_id}. "
                    f"At least one parameter refers to a dataset that could not be loaded.",
                )
            dataset = ds_map[arg.arg_value]
            aggregate_args[arg.arg_key] = DatasetReference(
                dataset_name=dataset.name if dataset.name else "",
                dataset_table_name=uuid_to_base26(dataset.id),
                dataset_id=UUID(dataset.id),
            )
        else:
            aggregate_args[arg.arg_key] = arg.arg_value
    return init_args, aggregate_args


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
