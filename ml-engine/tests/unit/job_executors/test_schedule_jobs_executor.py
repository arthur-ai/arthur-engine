from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest
from arthur_client.api_bindings import (
    Job,
    JobKind,
    JobsV1Api,
    MetricsCalculationJobSpec,
    Model,
    ModelMetricsSchedule,
    ModelsV1Api,
    PatchJob,
    PostJob,
    ScheduleJobsJobSpec,
)
from arthur_common.tools.functions import hash_nonce
from job_executors.schedule_jobs_executor import (
    ScheduleJobsExecutor,
    generate_next_job_series,
)


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


def test_execute_validation_failure_nonce_already_exists():
    """Test that execute fails when _validate_new_schedule_job finds an existing job with the same nonce."""
    # setup mocks
    mock_models_client = Mock(spec=ModelsV1Api)
    mock_jobs_client = Mock(spec=JobsV1Api)
    mock_logger = Mock()
    executor = ScheduleJobsExecutor(mock_models_client, mock_jobs_client, mock_logger)

    # setup test data
    model_id = "test_model_id"
    project_id = "test_project_id"
    schedule_id = "test_schedule_id"
    nonce = "test_nonce"
    start_timestamp = datetime(2023, 1, 1, 0, 0)

    # mock model
    mock_model = Mock(spec=Model)
    mock_model.project_id = project_id
    mock_model.schedule = ModelMetricsSchedule(
        id=schedule_id,
        cron="0 * * * *",
        lookback_period_seconds=3600,
    )

    # mock job
    mock_job = Mock(spec=Job)
    mock_job.id = "test_job_id"
    mock_job.schedule_id = schedule_id
    mock_job.nonce = nonce
    mock_job.attempts = 1
    mock_job.max_attempts = 3

    # mock job spec
    mock_job_spec = Mock(spec=ScheduleJobsJobSpec)
    mock_job_spec.scope_model_id = model_id
    mock_job_spec.start_timestamp = start_timestamp

    # mock expected responses
    mock_models_client.get_model.return_value = mock_model

    # mock the get_jobs call to return a job, indicating the nonce filtered on in the call exists
    mock_jobs_response = Mock()
    mock_jobs_response.records = [Mock()]  # Return one job indicating nonce exists
    mock_jobs_client.get_jobs.return_value = mock_jobs_response

    # mock the update_job call for _stop_job_retries
    mock_updated_job = Mock(spec=Job)
    mock_updated_job.max_attempts = 1
    mock_jobs_client.update_job.return_value = mock_updated_job

    # Execute and expect ValueError
    with pytest.raises(
        ValueError,
        match=f"Job with nonce {hash_nonce(nonce)} already exists",
    ):
        executor.execute(mock_job, mock_job_spec)

    # Verify the expected calls were made
    mock_models_client.get_model.assert_called_once_with(model_id)

    # Verify get_jobs was called with correct parameters
    mock_jobs_client.get_jobs.assert_called_once_with(
        project_id=project_id,
        nonce=hash_nonce(nonce),
        page=1,
        page_size=1,
        kinds=[JobKind.SCHEDULE_JOBS],
    )

    # Verify _stop_job_retries was called
    mock_jobs_client.update_job.assert_called_once_with(
        job_id=mock_job.id,
        patch_job=PatchJob(max_attempts=mock_job.attempts),
    )

    # Verify error was logged
    mock_logger.error.assert_called_once_with(
        "Validation error. Stopping this scheduled series of jobs.",
    )
