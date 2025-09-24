import logging
import signal
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from types import FrameType
from typing import Dict

import psutil
from arthur_client.api_bindings import (
    ApiClient,
    Job,
    JobDequeueParameters,
    JobLog,
    JobLogLevel,
    JobLogs,
    JobRun,
    JobState,
    JobsV1Api,
    PutJobState,
    UsersV1Api,
)
from arthur_client.api_bindings.exceptions import ApiException
from arthur_client.auth import (
    ArthurClientCredentialsAPISession,
    ArthurOAuthSessionAPIConfiguration,
    ArthurOIDCMetadata,
)
from config import Config
from health_check import MLEngineHealthCheck as HealthCheck
from job_runner import JobRunner, ProcessJobRunner, ThreadJobRunner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


@dataclass
class RunningJob:
    job_id: str
    runner: JobRunner
    memory_requirements: int
    job_run: JobRun


class JobAgent:
    def __init__(self, shutdown_grace_period_seconds: int = 15) -> None:
        sess = ArthurClientCredentialsAPISession(
            client_id=Config.settings.ARTHUR_CLIENT_ID,
            client_secret=Config.settings.ARTHUR_CLIENT_SECRET,
            metadata=ArthurOIDCMetadata(arthur_host=Config.settings.ARTHUR_API_HOST),
            verify=Config.settings.KEYCLOAK_SSL_VERIFY,
        )
        client = ApiClient(
            configuration=ArthurOAuthSessionAPIConfiguration(
                session=sess,
                verify_ssl=Config.settings.KEYCLOAK_SSL_VERIFY,
            ),
        )
        self.jobs_client = JobsV1Api(client)
        users_client = UsersV1Api(client)
        dpid = users_client.get_users_me().data_plane_id
        if not dpid:
            raise Exception("Data plane ID cannot be None when dequeueing jobs.")
        self.data_plane_id = dpid
        # Subtract 400 MB to account for this agent process + some buffer, etc
        self.total_memory_mb = psutil.virtual_memory().available // (1024 * 1024) - 400
        logger.info(f"Total memory MB: {self.total_memory_mb}")
        self.running_jobs: Dict[str, RunningJob] = {}
        self.shutting_down = False
        self.shutdown_grace_period_seconds = shutdown_grace_period_seconds
        self.health_check: HealthCheck = HealthCheck()

    def allocated_memory_mb(self) -> int:
        used_memory = sum(job.memory_requirements for job in self.running_jobs.values())
        return used_memory

    def available_memory_mb(self) -> int:
        calculated_available = self.total_memory_mb - self.allocated_memory_mb()

        real_time_free = psutil.virtual_memory().available // (1024 * 1024)

        # Return the lower value as a safeguard
        # This accounts for cases where jobs may have exceeded their memory requests
        return min(calculated_available, real_time_free)

    def _log_job_exit_code(self, job_id: str, runner: JobRunner) -> None:
        exit_code = runner.exitcode()
        self._post_job_log(
            message=f"Job exited with exit code {exit_code}",
            job_id=job_id,
            job_run_id=self.running_jobs[job_id].job_run.id,
            log_level=JobLogLevel.INFO if exit_code == 0 else JobLogLevel.ERROR,
        )

    def _handle_job_completed(self, job_id: str) -> None:
        if job_id in self.running_jobs:
            runner = self.running_jobs[job_id].runner
            self._log_job_exit_code(job_id, runner)
            # update job state
            try:
                job_state = runner.join()
            except ValueError as e:
                logger.error("Could not join completed job %s - %s", job_id, e)
                job_state = JobState.FAILED
            try:
                self.jobs_client.put_job_state(
                    job_id,
                    job_run_id=self.running_jobs[job_id].job_run.id,
                    put_job_state=PutJobState(job_state=job_state),
                )
            except ApiException as e:
                logger.error(
                    f"Failed to set the state of job {job_id} to {job_state}. Leaving the job in running_jobs and will try again. {str(e)}",
                )
            del self.running_jobs[job_id]

    def handle(self) -> None:
        if self.shutting_down:
            return
        try:
            job_run = self.jobs_client.post_dequeue_job(
                self.data_plane_id,
                job_dequeue_parameters=JobDequeueParameters(
                    memory_limit_mb=self.available_memory_mb(),
                ),
            )
            if job_run is not None:
                job = self.jobs_client.get_job(job_run.job_id)
                self._start_job(job, job_run)
        except ApiException as e:
            logger.error(
                f"Failed to dequeue next job. Received status code, response: {e.status}, {e.body}",
            )

    def _start_job(self, job: Job, job_run: JobRun) -> None:
        runner: JobRunner | None = None
        if job.memory_requirements_mb <= 50:
            runner = ThreadJobRunner(job, job_run)
        else:
            runner = ProcessJobRunner(job, job_run)
        runner.start()
        self.running_jobs[job.id] = RunningJob(
            job_id=job_run.job_id,
            runner=runner,
            memory_requirements=job.memory_requirements_mb,
            job_run=job_run,
        )

    def check_running_jobs(self) -> None:
        finished_jobs: list[str] = []
        for job_id, running_job in self.running_jobs.items():
            if not running_job.runner.is_alive():
                finished_jobs.append(job_id)

        for job_id in finished_jobs:
            self._handle_job_completed(job_id)

        running_job_count = len(self.running_jobs)
        if running_job_count > 0:
            logger.info(
                f"Running jobs: {running_job_count}, Total used memory: {self.allocated_memory_mb()} MB",
            )

    def _signal_handler(self, signum: int, _: FrameType | None) -> None:
        match signum:
            case signal.SIGTERM:
                logger.info("Received SIGTERM, initiating graceful shutdown...")
            case _:
                logger.warning(
                    f"Received unexpected signal {signum}, initiating graceful shutdown...",
                )
        self.shutting_down = True

    def _report_fail_for_jobs(self, jobs_to_fail: list[str]) -> None:
        for job_id in jobs_to_fail:
            logger.info(f"Failing job {job_id}...")
            try:
                self.jobs_client.put_job_state(
                    job_id,
                    job_run_id=self.running_jobs[job_id].job_run.id,
                    put_job_state=PutJobState(job_state=JobState.FAILED),
                )
                self._post_job_log(
                    f"Job {job_id} stopped due to hardware preemption event",
                    job_id,
                    self.running_jobs[job_id].job_run.id,
                    JobLogLevel.ERROR,
                )
                logger.info(f"Failed job {job_id}...")
            except ApiException as e:
                logger.error(
                    f"Unable to mark job {job_id} as failed. Since we're shutting down, don't have a choice but to leave it in the running state: {str(e)}",
                )

    def _terminate_fail_running_jobs(self) -> None:
        logger.info("Performing cleanup...")
        logger.info(f"Running job count: {len(self.running_jobs)}")

        # Give some time for the lightweight threads to finish their jobs and drain. Potentially the processes to exit on their own too.
        # Break early if all jobs finish before the end of the grace period.
        timeout = datetime.now() + timedelta(seconds=self.shutdown_grace_period_seconds)
        while datetime.now() < timeout:
            if not any(job.runner.is_alive() for job in self.running_jobs.values()):
                break
            time.sleep(0.25)

        # Gather any results that have been completed during the grace period and report their results
        self.check_running_jobs()
        jobs_to_fail: list[str] = []

        for job_id, running_job in self.running_jobs.items():
            logger.warning(
                f"Job {job_id} did not conclude in time, forcefully terminating (if applicable) and failing...",
            )
            jobs_to_fail.append(job_id)
            running_job.runner.kill()

        self._report_fail_for_jobs(jobs_to_fail)
        logger.info("Cleanup completed.")

    def _post_job_log(
        self,
        message: str,
        job_id: str,
        job_run_id: str,
        log_level: JobLogLevel,
    ) -> None:
        log = JobLog(
            log_level=log_level,
            log=message,
            log_timestamp=datetime.now(),
        )
        try:
            self.jobs_client.post_job_logs(job_id, job_run_id, JobLogs(logs=[log]))
        except ApiException as exc:
            logger.error("Failed to export log")
            logger.error(str(exc), exc_info=True)

    def run(self) -> None:
        # Register signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        self.health_check.start_server()

        counter = 0
        while True:
            if self.shutting_down:
                self._terminate_fail_running_jobs()
                return
            self.handle()
            self.check_running_jobs()
            self.health_check.liveness_ping()

            counter += 1
            if counter % 40 == 0:
                logger.info("Checking for jobs...")
            time.sleep(0.25)


if __name__ == "__main__":
    agent = JobAgent()
    agent.run()
