import tomllib
from collections.abc import Iterator
from pathlib import Path

import pytest
from arthur_client.api_bindings import ApiClient, Configuration
from arthur_client.api_bindings.exceptions import ApiException
from pytest_httpserver import HTTPServer

import tools.engine_version as engine_version_module
from job_agent import JobAgent
from job_executor import JobExecutor
from tools.engine_version import (
    ENGINE_VERSION_HEADER,
    VERSION_FILE,
    engine_version,
    set_engine_version_header,
)

PYPROJECT = Path(__file__).parents[3] / "pyproject.toml"


@pytest.fixture(autouse=True)
def clear_version_cache() -> Iterator[None]:
    engine_version.cache_clear()
    yield
    engine_version.cache_clear()


@pytest.fixture
def client() -> Iterator[ApiClient]:
    # An explicit Configuration keeps ApiClient from caching a process-global default.
    with ApiClient(Configuration()) as api_client:
        yield api_client


def test_version_file_matches_pyproject() -> None:
    # The version file is what ships in the image; version-workflow.yml bumps it
    # in the same commit as pyproject, so the two must never disagree.
    with PYPROJECT.open("rb") as f:
        pyproject_version = tomllib.load(f)["project"]["version"]
    assert VERSION_FILE.is_file()
    assert engine_version() == pyproject_version


def test_set_engine_version_header(client: ApiClient) -> None:
    # The control plane treats an absent header as an engine predating dataset
    # consolidation, so every client this engine builds must announce itself.
    set_engine_version_header(client)
    assert client.default_headers[ENGINE_VERSION_HEADER] == engine_version()


def test_agent_and_executor_send_header(app_plane_http_server: HTTPServer) -> None:
    # Checks the header on real requests, not just client config.
    assert engine_version() is not None
    JobAgent()

    model_path = "/api/v1/models/00000000-0000-0000-0000-000000000000"
    app_plane_http_server.expect_request(model_path).respond_with_data(status=404)
    with pytest.raises(ApiException):
        JobExecutor().models_client.get_model(model_path.rsplit("/", 1)[1])

    for path in ("/api/v1/users/me", model_path):
        requests = [r for r, _ in app_plane_http_server.log if r.path == path]
        assert requests, path
        for request in requests:
            assert request.headers.get(ENGINE_VERSION_HEADER) == engine_version()


def test_unreadable_version_sends_no_header(
    client: ApiClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # An unparseable value is a state the contract doesn't define; absent is legacy.
    monkeypatch.setattr(engine_version_module, "VERSION_FILE", tmp_path / "missing")
    assert engine_version() is None
    set_engine_version_header(client)
    assert ENGINE_VERSION_HEADER not in client.default_headers
