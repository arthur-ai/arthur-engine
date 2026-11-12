import heapq
import itertools
import logging
import threading
import time
from abc import ABC, abstractmethod
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from typing import Any, Generic, Hashable, Optional, Type, TypeVar

logger = logging.getLogger(__name__)

JobType = TypeVar("JobType", bound="BaseQueueJob")


class BaseQueueJob:
    """Represents a registered agent polling job to be executed."""

    def __init__(
        self,
        delay_seconds: int = 10,
    ):
        self.enqueued_at = datetime.now()
        self.delay_seconds = delay_seconds
        self.execute_at = time.time() + delay_seconds
        # Set by a job that ran too early (e.g. its trace is still growing) to be
        # queued again this many seconds after it finishes and frees its key.
        self.requeue_in: Optional[float] = None

    def reschedule(self, delay_seconds: float) -> None:
        self.delay_seconds = delay_seconds  # type: ignore[assignment]
        self.execute_at = time.time() + delay_seconds
        self.requeue_in = None


class BaseQueueService(ABC, Generic[JobType]):
    """Service that manages async execution of jobs using ThreadPoolExecutor."""

    job_model: Type[JobType]
    service_name: str
    background_thread_name: str

    def __init__(
        self,
        num_workers: int = 4,
        override_execution_delay: Optional[int] = None,
    ):
        self.num_workers = num_workers
        self.background_thread: Optional[threading.Thread] = None
        self.executor: Optional[ThreadPoolExecutor] = None
        self.shutdown_event = threading.Event()
        self.override_execution_delay = override_execution_delay
        self.active_jobs_lock = threading.Lock()
        self.active_jobs: set[Hashable] = set()
        # Delayed jobs wait here, not in a pool thread: one scheduler thread hands
        # each to the pool when it is due, so a burst of delayed jobs (or an idle
        # window re-queue) never ties up the workers that run due jobs.
        self._delayed: list[tuple[float, int, JobType, Future[Any]]] = []
        self._delayed_cv = threading.Condition()
        self._delayed_seq = itertools.count()
        self.scheduler_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start executor and background thread."""
        logger.info(
            f"Starting {self.service_name} with {self.num_workers} workers",
        )

        # Create executor for job execution
        self.executor = ThreadPoolExecutor(max_workers=self.num_workers)

        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            name=f"{self.background_thread_name}-scheduler",
            daemon=True,
        )
        self.scheduler_thread.start()

        # Start background thread that checks for stale annotations
        self.background_thread = threading.Thread(
            target=self._background_loop,
            name=self.background_thread_name,
            daemon=True,
        )
        self.background_thread.start()

        logger.info(f"{self.service_name} started")

    def stop(self, timeout: int = 30) -> None:
        """Stop executor and background thread"""
        logger.info(f"Stopping {self.service_name}")
        self.shutdown_event.set()

        with self._delayed_cv:
            self._delayed_cv.notify_all()
            dropped = self._delayed
            self._delayed = []
        for _, _, job, future in dropped:
            future.cancel()
            with self.active_jobs_lock:
                self.active_jobs.discard(self._get_job_key(job))
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=timeout)

        if self.executor:
            self.executor.shutdown(wait=True, cancel_futures=True)

        if self.background_thread:
            self.background_thread.join(timeout=timeout)
            if self.background_thread.is_alive():
                logger.warning("Background thread did not shut down gracefully")

        logger.info(f"{self.service_name} stopped")

    @abstractmethod
    def _get_job_key(self, job: JobType) -> Hashable:
        """Get a hashable key for a job to prevent duplicate enqueueing."""
        raise NotImplementedError

    def _run_due_job(self, job: JobType) -> Any:
        """Run a job that is due, on the pool thread executing this call."""
        if self.shutdown_event.is_set():
            logger.warning(f"Skipping job due to shutdown")
            with self.active_jobs_lock:
                self.active_jobs.discard(self._get_job_key(job))
            return None
        return self._execute_job_wrapper(job)

    def _scheduler_loop(self) -> None:
        """Hand delayed jobs to the pool as they come due."""
        while not self.shutdown_event.is_set():
            due: list[tuple[JobType, Future[Any]]] = []
            with self._delayed_cv:
                if not self._delayed:
                    self._delayed_cv.wait()
                else:
                    wait = self._delayed[0][0] - time.time()
                    if wait > 0:
                        self._delayed_cv.wait(timeout=wait)
                now = time.time()
                while self._delayed and self._delayed[0][0] <= now:
                    _, _, job, future = heapq.heappop(self._delayed)
                    due.append((job, future))
            for job, future in due:
                self._submit_due(job, future)

    def _submit_due(self, job: JobType, outer: Future[Any]) -> None:
        """Submit a due job and pass its outcome to the future enqueue returned."""
        if not outer.set_running_or_notify_cancel():
            with self.active_jobs_lock:
                self.active_jobs.discard(self._get_job_key(job))
            return
        try:
            assert self.executor is not None
            inner = self.executor.submit(self._run_due_job, job)
        except Exception as e:
            logger.error(f"Failed to submit due job: {e}", exc_info=True)
            with self.active_jobs_lock:
                self.active_jobs.discard(self._get_job_key(job))
            outer.set_exception(e)
            return

        def relay(done: Future[Any]) -> None:
            if done.cancelled():
                outer.set_exception(RuntimeError("job cancelled at shutdown"))
            elif done.exception() is not None:
                outer.set_exception(done.exception())  # type: ignore[arg-type]
            else:
                outer.set_result(done.result())

        inner.add_done_callback(relay)

    def delayed_job_count(self) -> int:
        """How many jobs are waiting for their delay to pass."""
        with self._delayed_cv:
            return len(self._delayed)

    def _execute_job_wrapper(self, job: JobType) -> Any:
        """Wrapper that tracks job execution and removes from active set when done."""
        job_key = self._get_job_key(job)
        try:
            result = self._execute_job(job)
            return result
        finally:
            with self.active_jobs_lock:
                self.active_jobs.discard(job_key)
            if job.requeue_in is not None and not self.shutdown_event.is_set():
                job.reschedule(job.requeue_in)
                self.enqueue(job)

    def enqueue(self, job: JobType) -> tuple[bool, Optional[Future[Any]]]:
        """Schedule a job to be executed.

        Returns:
            Tuple of (was_enqueued: bool, future: Optional[Future[Any]])
            - was_enqueued: True if enqueued, False if already active
            - future: Future object if enqueued, None otherwise
        """
        job_key = self._get_job_key(job)

        try:
            # Check if job is already active
            with self.active_jobs_lock:
                if job_key in self.active_jobs:
                    logger.debug(
                        f"Job with key {job_key} is already active, skipping enqueue",
                    )
                    return False, None
                self.active_jobs.add(job_key)

            if self.override_execution_delay is not None:
                wait_time = (
                    job.execute_at - job.delay_seconds + self.override_execution_delay
                )
            else:
                wait_time = job.execute_at

            wait_time = max(0, wait_time - time.time())
            if not self.executor:
                logger.error(
                    f"Cannot submit job: executor is not initialized. Start the {self.service_name} first.",
                )
                # Remove from active jobs since we couldn't enqueue
                with self.active_jobs_lock:
                    self.active_jobs.discard(job_key)
                raise ValueError(
                    f"{self.service_name} is not initialized. Start the {self.service_name} first.",
                )

            if wait_time > 0:
                future: Future[Any] = Future()
                with self._delayed_cv:
                    heapq.heappush(
                        self._delayed,
                        (time.time() + wait_time, next(self._delayed_seq), job, future),
                    )
                    self._delayed_cv.notify()
            else:
                future = self.executor.submit(self._run_due_job, job)
        except Exception as e:
            # Executor might be shutting down or have other issues
            logger.error(
                f"Failed to submit job wrapper for {job_key}: {e}",
                exc_info=True,
            )
            with self.active_jobs_lock:
                self.active_jobs.discard(job_key)
            raise e

        return True, future

    @abstractmethod
    def _background_loop(self) -> None:
        """Background thread that runs continuously"""
        raise NotImplementedError

    @abstractmethod
    def _execute_job(self, job: JobType) -> Any:
        """Execute a single job. Subclasses may return a value (e.g., trace count)."""
        raise NotImplementedError
