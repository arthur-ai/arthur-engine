"""What the job agent says about itself when it asks the Platform for work.

The Platform hands TEST_DISCOVERY_SOURCE jobs only to an engine whose last dequeue
declared `discovery_source_test=true`. The declaration must be made exactly when the
installed arthur-client can both send it and run the job, and never otherwise.
"""

import json

from arthur_client.api_bindings import User
from job_agent import JobAgent
from pytest_httpserver import HTTPServer

from arthur_client_support import (
    DEQUEUE_DECLARES_DISCOVERY_SOURCE_TEST,
    TEST_DISCOVERY_SOURCE_SUPPORTED,
)

DECLARES = DEQUEUE_DECLARES_DISCOVERY_SOURCE_TEST and TEST_DISCOVERY_SOURCE_SUPPORTED


def _dequeue_body(
    app_plane_http_server: HTTPServer,
    test_data_plane_user: User,
) -> dict:
    dequeue_url = f"/api/v1/data_planes/{test_data_plane_user.data_plane_id}/jobs/next"
    app_plane_http_server.expect_request(dequeue_url).respond_with_data(
        "Internal Server Error",
        status=500,
    )

    JobAgent().handle()

    [request] = [req for req, _ in app_plane_http_server.log if req.path == dequeue_url]
    body: dict = json.loads(request.data)
    return body


def test_the_dequeue_declares_test_connection_only_when_the_client_can(
    app_plane_http_server: HTTPServer,
    test_data_plane_user: User,
) -> None:
    body = _dequeue_body(app_plane_http_server, test_data_plane_user)

    assert "memory_limit_mb" in body
    if DECLARES:
        assert body["discovery_source_test"] is True
    else:
        # Exactly the request an engine sent before the field existed.
        assert "discovery_source_test" not in body
        assert set(body) == {"memory_limit_mb"}
