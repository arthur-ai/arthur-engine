"""What the job agent says about itself when it asks the Platform for work.

The Platform hands TEST_DISCOVERY_SOURCE jobs only to an engine whose last dequeue
declared `discovery_source_test=true`, and ONBOARDING_ANALYSIS jobs only to one that
declared `onboarding_analysis=true`. Each declaration must be made exactly when the
installed arthur-client can both send it and run the job, and never otherwise.
"""

import json
from typing import Optional

import pytest
from arthur_client.api_bindings import JobDequeueParameters, User
from pytest_httpserver import HTTPServer

import job_agent
from arthur_client_support import (
    DEQUEUE_DECLARES_DISCOVERY_SOURCE_TEST,
    DEQUEUE_DECLARES_ONBOARDING_ANALYSIS,
    ONBOARDING_ANALYSIS_SUPPORTED,
    TEST_DISCOVERY_SOURCE_SUPPORTED,
)
from job_agent import JobAgent

DECLARES = DEQUEUE_DECLARES_DISCOVERY_SOURCE_TEST and TEST_DISCOVERY_SOURCE_SUPPORTED
DECLARES_ONBOARDING = (
    DEQUEUE_DECLARES_ONBOARDING_ANALYSIS and ONBOARDING_ANALYSIS_SUPPORTED
)


class _DequeueParametersWithOnboarding(JobDequeueParameters):
    onboarding_analysis: Optional[bool] = None


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


def test_the_dequeue_declares_onboarding_analysis_only_when_the_client_can(
    app_plane_http_server: HTTPServer,
    test_data_plane_user: User,
) -> None:
    body = _dequeue_body(app_plane_http_server, test_data_plane_user)

    if DECLARES_ONBOARDING:
        assert body["onboarding_analysis"] is True
    else:
        assert "onboarding_analysis" not in body


def test_the_dequeue_declares_onboarding_analysis_when_the_client_can(
    app_plane_http_server: HTTPServer,
    test_data_plane_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # No published client has the field yet: stand in one that has it.
    monkeypatch.setattr(job_agent, "ONBOARDING_ANALYSIS_SUPPORTED", True)
    monkeypatch.setattr(job_agent, "DEQUEUE_DECLARES_ONBOARDING_ANALYSIS", True)
    monkeypatch.setattr(
        job_agent, "JobDequeueParameters", _DequeueParametersWithOnboarding
    )

    body = _dequeue_body(app_plane_http_server, test_data_plane_user)

    assert body["onboarding_analysis"] is True


def test_a_client_without_either_field_sends_the_old_request(
    app_plane_http_server: HTTPServer,
    test_data_plane_user: User,
) -> None:
    body = _dequeue_body(app_plane_http_server, test_data_plane_user)

    if not DECLARES and not DECLARES_ONBOARDING:
        # Exactly the request an engine sent before either field existed.
        assert set(body) == {"memory_limit_mb"}
