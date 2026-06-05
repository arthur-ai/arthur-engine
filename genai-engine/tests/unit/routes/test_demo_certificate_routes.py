import io
import os
import uuid
from unittest.mock import patch

import pytest

from tests.clients.base_test_client import GenaiEngineTestClientBase

_VALID_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20


@pytest.mark.unit_tests
def test_upload_certificate_stores_and_returns_url(client: GenaiEngineTestClientBase):
    with patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "enabled"}):
        response = client.base_client.post(
            "/api/v2/demo/certificate",
            files={"file": ("certificate.png", io.BytesIO(_VALID_PNG), "image/png")},
        )

    assert response.status_code == 200
    body = response.json()
    assert "certificate_id" in body
    cert_id = body["certificate_id"]
    assert uuid.UUID(cert_id)  # valid UUID
    assert body["certificate_url"] == f"/api/v2/demo/certificate/{cert_id}"


@pytest.mark.unit_tests
def test_get_certificate_returns_png(client: GenaiEngineTestClientBase):
    with patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "enabled"}):
        upload = client.base_client.post(
            "/api/v2/demo/certificate",
            files={"file": ("certificate.png", io.BytesIO(_VALID_PNG), "image/png")},
        )
        assert upload.status_code == 200
        cert_id = upload.json()["certificate_id"]

        get = client.base_client.get(f"/api/v2/demo/certificate/{cert_id}")

    assert get.status_code == 200
    assert get.headers["content-type"] == "image/png"
    assert get.content == _VALID_PNG


@pytest.mark.unit_tests
def test_get_certificate_returns_404_for_unknown_id(client: GenaiEngineTestClientBase):
    with patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "enabled"}):
        response = client.base_client.get(f"/api/v2/demo/certificate/{uuid.uuid4()}")

    assert response.status_code == 404


@pytest.mark.unit_tests
def test_upload_certificate_returns_400_for_non_png(client: GenaiEngineTestClientBase):
    with patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "enabled"}):
        response = client.base_client.post(
            "/api/v2/demo/certificate",
            files={"file": ("cert.jpg", io.BytesIO(b"\xff\xd8\xff"), "image/jpeg")},
        )

    assert response.status_code == 400
    assert "PNG" in response.json()["detail"]


@pytest.mark.unit_tests
def test_upload_certificate_returns_413_when_too_large(client: GenaiEngineTestClientBase):
    with patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "enabled"}):
        response = client.base_client.post(
            "/api/v2/demo/certificate",
            files={"file": ("certificate.png", io.BytesIO(b"\x00" * (5 * 1024 * 1024 + 1)), "image/png")},
        )

    assert response.status_code == 413


@pytest.mark.unit_tests
def test_upload_certificate_returns_400_when_demo_mode_disabled(client: GenaiEngineTestClientBase):
    with patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "disabled"}, clear=False):
        response = client.base_client.post(
            "/api/v2/demo/certificate",
            files={"file": ("certificate.png", io.BytesIO(_VALID_PNG), "image/png")},
        )

    assert response.status_code == 400
    assert "Demo mode" in response.json()["detail"]
