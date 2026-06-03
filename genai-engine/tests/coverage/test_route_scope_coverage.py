"""Route fuzz/coverage test (UP-4432, design doc §12).

Walks every FastAPI route on the live `app` and asserts the right
enforcement decorator is wired up:

- Pattern A: routes whose path contains `{task_id}` must carry the
  `enforce_org_scope` marker.
- Pattern D: routes whose handler accepts a `task_id` / `task_ids`
  parameter (directly or as a field on a Pydantic body/dependency) must
  carry the `enforce_query_org_scope` marker.

Pattern B was removed (design §7, commit 72dced7f). Pattern C is repository
-level — not detectable structurally; see the repository coverage test
(stretch, not currently shipped).

When a developer adds a new task-scoped route and forgets the decorator,
this test fails on that exact path. The fix is normally one line.
"""

import inspect
from typing import Optional

import pytest
from fastapi.routing import APIRoute
from pydantic import BaseModel

from tests.clients.base_test_client import app
from utils.constants import TENANT_USER
from utils.users import enforce_org_scope, enforce_query_org_scope


def _walk_wrapped(fn):
    """Yield `fn` and every `__wrapped__` ancestor, defensively bounded."""
    seen: set[int] = set()
    current = fn
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = getattr(current, "__wrapped__", None)


def _has_org_scope_marker(handler, kind: str) -> bool:
    """True when any wrapper in the decorator chain was produced by
    `enforce_org_scope` (kind=='path') or `enforce_query_org_scope`
    (kind=='query')."""
    for fn in _walk_wrapped(handler):
        if (
            getattr(fn, "_org_scope_enforced", False)
            and getattr(fn, "_org_scope_kind", None) == kind
        ):
            return True
    return False


def _is_admin_only(handler) -> bool:
    """Pattern E: route is gated by `permission_checker` with a frozenset
    that excludes TENANT-USER, so tenant keys are rejected before any
    handler logic runs and the org-scope decorator is unnecessary."""
    for fn in _walk_wrapped(handler):
        perms = getattr(fn, "_required_permissions", None)
        if perms is not None and TENANT_USER not in perms:
            return True
    return False


def _is_pydantic_model(annotation) -> bool:
    return inspect.isclass(annotation) and issubclass(annotation, BaseModel)


def _accepts_task_id_or_ids(handler) -> Optional[str]:
    """If the handler accepts `task_id` or `task_ids` directly as a kwarg or
    as a field on a Pydantic body/dependency, return the field name (the
    inner-most occurrence). Otherwise None.

    Mirrors how `_find_task_ids_holder` resolves the param at runtime.
    """
    try:
        sig = inspect.signature(handler)
    except (TypeError, ValueError):
        return None
    for name, p in sig.parameters.items():
        if name in ("task_id", "task_ids"):
            return name
        ann = p.annotation
        if _is_pydantic_model(ann):
            fields = getattr(ann, "model_fields", {})
            if "task_ids" in fields:
                return "task_ids"
            if "task_id" in fields:
                return "task_id"
    return None


def _iter_api_routes():
    for route in app.routes:
        if isinstance(route, APIRoute):
            yield route


# ---------------------------------------------------------------------------
# Pattern A — `{task_id}` in path must have `@enforce_org_scope`.
# ---------------------------------------------------------------------------


def _pattern_a_routes():
    """Routes with `{task_id}` in path, excluding admin-only routes
    (Pattern E — permission_checker rejects tenants first)."""
    return [
        r
        for r in _iter_api_routes()
        if "{task_id}" in r.path and not _is_admin_only(r.endpoint)
    ]


@pytest.mark.unit_tests
def test_pattern_a_routes_exist():
    """Sanity: the design expects ~60 path-scoped routes. If this drops to
    zero, the test is meaningless and probably misconfigured."""
    assert len(_pattern_a_routes()) > 0, "no {task_id} routes discovered"


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "route",
    _pattern_a_routes(),
    ids=lambda r: f"{sorted(r.methods)[0]} {r.path}",
)
def test_pattern_a_route_has_enforce_org_scope(route: APIRoute):
    assert _has_org_scope_marker(route.endpoint, "path"), (
        f"{route.path} has {{task_id}} in path but is missing "
        f"@enforce_org_scope. Add it to the handler in "
        f"{getattr(route.endpoint, '__module__', '?')}."
    )


# ---------------------------------------------------------------------------
# Pattern D — `task_id`/`task_ids` in query or body must have
# `@enforce_query_org_scope`.
# ---------------------------------------------------------------------------


def _pattern_d_routes():
    out = []
    for r in _iter_api_routes():
        # Pattern A routes already carry the path decorator; the query
        # decorator is independent but in practice a /tasks/{task_id}/*
        # endpoint rarely also accepts task_ids in the body. We still skip
        # them here to avoid double-flagging — if a route happens to take
        # both, Pattern A enforcement subsumes Pattern D for the path id.
        if "{task_id}" in r.path:
            continue
        # Pattern E (admin-only) routes are exempt — tenants are rejected
        # by permission_checker before the handler runs.
        if _is_admin_only(r.endpoint):
            continue
        if _accepts_task_id_or_ids(r.endpoint):
            out.append(r)
    return out


@pytest.mark.unit_tests
def test_pattern_d_routes_exist():
    """Sanity: the design expects 11 query-scoped routes."""
    assert len(_pattern_d_routes()) > 0, "no task_ids query routes discovered"


@pytest.mark.unit_tests
@pytest.mark.parametrize(
    "route",
    _pattern_d_routes(),
    ids=lambda r: f"{sorted(r.methods)[0]} {r.path}",
)
def test_pattern_d_route_has_enforce_query_org_scope(route: APIRoute):
    assert _has_org_scope_marker(route.endpoint, "query"), (
        f"{route.path} accepts task_id/task_ids query or body field but is "
        f"missing @enforce_query_org_scope. Add it to the handler in "
        f"{getattr(route.endpoint, '__module__', '?')}."
    )


# ---------------------------------------------------------------------------
# Smoke: removing the marker should make the suite fail.
# ---------------------------------------------------------------------------


@pytest.mark.unit_tests
def test_marker_detection_negative_case():
    """If a handler lacks the marker, the detector must say so. Guards
    against the introspection silently returning True on everything."""

    def plain_handler(task_id: str):
        return task_id

    assert not _has_org_scope_marker(plain_handler, "path")
    assert not _has_org_scope_marker(plain_handler, "query")


@pytest.mark.unit_tests
def test_marker_detection_positive_case():
    """A handler decorated with `@enforce_org_scope` must be detected."""

    @enforce_org_scope()
    async def path_handler(task_id, db_session, current_user):
        return task_id

    @enforce_query_org_scope()
    async def query_handler(task_ids, db_session, current_user):
        return task_ids

    assert _has_org_scope_marker(path_handler, "path")
    assert _has_org_scope_marker(query_handler, "query")
