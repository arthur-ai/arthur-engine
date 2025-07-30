import logging
from datetime import datetime, timedelta

import croniter
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
    PostJobBatch,
    PostJobKind,
    PostJobSpec,
    ScheduleJobsJobSpec,
)
from arthur_client.api_bindings.exceptions import NotFoundException
from arthur_common.tools.functions import hash_nonce
from tools.validators import validate_schedule


class ScheduleJobsExecutor:
    def __init__(
        self,
        models_client: ModelsV1Api,
        jobs_client: JobsV1Api,
        logger: logging.Logger,
    ):
        self.models_client = models_client
        self.jobs_client = jobs_client
        self.logger = logger

    def execute(self, job: Job, job_spec: ScheduleJobsJobSpec) -> None:
        try:
            model = self.models_client.get_model(job_spec.scope_model_id)
        except NotFoundException:
            self._stop_job_retries(job=job)
            raise ValueError(
                f"Model {job_spec.scope_model_id} no longer exists. Stopping this scheduled series of jobs.",
            )

        try:
            self._validate_job(model, job)
        except ValueError as e:
            self._handle_validation_failure(job, e)

        new_jobs = generate_next_job_series(
            job_spec.start_timestamp,
            job_spec.scope_model_id,
            model.schedule,
            job.nonce,
        )
        new_schedule_job = [
            job for job in new_jobs if job.kind == PostJobKind.SCHEDULE_JOBS
        ][0]

        try:
            self._validate_new_schedule_job(model, new_schedule_job)
        except ValueError as e:
            self._handle_validation_failure(job, e)

        self.jobs_client.post_submit_jobs_batch(
            project_id=model.project_id,
            post_job_batch=PostJobBatch(jobs=new_jobs),
        )

    def _handle_validation_failure(self, job: Job, exc: ValueError) -> None:
        self.logger.error(f"Validation error. Stopping this scheduled series of jobs.")
        self._stop_job_retries(job=job)
        raise exc

    def _stop_job_retries(self, job: Job) -> Job:
        """
        This job updates the job to set the max_attempts equal to the current attempt so it doesn't
        continue to retry.
        """
        new_job = self.jobs_client.update_job(
            job_id=job.id,
            patch_job=PatchJob(
                max_attempts=job.attempts,
            ),
        )
        self.logger.info(
            f"Successfully changed job's max_attempts from {job.max_attempts} to {new_job.max_attempts}",
        )
        return new_job

    @staticmethod
    def _validate_job(model: Model, job: Job) -> None:
        if not job.schedule_id:
            raise ValueError("Schedule id must be defined for scheduled jobs.")
        if not job.nonce:
            raise ValueError("Nonce expected for this job type.")

        validate_schedule(model, job.schedule_id)

    def _validate_new_schedule_job(self, model: Model, new_job: PostJob) -> None:
        """Validates schedule job nonce is unique before submission to protect against race condition. if the job nonce
        already exists in the jobs DB, the scheduled job has previously run successfully and already created the next
        scheduled job and any corresponding metrics calculation jobs"""
        jobs_with_nonce = self.jobs_client.get_jobs(
            project_id=model.project_id,
            nonce=new_job.nonce,
            page=1,
            page_size=1,
            kinds=[JobKind.SCHEDULE_JOBS],
        )
        if len(jobs_with_nonce.records) > 0:
            raise ValueError(
                f"Job with nonce {new_job.nonce} already exists, meaning this scheduled job previously ran successfully. ",
            )


"""
    TLDR: This is a long explainer to say make sure the first/last metrics jobs aren't duplicated by the previous/next schedule job execution.

    Important notes:
       - The start timestamp of the first MetricsCalculation job is inclusive and equal to the start time specified in the job spec.
       - Each job has a 2 hour lookback period to calculate metrics over

    Example output for hourly jobs (cron="0 * * * *") starting from 2023-01-01 00:00:00:

    Jobs:
        MetricsCalculation Jobs:
            1. Start: 2022-12-31 22:00:00, End: 2023-01-01 00:00:00 (2hr lookback)
            2. Start: 2022-12-31 23:00:00, End: 2023-01-01 01:00:00 (2hr lookback)
            3. Start: 2023-01-01 00:00:00, End: 2023-01-01 02:00:00 (2hr lookback)

        ScheduleJobs Job:
            Start: 2023-01-01 02:00:00

    Execution of the last Schedule Jobs job generates:

    Jobs:
        MetricsCalculation Jobs:
            1. Start: 2023-01-01 01:00:00, End: 2023-01-01 03:00:00 (2hr lookback)
            2. Start: 2023-01-01 02:00:00, End: 2023-01-01 04:00:00 (2hr lookback)
            3. Start: 2023-01-01 03:00:00, End: 2023-01-01 05:00:00 (2hr lookback)
        ScheduleJobs Job:
            Start: 2023-01-01 05:00:00

    **In reality there's 5 metrics jobs per batch, same logic around timestamp relationships though
"""


def generate_next_job_series(
    start_timestamp: datetime,
    model_id: str,
    schedule: ModelMetricsSchedule,
    nonce: str,
    k: int = 5,
) -> list[PostJob]:
    cron = croniter.croniter(schedule.cron, start_timestamp)
    new_jobs = []
    for _ in range(k):
        end_ts = cron.get_next(datetime)
        start_ts = end_ts - timedelta(seconds=schedule.lookback_period_seconds)
        new_jobs.append(
            PostJob(
                kind=PostJobKind.METRICS_CALCULATION,
                job_spec=PostJobSpec(
                    MetricsCalculationJobSpec(
                        scope_model_id=model_id,
                        start_timestamp=start_ts,
                        end_timestamp=end_ts,
                    ),
                ),
                schedule_id=schedule.id,
                ready_at=end_ts,
            ),
        )

    new_jobs.append(
        PostJob(
            kind=PostJobKind.SCHEDULE_JOBS,
            job_spec=PostJobSpec(
                ScheduleJobsJobSpec(scope_model_id=model_id, start_timestamp=end_ts),
            ),
            ready_at=end_ts,
            nonce=hash_nonce(nonce),
            schedule_id=schedule.id,
        ),
    )

    return new_jobs
