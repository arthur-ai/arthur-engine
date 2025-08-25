import logging
from datetime import datetime, timedelta
from typing import Optional, Type
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
import pytz
from arthur_client.api_bindings import (
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
from job_executors.metrics_calculation_executor import _create_alert_check_job
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
