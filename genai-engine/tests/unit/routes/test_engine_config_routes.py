import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from tests.clients.base_test_client import app


@pytest.mark.unit_tests
def test_engine_config_demo_mode_off_by_default():
    """FF returns false when GENAI_ENGINE_DEMO_MODE is not set."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("GENAI_ENGINE_DEMO_MODE", None)
        client = TestClient(app)
        response = client.get("/api/v2/engine-config")
    assert response.status_code == 200
    assert response.json() == {"demo_mode": False}


@pytest.mark.unit_tests
def test_engine_config_demo_mode_on_when_enabled():
    """FF returns true when GENAI_ENGINE_DEMO_MODE=ENABLED."""
    with patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "ENABLED"}):
        client = TestClient(app)
        response = client.get("/api/v2/engine-config")
    assert response.status_code == 200
    assert response.json() == {"demo_mode": True}


@pytest.mark.unit_tests
def test_engine_config_demo_mode_case_insensitive():
    """FF is case-insensitive — 'enabled' works same as 'ENABLED'."""
    with patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "enabled"}):
        client = TestClient(app)
        response = client.get("/api/v2/engine-config")
    assert response.status_code == 200
    assert response.json() == {"demo_mode": True}


@pytest.mark.unit_tests
def test_engine_config_demo_mode_off_when_disabled():
    """FF returns false when GENAI_ENGINE_DEMO_MODE=disabled."""
    with patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "disabled"}):
        client = TestClient(app)
        response = client.get("/api/v2/engine-config")
    assert response.status_code == 200
    assert response.json() == {"demo_mode": False}


@pytest.mark.unit_tests
def test_engine_config_no_auth_required():
    """Endpoint is accessible without any Authorization header."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("GENAI_ENGINE_DEMO_MODE", None)
        client = TestClient(app)
        response = client.get("/api/v2/engine-config")
    assert response.status_code == 200
