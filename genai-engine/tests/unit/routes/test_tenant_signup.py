"""POST /api/v2/tenant/signup — public tenant signup (UP-4430).

End-to-end through the FastAPI TestClient: the tests register the route,
exercise the real DB transaction, and cross-check that the returned bearer
token actually authenticates as a TENANT-USER against /users/me with
org_scope populated to the new org.

Error-path tests (retry, double-collision, rollback) still go through the
TestClient, but monkeypatch the repository class the route module imports
to simulate failure modes that are hard to trigger through the real DB.
"""

import os
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from tests.clients.base_test_client import app

SIGNUP_URL = "/api/v2/tenant/signup"
ME_URL = "/users/me"


def _count_demo_orgs() -> int:
    """Count organizations whose name starts with `demo-`. Used by the
    rollback test to verify no orphan org leaked into the DB."""
    from db_models import DatabaseOrganization
    from tests.clients.base_test_client import override_get_db_session

    db = override_get_db_session()
    return (
        db.query(DatabaseOrganization)
        .filter(DatabaseOrganization.name.like("demo-%"))
        .count()
    )


@pytest.mark.unit_tests
def test_signup_demo_mode_off_returns_404():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("GENAI_ENGINE_DEMO_MODE", None)
        client = TestClient(app)
        response = client.post(SIGNUP_URL)
    assert response.status_code == 404


@pytest.mark.unit_tests
def test_signup_demo_mode_on_returns_four_field_response():
    """Anonymous POST with the flag on returns the documented shape."""
    with patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "ENABLED"}):
        client = TestClient(app)
        response = client.post(SIGNUP_URL)

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"org_id", "task_id", "task_name", "api_key"}
    # org + task share the same `demo-<8 hex chars>` name
    assert body["task_name"].startswith("demo-")
    assert len(body["task_name"]) == len("demo-") + 8
    uuid.UUID(body["org_id"])  # parseable UUID
    assert body["api_key"]


@pytest.mark.unit_tests
def test_signup_no_auth_required():
    """Endpoint accepts calls with no Authorization header."""
    with patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "ENABLED"}):
        client = TestClient(app)
        response = client.post(SIGNUP_URL, headers={})
    assert response.status_code == 200


@pytest.mark.unit_tests
def test_signup_returned_key_authenticates_as_tenant():
    """The bearer token from signup, used against /users/me, returns
    org_scope and TENANT-USER — proving the key is fully wired to the
    new org."""
    with patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "ENABLED"}):
        client = TestClient(app)
        sig = client.post(SIGNUP_URL).json()
        me_resp = client.get(
            ME_URL,
            headers={"Authorization": f"Bearer {sig['api_key']}"},
        )

    assert me_resp.status_code == 200
    me = me_resp.json()
    assert "TENANT-USER" in me["roles"]
    assert me["org_scope"] == sig["org_id"]
    assert me["org"]["id"] == sig["org_id"]
    # org + task name match — same demo-<hex>
    assert me["org"]["name"] == sig["task_name"]


@pytest.mark.unit_tests
def test_signup_each_call_mints_distinct_org():
    """Two consecutive signups produce independent (org, task, key) triples."""
    with patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "ENABLED"}):
        client = TestClient(app)
        a = client.post(SIGNUP_URL).json()
        b = client.post(SIGNUP_URL).json()

    assert a["org_id"] != b["org_id"]
    assert a["task_id"] != b["task_id"]
    assert a["api_key"] != b["api_key"]


# --- Error-path tests ----------------------------------------------------
# These still go through the real TestClient, but monkeypatch the repository
# the route module imports so we can deterministically simulate failure
# modes that are otherwise hard to trigger through the real DB.


@pytest.mark.unit_tests
def test_signup_retries_once_on_org_name_collision(monkeypatch):
    """First create_organization raises IntegrityError; the retry succeeds."""
    from routers.v2 import tenant_signup_routes as mod

    real_cls = mod.OrganizationsRepository
    calls = {"n": 0}

    class FlakyOrgRepo:
        def __init__(self, db_session):
            self._inner = real_cls(db_session)

        def create_organization(self, **kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                raise IntegrityError(
                    "INSERT", {}, Exception("simulated unique violation")
                )
            return self._inner.create_organization(**kwargs)

    with patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "ENABLED"}):
        monkeypatch.setattr(mod, "OrganizationsRepository", FlakyOrgRepo)
        client = TestClient(app)
        response = client.post(SIGNUP_URL)

    assert response.status_code == 200
    assert calls["n"] == 2


@pytest.mark.unit_tests
def test_signup_returns_500_after_two_collisions(monkeypatch):
    """Both create_organization attempts raise IntegrityError → handler 500s."""
    from routers.v2 import tenant_signup_routes as mod

    calls = {"n": 0}

    class AlwaysFlakyOrgRepo:
        def __init__(self, db_session):
            pass

        def create_organization(self, **kwargs):
            calls["n"] += 1
            raise IntegrityError("INSERT", {}, Exception("simulated unique violation"))

    with patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "ENABLED"}):
        monkeypatch.setattr(mod, "OrganizationsRepository", AlwaysFlakyOrgRepo)
        client = TestClient(app)
        response = client.post(SIGNUP_URL)

    assert response.status_code == 500
    assert calls["n"] == 2


@pytest.mark.unit_tests
def test_signup_rolls_back_org_when_api_key_step_fails(monkeypatch):
    """If api_key creation fails after the org has been flushed, no orphan
    org persists in the DB — the whole transaction rolls back."""
    from routers.v2 import tenant_signup_routes as mod

    class BrokenApiKeyRepo:
        def __init__(self, db_session):
            pass

        def create_api_key(self, **kwargs):
            raise RuntimeError("simulated api key failure")

    before = _count_demo_orgs()
    with patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "ENABLED"}):
        monkeypatch.setattr(mod, "ApiKeyRepository", BrokenApiKeyRepo)
        client = TestClient(app)
        response = client.post(SIGNUP_URL)
    after = _count_demo_orgs()

    assert response.status_code == 500
    # rollback worked: no new demo-* org leaked into the DB
    assert after == before
