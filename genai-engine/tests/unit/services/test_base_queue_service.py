from typing import Hashable
from unittest.mock import patch

import pytest

from services.base_queue_service import BaseQueueJob, BaseQueueService


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


def test_enqueue_submits_job_with_delay_and_waits(service):
    """Test that enqueue passes the correct wait_time to _submit_job, and _submit_job waits that duration."""
    delay_seconds = 5
    job = BaseQueueJob(delay_seconds=delay_seconds)

    # Capture the args enqueue passes to _submit_job, without actually running it async
    with patch.object(service.executor, "submit") as mock_executor_submit:
        service.enqueue(job)

    # enqueue calls executor.submit(_submit_job, job, wait_time)
    _, enqueued_job, wait_time = mock_executor_submit.call_args.args
    assert 0 < wait_time <= delay_seconds

    # Now call _submit_job directly with that wait_time and assert it waits on it
    with patch.object(service.shutdown_event, "wait", return_value=False) as mock_wait:
        with patch.object(service.executor, "submit"):
            service._submit_job(enqueued_job, wait_time)

    mock_wait.assert_called_once_with(wait_time)
