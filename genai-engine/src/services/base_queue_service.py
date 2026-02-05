import logging
import threading
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Generic, Hashable, Optional, Type, TypeVar

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

    def start(self) -> None:
        """Start executor and background thread."""
        logger.info(
            f"Starting {self.service_name} with {self.num_workers} workers",
        )

        # Create executor for job execution
        self.executor = ThreadPoolExecutor(max_workers=self.num_workers)

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

    def _submit_job(self, job: JobType, wait_time: float) -> None:
        """Submit a job to the executor after the wait time."""
        if self.shutdown_event.is_set():
            logger.warning(f"Skipping job due to shutdown")
            return

        if self.shutdown_event.wait(wait_time):
            return

        if not self.executor:
            logger.error(
                f"Cannot submit job: executor is not initialized",
            )
            return

        self.executor.submit(self._execute_job_wrapper, job)

    def _execute_job_wrapper(self, job: JobType) -> None:
        """Wrapper that tracks job execution and removes from active set when done."""
        job_key = self._get_job_key(job)
        try:
            self._execute_job(job)
        finally:
            with self.active_jobs_lock:
                self.active_jobs.discard(job_key)

    def enqueue(self, job: JobType) -> bool:
        """Schedule a job to be executed. Returns True if enqueued, False if already active."""
        job_key = self._get_job_key(job)

        # Check if job is already active
        with self.active_jobs_lock:
            if job_key in self.active_jobs:
                logger.debug(
                    f"Job with key {job_key} is already active, skipping enqueue",
                )
                return False
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
        self.executor.submit(self._submit_job, job, wait_time)
        return True

    @abstractmethod
    def _background_loop(self) -> None:
        """Background thread that runs continuously"""
        raise NotImplementedError

    @abstractmethod
    def _execute_job(self, job: JobType) -> None:
        """Execute a single job."""
        raise NotImplementedError
