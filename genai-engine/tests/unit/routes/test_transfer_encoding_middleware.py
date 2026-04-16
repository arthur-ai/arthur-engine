import pytest
from fastapi.testclient import TestClient

from tests.clients.base_test_client import app


@pytest.fixture(scope="module")
def test_client() -> TestClient:
    return TestClient(app)


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
