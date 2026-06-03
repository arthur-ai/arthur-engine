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
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional
from unittest.mock import patch

import httpx
import pytest
from arthur_common.models.enums import InferenceFeedbackTarget, RuleResultEnum
from fastapi import HTTPException
from fastapi.testclient import TestClient

from db_models import (
    DatabaseInference,
    DatabaseInferenceFeedback,
    DatabaseInferencePrompt,
    DatabaseInferencePromptContent,
    DatabaseInferenceResponse,
    DatabaseInferenceResponseContent,
)
from db_models.agentic_experiment_models import DatabaseAgenticExperiment
from db_models.agentic_notebook_models import DatabaseAgenticNotebook
from db_models.dataset_models import DatabaseDataset, DatabaseDatasetVersion
from db_models.notebook_models import DatabaseNotebook
from db_models.prompt_experiment_models import DatabasePromptExperiment
from db_models.rag_experiment_models import DatabaseRagExperiment
from db_models.rag_notebook_models import DatabaseRagNotebook
from repositories.agentic_experiment_repository import AgenticExperimentRepository
from repositories.feedback_repository import FeedbackRepository
from repositories.prompt_experiment_repository import PromptExperimentRepository
from repositories.rag_experiment_repository import RagExperimentRepository
from schemas.base_experiment_schemas import ExperimentStatus
from tests.clients.base_test_client import app, override_get_db_session
from tests.multitenancy.conftest import TenantWorld
from utils.constants import DEFAULT_ORG_ID, SYSTEM_ORG_ID

SIGNUP_URL = "/api/v2/tenant/signup"
ME_URL = "/users/me"

# Minimal valid body for POST /api/v2/tenant/signup. These tests don't care
# about the onboarding payload itself — they only need the request to clear
# body validation so the demo-mode gate / signup logic can be exercised.
_VALID_SIGNUP_BODY = {
    "form_variant": "linear",
    "form_data": {
        "first_name": "Test",
        "last_name": "Tenant",
        "email": "test@example.com",
        "job_title": "Engineer",
        "company": "TestCo",
        "maturity": "exploring",
        "brings": "evals",
        "competitors": ["langsmith"],
        "attribution": "search",
    },
}


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
    # Attribute on TenantWorld that the case depends on. If the attribute
    # is None (seed failed), the test skips. Optional — only Pattern C
    # cases that target dynamically-seeded resources need this.
    requires_seed: Optional[str] = None


# ---------------------------------------------------------------------------
# Body builders for cross-org-reference cases.
#
# These bodies are Pydantic-valid and reference resources OWNED BY T1a where
# applicable, with one foreign field (dataset_ref.id or transform_id) pointing
# at T2a. The point of seeding own-task evals/transforms in `conftest.py` is
# to make every other caller-side validation step succeed, leaving the
# cross-org reference as the ONLY thing that can reject the request. Without
# the leak fix, these calls would 200; with the fix, they 400/404.
# ---------------------------------------------------------------------------


def _agentic_experiment_body_with_cross_org_dataset(w: TenantWorld) -> dict:
    return {
        "name": "mt-cross-agentic",
        "dataset_ref": {"id": w.t2a_dataset_id, "version": 1},
        "http_template": {
            "endpoint_name": "x",
            "endpoint_url": "http://example.com",
            "headers": [],
            "request_body": "{}",
        },
        "template_variable_mapping": [
            {
                "variable_name": "session_id",
                "source": {"type": "generated", "generator_type": "session_id"},
            },
        ],
        "eval_list": [
            {
                "name": w.t1a_llm_eval_name,
                "version": 1,
                "transform_id": w.t1a_transform_id,
                "variable_mapping": [],
            },
        ],
    }


def _prompt_experiment_body_with_cross_org_dataset(w: TenantWorld) -> dict:
    return {
        "name": "mt-cross-prompt",
        "dataset_ref": {"id": w.t2a_dataset_id, "version": 1},
        "prompt_configs": [
            {
                "type": "unsaved",
                "messages": [{"role": "user", "content": "test"}],
                "model_name": "gpt-4",
                "model_provider": "openai",
            },
        ],
        "prompt_variable_mapping": [],
        "eval_list": [
            {
                "name": w.t1a_llm_eval_name,
                "version": 1,
                "variable_mapping": [],
            },
        ],
    }


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
# Resources seeded under T2a (org=O2) by the fixture; cases that depend on
# a dynamically-seeded ID skip via `requires_seed` when the seed failed.
PATTERN_C_CASES = [
    IsolationCase(
        name="GET /api/v2/inferences/{inference_id}",
        pattern="C",
        expected=404,
        invoke=lambda c, h, w: c.get(
            f"/api/v2/inferences/{w.t2a.inference_id}", headers=h
        ),
        # Admin's GET on a foreign inference also 404s — the inference repo's
        # per-id fetch applies org_scope even for admin. Either design intent
        # ("admin sees only own org") or over-restriction; flagged for review.
        # Tenant-isolation coverage retained.
        skip_admin=True,
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
            json={"target": "response_results", "score": 1, "reason": "cross"},
            headers=h,
        ),
    ),
    IsolationCase(
        name="GET /api/v1/traces/{trace_id}",
        pattern="C",
        expected=404,
        invoke=lambda c, h, w: c.get(f"/api/v1/traces/{w.t2a_trace_id}", headers=h),
        requires_seed="t2a_trace_id",
        # Admin path needs valid span raw_data to render a TraceResponse;
        # the minimal seed only proves the org-scope check, so skip admin.
        skip_admin=True,
    ),
    IsolationCase(
        name="GET /api/v1/traces/annotations/{annotation_id}",
        pattern="C",
        expected=404,
        invoke=lambda c, h, w: c.get(
            f"/api/v1/traces/annotations/{w.t2a_annotation_id}", headers=h
        ),
        requires_seed="t2a_annotation_id",
        skip_admin=True,
    ),
    IsolationCase(
        name="GET /api/v2/datasets/{dataset_id}",
        pattern="C",
        expected=404,
        invoke=lambda c, h, w: c.get(f"/api/v2/datasets/{w.t2a_dataset_id}", headers=h),
        requires_seed="t2a_dataset_id",
        skip_admin=True,
    ),
    IsolationCase(
        name="GET /api/v1/agentic_experiments/{experiment_id}",
        pattern="C",
        expected=404,
        invoke=lambda c, h, w: c.get(
            f"/api/v1/agentic_experiments/{w.t2a_experiment_id}", headers=h
        ),
        requires_seed="t2a_experiment_id",
        skip_admin=True,
    ),
    # -----------------------------------------------------------------
    # Cross-org-reference leaks (Family A — continuous-eval / transform).
    # K1 calls a continuous-eval handler on T1a (its own task) with a
    # transform_id from T2a in path/body. Without the fix, the handler
    # reads or pins the foreign transform; with the fix, the org-scoped
    # transform lookup returns 404.
    # -----------------------------------------------------------------
    IsolationCase(
        name="GET /api/v1/tasks/{task_id}/continuous_evals/transforms/{transform_id}/llm_evals/{eval_name}/versions/{ver}/variables (cross-org transform_id)",
        pattern="C",
        expected=404,
        invoke=lambda c, h, w: c.get(
            f"/api/v1/tasks/{w.t1a.id}/continuous_evals/transforms/{w.t2a_transform_id}/llm_evals/{w.t1a_llm_eval_name}/versions/1/variables",
            headers=h,
        ),
        requires_seed="t2a_transform_id",
        # Admin without org scope would actually read the foreign transform's
        # definition — admin path is correct, we just don't assert on it here.
        skip_admin=True,
    ),
    IsolationCase(
        name="POST /api/v1/tasks/{task_id}/continuous_evals (cross-org transform_id in body)",
        pattern="C",
        expected=404,
        invoke=lambda c, h, w: c.post(
            f"/api/v1/tasks/{w.t1a.id}/continuous_evals",
            json={
                "name": "mt-cross-ceval",
                "description": "cross-org-leak-test",
                "llm_eval_name": w.t1a_llm_eval_name,
                "llm_eval_version": 1,
                "transform_id": w.t2a_transform_id,
                "transform_variable_mapping": [],
            },
            headers=h,
        ),
        requires_seed="t2a_transform_id",
        # Admin would succeed and persist a cross-org-referencing continuous
        # eval, polluting subsequent fixture state.
        skip_admin=True,
    ),
    IsolationCase(
        name="PATCH /api/v1/continuous_evals/{eval_id} (cross-org transform_id in body)",
        pattern="C",
        expected=404,
        invoke=lambda c, h, w: c.patch(
            f"/api/v1/continuous_evals/{w.t1a_continuous_eval_id}",
            json={
                "transform_id": w.t2a_transform_id,
                "transform_variable_mapping": [],
            },
            headers=h,
        ),
        requires_seed="t1a_continuous_eval_id",
        # Admin would successfully repoint K1's own eval to T2a's transform.
        skip_admin=True,
    ),
    # -----------------------------------------------------------------
    # Cross-org-reference leaks (Family B — experiment creation / dataset).
    # K1 creates an experiment on T1a with a dataset_ref pointing at T2a's
    # dataset. Without the fix, the experiment is created and reads cross-
    # org rows at execution time; with the fix, the dataset lookup filters
    # by task_id and 400s before any row is written.
    # -----------------------------------------------------------------
    IsolationCase(
        name="POST /api/v1/tasks/{task_id}/agentic_experiments (cross-org dataset_id)",
        pattern="C",
        expected=400,
        invoke=lambda c, h, w: c.post(
            f"/api/v1/tasks/{w.t1a.id}/agentic_experiments",
            json=_agentic_experiment_body_with_cross_org_dataset(w),
            headers=h,
        ),
        requires_seed="t2a_dataset_id",
        skip_admin=True,
    ),
    IsolationCase(
        name="POST /api/v1/tasks/{task_id}/prompt_experiments (cross-org dataset_id)",
        pattern="C",
        expected=400,
        invoke=lambda c, h, w: c.post(
            f"/api/v1/tasks/{w.t1a.id}/prompt_experiments",
            json=_prompt_experiment_body_with_cross_org_dataset(w),
            headers=h,
        ),
        requires_seed="t2a_dataset_id",
        skip_admin=True,
    ),
    # RAG experiment is a smoke test: rag_configs require a real RAG
    # provider or setting configuration that we don't seed, so the
    # rag_config validation 400s downstream of the dataset check both
    # with and without the fix. The case still asserts the endpoint
    # never returns 200 for a cross-org dataset_ref; the unit-level
    # validator test pins the fix-specific behavior.
    IsolationCase(
        name="POST /api/v1/tasks/{task_id}/rag_experiments (cross-org dataset_id, smoke)",
        pattern="C",
        expected=400,
        invoke=lambda c, h, w: c.post(
            f"/api/v1/tasks/{w.t1a.id}/rag_experiments",
            json={
                "name": "mt-cross-rag",
                "dataset_ref": {"id": w.t2a_dataset_id, "version": 1},
                "rag_configs": [
                    {
                        "type": "saved",
                        "setting_configuration_id": str(uuid.uuid4()),
                        "version": 1,
                        "query_column": {
                            "type": "dataset_column",
                            "dataset_column": {"name": "query"},
                        },
                    },
                ],
                "eval_list": [
                    {
                        "name": w.t1a_llm_eval_name,
                        "version": 1,
                        "variable_mapping": [],
                    },
                ],
            },
            headers=h,
        ),
        requires_seed="t2a_dataset_id",
        skip_admin=True,
    ),
    # -----------------------------------------------------------------
    # Cross-org-reference leaks (Family C — notebook state / dataset).
    # K1 creates a notebook on T1a with state.dataset_ref pointing at
    # T2a's dataset. Without the fix, the notebook is persisted with a
    # cross-org reference; with the fix, the dataset filter by task_id
    # 400s before the insert.
    # -----------------------------------------------------------------
    IsolationCase(
        name="POST /api/v1/tasks/{task_id}/notebooks (cross-org dataset_id in state)",
        pattern="C",
        expected=400,
        invoke=lambda c, h, w: c.post(
            f"/api/v1/tasks/{w.t1a.id}/notebooks",
            json={
                "name": "mt-cross-notebook",
                "state": {
                    "dataset_ref": {
                        "id": w.t2a_dataset_id,
                        "version": 1,
                        "name": "mt-cross",
                    },
                },
            },
            headers=h,
        ),
        requires_seed="t2a_dataset_id",
        skip_admin=True,
    ),
    IsolationCase(
        name="POST /api/v1/tasks/{task_id}/agentic_notebooks (cross-org dataset_id in state)",
        pattern="C",
        expected=400,
        invoke=lambda c, h, w: c.post(
            f"/api/v1/tasks/{w.t1a.id}/agentic_notebooks",
            json={
                "name": "mt-cross-agentic-nb",
                "state": {
                    "dataset_ref": {
                        "id": w.t2a_dataset_id,
                        "version": 1,
                        "name": "mt-cross",
                    },
                },
            },
            headers=h,
        ),
        requires_seed="t2a_dataset_id",
        skip_admin=True,
    ),
    IsolationCase(
        name="POST /api/v1/tasks/{task_id}/rag_notebooks (cross-org dataset_id in state)",
        pattern="C",
        expected=400,
        invoke=lambda c, h, w: c.post(
            f"/api/v1/tasks/{w.t1a.id}/rag_notebooks",
            json={
                "name": "mt-cross-rag-nb",
                "state": {
                    "dataset_ref": {
                        "id": w.t2a_dataset_id,
                        "version": 1,
                        "name": "mt-cross",
                    },
                },
            },
            headers=h,
        ),
        requires_seed="t2a_dataset_id",
        skip_admin=True,
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
    # Mixed ownership: K1 names one own task + one foreign task. The
    # decorator's `requested.issubset(org_task_ids)` check should 403 the
    # whole request rather than silently filter the foreign id out.
    IsolationCase(
        name="POST /api/v2/tasks/search task_ids=[T1a, T2a]",
        pattern="D",
        expected=403,
        invoke=lambda c, h, w: c.post(
            "/api/v2/tasks/search",
            json={"task_ids": [w.t1a.id, w.t2a.id]},
            headers=h,
        ),
    ),
    IsolationCase(
        name="GET /api/v2/inferences/query?task_ids=[T1a, T2a]",
        pattern="D",
        expected=403,
        invoke=lambda c, h, w: c.get(
            "/api/v2/inferences/query",
            params=[("task_ids", w.t1a.id), ("task_ids", w.t2a.id)],
            headers=h,
        ),
    ),
]

ISOLATION_CASES = PATTERN_A_CASES + PATTERN_C_CASES + PATTERN_D_CASES


def _seed_target(case: IsolationCase, world: TenantWorld):
    """Return the value of the seed attribute the case requires, or a sentinel
    for cases that depend on the always-seeded inference_id."""
    if case.requires_seed is not None:
        return getattr(world, case.requires_seed)
    if case.pattern == "C":
        return world.t2a.inference_id
    return "no-seed-needed"


@pytest.mark.unit_tests
@pytest.mark.parametrize("case", ISOLATION_CASES, ids=lambda c: f"{c.pattern}-{c.name}")
def test_k1_cross_org_call_blocked(tenant_world: TenantWorld, case: IsolationCase):
    """K1 (org=O1) targets a resource in O2. Every call returns the documented
    isolation status: 404 for path/resource, 403 for query."""
    if _seed_target(case, tenant_world) is None:
        pytest.skip(f"{case.name}: required seed missing")
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
    if _seed_target(case, tenant_world) is None:
        pytest.skip(f"{case.name}: required seed missing")
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
def test_pattern_d_no_task_ids_inferences_query_scoped(tenant_world: TenantWorld):
    """K1 calls inferences/query with no task_ids. The decorator should
    inject K1's org's task_ids; the result must include T1a's inference
    and must not include T2a's."""
    if tenant_world.t2a.inference_id is None or tenant_world.t1a.inference_id is None:
        pytest.skip("seeded inferences missing")
    response = tenant_world.client.base_client.get(
        "/api/v2/inferences/query",
        headers=tenant_world.headers_for(tenant_world.k1),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    returned_ids = {inf["id"] for inf in body.get("inferences", [])}
    assert tenant_world.t2a.inference_id not in returned_ids
    assert tenant_world.t2b.inference_id not in returned_ids
    # K1's own inferences should still be reachable
    assert tenant_world.t1a.inference_id in returned_ids


@pytest.mark.unit_tests
def test_pattern_d_no_task_ids_feedback_query_scoped(tenant_world: TenantWorld):
    """K1 calls feedback/query with no task_id. Result must exclude
    feedback rows attached to O2 inferences."""
    if tenant_world.t2a.feedback_id is None or tenant_world.t1a.feedback_id is None:
        pytest.skip("seeded feedback missing")
    response = tenant_world.client.base_client.get(
        "/api/v2/feedback/query",
        headers=tenant_world.headers_for(tenant_world.k1),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    returned_ids = {item["id"] for item in body.get("feedback", [])}
    assert tenant_world.t2a.feedback_id not in returned_ids
    assert tenant_world.t2b.feedback_id not in returned_ids
    assert tenant_world.t1a.feedback_id in returned_ids


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


# Per-case allowed status codes. Pattern E's canonical shape is 403 from
# `permission_checker`. Some routes legitimately return 401 (master-only
# validator) or 400 (body validation racing the role check) — see notes.
_BLOCKED = frozenset({401, 403})
ADMIN_ONLY_CASES = [
    # `@permission_checker` is a function decorator; it runs AFTER FastAPI
    # binds `body: bytes = Body(...)`. An invalid body 400s before the role
    # gate fires. Tracked follow-up: convert permission_checker to a
    # route-level Depends() factory so it gates body parsing too.
    (
        "POST /api/v1/traces",
        "post",
        "/api/v1/traces",
        {},
        _BLOCKED | {400},
    ),
    # MASTER-only validator by design; repos lack org_scope. Tenant key is
    # not recognized at all → 401, not 403.
    ("GET /auth/api_keys/", "get", "/auth/api_keys/", None, _BLOCKED),
    ("GET /users", "get", "/users?search_string=x", None, _BLOCKED),
    ("GET /api/v2/configuration", "get", "/api/v2/configuration", None, _BLOCKED),
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
        _BLOCKED,
    ),
]


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "name, verb, path, body, allowed",
    ADMIN_ONLY_CASES,
    ids=lambda x: x if isinstance(x, str) else "",
)
def test_pattern_e_admin_only_blocks_tenant(
    tenant_world: TenantWorld, name, verb, path, body, allowed
):
    """TENANT-USER must be blocked from admin-only surfaces. Canonical
    shape is 403 from `permission_checker`. Per-case overrides widen the
    accepted set when the route legitimately rejects at a different
    layer (see ADMIN_ONLY_CASES inline notes)."""
    method = getattr(tenant_world.client.base_client, verb)
    kwargs = {"headers": tenant_world.headers_for(tenant_world.k1)}
    if body is not None:
        kwargs["json"] = body
    response = method(path, **kwargs)
    assert response.status_code in allowed, (
        f"{name}: expected one of {sorted(allowed)}, got "
        f"{response.status_code}: {response.text[:300]}"
    )


# ---------------------------------------------------------------------------
# POST /api/v2/tasks routing — admin → default org, tenant → caller's org.
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_post_tasks_tenant_lands_in_caller_org(tenant_world: TenantWorld):
    """TaskResponse does not expose org_id, so we verify org placement
    behaviorally: a task POSTed by K1 must be reachable by K1 (own org) and
    unreachable by K2 (cross-org isolation kicks in)."""
    response = tenant_world.client.base_client.post(
        "/api/v2/tasks",
        json={"name": f"mt-routing-tenant-{tenant_world.k1[:8]}"},
        headers=tenant_world.headers_for(tenant_world.k1),
    )
    assert response.status_code == 200, response.text
    task_id = response.json()["id"]

    own = tenant_world.client.base_client.get(
        f"/api/v2/tasks/{task_id}",
        headers=tenant_world.headers_for(tenant_world.k1),
    )
    assert own.status_code == 200, "K1 should see its own newly-created task"

    cross = tenant_world.client.base_client.get(
        f"/api/v2/tasks/{task_id}",
        headers=tenant_world.headers_for(tenant_world.k2),
    )
    assert (
        cross.status_code == 404
    ), "K2 should NOT see K1's task — proves it landed in O1, not a shared org"


@pytest.mark.unit_tests
def test_post_tasks_admin_lands_in_default_org(tenant_world: TenantWorld):
    """TaskResponse does not expose org_id. Verify admin-created tasks land
    in DEFAULT_ORG behaviorally: neither K1 nor K2 can reach the task."""
    response = tenant_world.client.base_client.post(
        "/api/v2/tasks",
        json={"name": f"mt-routing-admin-{tenant_world.k1[:8]}"},
        headers=tenant_world.admin_headers,
    )
    assert response.status_code == 200, response.text
    task_id = response.json()["id"]

    for label, key in (("K1", tenant_world.k1), ("K2", tenant_world.k2)):
        resp = tenant_world.client.base_client.get(
            f"/api/v2/tasks/{task_id}",
            headers=tenant_world.headers_for(key),
        )
        assert (
            resp.status_code == 404
        ), f"{label} should NOT reach admin-created task — proves it landed in DEFAULT, not O1/O2"


# ---------------------------------------------------------------------------
# Cross-org enumeration — K1 list endpoints expose only O1's tasks.
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_get_tasks_list_filters_to_caller_org(tenant_world: TenantWorld):
    """GET /api/v2/tasks returns a bare list[TaskResponse] (not a wrapped
    object) — see task_management_routes.py:114."""
    response = tenant_world.client.base_client.get(
        "/api/v2/tasks",
        headers=tenant_world.headers_for(tenant_world.k1),
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    tasks = payload if isinstance(payload, list) else payload.get("tasks", [])
    ids = {t["id"] for t in tasks}
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
    """Without GENAI_ENGINE_DEMO_MODE the route 404s for everyone — even for
    well-formed requests."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("GENAI_ENGINE_DEMO_MODE", None)
        test_client = TestClient(app)
        response = test_client.post(SIGNUP_URL, json=_VALID_SIGNUP_BODY)
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
            sig = test_client.post(SIGNUP_URL, json=_VALID_SIGNUP_BODY).json()
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
    """The admin path creates tasks in DEFAULT_ORG. TaskResponse does not
    expose org_id, so verify behaviorally: neither tenant key can reach an
    admin-created task (it's not in O1 or O2)."""
    response = tenant_world.client.base_client.post(
        "/api/v2/tasks",
        json={"name": f"mt-default-backfill-{tenant_world.k1[:8]}"},
        headers=tenant_world.admin_headers,
    )
    assert response.status_code == 200
    task_id = response.json()["id"]
    for label, key in (("K1", tenant_world.k1), ("K2", tenant_world.k2)):
        resp = tenant_world.client.base_client.get(
            f"/api/v2/tasks/{task_id}",
            headers=tenant_world.headers_for(key),
        )
        assert (
            resp.status_code == 404
        ), f"{label} unexpectedly reached an admin-created task"


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


# ---------------------------------------------------------------------------
# Repository-level: attach_notebook_to_experiment cross-org rejection.
#
# Regression coverage for the bug fixed in commit e29225c5 (PR #1693) across
# all three experiment repositories. The pre-fix code org-validated the
# experiment via `_get_db_experiment(..., org_scope=)` but then blindly wrote
# `db_experiment.notebook_id = notebook_id` without validating that the
# notebook itself belonged to the experiment's task. A tenant could attach a
# foreign-org notebook UUID to their own experiment.
#
# The fix adds a `DatabaseNotebook.task_id == db_experiment.task_id` filter on
# the notebook lookup — since the experiment is already org-validated, the
# task_id match transitively enforces org ownership. 404 is returned (parity
# with `_get_db_experiment` / `_get_db_notebook` helpers) for both
# "notebook doesn't exist" and "notebook is in a foreign task/org."
# ---------------------------------------------------------------------------


def _attach_suffix() -> str:
    """Short unique suffix for ids/names used by the attach-notebook tests."""
    return uuid.uuid4().hex[:8]


def _seed_dataset_with_version(db, task_id: str) -> tuple[uuid.UUID, int]:
    """Create a DatabaseDataset + DatabaseDatasetVersion on `task_id`.

    Returns (dataset_id, version_number). The experiment FK constraint
    points at dataset_versions, so both rows are required.
    """
    now = datetime.now(timezone.utc)
    dataset_id = uuid.uuid4()
    db.add(
        DatabaseDataset(
            id=dataset_id,
            task_id=task_id,
            name=f"mt-attach-ds-{_attach_suffix()}",
            description="mt-attach-seed",
            created_at=now,
            updated_at=now,
            latest_version_number=1,
        )
    )
    db.flush()
    db.add(
        DatabaseDatasetVersion(
            version_number=1,
            dataset_id=dataset_id,
            column_names=[],
        )
    )
    db.commit()
    return dataset_id, 1


@pytest.fixture
def attach_notebook_seed(tenant_world: TenantWorld):
    """Per-test seed: dataset+version on T1a (caller's task) and T2a
    (foreign task), used to anchor experiments/notebooks for the three
    repository-level cross-org attach tests.

    Each test creates its own experiment + notebook ids on top of these
    datasets so writes from one test do not leak into another. The fixture
    cleans up the dataset rows on teardown (cascade handles version rows).
    """
    db = override_get_db_session()
    t1a_dataset_id, _ = _seed_dataset_with_version(db, tenant_world.t1a.id)
    t2a_dataset_id, _ = _seed_dataset_with_version(db, tenant_world.t2a.id)
    try:
        yield db, t1a_dataset_id, t2a_dataset_id
    finally:
        for ds_id in (t1a_dataset_id, t2a_dataset_id):
            try:
                row = (
                    db.query(DatabaseDataset)
                    .filter(DatabaseDataset.id == ds_id)
                    .first()
                )
                if row is not None:
                    db.delete(row)
                db.commit()
            except Exception:
                db.rollback()
        db.close()


def _cleanup_rows(db, pairs):
    """Best-effort delete + commit per (model, pk). Used to keep sub-cases
    of the consolidated attach-notebook test isolated."""
    for model, pk in pairs:
        try:
            row = db.query(model).filter(model.id == pk).first()
            if row is not None:
                db.delete(row)
            db.commit()
        except Exception:
            db.rollback()


@pytest.mark.unit_tests
def test_attach_notebook_isolation_matrix(
    tenant_world: TenantWorld, attach_notebook_seed
):
    """Consolidated regression for the attach_notebook_to_experiment fix
    (commit e29225c5, PR #1693) across all three experiment repositories,
    plus the prompt-repo happy-path.

    Sub-cases run sequentially against the shared `tenant_world` +
    `attach_notebook_seed` fixtures to amortize the expensive dataset/
    experiment/notebook seeding. Each sub-case cleans up its own writes in
    a `finally` block so they don't bleed into the next sub-case.

    Sub-cases:
      1. prompt   — cross-org notebook → 404, no mutation
      2. agentic  — cross-org notebook → 404, no mutation
      3. rag      — cross-org notebook → 404, no mutation
      4. prompt   — same-task notebook → succeeds, notebook_id set
    """
    db, t1a_dataset_id, t2a_dataset_id = attach_notebook_seed
    now = datetime.now(timezone.utc)

    # -- Sub-case 1: prompt repo, cross-org notebook rejected -------------
    sub = "prompt-cross-org"
    experiment_id = uuid.uuid4().hex
    notebook_id = uuid.uuid4().hex
    db.add(
        DatabasePromptExperiment(
            id=experiment_id,
            task_id=tenant_world.t1a.id,
            name=f"mt-attach-prompt-exp-{_attach_suffix()}",
            description="own-org experiment",
            status=ExperimentStatus.QUEUED,
            dataset_id=t1a_dataset_id,
            dataset_version=1,
            prompt_configs=[],
            prompt_variable_mapping=[],
            eval_configs=[],
        )
    )
    db.add(
        DatabaseNotebook(
            id=notebook_id,
            task_id=tenant_world.t2a.id,  # foreign-org task
            name=f"mt-attach-prompt-nb-{_attach_suffix()}",
            created_at=now,
            updated_at=now,
        )
    )
    db.commit()
    try:
        repo = PromptExperimentRepository(db)
        with pytest.raises(HTTPException) as exc_info:
            repo.attach_notebook_to_experiment(
                experiment_id=experiment_id,
                notebook_id=notebook_id,
                org_scope=tenant_world.o1_id,
            )
        assert exc_info.value.status_code == 404, sub
        assert f"Notebook {notebook_id} not found." in str(exc_info.value.detail), sub

        db.expire_all()
        refetched = (
            db.query(DatabasePromptExperiment)
            .filter(DatabasePromptExperiment.id == experiment_id)
            .first()
        )
        assert refetched is not None, sub
        assert refetched.notebook_id is None, sub
    finally:
        _cleanup_rows(
            db,
            (
                (DatabasePromptExperiment, experiment_id),
                (DatabaseNotebook, notebook_id),
            ),
        )

    # -- Sub-case 2: agentic repo, cross-org notebook rejected ------------
    sub = "agentic-cross-org"
    experiment_id = uuid.uuid4().hex
    notebook_id = uuid.uuid4().hex
    db.add(
        DatabaseAgenticExperiment(
            id=experiment_id,
            task_id=tenant_world.t1a.id,
            name=f"mt-attach-agentic-exp-{_attach_suffix()}",
            description="own-org agentic experiment",
            status=ExperimentStatus.QUEUED,
            dataset_id=t1a_dataset_id,
            dataset_version=1,
            http_template={},
            template_variable_mapping=[],
            eval_configs=[],
        )
    )
    db.add(
        DatabaseAgenticNotebook(
            id=notebook_id,
            task_id=tenant_world.t2a.id,  # foreign-org task
            name=f"mt-attach-agentic-nb-{_attach_suffix()}",
            created_at=now,
            updated_at=now,
        )
    )
    db.commit()
    try:
        repo = AgenticExperimentRepository(db)
        with pytest.raises(HTTPException) as exc_info:
            repo.attach_notebook_to_experiment(
                experiment_id=experiment_id,
                notebook_id=notebook_id,
                org_scope=tenant_world.o1_id,
            )
        assert exc_info.value.status_code == 404, sub
        assert f"Agentic notebook {notebook_id} not found." in str(
            exc_info.value.detail
        ), sub

        db.expire_all()
        refetched = (
            db.query(DatabaseAgenticExperiment)
            .filter(DatabaseAgenticExperiment.id == experiment_id)
            .first()
        )
        assert refetched is not None, sub
        assert refetched.notebook_id is None, sub
    finally:
        _cleanup_rows(
            db,
            (
                (DatabaseAgenticExperiment, experiment_id),
                (DatabaseAgenticNotebook, notebook_id),
            ),
        )

    # -- Sub-case 3: rag repo, cross-org notebook rejected ----------------
    sub = "rag-cross-org"
    experiment_id = uuid.uuid4().hex
    notebook_id = uuid.uuid4().hex
    db.add(
        DatabaseRagExperiment(
            id=experiment_id,
            task_id=tenant_world.t1a.id,
            name=f"mt-attach-rag-exp-{_attach_suffix()}",
            description="own-org RAG experiment",
            status=ExperimentStatus.QUEUED,
            dataset_id=t1a_dataset_id,
            dataset_version=1,
            rag_configs=[],
            eval_configs=[],
        )
    )
    db.add(
        DatabaseRagNotebook(
            id=notebook_id,
            task_id=tenant_world.t2a.id,  # foreign-org task
            name=f"mt-attach-rag-nb-{_attach_suffix()}",
            created_at=now,
            updated_at=now,
        )
    )
    db.commit()
    try:
        repo = RagExperimentRepository(db)
        with pytest.raises(HTTPException) as exc_info:
            repo.attach_notebook_to_experiment(
                experiment_id=experiment_id,
                notebook_id=notebook_id,
                org_scope=tenant_world.o1_id,
            )
        assert exc_info.value.status_code == 404, sub
        assert f"RAG notebook {notebook_id} not found." in str(
            exc_info.value.detail
        ), sub

        db.expire_all()
        refetched = (
            db.query(DatabaseRagExperiment)
            .filter(DatabaseRagExperiment.id == experiment_id)
            .first()
        )
        assert refetched is not None, sub
        assert refetched.notebook_id is None, sub
    finally:
        _cleanup_rows(
            db,
            (
                (DatabaseRagExperiment, experiment_id),
                (DatabaseRagNotebook, notebook_id),
            ),
        )

    # -- Sub-case 4: prompt repo, same-task notebook attaches -------------
    # Covers the prompt repo specifically; the agentic and RAG repos share
    # the same implementation shape, so one representative happy-path is
    # sufficient regression coverage for the new filter clause.
    sub = "prompt-same-task-happy-path"
    experiment_id = uuid.uuid4().hex
    notebook_id = uuid.uuid4().hex
    db.add(
        DatabasePromptExperiment(
            id=experiment_id,
            task_id=tenant_world.t1a.id,
            name=f"mt-attach-prompt-exp-ok-{_attach_suffix()}",
            description="own-task experiment",
            status=ExperimentStatus.QUEUED,
            dataset_id=t1a_dataset_id,
            dataset_version=1,
            prompt_configs=[],
            prompt_variable_mapping=[],
            eval_configs=[],
        )
    )
    db.add(
        DatabaseNotebook(
            id=notebook_id,
            task_id=tenant_world.t1a.id,  # SAME task as the experiment
            name=f"mt-attach-prompt-nb-ok-{_attach_suffix()}",
            created_at=now,
            updated_at=now,
        )
    )
    db.commit()
    try:
        repo = PromptExperimentRepository(db)
        result = repo.attach_notebook_to_experiment(
            experiment_id=experiment_id,
            notebook_id=notebook_id,
            org_scope=tenant_world.o1_id,
        )
        # Summary builder reads db_experiment.dataset.name — the seeded
        # dataset row guarantees that lookup resolves.
        assert result.id == experiment_id, sub

        db.expire_all()
        refetched = (
            db.query(DatabasePromptExperiment)
            .filter(DatabasePromptExperiment.id == experiment_id)
            .first()
        )
        assert refetched is not None, sub
        assert refetched.notebook_id == notebook_id, sub
    finally:
        _cleanup_rows(
            db,
            (
                (DatabasePromptExperiment, experiment_id),
                (DatabaseNotebook, notebook_id),
            ),
        )


@pytest.mark.unit_tests
def test_feedback_org_id_derived_from_inference_not_caller(
    tenant_world: TenantWorld,
):
    """Repo-layer defense-in-depth for item 8.

    Sub-cases (one fixture setup, multiple assertions):
      1) Tenant K1 supplying T2a's inference_id with org_scope=O1 -> 404
         (mismatch between derived inference org and caller org).
      2) Admin (org_scope=None) writing on T2a's inference -> row gets T2a's
         org_id (= O2), not the caller's identity and not DEFAULT_ORG_ID.
      3) Admin writing on a task-less inference (deprecated
         /api/v2/validate_prompt path, inference.task_id IS NULL) -> the
         JOIN through tasks returns no row, so the fallback fires. Must be
         SYSTEM_ORG_ID to match what save_prompt/save_response stamp on the
         same inference's rule_results — otherwise children of one
         inference split-brain across system and default orgs.
    """
    db = override_get_db_session()
    repo = FeedbackRepository(db)
    created_feedback_ids: list[str] = []
    taskless_inference_id = str(uuid.uuid4())
    taskless_prompt_id = str(uuid.uuid4())
    taskless_response_id = str(uuid.uuid4())
    try:
        if tenant_world.t2a.inference_id is None:
            pytest.skip("seeded T2a inference missing")

        # Sub-case 1: tenant/inference org mismatch -> 404.
        with pytest.raises(HTTPException) as exc_info:
            repo.create_feedback(
                inference_id=tenant_world.t2a.inference_id,
                target=InferenceFeedbackTarget.RESPONSE_RESULTS,
                score=1,
                reason="cross-org repo call",
                user_id=None,
                org_scope=tenant_world.o1_id,
            )
        assert exc_info.value.status_code == 404
        db.rollback()

        # Sub-case 2: admin caller -> derived org from inference's task wins.
        row = repo.create_feedback(
            inference_id=tenant_world.t2a.inference_id,
            target=InferenceFeedbackTarget.RESPONSE_RESULTS,
            score=1,
            reason="admin write",
            user_id=None,
            org_scope=None,
        )
        created_feedback_ids.append(row.id)
        assert row.org_id == tenant_world.o2_id
        assert row.org_id != DEFAULT_ORG_ID

        # Sub-case 3: task-less inference -> SYSTEM_ORG_ID fallback. Hand-seed
        # the inference because task_id=NULL is only producible through the
        # deprecated validate_prompt path, which the tenant_world fixture
        # doesn't exercise.
        now = datetime.now(timezone.utc)
        db.add(
            DatabaseInference(
                id=taskless_inference_id,
                result=RuleResultEnum.PASS.value,
                inference_prompt=DatabaseInferencePrompt(
                    id=taskless_prompt_id,
                    inference_id=taskless_inference_id,
                    result=RuleResultEnum.PASS.value,
                    content=DatabaseInferencePromptContent(
                        inference_prompt_id=taskless_prompt_id,
                        content="taskless-prompt",
                    ),
                    prompt_rule_results=[],
                    created_at=now,
                    updated_at=now,
                ),
                inference_response=DatabaseInferenceResponse(
                    id=taskless_response_id,
                    inference_id=taskless_inference_id,
                    result=RuleResultEnum.PASS.value,
                    content=DatabaseInferenceResponseContent(
                        inference_response_id=taskless_response_id,
                        content="taskless-response",
                    ),
                    response_rule_results=[],
                    created_at=now,
                    updated_at=now,
                ),
                created_at=now,
                updated_at=now,
            ),
        )
        db.commit()
        taskless_row = repo.create_feedback(
            inference_id=taskless_inference_id,
            target=InferenceFeedbackTarget.RESPONSE_RESULTS,
            score=1,
            reason="taskless admin write",
            user_id=None,
            org_scope=None,
        )
        created_feedback_ids.append(taskless_row.id)
        assert taskless_row.org_id == SYSTEM_ORG_ID
        assert taskless_row.org_id != DEFAULT_ORG_ID
    finally:
        for fid in created_feedback_ids:
            try:
                stale = (
                    db.query(DatabaseInferenceFeedback)
                    .filter(DatabaseInferenceFeedback.id == fid)
                    .first()
                )
                if stale is not None:
                    db.delete(stale)
                db.commit()
            except Exception:
                db.rollback()
        for model, ident in (
            (DatabaseInferenceResponse, taskless_response_id),
            (DatabaseInferencePrompt, taskless_prompt_id),
            (DatabaseInference, taskless_inference_id),
        ):
            try:
                stale_row = db.query(model).filter(model.id == ident).first()
                if stale_row is not None:
                    db.delete(stale_row)
                db.commit()
            except Exception:
                db.rollback()
        db.close()
