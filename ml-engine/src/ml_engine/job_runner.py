import logging
import multiprocessing
import sys
import time
from threading import Thread
from typing import Optional, Protocol

from arthur_client.api_bindings import Job, JobRun, JobState

from job_executor import JobExecutor

logger = logging.getLogger()

runner_not_started_error_string = "Runner not started."


class JobRunner(Protocol):
    def exitcode(self) -> Optional[int]: ...

    def start(self) -> None: ...

    def is_alive(self) -> bool: ...

    def join(self) -> JobState: ...

    def kill(self) -> None: ...


class ProcessJobRunner:
    def __init__(self, job: Job, job_run: JobRun):
        self.job_run = job_run
        self.job = job

        ctx = multiprocessing.get_context("spawn")
        self.runner = ctx.Process(
            target=self._job_executor_wrapper,
            args=(self.job_run,),
        )

    def exitcode(self) -> Optional[int]:
        # return shell exit code instead of python subprocess exit code:
        # https://tldp.org/LDP/abs/html/exitcodes.html
        if self.runner.exitcode is not None and self.runner.exitcode < 0:
            # https://docs.python.org/3/library/multiprocessing.html#multiprocessing.Process.exitcode -
            # if the exitcode is negative, that means the process was terminated by a signal, so the
            # equivalent shell exit code is as follows
            return 128 + abs(self.runner.exitcode)
        return self.runner.exitcode

    def start(self) -> None:
        self.runner.start()

    def is_alive(self) -> bool:
        return self.runner.is_alive()

    def join(self) -> JobState:
        if self.is_alive():
            raise ValueError("Cannot call join on a running job runner.")
        self.runner.join()
        logger.info(
            f"Process {self.runner.pid} exited with code {self.runner.exitcode}",
        )
        if self.runner.exitcode == 0:
            return JobState.COMPLETED
        else:
            return JobState.FAILED

    def kill(self) -> None:
        try:
            self.runner.kill()
            start_time = time.time()
            while self.runner.is_alive() and time.time() - start_time < 5:
                time.sleep(0.1)
            if self.runner.is_alive():
                logger.warning(
                    f"Process {self.runner.pid} did not terminate within 5 seconds after kill signal.",
                )
        except Exception as e:
            logger.warning(f"Failed to kill process {self.runner.pid} with error: {e}")

    @staticmethod
    def _job_executor_wrapper(job_run: JobRun) -> None:
        try:
            result = JobExecutor().execute(job_run)
        except Exception as e:
            logger.error(
                "Unexpected exception executing job %s - %s",
                job_run.job_id,
                e,
            )
            result = JobState.FAILED

        if result == JobState.COMPLETED:
            sys.exit(0)
        else:
            sys.exit(1)


class ThreadJobRunner:
    class _ResultHolder:
        def __init__(self) -> None:
            self.terminal_job_state: JobState | None = None
            self.exit_code: int | None = None

    def __init__(self, job: Job, job_run: JobRun):
        self.job_run = job_run
        self.job = job
        self.thread_result_holder = self._ResultHolder()
        # IMPORTANT mark jobs as daemons so in case the main agent thread exits,
        # these don't prevent the process from exiting, so the container can be restarted
        # https://stackoverflow.com/questions/190010/daemon-threads-explanation/190017#190017
        self.runner = Thread(
            target=self._job_executor_wrapper,
            args=(
                self.job_run,
                self.thread_result_holder,
            ),
            daemon=True,
        )

    def exitcode(self) -> Optional[int]:
        return self.thread_result_holder.exit_code

    def start(self) -> None:
        self.runner.start()

    def is_alive(self) -> bool:
        return self.runner.is_alive()

    def join(self) -> JobState:
        if self.is_alive():
            raise ValueError("Cannot call join on a running job runner.")
        self.runner.join()
        result = self.thread_result_holder.terminal_job_state
        if result is None:
            raise ValueError("Job runner did not set terminal job state.")
        return result

    def kill(self) -> None:
        # Threads cannot be killed, they will exit on their own
        pass

    @staticmethod
    def _job_executor_wrapper(
        job_run: JobRun,
        thread_result_holder: _ResultHolder,
    ) -> None:
        try:
            result = JobExecutor().execute(job_run)
        except Exception as e:
            logger.error(
                "Unexpected exception executing job %s - %s",
                job_run.job_id,
                e,
            )
            result = JobState.FAILED

        thread_result_holder.terminal_job_state = result

        if result == JobState.COMPLETED:
            thread_result_holder.exit_code = 0
        else:
            thread_result_holder.exit_code = 1
