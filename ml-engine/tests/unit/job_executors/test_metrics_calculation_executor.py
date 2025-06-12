from datetime import datetime, timedelta
from uuid import uuid4

from arthur_client.api_bindings import (
    AlertCheckJobSpec,
    JobKind,
    MetricsCalculationJobSpec,
    MetricsVersion,
    PostJob,
    PostJobBatch,
)
from job_executors.metrics_calculation_executor import _create_alert_check_job
from mock_data.mock_data_generator import random_model


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
