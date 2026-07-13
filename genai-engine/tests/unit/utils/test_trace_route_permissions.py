"""Lock in the trace-route permission policy from UP-4428.

Design intent (design doc §2 Non-Goals, confirmed on PR #1661):
  - Trace INGEST is admin-only in v1 — POST /api/v1/traces uses TRACES_WRITE
    so the broadened INFERENCE_WRITE does not silently grant tenants upload access.
  - Trace ANNOTATIONS are tenant-allowed — annotation endpoints stay on
    INFERENCE_WRITE, which includes TENANT-USER.

This test walks the route source files and asserts the @permission_checker
decorator argument matches the expected enum. A future refactor that swaps the
gate on any of these four endpoints will fail here, regardless of how the
underlying frozensets are reshuffled.
"""

import ast
from pathlib import Path

import pytest

from schemas.enums import PermissionLevelsEnum
from utils import constants

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC = _REPO_ROOT / "src"


def _decorator_permission(file_path: Path, route_func: str) -> str | None:
    """Extract the PermissionLevelsEnum.X attribute name from
    @permission_checker(permissions=PermissionLevelsEnum.X.value) on `route_func`.
    Returns None if the function or decorator is missing.
    """
    tree = ast.parse(file_path.read_text())
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != route_func:
            continue
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            if getattr(dec.func, "id", None) != "permission_checker":
                continue
            for kw in dec.keywords:
                if kw.arg != "permissions":
                    continue
                v = kw.value
                if (
                    isinstance(v, ast.Attribute)
                    and v.attr == "value"
                    and isinstance(v.value, ast.Attribute)
                    and isinstance(v.value.value, ast.Name)
                    and v.value.value.id == "PermissionLevelsEnum"
                ):
                    return v.value.attr
    return None


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "rel_path, func_name, expected",
    [
        # Trace ingest: admin-only — tenants cannot upload traces in v1.
        ("routers/v1/trace_api_routes.py", "receive_traces", "TRACES_WRITE"),
        ("routers/v1/legacy_span_routes.py", "receive_traces", "TRACES_WRITE"),
        # Trace annotations: tenant-allowed — tenants may annotate traces they can read.
        ("routers/v1/trace_api_routes.py", "annotate_trace", "INFERENCE_WRITE"),
        (
            "routers/v1/trace_api_routes.py",
            "delete_annotation_from_trace",
            "INFERENCE_WRITE",
        ),
    ],
)
def test_trace_route_permission_gate(rel_path, func_name, expected):
    actual = _decorator_permission(_SRC / rel_path, func_name)
    assert actual == expected, (
        f"{rel_path}::{func_name} must be gated by "
        f"PermissionLevelsEnum.{expected}.value, found "
        f"PermissionLevelsEnum.{actual}.value"
        if actual
        else f"{rel_path}::{func_name} has no permission_checker decorator"
    )


# --- TRACES_WRITE frozenset content invariants ----------------------------------
#
# The route-gate test above only asserts the route points at TRACES_WRITE; it
# says nothing about which roles that frozenset contains. These tests lock the
# *contents* because the trace ingest path has no org-scope enforcement (the
# target task/org comes from the caller-controlled payload), so this frozenset
# is the only thing preventing a cross-org trace write.


@pytest.mark.unit_tests
def test_traces_write_excludes_tenant_user():
    """THE cross-org isolation invariant. TENANT-USER is the only org-scoped
    role; every other role here is a cross-org operator key (org_id IS NULL).
    Admitting TENANT-USER would let an O1-scoped key write traces into O2's
    tasks, because the write path never checks the caller's org against the
    payload's target task. Never add TENANT_USER to TRACES_WRITE.
    """
    assert (
        constants.TENANT_USER not in PermissionLevelsEnum.TRACES_WRITE.value
    ), "TENANT_USER must never be in TRACES_WRITE — it would allow cross-org trace writes"


@pytest.mark.unit_tests
def test_traces_write_restores_data_plane_ingest_roles():
    """Regression guard for UP-4428. Trace ingest was unintentionally narrowed
    to {ORG_ADMIN, TASK_ADMIN}, dropping the data-plane ingestion roles that
    INFERENCE_WRITE has always granted. Application integration keys
    (VALIDATION-USER) and chatbot keys (CHAT-USER) must keep trace-write.
    """
    traces_write = PermissionLevelsEnum.TRACES_WRITE.value
    for role in (constants.VALIDATION_USER, constants.CHAT_USER):
        assert role in traces_write, f"{role} must retain trace-write access"


@pytest.mark.unit_tests
def test_traces_write_equals_inference_write_minus_tenant_user():
    """TRACES_WRITE is exactly INFERENCE_WRITE minus TENANT_USER. Trace ingest
    and inference submission are the same data-plane action; the only role
    trace ingest withholds is the org-scoped tenant role. If INFERENCE_WRITE
    gains/loses a role, this forces a deliberate decision about TRACES_WRITE.
    """
    inference_write = PermissionLevelsEnum.INFERENCE_WRITE.value
    expected = inference_write - {constants.TENANT_USER}
    assert PermissionLevelsEnum.TRACES_WRITE.value == expected, (
        "TRACES_WRITE drifted from INFERENCE_WRITE - {TENANT_USER}; "
        f"expected {sorted(expected)}, got {sorted(PermissionLevelsEnum.TRACES_WRITE.value)}"
    )
