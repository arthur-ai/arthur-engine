import threading
import time
from typing import Hashable
from unittest.mock import patch

import pytest

from services.base_queue_service import BaseQueueJob, BaseQueueService
from services.continuous_eval import (
    get_continuous_eval_queue_service,
    initialize_continuous_eval_queue_service,
)


class TestQueueService(BaseQueueService[BaseQueueJob]):
    """Minimal concrete subclass of BaseQueueService used only for unit testing the base class behavior."""

    job_model = BaseQueueJob
    service_name = "test_queue_service"
    background_thread_name = "test-queue-background"

    def _get_job_key(self, job: BaseQueueJob) -> Hashable:
        return id(job)

    def _background_loop(self) -> None:
        self.shutdown_event.wait()

    def _execute_job(self, job: BaseQueueJob) -> None:
        pass


@pytest.fixture
def service():
    svc = TestQueueService(num_workers=2)
    svc.start()
    yield svc
    svc.stop(timeout=5)


class RecordingQueueService(TestQueueService):
    """Records when each job ran, relative to when the test started."""

    def __init__(self, num_workers: int):
        super().__init__(num_workers=num_workers)
        self.started = time.monotonic()
        self.ran_at: dict[str, float] = {}

    def _get_job_key(self, job: BaseQueueJob) -> Hashable:
        return job.name  # type: ignore[attr-defined]

    def _execute_job(self, job: BaseQueueJob) -> str:
        self.ran_at[job.name] = time.monotonic() - self.started  # type: ignore[attr-defined]
        return job.name  # type: ignore[attr-defined]


def _job(name: str, delay_seconds: float) -> BaseQueueJob:
    job = BaseQueueJob(delay_seconds=delay_seconds)  # type: ignore[arg-type]
    job.name = name  # type: ignore[attr-defined]
    return job


@pytest.mark.unit_tests
def test_a_delayed_job_does_not_hold_a_worker():
    """One worker, a job delayed 1.5 s, then a job due now: the due job runs at
    once instead of waiting behind the delayed one's sleep."""
    svc = RecordingQueueService(num_workers=1)
    svc.start()
    try:
        _, delayed = svc.enqueue(_job("delayed", 1.5))
        _, due = svc.enqueue(_job("due", 0))
        assert due.result(timeout=5) == "due"
        assert svc.ran_at["due"] < 0.5
        assert svc.delayed_job_count() == 1
        assert delayed.result(timeout=5) == "delayed"
        assert svc.ran_at["delayed"] >= 1.5
    finally:
        svc.stop(timeout=5)


@pytest.mark.unit_tests
def test_delayed_jobs_run_in_due_order_and_release_their_key():
    svc = RecordingQueueService(num_workers=2)
    svc.start()
    try:
        futures = [
            svc.enqueue(_job(name, delay))[1]
            for name, delay in (("c", 0.6), ("a", 0.2), ("b", 0.4))
        ]
        for future in futures:
            future.result(timeout=5)
        assert sorted(svc.ran_at, key=svc.ran_at.get) == ["a", "b", "c"]
        # Once run, the same key can be queued again.
        assert svc.enqueue(_job("a", 0))[0] is True
    finally:
        svc.stop(timeout=5)


@pytest.mark.unit_tests
def test_a_queued_key_is_not_queued_twice_and_stop_drops_delayed_jobs():
    svc = RecordingQueueService(num_workers=1)
    svc.start()
    enqueued, future = svc.enqueue(_job("later", 30))
    assert enqueued is True
    assert svc.enqueue(_job("later", 0)) == (False, None)
    svc.stop(timeout=5)
    assert future.cancelled()
    assert "later" not in svc.active_jobs
    assert "later" not in svc.ran_at


def _fail_the_second_thread_start():
    """Patches Thread.start so the scheduler thread starts and the background
    thread does not, as when the process can't create another thread."""
    real_start = threading.Thread.start
    started = []

    def start(thread: threading.Thread) -> None:
        if started:
            raise RuntimeError("can't start new thread")
        started.append(thread)
        real_start(thread)

    return patch.object(threading.Thread, "start", start)


@pytest.mark.unit_tests
def test_stop_after_a_start_that_failed_part_way():
    svc = TestQueueService(num_workers=1)
    with _fail_the_second_thread_start(), pytest.raises(RuntimeError):
        svc.start()
    assert svc.scheduler_thread is not None and svc.scheduler_thread.is_alive()

    # The background thread never started; stop() must not try to join it.
    svc.stop(timeout=5)
    assert not svc.scheduler_thread.is_alive()


@pytest.mark.unit_tests
def test_a_failed_start_leaves_no_continuous_eval_service_behind():
    with _fail_the_second_thread_start(), pytest.raises(RuntimeError):
        initialize_continuous_eval_queue_service(num_workers=1)
    assert get_continuous_eval_queue_service() is None
    assert not any(
        thread.name.startswith("continuous-eval-background")
        for thread in threading.enumerate()
    )
