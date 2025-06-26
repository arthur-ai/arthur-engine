import json
import multiprocessing
import time
from unittest.mock import patch

from arthur_client.api_bindings import JobKind, JobRun, JobState, PutJobState, User
from job_agent import JobAgent
from mock_data.api_mock_helpers import expect_post_job_logs, expect_put_job_state
from pytest_httpserver import HTTPServer

ctx = multiprocessing.get_context("spawn")
from mock_data.mock_data_generator import random_job_job_run


def mock_process_job_executor_execute(job_run: JobRun) -> None:
    time.sleep(5)


def mock_thread_job_executor_execute(job_run: JobRun, thread_result_holder) -> None:
    time.sleep(0.1)
    thread_result_holder.terminal_job_state = JobState.COMPLETED


def test_termination(app_plane_http_server: HTTPServer, test_data_plane_user: User):
    job_agent = JobAgent(shutdown_grace_period_seconds=0.5)
    job_agent.data_plane_id = test_data_plane_user.data_plane_id
    job_agent.total_memory_mb = 1000

    with patch(
        "job_runner.ProcessJobRunner._job_executor_wrapper",
        mock_process_job_executor_execute,
    ), patch(
        "job_runner.ThreadJobRunner._job_executor_wrapper",
        side_effect=mock_thread_job_executor_execute,
    ):
        metrics_job, metrics_job_run = random_job_job_run()
        metrics_job.kind = JobKind.METRICS_CALCULATION
        metrics_job.memory_requirements_mb = 100
        job_agent._start_job(metrics_job, metrics_job_run)

        connector_job, connector_job_run = random_job_job_run()
        connector_job.kind = JobKind.CONNECTOR_CHECK
        job_agent._start_job(connector_job, connector_job_run)

        job_agent.shutting_down = True

        # Job 1 should be forcibly killed and ask for the current job state, then PUT the failed state.
        # Job 2 should finish on its own during the grace period
        job_url = f"/api/v1/jobs/{metrics_job.id}"
        app_plane_http_server.expect_oneshot_request(job_url).respond_with_data(
            json.dumps(metrics_job.to_dict(), default=str),
            content_type="application/json",
        )

        put_connector_job_state_matcher = expect_put_job_state(
            app_plane_http_server,
            connector_job.id,
            connector_job_run.id,
            put_job_state_body=PutJobState(job_state=JobState.COMPLETED),
            job_response=connector_job,
        )
        put_metrics_job_state_matcher = expect_put_job_state(
            app_plane_http_server,
            metrics_job.id,
            metrics_job_run.id,
            put_job_state_body=PutJobState(job_state=JobState.FAILED),
            job_response=metrics_job,
        )

        post_job_logs_matcher = expect_post_job_logs(
            app_plane_http_server,
            metrics_job.id,
            metrics_job_run.id,
        )

        job_agent.run()

        app_plane_http_server.assert_request_made(
            put_metrics_job_state_matcher,
            count=1,
        )
        app_plane_http_server.assert_request_made(
            put_connector_job_state_matcher,
            count=1,
        )
        app_plane_http_server.assert_request_made(post_job_logs_matcher, count=1)
