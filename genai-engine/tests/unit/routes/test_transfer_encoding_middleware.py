from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from server import TransferEncodingMiddleware, get_test_app
from tests.clients.base_test_client import app

_minimal_app = FastAPI()
_minimal_app.add_middleware(TransferEncodingMiddleware)


@_minimal_app.delete("/resource", status_code=204)
async def delete_resource() -> None:
    return None


@pytest.fixture(scope="module")
def test_client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="module")
def minimal_client() -> TestClient:
    return TestClient(_minimal_app)


@pytest.mark.unit_tests
def test_transfer_encoding_middleware_on_200(test_client: TestClient):
    resp = test_client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("transfer-encoding") == "chunked"
    assert "content-length" not in resp.headers


@pytest.mark.unit_tests
def test_transfer_encoding_middleware_on_error_response(test_client: TestClient):
    resp = test_client.get("/api/v1/traces", params={"task_ids": "some-task"})
    assert resp.status_code in (401, 403)
    assert resp.headers.get("transfer-encoding") == "chunked"
    assert "content-length" not in resp.headers


@pytest.mark.unit_tests
def test_transfer_encoding_middleware_skipped_on_204(minimal_client: TestClient):
    resp = minimal_client.delete("/resource")
    assert resp.status_code == 204
    assert "transfer-encoding" not in resp.headers


@pytest.mark.unit_tests
def test_transfer_encoding_middleware_disabled_on_200():
    with patch("server.is_transfer_encoding_middleware_enabled", return_value=False):
        client = TestClient(get_test_app())
        resp = client.get("/health")
        assert resp.status_code == 200
        assert "transfer-encoding" not in resp.headers


@pytest.mark.unit_tests
def test_transfer_encoding_middleware_disabled_on_error_response():
    with patch("server.is_transfer_encoding_middleware_enabled", return_value=False):
        client = TestClient(get_test_app())
        resp = client.get("/api/v1/traces", params={"task_ids": "some-task"})
        assert resp.status_code >= 400
        assert "transfer-encoding" not in resp.headers
