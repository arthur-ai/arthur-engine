"""Two trees vendor one upstream, and must vendor it at one ref.

The endpoint vendors ai-detection-spec's osquery binding: the queries and the runner a fleet
runs. ml-engine vendors the matcher and the catalog the collector matches with, because it
packages from `packages = ["src/ml_engine"]`, so anything the connector imports at runtime
has to live inside that directory. The two share no file. They must still come from one
release: the row layouts move with it, and a matcher reading rows of another layout
publishes wrong values without anything failing.

Neither half belongs in the other tree. Upstream's own bundler refuses to pack the catalog or
the matcher (`FORBIDDEN = ("catalog/", "agents.yaml", "routes.yaml", "catalog.json",
"bin/classify")`), and a copy beside the deployable is a second one that two people can edit.

Skipped when the integration is absent, so ml-engine remains testable on its own.
"""

import pathlib

import pytest

ML_VENDOR = (
    pathlib.Path(__file__).resolve().parents[3]
    / "src"
    / "ml_engine"
    / "discovery"
    / "_vendor"
)
ENDPOINT_VENDOR = (
    pathlib.Path(__file__).resolve().parents[4]
    / "integrations"
    / "endpoint-ai-discovery"
    / "vendor"
    / "ai-detection-spec"
)

needs_endpoint = pytest.mark.skipif(
    not ENDPOINT_VENDOR.is_dir(),
    reason="endpoint integration not present in this checkout",
)


def _stamp(path: pathlib.Path) -> dict[str, str]:
    """Parse a VERSION stamp written by tools/vendor-queries.sh."""
    out = {}
    for line in (path / "VERSION").read_text().splitlines():
        if line.strip():
            key, _, value = line.partition(" ")
            out[key.strip()] = value.strip()
    return out


@needs_endpoint
@pytest.mark.parametrize("path", ["catalog", "bin/classify"])
def test_the_endpoint_tree_vendors_no_catalog_and_no_matcher(path: str) -> None:
    """Both are the collector's. The endpoint enumerates and matches nothing."""
    assert not (ENDPOINT_VENDOR / path).exists()


@needs_endpoint
def test_both_copies_name_the_same_upstream_ref() -> None:
    """A vendor bump on one side and not the other is the whole risk."""
    ml, endpoint = _stamp(ML_VENDOR), _stamp(ENDPOINT_VENDOR)
    assert ml["sha"] == endpoint["sha"], (
        f"ml-engine vendors {ml['ref']} ({ml['sha'][:12]}) but the endpoint vendors "
        f"{endpoint['ref']} ({endpoint['sha'][:12]}). Vendor the endpoint at the ref you "
        f"want, then run scripts/vendor_ai_detection_spec.py."
    )
    assert ml["ref"] == endpoint["ref"]
    assert ml["repo"] == endpoint["repo"]
