"""Route introspection helpers.

FastAPI >= 0.140 changed `APIRouter.include_router`: instead of eagerly
copying each included router's routes into the parent's `app.routes` as
`APIRoute` instances, the parent now holds a single lazy `_IncludedRouter`
object per `include_router` call and resolves the effective routes on demand.

Any code that walks `app.routes` looking for `APIRoute` instances therefore
only sees routes defined directly on the app (a handful), not the hundreds
contributed by included routers. `iter_api_routes` restores the flattened
view by recursing through the nested routers.

Note: every router in this service is included without a prefix (paths are
declared in full on each router), so the yielded `APIRoute.path` values are
already the effective request paths. If a prefixed `include_router` is ever
added, this helper would need to compose the prefix onto the child paths.
"""

from typing import Iterator

from fastapi import FastAPI
from fastapi.routing import APIRoute


def iter_api_routes(app: FastAPI) -> Iterator[APIRoute]:
    """Yield every `APIRoute` reachable from `app`, descending into routers
    that FastAPI >= 0.140 keeps nested rather than flattened."""

    def walk(routes: object) -> Iterator[APIRoute]:
        for route in routes:  # type: ignore[attr-defined]
            if isinstance(route, APIRoute):
                yield route
            # FastAPI >= 0.140: `_IncludedRouter` wraps the original APIRouter,
            # whose `.routes` hold the real (possibly further nested) routes.
            inner = getattr(route, "original_router", None)
            if inner is not None and getattr(inner, "routes", None) is not None:
                yield from walk(inner.routes)

    yield from walk(app.routes)
