import uuid
from datetime import datetime, timezone

import pytest
from arthur_client.api_bindings import JobRun, JobState, User
from job_agent import JobAgent
from pytest_httpserver import HTTPServer, RequestMatcher


def test_500_error(app_plane_http_server: HTTPServer, test_data_plane_user: User):
    dequeue_url = f"/api/v1/data_planes/{test_data_plane_user.data_plane_id}/jobs/next"
    app_plane_http_server.expect_request(dequeue_url).respond_with_data(
        "Internal Server Error",
        status=500,
    )

    agent = JobAgent()
    agent.handle()

    # Test above doesn't throw and 500 request was still made
    app_plane_http_server.assert_request_made(
        RequestMatcher(
            f"/api/v1/data_planes/{test_data_plane_user.data_plane_id}/jobs/next",
        ),
    )


@pytest.mark.skip(reason="Skipping unknown job spec error test, TODO: fixup later")
def test_unknown_job_spec_error(
    app_plane_http_server: HTTPServer,
    test_data_plane_user: User,
):
    job_run = JobRun(
        id=str(uuid.uuid4()),
        job_id=str(uuid.uuid4()),
        state=JobState.RUNNING,
        job_attempt=1,
        start_timestamp=datetime.now(timezone.utc),
    )
    # mock call to dequeue job run
    dequeue_url = f"/api/v1/data_planes/{test_data_plane_user.data_plane_id}/jobs/next"
    app_plane_http_server.expect_request(dequeue_url).respond_with_data(
        job_run.model_dump_json(),
        status=200,
        content_type="application/json",
    )

    job_d = {
        "id": job_run.job_id,
        "kind": "new_job_kind",
        "job_spec": {
            "job_type": "new_job_kind",
            "connector_id": "55f1a724-7528-4462-92e4-ad9b24aabae9",
        },
        "state": "running",
        "project_id": "fd891213-3761-4184-a547-ddfa1d53940e",
        "data_plane_id": test_data_plane_user.data_plane_id,
        "queued_at": "2025-05-28T19:46:53.237328Z",
        "ready_at": "2025-05-28T19:46:53.237333Z",
        "started_at": "2025-05-28T19:46:53.237333Z",
        "trigger_type": "user",
        "attempts": 0,
        "max_attempts": 1,
        "memory_requirements_mb": 50,
        "job_priority": 100,
    }

    # mock call to get job, can't use object as need to use unknown job spec
    job_url = f"/api/v1/jobs/{job_run.job_id}"
    app_plane_http_server.expect_request(job_url).respond_with_json(
        job_d,
    )

    # mock call to update job state
    job_update_state_url = f"/api/v1/jobs/{job_run.job_id}/state"
    app_plane_http_server.expect_request(job_update_state_url).respond_with_json(
        job_d,
    )

    # mock call to write job log
    add_job_logs_url = f"/api/v1/jobs/{job_run.job_id}/runs/{job_run.id}/logs"
    app_plane_http_server.expect_request(add_job_logs_url).respond_with_data(status=204)

    agent = JobAgent()
    agent.handle()

    # Test above doesn't throw
    app_plane_http_server.assert_request_made(RequestMatcher(dequeue_url))
    app_plane_http_server.assert_request_made(RequestMatcher(job_url))
    app_plane_http_server.assert_request_made(RequestMatcher(job_update_state_url))
    app_plane_http_server.assert_request_made(RequestMatcher(add_job_logs_url))
