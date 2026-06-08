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
