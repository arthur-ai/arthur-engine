import logging
import signal
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from types import FrameType
from typing import Any, Dict

from arthur_client.api_bindings import (
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

from arthur_client_support import (
    DEQUEUE_DECLARES_DISCOVERY_SOURCE_TEST,
    TEST_DISCOVERY_SOURCE_SUPPORTED,
)
from health_check import MLEngineHealthCheck as HealthCheck
from job_runner import JobRunner, ProcessJobRunner, ThreadJobRunner
from memory_limits import ContainerMemory
from tools.platform_api_client import build_platform_api_client

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
        client = build_platform_api_client()
        self.jobs_client = JobsV1Api(client)
        users_client = UsersV1Api(client)
        dpid = users_client.get_users_me().data_plane_id
        if not dpid:
            raise Exception("Data plane ID cannot be None when dequeueing jobs.")
        self.data_plane_id = dpid
        # Read through the container's limit: psutil alone reports the host's memory,
        # which can be far more than the container is allowed to use.
        self.memory = ContainerMemory.detect()
        limit_mb = (
            "none"
            if self.memory.limit_bytes is None
            else self.memory.limit_bytes // (1024 * 1024)
        )
        logger.info(f"Memory limit MB: {limit_mb}, source: {self.memory.source}")
        # Subtract 400 MB to account for this agent process + some buffer, etc
        self.total_memory_mb = self.memory.available_mb() - 400
        # What the budget was before the container limit was read, used only while no
        # job is running so that no job admitted before becomes impossible to admit.
        self.host_total_memory_mb = self.memory.host_available_mb() - 400
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

        real_time_free = self.memory.available_mb()

        # Return the lower value as a safeguard
        # This accounts for cases where jobs may have exceeded their memory requests
        return max(min(calculated_available, real_time_free), 0)

    def _dequeue_memory_limit_mb(self) -> int:
        """Memory to offer the platform when asking for the next job.

        While no job is running, it is never less than the budget read from the host
        alone (the behaviour before the container limit was read). A job larger than
        the container's budget, e.g. a 1,500 MB job on a 2 GB container, is then still
        admitted, alone, as it was before, rather than left queued for good.
        """
        available = self.available_memory_mb()
        if self.running_jobs:
            return available
        host_only = min(self.host_total_memory_mb, self.memory.host_available_mb())
        return max(available, host_only)

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
                job_dequeue_parameters=self._dequeue_parameters(),
            )
            if job_run is not None:
                job = self._read_job(job_run)
                if job is not None:
                    self._start_job(job, job_run)
        except ApiException as e:
            logger.error(
                f"Failed to dequeue next job. Received status code, response: {e.status}, {e.body}",
            )

    def _dequeue_parameters(self) -> JobDequeueParameters:
        """What this engine can take, including whether it runs Test Connection jobs.

        `discovery_source_test` is sent only when the installed client both has the
        field and can run the job; otherwise the request is exactly what it was before
        the field existed. Built from a dict because the pinned client's model does
        not declare the field, and a keyword it does not know would not type-check.
        """
        params: dict[str, Any] = {"memory_limit_mb": self._dequeue_memory_limit_mb()}
        if TEST_DISCOVERY_SOURCE_SUPPORTED and DEQUEUE_DECLARES_DISCOVERY_SOURCE_TEST:
            params["discovery_source_test"] = True
        return JobDequeueParameters(**params)

    def _read_job(self, job_run: JobRun) -> Job | None:
        """The dequeued run's job, or None once a job this engine cannot read is failed.

        A job the installed arthur-client cannot deserialize -- in practice a job kind
        newer than this engine, whose spec matches none of the ones it knows -- raises a
        plain ValueError, not an ApiException. Left to propagate it would end the agent
        and strand every job it is running, so the one run is failed, with the reason
        in its log, and the agent carries on.
        """
        try:
            return self.jobs_client.get_job(job_run.job_id)
        except ApiException:
            raise
        except Exception as e:
            logger.error(
                f"Could not read job {job_run.job_id} (run {job_run.id}); failing it",
                exc_info=True,
            )
            self._fail_unreadable_job(job_run, e)
            return None

    def _fail_unreadable_job(self, job_run: JobRun, error: Exception) -> None:
        """Best effort: a failure to report is logged, never raised into the loop."""
        # The exception type only: the message of a deserialization failure echoes the
        # job's whole JSON body back.
        message = (
            f"This engine could not read the job ({type(error).__name__}). It is most "
            f"likely a job kind this engine version does not support; upgrade the "
            f"engine to run it."
        )
        try:
            self._post_job_log(message, job_run.job_id, job_run.id, JobLogLevel.ERROR)
        except Exception:
            logger.error(
                f"Failed to post the log for unreadable job {job_run.job_id}",
                exc_info=True,
            )
        try:
            self.jobs_client.put_job_state(
                job_run.job_id,
                job_run_id=job_run.id,
                put_job_state=PutJobState(job_state=JobState.FAILED),
            )
        except Exception:
            logger.error(
                f"Failed to mark unreadable job {job_run.job_id} as failed",
                exc_info=True,
            )

    def _start_job(self, job: Job, job_run: JobRun) -> None:
        if job.memory_requirements_mb > self.total_memory_mb:
            logger.warning(
                f"Job {job.id} requires {job.memory_requirements_mb} MB, more than this "
                f"engine's budget of {self.total_memory_mb} MB; running it alone. "
                f"Raise the container's memory limit to run it alongside other jobs.",
            )
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
            try:
                self.handle()
                self.check_running_jobs()
            except Exception:
                # One bad iteration must not end the agent: every job it is running
                # would stop reporting state until it was re-dequeued. Shutdown is
                # unaffected -- it is checked above, and a signal only sets a flag.
                logger.error(
                    "Unexpected error in the job agent loop; continuing",
                    exc_info=True,
                )
            self.health_check.liveness_ping()

            counter += 1
            if counter % 40 == 0:
                logger.info("Checking for jobs...")
            time.sleep(0.25)


if __name__ == "__main__":
    agent = JobAgent()
    agent.run()
