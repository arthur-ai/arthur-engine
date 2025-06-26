import os
import sys
import time
from typing import Generator

import pytest
from arthur_client.api_bindings import User
from mock_data.mock_data_generator import (
    oidc_config,
    random_access_token,
    random_dataplane_user,
)
from pytest_httpserver import HTTPServer

os.environ["TZ"] = "UTC"
time.tzset()

# Add app to import path so `dependencies`,`server`, etc. can be imported as if they're local
sys.path.append("src/ml_engine")

from config import Config


@pytest.fixture()
def test_data_plane_user() -> User:
    return random_dataplane_user()


# Preserve environment variables and set appropriate ones for connecting to the mock
@pytest.fixture(scope="function")
def app_plane_http_server(
    httpserver: HTTPServer,
    test_data_plane_user: User,
) -> Generator[HTTPServer, None, None]:
    old_environ = dict(os.environ)

    base_url = "http://" + httpserver.host + ":" + str(httpserver.port)

    Config.settings.ARTHUR_API_HOST = base_url
    Config.settings.ARTHUR_CLIENT_ID = "123"
    Config.settings.ARTHUR_CLIENT_SECRET = "456"

    httpserver.expect_request(
        "/api/v1/auth/oidc/.well-known/openid-configuration",
    ).respond_with_data(oidc_config(base_url))
    httpserver.expect_request(
        "/realms/arthur/protocol/openid-connect/token",
    ).respond_with_data(random_access_token())
    httpserver.expect_request("/api/v1/users/me").respond_with_data(
        test_data_plane_user.model_dump_json(),
        content_type="application/json",
    )

    yield httpserver

    # Restore environment variables for other tests in the process
    os.environ.clear()
    os.environ.update(old_environ)
