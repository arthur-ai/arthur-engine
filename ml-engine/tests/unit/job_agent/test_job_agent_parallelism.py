import sys
import time
from unittest.mock import patch

from arthur_client.api_bindings import Job, JobRun, JobState, PutJobState, User
from job_agent import JobAgent
from mock_data.api_mock_helpers import (
    expect_dequeue_job_request,
    expect_get_job_request,
    expect_post_job_logs,
    expect_put_job_state,
)
from mock_data.mock_data_generator import random_job_job_run
from pytest_httpserver import HTTPServer, RequestMatcher


def mock_process_job_executor_execute_failure(job_run: JobRun) -> None:
    time.sleep(0.1)
    sys.exit(1)


def mock_process_job_executor_execute(job_run: JobRun) -> None:
    time.sleep(0.1)


def mock_thread_job_executor_execute(job_run: JobRun, thread_result_holder) -> None:
    time.sleep(0.1)
    thread_result_holder.terminal_job_state = JobState.COMPLETED
    thread_result_holder.exit_code = 0


def test_handle(app_plane_http_server: HTTPServer, test_data_plane_user: User):
    job_agent = JobAgent()
    job_agent.data_plane_id = test_data_plane_user.data_plane_id
    job_agent.total_memory_mb = 1000
    job, job_run = random_job_job_run(test_data_plane_user.data_plane_id)

    dequeue_job_matcher = expect_dequeue_job_request(
        app_plane_http_server,
        test_data_plane_user.data_plane_id,
        job_run,
    )
    get_job_matcher = expect_get_job_request(app_plane_http_server, job.id, job)
    post_job_logs_matcher = expect_post_job_logs(
        app_plane_http_server,
        job.id,
        job_run.id,
    )
    put_job_state_matcher = expect_put_job_state(
        app_plane_http_server,
        job.id,
        job_run.id,
        put_job_state_body=PutJobState(job_state=JobState.COMPLETED),
        job_response=job,
    )

    with patch(
        "job_runner.ProcessJobRunner._job_executor_wrapper",
        side_effect=mock_process_job_executor_execute,
    ), patch(
        "job_runner.ThreadJobRunner._job_executor_wrapper",
        side_effect=mock_thread_job_executor_execute,
    ):
        job_agent.handle()

        assert len(job_agent.running_jobs) == 1
        assert job_agent.available_memory_mb() == 960

        # Test that the job is removed from running_jobs when it's done
        time.sleep(0.15)
        job_agent.check_running_jobs()

        assert len(job_agent.running_jobs) == 0

    app_plane_http_server.assert_request_made(dequeue_job_matcher, count=1)
    app_plane_http_server.assert_request_made(get_job_matcher, count=1)
    app_plane_http_server.assert_request_made(
        post_job_logs_matcher,
        count=1,
    )  # logs with exit code posted
    app_plane_http_server.assert_request_made(put_job_state_matcher, count=1)


def test_dequeue_multiple_jobs(
    app_plane_http_server: HTTPServer,
    test_data_plane_user: User,
):
    job_agent = JobAgent()
    job_agent.data_plane_id = test_data_plane_user.data_plane_id
    job_agent.total_memory_mb = 1000
    job_runs: list[JobRun] = []
    jobs: list[Job] = []
    get_job_matchers: list[RequestMatcher] = []
    put_job_state_matchers: list[RequestMatcher] = []

    for _ in range(3):
        job, job_run = random_job_job_run()
        job_runs.append(job_run)
        jobs.append(job)

    dequeue_matcher = expect_dequeue_job_request(
        app_plane_http_server,
        test_data_plane_user.data_plane_id,
        job_runs[0],
    )
    for job_run in job_runs[1:]:
        expect_dequeue_job_request(
            app_plane_http_server,
            test_data_plane_user.data_plane_id,
            job_run,
        )

    for job in jobs:
        get_job_matchers.append(
            expect_get_job_request(app_plane_http_server, job.id, job),
        )
        put_job_state_matchers.append(
            expect_put_job_state(
                app_plane_http_server,
                job.id,
                None,
                put_job_state_body=PutJobState(job_state=JobState.COMPLETED),
                job_response=job,
            ),
        )

    with patch(
        "job_runner.ProcessJobRunner._job_executor_wrapper",
        side_effect=mock_process_job_executor_execute,
    ), patch(
        "job_runner.ThreadJobRunner._job_executor_wrapper",
        side_effect=mock_thread_job_executor_execute,
    ):
        for i in range(3):
            job_agent.handle()
            assert len(job_agent.running_jobs) == i + 1
            assert job_agent.available_memory_mb() == 1000 - (40 * (i + 1))

        # Verify that all jobs are running
        assert len(job_agent.running_jobs) == 3

        # Allow some time for jobs to complete
        time.sleep(0.15)

        # Check that jobs are removed when completed
        job_agent.check_running_jobs()
        assert len(job_agent.running_jobs) == 0

    app_plane_http_server.assert_request_made(dequeue_matcher, count=3)
    for matcher in get_job_matchers:
        app_plane_http_server.assert_request_made(matcher, count=1)
    for matcher in put_job_state_matchers:
        app_plane_http_server.assert_request_made(matcher, count=1)


def test_handle_process_failure(
    app_plane_http_server: HTTPServer,
    test_data_plane_user: User,
):
    job_agent = JobAgent()
    job_agent.data_plane_id = test_data_plane_user.data_plane_id
    job_agent.total_memory_mb = 10000
    job, job_run = random_job_job_run(test_data_plane_user.data_plane_id)

    job.memory_requirements_mb = 5000

    dequeue_job_matcher = expect_dequeue_job_request(
        app_plane_http_server,
        test_data_plane_user.data_plane_id,
        job_run,
    )
    get_job_matcher = expect_get_job_request(app_plane_http_server, job.id, job)
    post_job_logs_matcher = expect_post_job_logs(
        app_plane_http_server,
        job.id,
        job_run.id,
    )
    put_job_state_matcher = expect_put_job_state(
        app_plane_http_server,
        job.id,
        job_run.id,
        put_job_state_body=PutJobState(job_state=JobState.FAILED),
        job_response=job,
    )

    with patch(
        "job_runner.ProcessJobRunner._job_executor_wrapper",
        mock_process_job_executor_execute_failure,
    ):
        job_agent.handle()

        assert len(job_agent.running_jobs) == 1

        # The exact time it takes for the process to spawn, execute, and exit varies by platform, give it 10 seconds max
        start_time = time.time()
        while time.time() - start_time < 10 and len(job_agent.running_jobs) > 0:
            time.sleep(0.1)
            job_agent.check_running_jobs()

        job_agent.check_running_jobs()

        assert len(job_agent.running_jobs) == 0

    app_plane_http_server.assert_request_made(dequeue_job_matcher, count=1)
    app_plane_http_server.assert_request_made(get_job_matcher, count=1)
    app_plane_http_server.assert_request_made(
        post_job_logs_matcher,
        count=1,
    )  # logs with exit code posted
    app_plane_http_server.assert_request_made(put_job_state_matcher, count=1)
