"""Multi-tenant isolation matrix (UP-4432, design doc §12).

Drives cross-org HTTP calls against the seeded two-org world (see
`conftest.py`) and asserts the enforcement patterns return the documented
status codes. Patterns A/C/D are parametrized over a small registry of
representative endpoints — the route fuzz test (`tests/coverage/`) catches
structural drift across the full surface; this file asserts behavioral
correctness against real DB state.

Pattern B (body-task_id) was implemented and removed during UP-4425 — see
design doc §7 and commit 72dced7f. No cases here.
"""

import os
from dataclasses import dataclass
from typing import Callable
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient

from tests.clients.base_test_client import app
from tests.multitenancy.conftest import TenantWorld
from utils.constants import DEFAULT_ORG_ID

SIGNUP_URL = "/api/v2/tenant/signup"
ME_URL = "/users/me"


# ---------------------------------------------------------------------------
# Parametrized isolation cases (Patterns A, C, D).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IsolationCase:
    """A single cross-org call: invoke as K1 against an O2 resource and
    assert the documented failure code."""

    name: str
    pattern: str  # "A" | "C" | "D"
    expected: int
    # Builds the httpx.Response. `c` is the shared base_client; `headers` is
    # K1's tenant headers; `w` is the seeded world.
    invoke: Callable[[httpx.Client, dict, TenantWorld], httpx.Response]
    # When True, skip the admin-still-succeeds counterpart — admin would
    # actually mutate T2a's state and cascade-break subsequent tests
    # (e.g. hard-delete the task or its inference).
    skip_admin: bool = False


# Pattern A — path task_id. Caller K1 (O1); path carries T2a (O2). Expect 404.
PATTERN_A_CASES = [
    IsolationCase(
        name="GET /api/v2/tasks/{task_id}",
        pattern="A",
        expected=404,
        invoke=lambda c, h, w: c.get(f"/api/v2/tasks/{w.t2a.id}", headers=h),
    ),
    IsolationCase(
        name="DELETE /api/v2/tasks/{task_id}",
        pattern="A",
        expected=404,
        invoke=lambda c, h, w: c.delete(f"/api/v2/tasks/{w.t2a.id}", headers=h),
        # delete_task is a hard DELETE — admin counterpart would wipe T2a and
        # cascade-break subsequent tests. Tenant-isolation coverage retained.
        skip_admin=True,
    ),
    IsolationCase(
        name="POST /api/v2/tasks/{task_id}/unarchive",
        pattern="A",
        expected=404,
        invoke=lambda c, h, w: c.post(f"/api/v2/tasks/{w.t2a.id}/unarchive", headers=h),
    ),
    IsolationCase(
        name="POST /api/v2/tasks/{task_id}/validate_prompt",
        pattern="A",
        expected=404,
        invoke=lambda c, h, w: c.post(
            f"/api/v2/tasks/{w.t2a.id}/validate_prompt",
            json={"prompt": "x", "user_id": "u", "conversation_id": "cv"},
            headers=h,
        ),
    ),
    IsolationCase(
        name="POST /api/v2/tasks/{task_id}/datasets",
        pattern="A",
        expected=404,
        invoke=lambda c, h, w: c.post(
            f"/api/v2/tasks/{w.t2a.id}/datasets",
            json={"name": "x", "description": "x"},
            headers=h,
        ),
    ),
    IsolationCase(
        name="POST /api/v2/tasks/{task_id}/rules",
        pattern="A",
        expected=404,
        invoke=lambda c, h, w: c.post(
            f"/api/v2/tasks/{w.t2a.id}/rules",
            json={
                "name": "x",
                "type": "RegexRule",
                "apply_to_prompt": True,
                "apply_to_response": False,
                "config": {"regex_patterns": ["x"]},
            },
            headers=h,
        ),
    ),
    IsolationCase(
        name="GET /api/v1/tasks/{task_id}/continuous_evals",
        pattern="A",
        expected=404,
        invoke=lambda c, h, w: c.get(
            f"/api/v1/tasks/{w.t2a.id}/continuous_evals", headers=h
        ),
    ),
    IsolationCase(
        name="GET /api/v1/tasks/{task_id}/traces/transforms",
        pattern="A",
        expected=404,
        invoke=lambda c, h, w: c.get(
            f"/api/v1/tasks/{w.t2a.id}/traces/transforms", headers=h
        ),
    ),
]

# Pattern C — resource-id-scoped (repository filter). Expect 404.
PATTERN_C_CASES = [
    IsolationCase(
        name="GET /api/v2/inferences/{inference_id}",
        pattern="C",
        expected=404,
        invoke=lambda c, h, w: c.get(
            f"/api/v2/inferences/{w.t2a.inference_id}", headers=h
        ),
    ),
    # Feedback planting: K1 tries to attach feedback to T2a's inference. The
    # inference fetch returns None for K1, so the route 404s before any row
    # is written.
    IsolationCase(
        name="POST /api/v2/feedback/{inference_id}",
        pattern="C",
        expected=404,
        invoke=lambda c, h, w: c.post(
            f"/api/v2/feedback/{w.t2a.inference_id}",
            json={"target": "context_relevance", "score": 1, "reason": "cross"},
            headers=h,
        ),
    ),
]

# Pattern D — query-param task_ids. Caller explicitly names a foreign ID.
# Expect 403 (the caller named the ID; no enumeration concern to hide).
PATTERN_D_CASES = [
    IsolationCase(
        name="GET /api/v2/inferences/query?task_ids=T2a",
        pattern="D",
        expected=403,
        invoke=lambda c, h, w: c.get(
            "/api/v2/inferences/query",
            params={"task_ids": w.t2a.id},
            headers=h,
        ),
    ),
    IsolationCase(
        name="GET /api/v2/feedback/query?task_id=T2a",
        pattern="D",
        expected=403,
        invoke=lambda c, h, w: c.get(
            "/api/v2/feedback/query",
            params={"task_id": w.t2a.id},
            headers=h,
        ),
    ),
    IsolationCase(
        name="POST /api/v2/tasks/search task_ids=[T2a]",
        pattern="D",
        expected=403,
        invoke=lambda c, h, w: c.post(
            "/api/v2/tasks/search",
            json={"task_ids": [w.t2a.id]},
            headers=h,
        ),
    ),
]

ISOLATION_CASES = PATTERN_A_CASES + PATTERN_C_CASES + PATTERN_D_CASES


@pytest.mark.unit_tests
@pytest.mark.parametrize("case", ISOLATION_CASES, ids=lambda c: f"{c.pattern}-{c.name}")
def test_k1_cross_org_call_blocked(tenant_world: TenantWorld, case: IsolationCase):
    """K1 (org=O1) targets a resource in O2. Every call returns the documented
    isolation status: 404 for path/resource, 403 for query."""
    if case.pattern == "C" and tenant_world.t2a.inference_id is None:
        pytest.skip("Pattern C cases require seeded inference; seed failed")
    response = case.invoke(
        tenant_world.client.base_client,
        tenant_world.headers_for(tenant_world.k1),
        tenant_world,
    )
    assert (
        response.status_code == case.expected
    ), f"{case.name}: expected {case.expected}, got {response.status_code}: {response.text[:300]}"


_ADMIN_CASES = [c for c in ISOLATION_CASES if not c.skip_admin]


@pytest.mark.unit_tests
@pytest.mark.parametrize("case", _ADMIN_CASES, ids=lambda c: f"{c.pattern}-{c.name}")
def test_admin_still_succeeds(tenant_world: TenantWorld, case: IsolationCase):
    """Admin caller hits the same paths against T2a and is not blocked by org
    scope. We accept any 2xx OR any non-403/404 (e.g. 422 from a malformed
    body) — the assertion is specifically that org-scope did not fire."""
    if case.pattern == "C" and tenant_world.t2a.inference_id is None:
        pytest.skip("Pattern C cases require seeded inference; seed failed")
    response = case.invoke(
        tenant_world.client.base_client,
        tenant_world.admin_headers,
        tenant_world,
    )
    # The admin must NOT receive the tenant-isolation failure codes for the
    # foreign resource. (We do allow 422 / 5xx from validation issues on the
    # synthetic bodies used by some cases.)
    assert response.status_code not in (403, 404), (
        f"{case.name}: admin unexpectedly blocked with {response.status_code}: "
        f"{response.text[:300]}"
    )


# ---------------------------------------------------------------------------
# Pattern D — no `task_ids` supplied → decorator injects caller's org tasks.
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_pattern_d_no_task_ids_transparently_scoped(tenant_world: TenantWorld):
    """K1 calls task search with no task_ids — results should restrict to
    O1's tasks transparently. K1 must NOT see T2a or T2b."""
    response = tenant_world.client.base_client.post(
        "/api/v2/tasks/search",
        json={},
        headers=tenant_world.headers_for(tenant_world.k1),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    returned_ids = {t["id"] for t in body.get("tasks", [])}
    assert tenant_world.t2a.id not in returned_ids
    assert tenant_world.t2b.id not in returned_ids
    # K1 SHOULD see its own tasks
    assert {tenant_world.t1a.id, tenant_world.t1b.id}.issubset(returned_ids)


@pytest.mark.unit_tests
def test_pattern_d_own_task_ids_allowed(tenant_world: TenantWorld):
    """K1 calls task search explicitly naming its own task_ids — 200 normal."""
    response = tenant_world.client.base_client.post(
        "/api/v2/tasks/search",
        json={"task_ids": [tenant_world.t1a.id, tenant_world.t1b.id]},
        headers=tenant_world.headers_for(tenant_world.k1),
    )
    assert response.status_code == 200, response.text


# ---------------------------------------------------------------------------
# inference_id shortcut on GET /api/v2/inferences/query (design §7).
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_inference_id_shortcut_isolated(tenant_world: TenantWorld):
    """K1 hits ?inference_id=<T2a_inference> on the query endpoint. The
    decorator-rewritten task_ids set is K1's org's tasks; T2a's inference
    is not in that set, so the response is an empty list (not 404 — the
    tenant-safe shape is the empty result)."""
    if tenant_world.t2a.inference_id is None:
        pytest.skip("seeded inference missing")
    response = tenant_world.client.base_client.get(
        "/api/v2/inferences/query",
        params={"inference_id": tenant_world.t2a.inference_id},
        headers=tenant_world.headers_for(tenant_world.k1),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get("inferences") == []
    assert body.get("count") == 0


# ---------------------------------------------------------------------------
# Pattern E — admin-only endpoints reject TENANT-USER at permission_checker.
# ---------------------------------------------------------------------------


ADMIN_ONLY_CASES = [
    ("POST /api/v1/traces", "post", "/api/v1/traces", {}),
    ("GET /auth/api_keys/", "get", "/auth/api_keys/", None),
    ("GET /users", "get", "/users?search_string=x", None),
    ("GET /api/v2/configuration", "get", "/api/v2/configuration", None),
    (
        "POST /api/v2/default_rules",
        "post",
        "/api/v2/default_rules",
        {
            "name": "x",
            "type": "RegexRule",
            "apply_to_prompt": True,
            "apply_to_response": False,
            "config": {"regex_patterns": ["x"]},
        },
    ),
]


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "name, verb, path, body",
    ADMIN_ONLY_CASES,
    ids=lambda x: x if isinstance(x, str) else "",
)
def test_pattern_e_admin_only_blocks_tenant(
    tenant_world: TenantWorld, name, verb, path, body
):
    """TENANT-USER must receive 403 from permission_checker before any
    handler logic runs."""
    method = getattr(tenant_world.client.base_client, verb)
    kwargs = {"headers": tenant_world.headers_for(tenant_world.k1)}
    if body is not None:
        kwargs["json"] = body
    response = method(path, **kwargs)
    assert (
        response.status_code == 403
    ), f"{name}: expected 403, got {response.status_code}: {response.text[:300]}"


# ---------------------------------------------------------------------------
# POST /api/v2/tasks routing — admin → default org, tenant → caller's org.
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_post_tasks_tenant_lands_in_caller_org(tenant_world: TenantWorld):
    response = tenant_world.client.base_client.post(
        "/api/v2/tasks",
        json={"name": f"mt-routing-tenant-{tenant_world.k1[:8]}"},
        headers=tenant_world.headers_for(tenant_world.k1),
    )
    assert response.status_code == 200, response.text
    task_id = response.json()["id"]
    # Read it back as admin and confirm org_id
    admin_resp = tenant_world.client.base_client.get(
        f"/api/v2/tasks/{task_id}",
        headers=tenant_world.admin_headers,
    )
    assert admin_resp.status_code == 200
    assert admin_resp.json().get("org_id") == str(tenant_world.o1_id)


@pytest.mark.unit_tests
def test_post_tasks_admin_lands_in_default_org(tenant_world: TenantWorld):
    response = tenant_world.client.base_client.post(
        "/api/v2/tasks",
        json={"name": f"mt-routing-admin-{tenant_world.k1[:8]}"},
        headers=tenant_world.admin_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body.get("org_id") == str(DEFAULT_ORG_ID)


# ---------------------------------------------------------------------------
# Cross-org enumeration — K1 list endpoints expose only O1's tasks.
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_get_tasks_list_filters_to_caller_org(tenant_world: TenantWorld):
    response = tenant_world.client.base_client.get(
        "/api/v2/tasks",
        headers=tenant_world.headers_for(tenant_world.k1),
    )
    assert response.status_code == 200, response.text
    ids = {t["id"] for t in response.json().get("tasks", [])}
    assert tenant_world.t2a.id not in ids
    assert tenant_world.t2b.id not in ids


# ---------------------------------------------------------------------------
# /users/me — shape varies by caller type.
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_users_me_for_tenant(tenant_world: TenantWorld):
    response = tenant_world.client.base_client.get(
        ME_URL, headers=tenant_world.headers_for(tenant_world.k1)
    )
    assert response.status_code == 200
    body = response.json()
    assert "TENANT-USER" in body["roles"]
    assert body["org_scope"] == str(tenant_world.o1_id)
    assert body["org"]["id"] == str(tenant_world.o1_id)


@pytest.mark.unit_tests
def test_users_me_for_admin(tenant_world: TenantWorld):
    response = tenant_world.client.base_client.get(
        ME_URL, headers=tenant_world.admin_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["org_scope"] is None
    assert body["org"] is None


# ---------------------------------------------------------------------------
# Tenant signup — feature-flag gating.
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_signup_flag_off_returns_404():
    """Without GENAI_ENGINE_DEMO_MODE the route 404s for everyone."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("GENAI_ENGINE_DEMO_MODE", None)
        test_client = TestClient(app)
        response = test_client.post(SIGNUP_URL)
    assert response.status_code == 404


@pytest.mark.unit_tests
def test_signup_flag_on_returned_key_can_only_access_new_task(
    tenant_world: TenantWorld,
):
    """Flag-on signup yields a tenant key isolated to its newly-minted org —
    cannot reach O1's or O2's tasks."""
    tenant_world.client.base_client.put(
        "/api/v1/model_providers/anthropic",
        json={"api_key": "test-key"},
        headers=tenant_world.admin_headers,
    )
    try:
        with patch.dict(os.environ, {"GENAI_ENGINE_DEMO_MODE": "ENABLED"}):
            test_client = TestClient(app)
            sig = test_client.post(SIGNUP_URL).json()
        new_headers = {"Authorization": f"Bearer {sig['api_key']}"}
        # New tenant CANNOT see T1a
        cross = tenant_world.client.base_client.get(
            f"/api/v2/tasks/{tenant_world.t1a.id}", headers=new_headers
        )
        assert cross.status_code == 404
        # New tenant CAN see its own task
        own = tenant_world.client.base_client.get(
            f"/api/v2/tasks/{sig['task_id']}", headers=new_headers
        )
        assert own.status_code == 200
    finally:
        tenant_world.client.base_client.delete(
            "/api/v1/model_providers/anthropic",
            headers=tenant_world.admin_headers,
        )


# ---------------------------------------------------------------------------
# System org — tenants can never reach any system task by any pattern.
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_system_org_task_invisible_to_tenant(tenant_world: TenantWorld):
    if tenant_world.system_task_id is None:
        pytest.skip("no system task seeded")
    # Pattern A — direct path
    resp = tenant_world.client.base_client.get(
        f"/api/v2/tasks/{tenant_world.system_task_id}",
        headers=tenant_world.headers_for(tenant_world.k1),
    )
    assert resp.status_code == 404


@pytest.mark.unit_tests
def test_system_org_task_visible_to_admin(tenant_world: TenantWorld):
    if tenant_world.system_task_id is None:
        pytest.skip("no system task seeded")
    resp = tenant_world.client.base_client.get(
        f"/api/v2/tasks/{tenant_world.system_task_id}",
        headers=tenant_world.admin_headers,
    )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Backfill — pre-existing tasks live in the `default` org.
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_default_org_holds_admin_created_tasks(tenant_world: TenantWorld):
    """The admin client created a TASK_ADMIN test key + tasks via the HTTP
    API at startup; those tasks land in the default org (admin path). We
    confirm via the org_id field on a fresh admin-created task."""
    response = tenant_world.client.base_client.post(
        "/api/v2/tasks",
        json={"name": f"mt-default-backfill-{tenant_world.k1[:8]}"},
        headers=tenant_world.admin_headers,
    )
    assert response.status_code == 200
    assert response.json().get("org_id") == str(DEFAULT_ORG_ID)


# ---------------------------------------------------------------------------
# Trace uploads — admin-only (Pattern E for tenants, allowed for admin).
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_traces_upload_admin_only_blocks_tenant(tenant_world: TenantWorld):
    response = tenant_world.client.base_client.post(
        "/api/v1/traces",
        content=b"",  # any payload — permission check fires before body parse
        headers={
            **tenant_world.headers_for(tenant_world.k1),
            "Content-Type": "application/x-protobuf",
        },
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Model providers — read responses must not contain credential fields.
# ---------------------------------------------------------------------------


_CREDENTIAL_KEYS = {"api_key", "secret", "secret_key", "client_secret", "password"}


@pytest.mark.unit_tests
def test_model_provider_read_returns_no_credentials(tenant_world: TenantWorld):
    resp = tenant_world.client.base_client.get(
        "/api/v1/model_providers",
        headers=tenant_world.headers_for(tenant_world.k1),
    )
    assert resp.status_code == 200
    # Walk the response and assert no field name resembles a credential.
    payload = resp.json()

    def _walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                assert k not in _CREDENTIAL_KEYS, f"credential leak: {k}"
                _walk(v)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(payload)


# ---------------------------------------------------------------------------
# Multi-task within own org — K1 reads T1a and T1b.
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_k1_reads_both_own_tasks(tenant_world: TenantWorld):
    h = tenant_world.headers_for(tenant_world.k1)
    a = tenant_world.client.base_client.get(
        f"/api/v2/tasks/{tenant_world.t1a.id}", headers=h
    )
    b = tenant_world.client.base_client.get(
        f"/api/v2/tasks/{tenant_world.t1b.id}", headers=h
    )
    assert a.status_code == 200
    assert b.status_code == 200
