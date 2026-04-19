import logging
from datetime import datetime, timedelta, timezone

from arthur_client.api_bindings import (
    CompliancePolicyCheckJobSpec,
    Job,
    JobKind,
    JobsV1Api,
    Model,
    ModelsV1Api,
    PatchJob,
    PoliciesV1Api,
    PostJob,
    PostJobBatch,
    PostJobKind,
    PostJobSpec,
    ScheduleComplianceJobsJobSpec,
)
from arthur_client.api_bindings.exceptions import NotFoundException
from arthur_common.tools.functions import hash_nonce

COMPLIANCE_CHECK_INTERVAL = timedelta(hours=24)


class ScheduleComplianceJobsExecutor:
    def __init__(
        self,
        models_client: ModelsV1Api,
        jobs_client: JobsV1Api,
        policies_client: PoliciesV1Api,
        logger: logging.Logger,
    ):
        self.models_client = models_client
        self.jobs_client = jobs_client
        self.policies_client = policies_client
        self.logger = logger

    def execute(self, job: Job, job_spec: ScheduleComplianceJobsJobSpec) -> None:
        try:
            model = self.models_client.get_model(job_spec.scope_model_id)
        except NotFoundException:
            self._stop_job_retries(job=job)
            raise ValueError(
                f"Model {job_spec.scope_model_id} no longer exists. Stopping this scheduled series of jobs.",
            )

        try:
            self._validate_job(job)
            self._validate_schedule_id(model, job)
            self._validate_model_has_assignments(model, job)
        except ValueError as e:
            self._handle_validation_failure(job, e)

        new_jobs = generate_next_compliance_job_series(
            model_id=job_spec.scope_model_id,
            nonce=job.nonce,
            schedule_id=job.schedule_id,
        )
        new_schedule_job = [
            j for j in new_jobs if j.kind == PostJobKind.SCHEDULE_COMPLIANCE_JOBS
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
        self.logger.error("Validation error. Stopping this scheduled series of jobs.")
        self._stop_job_retries(job=job)
        raise exc

    def _stop_job_retries(self, job: Job) -> Job:
        """
        Updates the job to set max_attempts equal to the current attempt so it doesn't
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
    def _validate_job(job: Job) -> None:
        if not job.schedule_id:
            raise ValueError("Schedule id must be defined for scheduled jobs.")
        if not job.nonce:
            raise ValueError("Nonce expected for this job type.")

    def _validate_schedule_id(self, model: Model, job: Job) -> None:
        """Stop the chain if the model's compliance_schedule_id doesn't match."""
        model_schedule_id = model.compliance_schedule_id
        if model_schedule_id != job.schedule_id:
            raise ValueError(
                f"Model {model.id} has compliance_schedule_id={model_schedule_id} "
                f"but job has schedule_id={job.schedule_id}. "
                "This chain is orphaned; stopping.",
            )

    def _validate_model_has_assignments(self, model: Model, job: Job) -> None:
        """Stop the schedule chain if the model no longer has any policy assignments."""
        assignments = self.policies_client.list_model_policy_assignments(
            model_id=model.id, page=1, page_size=1
        )
        if assignments.pagination.total_records == 0:
            raise ValueError(
                f"Model {model.id} has no policy assignments. "
                "Schedule was removed; stopping this chain.",
            )

    def _validate_new_schedule_job(self, model: Model, new_job: PostJob) -> None:
        """Validates schedule job nonce is unique before submission to protect against race condition."""
        jobs_with_nonce = self.jobs_client.get_jobs(
            project_id=model.project_id,
            nonce=new_job.nonce,
            page=1,
            page_size=1,
            kinds=[JobKind.SCHEDULE_COMPLIANCE_JOBS],
        )
        if len(jobs_with_nonce.records) > 0:
            raise ValueError(
                f"Job with nonce {new_job.nonce} already exists, meaning this scheduled job previously ran successfully. ",
            )


def generate_next_compliance_job_series(
    model_id: str,
    nonce: str,
    schedule_id: str,
    k: int = 3,
) -> list[PostJob]:
    now = datetime.now(timezone.utc)
    new_jobs = []

    for i in range(1, k + 1):
        run_at = now + COMPLIANCE_CHECK_INTERVAL * i
        new_jobs.append(
            PostJob(
                kind=PostJobKind.COMPLIANCE_POLICY_CHECK,
                job_spec=PostJobSpec(
                    CompliancePolicyCheckJobSpec(
                        scope_model_id=model_id,
                        policy_assignment_id=None,
                    ),
                ),
                ready_at=run_at,
                schedule_id=schedule_id,
            ),
        )

    new_jobs.append(
        PostJob(
            kind=PostJobKind.SCHEDULE_COMPLIANCE_JOBS,
            job_spec=PostJobSpec(
                ScheduleComplianceJobsJobSpec(scope_model_id=model_id),
            ),
            ready_at=now + COMPLIANCE_CHECK_INTERVAL * k,
            nonce=hash_nonce(nonce),
            schedule_id=schedule_id,
        ),
    )

    return new_jobs
