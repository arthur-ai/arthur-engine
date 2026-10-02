import json
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

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


def _unknown_kind_job_run(
    app_plane_http_server: HTTPServer,
    test_data_plane_user: User,
) -> tuple[JobRun, dict]:
    """A dequeued run whose job is a kind this engine's arthur-client cannot parse."""
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

    return job_run, job_d


def test_unknown_job_spec_error(
    app_plane_http_server: HTTPServer,
    test_data_plane_user: User,
):
    job_run, job_d = _unknown_kind_job_run(app_plane_http_server, test_data_plane_user)

    # mock call to update job state
    job_update_state_url = f"/api/v1/jobs/{job_run.job_id}/state"
    app_plane_http_server.expect_request(
        job_update_state_url,
        method="PUT",
    ).respond_with_json(job_d)

    # mock call to write job log
    add_job_logs_url = f"/api/v1/jobs/{job_run.job_id}/runs/{job_run.id}/logs"
    app_plane_http_server.expect_request(add_job_logs_url).respond_with_data(status=204)

    agent = JobAgent()
    agent.handle()

    # Test above doesn't throw, and the run is failed rather than started
    assert agent.running_jobs == {}
    app_plane_http_server.assert_request_made(
        RequestMatcher(
            f"/api/v1/data_planes/{test_data_plane_user.data_plane_id}/jobs/next"
        ),
    )
    app_plane_http_server.assert_request_made(
        RequestMatcher(f"/api/v1/jobs/{job_run.job_id}"),
    )
    app_plane_http_server.assert_request_made(
        RequestMatcher(
            job_update_state_url,
            method="PUT",
            query_string=f"job_run_id={job_run.id}",
            json={"job_state": JobState.FAILED.value},
        ),
    )
    log_requests = [
        req for req, _ in app_plane_http_server.log if req.path == add_job_logs_url
    ]
    assert len(log_requests) == 1
    [log] = json.loads(log_requests[0].data)["logs"]
    assert log["log_level"] == "error"
    assert "does not support" in log["log"]
    assert "upgrade the engine" in log["log"]
    # The deserializer's message echoes the job body; only its type is reported.
    assert "new_job_kind" not in log["log"]


def test_unknown_job_spec_error_survives_failing_to_report_it(
    app_plane_http_server: HTTPServer,
    test_data_plane_user: User,
):
    job_run, _ = _unknown_kind_job_run(app_plane_http_server, test_data_plane_user)
    app_plane_http_server.expect_request(
        f"/api/v1/jobs/{job_run.job_id}/state",
    ).respond_with_data("Internal Server Error", status=500)
    app_plane_http_server.expect_request(
        f"/api/v1/jobs/{job_run.job_id}/runs/{job_run.id}/logs",
    ).respond_with_data("Internal Server Error", status=500)

    agent = JobAgent()
    agent.handle()

    assert agent.running_jobs == {}


def test_reporting_an_unreadable_job_never_raises(
    app_plane_http_server: HTTPServer,
    test_data_plane_user: User,
):
    """Not only an ApiException: nothing that goes wrong while reporting escapes."""
    agent = JobAgent()
    agent.jobs_client = MagicMock()
    agent.jobs_client.get_job.side_effect = ValueError("No match found")
    agent.jobs_client.post_job_logs.side_effect = RuntimeError("log route down")
    agent.jobs_client.put_job_state.side_effect = RuntimeError("state route down")
    job_run = JobRun(
        id=str(uuid.uuid4()),
        job_id=str(uuid.uuid4()),
        state=JobState.RUNNING,
        job_attempt=1,
        start_timestamp=datetime.now(timezone.utc),
    )
    agent.jobs_client.post_dequeue_job.return_value = job_run

    agent.handle()

    agent.jobs_client.put_job_state.assert_called_once()
    args, kwargs = agent.jobs_client.put_job_state.call_args
    assert args == (job_run.job_id,)
    assert kwargs["job_run_id"] == job_run.id
    assert kwargs["put_job_state"].job_state == JobState.FAILED
    agent.jobs_client.post_job_logs.assert_called_once()
    assert agent.running_jobs == {}


def test_run_survives_an_unexpected_error_in_one_iteration(
    app_plane_http_server: HTTPServer,
    test_data_plane_user: User,
    monkeypatch: pytest.MonkeyPatch,
):
    agent = JobAgent()
    monkeypatch.setattr(agent.health_check, "start_server", lambda: None)
    monkeypatch.setattr("job_agent.time.sleep", lambda _s: None)
    calls = {"handle": 0}

    def handle() -> None:
        calls["handle"] += 1
        if calls["handle"] == 1:
            raise RuntimeError("boom")
        # The loop came round again; stop it the way SIGTERM does.
        agent.shutting_down = True

    monkeypatch.setattr(agent, "handle", handle)
    monkeypatch.setattr(agent, "_terminate_fail_running_jobs", lambda: None)

    agent.run()

    assert calls["handle"] == 2
