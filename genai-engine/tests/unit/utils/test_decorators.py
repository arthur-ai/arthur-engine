import queue
import threading
import time

import pytest
from genai_engine.utils.decorators import with_lock


@pytest.mark.unit_tests
def test_with_lock_behavior():
    @with_lock("/tmp/test.lock")
    def test_func(q, delay):
        time.sleep(delay)
        q.put("test")

    # Create a queue to store results
    result_queue = queue.Queue()

    # Run the function in one thread with a delay
    thread_1 = threading.Thread(target=test_func, args=(result_queue, 5))
    thread_1.start()

    # Give the first thread a moment to acquire the lock
    time.sleep(1)

    # Run the function in another thread without delay
    thread_2 = threading.Thread(target=test_func, args=(result_queue, 0))
    thread_2.start()

    thread_1.join()
    thread_2.join()

    # Retrieve results from the queue
    result_1 = result_queue.get()
    result_2 = None
    if not result_queue.empty():
        result_2 = result_queue.get()

    assert result_1 == "test"
    assert result_2 is None
