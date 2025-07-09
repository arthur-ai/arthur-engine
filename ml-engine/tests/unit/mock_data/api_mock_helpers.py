import json
import multiprocessing

from arthur_client.api_bindings import Job, JobRun, PutJobState
from pytest_httpserver import HTTPServer, RequestMatcher
from werkzeug import Response

ctx = multiprocessing.get_context("spawn")


def expect_dequeue_job_request(
    app_plane_http_server: HTTPServer,
    data_plane_id: str,
    job_run_response: JobRun,
) -> RequestMatcher:
    dequeue_url = f"/api/v1/data_planes/{data_plane_id}/jobs/next"
    handler = app_plane_http_server.expect_oneshot_request(dequeue_url)
    handler.respond_with_data(
        json.dumps(job_run_response.to_dict(), default=str),
        content_type="application/json",
    )
    return handler.matcher


def expect_get_job_request(
    app_plane_http_server: HTTPServer,
    job_id: str,
    job_response: Job,
) -> RequestMatcher:
    job_url = f"/api/v1/jobs/{job_id}"
    handler = app_plane_http_server.expect_oneshot_request(job_url)
    handler.respond_with_data(
        json.dumps(job_response.to_dict(), default=str),
        content_type="application/json",
    )
    return handler.matcher


def expect_post_job_logs(
    app_plane_http_server: HTTPServer,
    job_id: str,
    job_run_id: str,
) -> RequestMatcher:
    job_url = f"/api/v1/jobs/{job_id}/runs/{job_run_id}/logs"
    handler = app_plane_http_server.expect_oneshot_request(job_url, method="POST")
    handler.respond_with_response(Response(status=204))
    return handler.matcher


def expect_put_job_state(
    app_plane_http_server: HTTPServer,
    job_id: str,
    job_run_id: str | None,
    put_job_state_body: PutJobState,
    job_response: Job,
) -> RequestMatcher:
    put_job_state_url = f"/api/v1/jobs/{job_id}/state"
    handler = app_plane_http_server.expect_oneshot_request(
        put_job_state_url,
        query_string=f"job_run_id={job_run_id}" if job_run_id else None,
        data=json.dumps(put_job_state_body.to_dict(), default=str),
    )
    handler.respond_with_data(
        json.dumps(job_response.to_dict(), default=str),
        content_type="application/json",
    )
    return handler.matcher
