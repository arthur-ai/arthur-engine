import os
from unittest.mock import patch

import pytest
from tests.clients.base_test_client import MASTER_API_KEY, GenaiEngineTestClientBase


@pytest.fixture()
def disable_master_key_general_usage(monkeypatch):
    with patch.dict(os.environ):
        envvars = {
            "ALLOW_ADMIN_KEY_GENERAL_ACCESS": "disabled",
        }
        for k, v in envvars.items():
            monkeypatch.setenv(k, v)
        yield


@pytest.mark.unit_tests
def test_allow_admin_key_general_access_disabled(
    disable_master_key_general_usage,
    client: GenaiEngineTestClientBase,
):
    client.authorized_user_api_key_headers = {
        "Authorization": "Bearer %s" % MASTER_API_KEY,
    }
    status_code, _ = client.get_default_rules()
    assert status_code == 403


@pytest.mark.unit_tests
def test_allow_admin_key_general_access_enabled(client: GenaiEngineTestClientBase):
    client.authorized_user_api_key_headers = {
        "Authorization": "Bearer %s" % MASTER_API_KEY,
    }
    status_code, _ = client.get_default_rules()
    assert status_code == 200
