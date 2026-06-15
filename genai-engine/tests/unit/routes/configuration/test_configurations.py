import os
import re
from unittest.mock import patch

import pytest

from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
)
from utils import utils


@pytest.mark.unit_tests
def test_trace_retention_days_config(client: GenaiEngineTestClientBase):
    """GET config returns default trace_retention_days (90); POST can update it."""
    headers = {"Authorization": "Bearer admin_0"}
    get_resp = client.get_configs(headers=headers)
    assert get_resp.status_code == 200
    configs = get_resp.json()
    assert "trace_retention_days" in configs
    assert configs["trace_retention_days"] == 90

    update_resp = client.update_configs(
        {"trace_retention_days": 30},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["trace_retention_days"] == 30

    get_resp2 = client.get_configs(headers=headers)
    assert get_resp2.status_code == 200
    assert get_resp2.json()["trace_retention_days"] == 30

    # Invalid value is rejected
    invalid_resp = client.update_configs(
        {"trace_retention_days": 99},
        headers=headers,
    )
    assert invalid_resp.status_code == 400


@pytest.mark.unit_tests
def test_version_read_env_var_not_present():
    version = utils.get_genai_engine_version()
    semver_regex = r"^\d+\.\d+\.\d+$"
    assert (
        re.match(semver_regex, version) is not None
    ), "Version is not a valid semantic version"


@pytest.mark.unit_tests
def test_display_settings_scope_url_absent(client: GenaiEngineTestClientBase):
    """scope_url is None when SCOPE_FE_INGRESS_URI is not set."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("SCOPE_FE_INGRESS_URI", None)
        response = client.base_client.get("/api/v2/display-settings")
    assert response.status_code == 200
    assert response.json()["scope_url"] is None


@pytest.mark.unit_tests
def test_display_settings_scope_url_empty_string(client: GenaiEngineTestClientBase):
    """scope_url is None when SCOPE_FE_INGRESS_URI is set to empty string."""
    with patch.dict(os.environ, {"SCOPE_FE_INGRESS_URI": ""}):
        response = client.base_client.get("/api/v2/display-settings")
    assert response.status_code == 200
    assert response.json()["scope_url"] is None


@pytest.mark.unit_tests
def test_display_settings_scope_url_https(client: GenaiEngineTestClientBase):
    """scope_url is returned when SCOPE_FE_INGRESS_URI is a valid https URL."""
    with patch.dict(
        os.environ,
        {"SCOPE_FE_INGRESS_URI": "https://platform.example.com"},
    ):
        response = client.base_client.get("/api/v2/display-settings")
    assert response.status_code == 200
    assert response.json()["scope_url"] == "https://platform.example.com"


@pytest.mark.unit_tests
def test_display_settings_scope_url_non_https_rejected(
    client: GenaiEngineTestClientBase,
):
    """scope_url is None when SCOPE_FE_INGRESS_URI is not https."""
    with patch.dict(
        os.environ,
        {"SCOPE_FE_INGRESS_URI": "http://platform.example.com"},
    ):
        response = client.base_client.get("/api/v2/display-settings")
    assert response.status_code == 200
    assert response.json()["scope_url"] is None
