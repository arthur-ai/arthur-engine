import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Type
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

import pytest
import pytz
from arthur_client.api_bindings import (
    AggregationKind,
    AggregationSpec,
    AggregationSpecSchema,
    AlertCheckJobSpec,
    Dataset,
    DatasetSchema,
    JobKind,
    MetricsArgSpec,
    MetricsCalculationJobSpec,
    MetricsVersion,
    PostJob,
    PostJobBatch,
)
from arthur_common.aggregations import AggregationFunction
from arthur_common.tools.aggregation_loader import AggregationLoader
from dataset_loader import DatasetLoader
from job_executors.metrics_calculation_executor import (
    MetricsCalculationExecutor,
    _create_alert_check_job,
)
from metric_calculators.default_metric_calculator import DefaultMetricCalculator
from mock_data.connector_helpers import MOCK_BQ_DATASET
from mock_data.mock_data_generator import random_model

logger = logging.getLogger("job_logger")


def _get_aggregation_schema_by_id(
    agg_id: str,
) -> tuple[AggregationSpecSchema, Type[AggregationFunction]]:
    functions = AggregationLoader.load_aggregations()
    for function in functions:
        if str(function[0].id) == agg_id:
            return function[0], function[1]
    else:
        raise ValueError(f"Aggregation function with id {agg_id} not found for test.")


def column_name_to_id(name: str, schema: DatasetSchema) -> UUID:
    for col in schema.columns:
        if col.source_name == name:
            return UUID(col.id)
    else:
        raise ValueError(f"Could not find column {name}")


def test_create_alert_check_job():
    model = random_model()
    model_id = str(uuid4())
    model.id = model_id

    mv = MetricsVersion(
        created_at=datetime.now(),
        updated_at=datetime.now(),
        version_num=1,
        scope_model_id=model_id,
        range_start=datetime.now(),
        range_end=datetime.now(),
    )
    metrics_start_time = datetime.now() - timedelta(hours=2)
    metrics_end_time = datetime.now() - timedelta(hours=1)
    metrics_job_spec = MetricsCalculationJobSpec(
        scope_model_id=model_id,
        start_timestamp=metrics_start_time,
        end_timestamp=metrics_end_time,
    )
    alert_job_batch = _create_alert_check_job(model, metrics_job_spec, mv)

    assert isinstance(alert_job_batch, PostJobBatch)
    assert len(alert_job_batch.jobs) == 1

    assert isinstance(alert_job_batch.jobs[0], PostJob)
    job = alert_job_batch.jobs[0]
    assert job.kind == JobKind.ALERT_CHECK

    assert isinstance(
        alert_job_batch.jobs[0].job_spec.actual_instance,
        AlertCheckJobSpec,
    )

    alert_check_job = alert_job_batch.jobs[0].job_spec.actual_instance

    assert alert_check_job.scope_model_id == model_id
    assert alert_check_job.check_range_start_timestamp == metrics_start_time
    assert alert_check_job.check_range_end_timestamp == metrics_end_time


@pytest.mark.parametrize(
    "segmentation_col_names,error_str",
    [
        # column with bad dtype
        (["timestamp"], "data type mismatch"),
        # column with too many possibilities
        (["numeric_col"], "column exceeds the limit of allowed unique values"),
        # more than 3 columns
        (["name", "description", "desc2", "id"], "Max 3 columns can be applied"),
        # null segmentation_cols arg value—should fail because parameter is not expected list type
        (None, "Column list parameter should be list type"),
        # empty list segmentation_cols arg value—should pass because argument is optional
        ([], None),
    ],
)
def test_process_agg_args(
    mock_bigquery_client,
    segmentation_col_names: Optional[list[str]],
    error_str: Optional[str],
) -> None:
    # configure data mocks
    first_timestamp = datetime(2024, 1, 1).astimezone(pytz.timezone("UTC"))
    first_timestamp_str = first_timestamp.isoformat()
    second_timestamp = datetime(2024, 1, 1, hour=2).astimezone(pytz.timezone("UTC"))
    expected_data = [
        {
            "id": str(uuid4()),
            "name": "Test1",
            "timestamp": first_timestamp_str,
            "description": "test inference 1",
            "desc2": "another string col",
            "numeric_col": i,
        }
        for i in list(range(101))
    ]

    # configure dataset mocks
    datasets_client = Mock()
    dataset = Dataset.model_validate(MOCK_BQ_DATASET)
    datasets_client.get_dataset.return_value = dataset

    # configure connector mocks
    mock_connector = Mock()
    mock_connector.read.return_value = expected_data
    connector_constructor = Mock()
    connector_constructor.get_connector_from_spec.return_value = mock_connector

    # load mocked data into duckdb
    dataset_loader = DatasetLoader(
        connector_constructor=connector_constructor,
        datasets_client=datasets_client,
        logger=logger,
    )
    conn, unloaded_datasets = dataset_loader.load_datasets(
        dataset_ids=[dataset.id],
        start_time=first_timestamp - timedelta(seconds=5),
        end_time=second_timestamp + timedelta(seconds=5),
        filters=None,
        pagination_options=None,
    )
    assert len(unloaded_datasets) == 0

    agg_spec = AggregationSpec(
        aggregation_id="00000000-0000-0000-0000-00000000000a",
        aggregation_init_args=[],
        aggregation_args=[
            MetricsArgSpec(
                arg_key="dataset",
                arg_value=dataset.id,
            ),
            MetricsArgSpec(
                arg_key="segmentation_cols",
                arg_value=(
                    [
                        column_name_to_id(col_name, dataset.dataset_schema)
                        for col_name in segmentation_col_names
                    ]
                    if segmentation_col_names is not None
                    else None
                ),
            ),
        ],
    )
    agg_function_schema, agg_function_type = _get_aggregation_schema_by_id(
        "00000000-0000-0000-0000-00000000000a",
    )

    metrics_calculator = DefaultMetricCalculator(
        conn,
        logger,
        agg_spec,
        agg_function_schema,
        agg_function_type,
    )

    if error_str:
        with pytest.raises(ValueError) as exc:
            metrics_calculator.process_agg_args([dataset])
        assert error_str in str(exc.value)
    else:
        metrics_calculator.process_agg_args([dataset])


@patch("job_executors.metrics_calculation_executor.ML_ENGINE_AGGREGATION_TIMEOUT", 1)
def test_metrics_calculation_timeout(mock_bigquery_client, caplog):
    """Test metrics calculation timeout works properly."""
    first_timestamp = datetime(2024, 1, 1).astimezone(pytz.timezone("UTC"))
    first_timestamp_str = first_timestamp.isoformat()
    second_timestamp = datetime(2024, 1, 1, hour=2).astimezone(pytz.timezone("UTC"))
    expected_data = [
        {
            "id": str(uuid4()),
            "name": "Test1",
            "timestamp": first_timestamp_str,
            "description": "test inference 1",
            "numeric_col": 1,
        },
    ]

    # configure mock datasets
    datasets_client = Mock()
    dataset = Dataset.model_validate(MOCK_BQ_DATASET)
    datasets_client.get_dataset.return_value = dataset

    # configure mock connector
    mock_connector = Mock()
    mock_connector.read.return_value = expected_data
    connector_constructor = Mock()
    connector_constructor.get_connector_from_spec.return_value = mock_connector

    # load data
    dataset_loader = DatasetLoader(
        connector_constructor=connector_constructor,
        datasets_client=datasets_client,
        logger=logger,
    )
    conn, unloaded_datasets = dataset_loader.load_datasets(
        dataset_ids=[dataset.id],
        start_time=first_timestamp - timedelta(seconds=5),
        end_time=second_timestamp + timedelta(seconds=5),
        filters=None,
        pagination_options=None,
    )

    # create aggregation spec
    agg_spec = AggregationSpec(
        aggregation_id="00000000-0000-0000-0000-00000000000a",
        aggregation_kind=AggregationKind.DEFAULT,
        aggregation_init_args=[],
        aggregation_args=[
            MetricsArgSpec(
                arg_key="dataset",
                arg_value=dataset.id,
            ),
        ],
    )

    # mock the calculator to simulate a slow operation that exceeds timeout
    with patch(
        "job_executors.metrics_calculation_executor.DefaultMetricCalculator",
    ) as mock_calc_class:
        mock_calculator = Mock()
        mock_calc_class.return_value = mock_calculator

        # make the aggregate method take longer than the timeout
        def slow_aggregate(*args, **kwargs):
            time.sleep(2)
            return []

        mock_calculator.aggregate.side_effect = slow_aggregate
        mock_calculator.process_agg_args.return_value = ([], [])
        mock_calculator.agg_schema.name = "test_aggregation"

        # mock the model andother dependencies
        mock_models_client = Mock()
        mock_datasets_client = Mock()
        mock_metrics_client = Mock()
        mock_jobs_client = Mock()
        mock_custom_aggs_client = Mock()
        mock_model = Mock()

        # create a dataset reference with dataset_id attribute
        mock_dataset_ref = Mock()
        mock_dataset_ref.dataset_id = dataset.id
        mock_model.datasets = [mock_dataset_ref]
        mock_model.model_problem_types = []
        mock_model.id = "test-model-id"

        # mock the metric_config with aggregation_specs
        mock_metric_config = Mock()
        mock_metric_config.aggregation_specs = [agg_spec]
        mock_model.metric_config = mock_metric_config

        # mock project_id for alert check job creation
        mock_model.project_id = "test-project-id"
        mock_models_client.get_model.return_value = mock_model

        # make sure the datasets_client returns the actual dataset
        mock_datasets_client.get_dataset.return_value = dataset

        executor = MetricsCalculationExecutor(
            models_client=mock_models_client,
            datasets_client=mock_datasets_client,
            metrics_client=mock_metrics_client,
            jobs_client=mock_jobs_client,
            custom_aggregations_client=mock_custom_aggs_client,
            connector_constructor=connector_constructor,
            logger=logger,
        )

        # mock the _load_data method to return the prepared connection and no failed datasets
        with patch.object(executor, "_load_data") as mock_load_data:
            mock_load_data.return_value = (conn, set())

            # create a test job spec
            job_spec = MetricsCalculationJobSpec(
                aggregation_specs=[agg_spec],
                dataset_ids=[dataset.id],
                start_timestamp=first_timestamp,
                end_timestamp=second_timestamp,
                scope_model_id="test-model-id",
            )

            # create a mock job
            mock_job = Mock()
            mock_job.schedule_id = None

            # test there is a ValueError
            with pytest.raises(ValueError) as exc_info:
                executor.execute(mock_job, job_spec)

            # verify that the error message indicates a timeout or processing failure
            error_message = str(exc_info.value)
            expected_err_message = f"Error calculating aggregation(s) with id(s) {agg_spec.aggregation_id}. Metrics were still calculated for any other aggregations configured for the model."

            assert error_message == expected_err_message

            # test the timeout error message is logged
            assert any(
                f"Aggregation calculation timed out for {agg_spec.aggregation_id} - {mock_calculator.agg_schema.name}"
                in rec.message
                for rec in caplog.records
            )
