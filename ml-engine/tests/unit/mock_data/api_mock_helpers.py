import json
import multiprocessing

from arthur_client.api_bindings import (
    Dataset,
    HealthStatus,
    Job,
    JobRun,
    Model,
    PutJobState,
    TaskConnectionInfo,
)
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


def expect_health_request(
    app_plane_http_server: HTTPServer,
    health_status: HealthStatus | None,
) -> RequestMatcher:
    """Stubs the platform version probe. A None health_status makes it unreachable."""
    handler = app_plane_http_server.expect_request("/api/health")
    if health_status is None:
        handler.respond_with_response(Response(status=500))
    else:
        handler.respond_with_data(
            health_status.model_dump_json(),
            content_type="application/json",
        )
    return handler.matcher


def expect_post_connector_dataset(
    app_plane_http_server: HTTPServer,
    connector_id: str,
    dataset_response: Dataset,
) -> RequestMatcher:
    """One dataset creation. Register once per dataset the engine should create."""
    handler = app_plane_http_server.expect_oneshot_request(
        f"/api/v1/connectors/{connector_id}/datasets",
        method="POST",
    )
    handler.respond_with_data(
        dataset_response.model_dump_json(),
        content_type="application/json",
    )
    return handler.matcher


def expect_delete_dataset(
    app_plane_http_server: HTTPServer,
    dataset_id: str,
) -> RequestMatcher:
    handler = app_plane_http_server.expect_request(
        f"/api/v1/datasets/{dataset_id}",
        method="DELETE",
    )
    handler.respond_with_response(Response(status=204))
    return handler.matcher


def expect_post_model(
    app_plane_http_server: HTTPServer,
    project_id: str,
    model_response: Model,
) -> RequestMatcher:
    handler = app_plane_http_server.expect_oneshot_request(
        f"/api/v1/projects/{project_id}/models",
        method="POST",
    )
    handler.respond_with_data(
        model_response.model_dump_json(),
        content_type="application/json",
    )
    return handler.matcher


def expect_post_model_rejection(
    app_plane_http_server: HTTPServer,
    project_id: str,
    detail: str,
) -> RequestMatcher:
    """A model creation the platform refuses, in the shape scope returns errors in."""
    handler = app_plane_http_server.expect_oneshot_request(
        f"/api/v1/projects/{project_id}/models",
        method="POST",
    )
    handler.respond_with_json({"detail": detail}, status=400)
    return handler.matcher


def expect_put_task_connection_info(
    app_plane_http_server: HTTPServer,
    model_id: str,
    task_connection_info: TaskConnectionInfo,
) -> RequestMatcher:
    handler = app_plane_http_server.expect_request(
        f"/api/v1/models/{model_id}/task/connection_info",
        method="PUT",
    )
    handler.respond_with_data(
        task_connection_info.model_dump_json(),
        content_type="application/json",
    )
    return handler.matcher
