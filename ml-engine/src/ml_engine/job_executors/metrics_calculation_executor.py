import logging
from typing import Any, Set, Tuple

import pandas as pd
from arthur_client.api_bindings import (
    AggregationKind,
    AggregationSpec,
    AlertCheckJobSpec,
    CustomAggregationsV1Api,
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
from arthur_client.api_bindings.exceptions import NotFoundException
from arthur_common.models.connectors import SHIELD_DATASET_TASK_ID_FIELD
from arthur_common.models.metrics import DatasetReference, MetricsColumnSchemaUnion # TODO: replace when property method fixed in openapi
from arthur_common.models.datasets import ModelProblemType
from arthur_common.models.metrics import (
    DatasetReference,
    Dimension,
    NumericMetric,
    NumericTimeSeries,
    SketchMetric,
    SketchTimeSeries,
)
from arthur_common.tools.aggregation_loader import AggregationLoader
from connectors.shield_connector import ShieldBaseConnector
from dataset_loader import DatasetLoader
from duckdb import DuckDBPyConnection
from metric_calculators.custom_metric_sql_calculator import CustomMetricSQLCalculator
from metric_calculators.default_metric_calculator import DefaultMetricCalculator
from metric_calculators.metric_calculator import MetricCalculator
from tools.connector_constructor import ConnectorConstructor
from tools.validators import validate_schedule

from common_client.arthur_common_generated.models import (
    AggregationSpecSchema,
    Dimension,
    ModelProblemType,
    NumericMetric,
    NumericTimeSeries,
    ScopeSchemaTag,
    SketchMetric,
    SketchTimeSeries,
)


class MetricsCalculationExecutor:
    def __init__(
        self,
        models_client: ModelsV1Api,
        datasets_client: DatasetsV1Api,
        metrics_client: MetricsV1Api,
        jobs_client: JobsV1Api,
        custom_aggregations_client: CustomAggregationsV1Api,
        connector_constructor: ConnectorConstructor,
        logger: logging.Logger,
    ):
        self.models_client = models_client
        self.datasets_client = datasets_client
        self.metrics_client = metrics_client
        self.jobs_client = jobs_client
        self.custom_aggregations_client = custom_aggregations_client
        self.connector_constructor = connector_constructor
        self.logger = logger
        self.default_aggregations = {
            str(agg_schema.id): (agg_func, agg_schema)
            for agg_schema, agg_func in AggregationLoader.load_aggregations()
        }  # map from schema ID to AggregationFunction and aggregation schema for default aggregations
        self.logger.info(
            f"Loaded {len(self.default_aggregations)} default aggregation functions",
        )

    def execute(self, job: Job, job_spec: MetricsCalculationJobSpec) -> None:
        model = self.models_client.get_model(job_spec.scope_model_id)
        is_agentic = ModelProblemType.AGENTIC_TRACE in model.model_problem_types

        datasets = []
        for dsr in model.datasets:
            datasets.append(self.datasets_client.get_dataset(dsr.dataset_id))

        if job.schedule_id:
            validate_schedule(model, job.schedule_id)

        # Explicitly run metric computation for agentic models, via connector
        if is_agentic:
            for ds in datasets:
                connector_id, task_ids = self._extract_connector_id_and_task_ids(ds)
                if connector_id is not None and task_ids:
                    self._run_agentic_metric_computation(
                        connector_id,
                        job_spec,
                        task_ids,
                    )

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

    def _pick_metric_calculator(
        self,
        agg_spec: AggregationSpec,
        duckdb_conn: DuckDBPyConnection,
    ) -> MetricCalculator:
        """Returns the MetricCalculator needed to calculate the aggregation represented by agg_spec.
        :param: agg_spec: AggregationSpec of the aggregation to calculate.
        :param duckdb_conn: DuckDBConnection with loaded dataset.
        """
        # see if agg spec corresponds to a default aggregation function
        match agg_spec.aggregation_kind:
            case AggregationKind.DEFAULT:
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
            case AggregationKind.CUSTOM:
                try:
                    custom_aggs = (
                        self.custom_aggregations_client.get_custom_aggregation(
                            custom_aggregation_id=agg_spec.aggregation_id,
                            version=agg_spec.aggregation_version,
                        )
                    )
                except NotFoundException:
                    raise ValueError(
                        f"No aggregation with id {agg_spec.aggregation_id} could be fetched for execution "
                        f"from the set of custom aggregations.",
                    )
                return CustomMetricSQLCalculator(
                    duckdb_conn,
                    self.logger,
                    agg_spec,
                    custom_aggs,
                )
            case _:
                raise ValueError(
                    f"Aggregation type {agg_spec.aggregation_kind} not supported for execution.",
                )

    def _calculate_metrics(
        self,
        model: Model,
        datasets: list[Dataset],
        duckdb_conn: DuckDBPyConnection,
    ) -> list[NumericMetric | SketchMetric]:
        metrics: list[NumericMetric | SketchMetric] = []
        calculator = None
        for agg_spec in model.metric_config.aggregation_specs:
            try:
                calculator = self._pick_metric_calculator(agg_spec, duckdb_conn)
                self.logger.info(
                    f"Calculating aggregation with name {calculator.agg_schema.name}",
                )
                init_args, aggregate_args = calculator.process_agg_args(
                    datasets,
                )
                metrics_to_add = calculator.aggregate(
                    init_args,
                    aggregate_args,
                )
                self._add_dataset_dimensions_to_metrics(metrics_to_add, aggregate_args)
                metrics.extend(metrics_to_add)
            except Exception as exc:
                # continue with future metrics calculations in case they're successful and log an error
                error_msg = f"Failed to process aggregation {agg_spec.aggregation_id}"
                if calculator:
                    error_msg += f" - {calculator.agg_schema.name}"
                self.logger.error(
                    error_msg,
                    exc_info=exc,
                )
        return metrics

    def _add_dataset_dimensions_to_metrics(
        self,
        metrics_to_add: list[NumericMetric | SketchMetric],
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
