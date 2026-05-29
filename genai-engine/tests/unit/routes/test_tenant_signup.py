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

from db_models import DatabaseOrganization
from db_models.onboarding_models import DatabaseOnboardingSubmission
from tests.clients.base_test_client import (
    GenaiEngineTestClientBase,
    app,
    override_get_db_session,
)

SIGNUP_URL = "/api/v2/tenant/signup"
ME_URL = "/users/me"

SAMPLE_SIGNUP_BODY = {
    "form_variant": "linear",
    "form_data": {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": "ada@example.com",
        "job_title": "Engineer",
        "company": "Analytical Engines",
        "maturity": "exploring",
        "brings": "evals",
        "brings_other": "",
        "competitors": ["langsmith"],
        "competitor_other": "",
        "attribution": "search",
        "attribution_other": "",
    },
}


@pytest.fixture(autouse=True)
def _disable_recaptcha_by_default(monkeypatch):
    """Keep reCAPTCHA unconfigured for every test in this module so the
    fail-open signup paths are deterministic regardless of the developer's
    local ``.env`` (which may carry real reCAPTCHA credentials). The tests that
    exercise the reCAPTCHA gate stub the verifier directly and so are
    unaffected by config state.
    """
    for var in (
        "RECAPTCHA_ENTERPRISE_PROJECT_ID",
        "RECAPTCHA_ENTERPRISE_SITE_KEY",
        "RECAPTCHA_ENTERPRISE_API_KEY",
    ):
        monkeypatch.delenv(var, raising=False)


def _signup(client: TestClient):
    return client.post(SIGNUP_URL, json=SAMPLE_SIGNUP_BODY)


def _count_demo_orgs() -> int:
    """Count organizations whose name starts with `demo-`. Used by the
    rollback test to verify no orphan org leaked into the DB."""
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
        response = _signup(client)
    assert response.status_code == 404


@pytest.mark.unit_tests
def test_signup_demo_mode_on_returns_four_field_response(
    client: GenaiEngineTestClientBase,
):
    """Anonymous POST with the flag on returns the documented shape."""
    client.base_client.put(
        "/api/v1/model_providers/anthropic",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )

    try:
        with patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "ENABLED"}):
            test_client = TestClient(app)
            response = _signup(test_client)

        assert response.status_code == 200
        body = response.json()
        assert set(body.keys()) == {"org_id", "task_id", "task_name", "api_key"}
        # org + task share the same `demo-<8 hex chars>` name
        assert body["task_name"].startswith("demo-")
        assert len(body["task_name"]) == len("demo-") + 8
        uuid.UUID(body["org_id"])  # parseable UUID
        assert body["api_key"]
    finally:
        client.base_client.delete(
            "/api/v1/model_providers/anthropic",
            headers=client.authorized_user_api_key_headers,
        )


@pytest.mark.unit_tests
def test_signup_no_auth_required(client: GenaiEngineTestClientBase):
    """Endpoint accepts calls with no Authorization header."""
    client.base_client.put(
        "/api/v1/model_providers/anthropic",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )

    try:
        with patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "ENABLED"}):
            test_client = TestClient(app)
            response = test_client.post(
                SIGNUP_URL,
                json=SAMPLE_SIGNUP_BODY,
                headers={},
            )
        assert response.status_code == 200
    finally:
        client.base_client.delete(
            "/api/v1/model_providers/anthropic",
            headers=client.authorized_user_api_key_headers,
        )


@pytest.mark.unit_tests
def test_signup_returned_key_authenticates_as_tenant(
    client: GenaiEngineTestClientBase,
):
    """The bearer token from signup, used against /users/me, returns
    org_scope and TENANT-USER — proving the key is fully wired to the
    new org."""
    client.base_client.put(
        "/api/v1/model_providers/anthropic",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )

    try:
        with patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "ENABLED"}):
            test_client = TestClient(app)
            sig = _signup(test_client).json()
            me_resp = test_client.get(
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
    finally:
        client.base_client.delete(
            "/api/v1/model_providers/anthropic",
            headers=client.authorized_user_api_key_headers,
        )


@pytest.mark.unit_tests
def test_signup_each_call_mints_distinct_org(client: GenaiEngineTestClientBase):
    """Two consecutive signups produce independent (org, task, key) triples."""
    client.base_client.put(
        "/api/v1/model_providers/anthropic",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )

    try:
        with patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "ENABLED"}):
            test_client = TestClient(app)
            a = _signup(test_client).json()
            b = _signup(test_client).json()

        assert a["org_id"] != b["org_id"]
        assert a["task_id"] != b["task_id"]
        assert a["api_key"] != b["api_key"]
    finally:
        client.base_client.delete(
            "/api/v1/model_providers/anthropic",
            headers=client.authorized_user_api_key_headers,
        )


@pytest.mark.unit_tests
def test_signup_creates_demo_items_on_task(client: GenaiEngineTestClientBase):
    """Signup creates the full demo bundle on the new task: 2 agentic prompts,
    2 trace transforms, 3 continuous evals, 1 dataset, and 3 replayed traces.
    The continuous-eval enqueue step receives the replayed spans but is
    patched out so no background jobs are actually scheduled.
    """
    test_client = TestClient(app)

    # Demo orchestrator needs a configured model provider to resolve a
    # provider/model; register Anthropic with admin headers before signup.
    response = client.base_client.put(
        "/api/v1/model_providers/anthropic",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )
    assert response.status_code == 201

    try:
        with (
            patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "ENABLED"}),
            patch(
                "repositories.continuous_evals_repository.ContinuousEvalsRepository.enqueue_continuous_evals_for_root_spans",
                return_value=None,
            ) as mock_enqueue,
        ):
            sig = client.base_client.post(
                SIGNUP_URL,
                json=SAMPLE_SIGNUP_BODY,
            ).json()
            task_id = sig["task_id"]
            tenant_headers = {"Authorization": f"Bearer {sig['api_key']}"}

        # Replayed traces are handed to the enqueue method, but no jobs are
        # actually enqueued (the real implementation is patched out).
        mock_enqueue.assert_called_once()
        enqueued_spans = mock_enqueue.call_args.args[0]
        assert len(enqueued_spans) > 0

        # 2 agentic prompts
        resp = client.base_client.get(
            f"/api/v1/tasks/{task_id}/prompts/demo_task_prompt/versions/1",
            headers=tenant_headers,
        )
        assert resp.status_code == 200
        resp = client.base_client.get(
            f"/api/v1/tasks/{task_id}/prompts/demo_chatbot_summarizer_prompt/versions/1",
            headers=tenant_headers,
        )
        assert resp.status_code == 200

        # 2 trace transforms
        resp = client.base_client.get(
            f"/api/v1/tasks/{task_id}/traces/transforms",
            headers=tenant_headers,
        )
        assert resp.status_code == 200
        transform_names = {t["name"] for t in resp.json()["transforms"]}
        assert transform_names == {
            "Answer Relevance Eval",
            "Response Extraction Transform",
        }

        # 3 continuous evals
        resp = client.base_client.get(
            f"/api/v1/tasks/{task_id}/continuous_evals",
            headers=tenant_headers,
        )
        assert resp.status_code == 200
        eval_names = {e["name"] for e in resp.json()["evals"]}
        assert eval_names == {
            "Answer Relevance Continuous Eval",
            "Conciseness Continuous Eval",
            "Readability Continuous Eval",
        }

        # 1 dataset
        resp = client.base_client.get(
            f"/api/v2/tasks/{task_id}/datasets/search",
            headers=tenant_headers,
        )
        assert resp.status_code == 200
        datasets = resp.json()["datasets"]
        assert len(datasets) == 1
        assert datasets[0]["name"] == "Demo Dataset"

        # 3 replayed traces
        resp = client.base_client.get(
            f"/api/v1/traces?task_ids={task_id}",
            headers=tenant_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["count"] == 3
    finally:
        response = client.base_client.delete(
            "/api/v1/model_providers/anthropic",
            headers=client.authorized_user_api_key_headers,
        )
        assert response.status_code == 204


# --- Error-path tests ----------------------------------------------------
# These still go through the real TestClient, but monkeypatch the repository
# the route module imports so we can deterministically simulate failure
# modes that are otherwise hard to trigger through the real DB.


@pytest.mark.unit_tests
def test_signup_retries_once_on_org_name_collision(
    client: GenaiEngineTestClientBase,
    monkeypatch,
):
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
                    "INSERT",
                    {},
                    Exception("simulated unique violation"),
                )
            return self._inner.create_organization(**kwargs)

    client.base_client.put(
        "/api/v1/model_providers/anthropic",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )

    try:
        with patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "ENABLED"}):
            monkeypatch.setattr(mod, "OrganizationsRepository", FlakyOrgRepo)
            test_client = TestClient(app)
            response = _signup(test_client)

        assert response.status_code == 200
        assert calls["n"] == 2
    finally:
        client.base_client.delete(
            "/api/v1/model_providers/anthropic",
            headers=client.authorized_user_api_key_headers,
        )


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
        response = _signup(client)

    assert response.status_code == 500
    assert calls["n"] == 2


@pytest.mark.unit_tests
def test_signup_persists_onboarding_submission(
    client: GenaiEngineTestClientBase,
    tracked_onboarding_submissions,
):
    client.base_client.put(
        "/api/v1/model_providers/anthropic",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )

    try:
        with patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "ENABLED"}):
            test_client = TestClient(app)
            response = _signup(test_client)

        assert response.status_code == 200

        db_session = override_get_db_session()
        try:
            submissions = (
                db_session.query(DatabaseOnboardingSubmission)
                .order_by(DatabaseOnboardingSubmission.created_at.desc())
                .all()
            )
            submission = next(
                (
                    row
                    for row in submissions
                    if row.form_data.get("email")
                    == SAMPLE_SIGNUP_BODY["form_data"]["email"]
                ),
                None,
            )
            assert submission is not None
            tracked_onboarding_submissions.append(submission.id)
            assert submission.form_variant == "linear"
        finally:
            db_session.close()
    finally:
        client.base_client.delete(
            "/api/v1/model_providers/anthropic",
            headers=client.authorized_user_api_key_headers,
        )


# --- reCAPTCHA gate ------------------------------------------------------
# The verifier fails open when reCAPTCHA is unconfigured (the default in the
# test env), so the happy-path tests above exercise that branch. These tests
# stub the verifier the route module imports to assert the rejection path and
# that the submitted token is forwarded for assessment.


@pytest.mark.unit_tests
def test_signup_rejected_when_recaptcha_fails(monkeypatch):
    """A failed assessment short-circuits provisioning with a 400."""
    from clients.recaptcha.recaptcha_verifier import RecaptchaVerificationResult
    from routers.v2 import tenant_signup_routes as mod

    class RejectingVerifier:
        def verify(self, token, action=None):
            return RecaptchaVerificationResult(success=False, reason="low_score")

    before = _count_demo_orgs()
    with patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "ENABLED"}):
        monkeypatch.setattr(mod, "RecaptchaEnterpriseVerifier", RejectingVerifier)
        client = TestClient(app)
        response = _signup(client)
    after = _count_demo_orgs()

    assert response.status_code == 400
    assert "reCAPTCHA" in response.json()["detail"]
    # No provisioning happened.
    assert after == before


@pytest.mark.unit_tests
def test_signup_forwards_recaptcha_token_to_verifier(
    client: GenaiEngineTestClientBase,
    monkeypatch,
):
    """The token from the request body is handed to the verifier."""
    from clients.recaptcha.recaptcha_verifier import RecaptchaVerificationResult
    from routers.v2 import tenant_signup_routes as mod

    seen = {}

    class CapturingVerifier:
        def verify(self, token, action=None):
            seen["token"] = token
            seen["action"] = action
            return RecaptchaVerificationResult(success=True, score=0.9)

    client.base_client.put(
        "/api/v1/model_providers/anthropic",
        json={"api_key": "test-key"},
        headers=client.authorized_user_api_key_headers,
    )

    try:
        body = {**SAMPLE_SIGNUP_BODY, "recaptcha_token": "the-token"}
        with patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "ENABLED"}):
            monkeypatch.setattr(
                mod,
                "RecaptchaEnterpriseVerifier",
                CapturingVerifier,
            )
            test_client = TestClient(app)
            response = test_client.post(SIGNUP_URL, json=body)

        assert response.status_code == 200
        assert seen["token"] == "the-token"
    finally:
        client.base_client.delete(
            "/api/v1/model_providers/anthropic",
            headers=client.authorized_user_api_key_headers,
        )


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
        response = _signup(client)
    after = _count_demo_orgs()

    assert response.status_code == 500
    # rollback worked: no new demo-* org leaked into the DB
    assert after == before
