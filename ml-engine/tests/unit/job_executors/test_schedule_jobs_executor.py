from datetime import datetime, timedelta

import pytest
from arthur_client.api_bindings import (
    JobKind,
    MetricsCalculationJobSpec,
    ModelMetricsSchedule,
    PostJob,
    ScheduleJobsJobSpec,
)
from arthur_common.tools.functions import hash_nonce
from job_executors.schedule_jobs_executor import generate_next_job_series


@pytest.mark.parametrize(
    "start_timestamp, model_id, schedule, nonce, k, expected_jobs_count, job_period_seconds",
    [
        (
            datetime(2023, 1, 1, 0, 0),
            "test_model_id",
            ModelMetricsSchedule(
                id="test_schedule_id",
                cron="0 * * * *",
                lookback_period_seconds=3600,
            ),
            "test_nonce",
            5,
            6,
            3600,
        ),
        (
            datetime(2023, 1, 1, 0, 0),
            "test_model_id",
            ModelMetricsSchedule(
                id="test_schedule_id",
                cron="0 0 * * *",
                lookback_period_seconds=3600,
            ),
            "test_nonce",
            3,
            4,
            86400,
        ),
    ],
)
def test_generate_next_job_series(
    start_timestamp: datetime,
    model_id: str,
    schedule: ModelMetricsSchedule,
    nonce: str,
    k: int,
    expected_jobs_count: int,
    job_period_seconds: int,
):
    new_jobs = generate_next_job_series(start_timestamp, model_id, schedule, nonce, k)

    assert len(new_jobs) == expected_jobs_count
    schedule_job = new_jobs[-1]
    metrics_jobs = new_jobs[:-1]

    for job in metrics_jobs:
        assert isinstance(job, PostJob)
        assert job.kind == JobKind.METRICS_CALCULATION
        assert isinstance(job.job_spec.actual_instance, MetricsCalculationJobSpec)
        assert job.job_spec.actual_instance.scope_model_id == model_id
        assert job.schedule_id == schedule.id

    assert isinstance(schedule_job, PostJob)
    assert schedule_job.kind == JobKind.SCHEDULE_JOBS
    assert isinstance(schedule_job.job_spec.actual_instance, ScheduleJobsJobSpec)
    assert schedule_job.job_spec.actual_instance.scope_model_id == model_id
    assert schedule_job.schedule_id == schedule.id
    assert schedule_job.nonce == hash_nonce(nonce)

    # Check that the timestamps are correctly set
    for i in range(1, k):
        prev_job = new_jobs[i - 1]
        curr_job = new_jobs[i]
        assert isinstance(prev_job.job_spec.actual_instance, MetricsCalculationJobSpec)
        assert isinstance(curr_job.job_spec.actual_instance, MetricsCalculationJobSpec)

        # The job sequence should always be spaced by the cron schedule's period
        assert (
            curr_job.job_spec.actual_instance.start_timestamp
            - prev_job.job_spec.actual_instance.start_timestamp
            == timedelta(seconds=job_period_seconds)
        )
        assert (
            curr_job.job_spec.actual_instance.end_timestamp
            - prev_job.job_spec.actual_instance.end_timestamp
            == timedelta(seconds=job_period_seconds)
        )

        # The job start/end duration should be dictated by the lookback period
        assert (
            curr_job.job_spec.actual_instance.end_timestamp
            - curr_job.job_spec.actual_instance.start_timestamp
        ) == timedelta(seconds=schedule.lookback_period_seconds)

    # Check that the last ScheduleJobs job has the correct start_timestamp
    assert (
        schedule_job.job_spec.actual_instance.start_timestamp
        == metrics_jobs[-1].job_spec.actual_instance.end_timestamp
    )
