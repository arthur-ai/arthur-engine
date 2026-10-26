"""Catalog documents for tests, in the spec's form (SPEC.md 4).

Built over the vendored catalog's own routes, platforms and classifications, so a test names
only its agents, and every route it uses is declared as the shipped catalog declares it.
"""

import json
import pathlib
from typing import Any, Iterable

_FLOOR = json.loads(
    (
        pathlib.Path(__file__).resolve().parents[2]
        / "src"
        / "ml_engine"
        / "discovery"
        / "_vendor"
        / "catalog.json"
    ).read_text(),
)

# What a superseded identifier must carry (SPEC.md 7.2). A test needs the status, not a proof.
_SUPERSEDED = {
    "last_version": "0.1.0",
    "last_proved": "2026-01-01",
    "by": "a test",
    "run": "0",
}


def agent(
    id: str,
    name: str,
    classification: str,
    platforms: Iterable[str] = ("darwin",),
    superseded: Iterable[tuple[str, str]] = (),
    **routes: list[str],
) -> dict[str, Any]:
    """One agent, its identifiers given per route: `agent("x", "X", "Coding agent",
    npm=["x"])`. A (route, value) in `superseded` belongs to a release the vendor has
    replaced."""
    replaced = set(superseded)
    return {
        "id": id,
        "name": name,
        "classification": classification,
        "platforms": list(platforms),
        "identifiers": [
            (
                {
                    "route": route,
                    "value": value,
                    "status": "superseded",
                    "superseded": _SUPERSEDED,
                }
                if (route, value) in replaced
                else {"route": route, "value": value, "status": "current"}
            )
            for route, values in routes.items()
            for value in values
        ],
    }


def document(*agents: dict[str, Any]) -> str:
    """A catalog document holding `agents`, as the text a source config carries."""
    keep = ("format", "platforms", "platform_groups", "classifications", "routes")
    return json.dumps({**{k: _FLOOR[k] for k in keep}, "agents": list(agents)})
