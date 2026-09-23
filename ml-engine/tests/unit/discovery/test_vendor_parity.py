"""One file is vendored twice, and the two copies must be the same upstream.

The catalog is NOT one of them any more. It was vendored into the endpoint tree when
the collector was going to live there; the collector is here now, so that copy had no
consumer left -- every reference to it in the endpoint tree is a guard asserting it must
never reach a Mac, which upstream's own bundler enforces anyway
(`FORBIDDEN = ("catalog/", "agents.yaml", "routes.yaml", "bin/classify")`).

What is still duplicated is `bin/classify`, because the endpoint vendors `bin/` as the
unit upstream ships and its runbook documents running the matcher by hand against a
payload. ml-engine cannot share that copy: it packages from `packages = ["src/ml_engine"]`,
so anything the connector imports at runtime has to live inside that directory.

Two copies of one upstream file is the arrangement that drifts silently -- it is the
failure that deleted a hand-written second implementation from the endpoint tree, where
every test passed because the tests tested the copy. So the ref is asserted instead.

Skipped when the integration is absent, so ml-engine remains testable on its own.
"""

import hashlib
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
    / "osquery-ai-discovery"
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
def test_the_endpoint_tree_no_longer_vendors_a_second_catalog() -> None:
    """The signatures are the collector's. A copy beside the deployable is a second
    catalog that nothing reads and that two people can edit."""
    assert not (ENDPOINT_VENDOR / "catalog").exists()


@needs_endpoint
def test_both_copies_name_the_same_upstream_ref() -> None:
    """A vendor bump on one side and not the other is the whole risk."""
    ml, endpoint = _stamp(ML_VENDOR), _stamp(ENDPOINT_VENDOR)
    assert ml["sha"] == endpoint["sha"], (
        f"ml-engine vendors {ml['ref']} ({ml['sha'][:12]}) but the endpoint vendors "
        f"{endpoint['ref']} ({endpoint['sha'][:12]}). Re-vendor both, then regenerate "
        f"_vendor/SHA256SUMS."
    )
    assert ml["ref"] == endpoint["ref"]


@needs_endpoint
@pytest.mark.parametrize("ml_name,endpoint_name", [("classify.py", "bin/classify")])
def test_shared_files_are_byte_identical(ml_name: str, endpoint_name: str) -> None:
    """Same ref is necessary but not sufficient: assert the bytes too.

    `classify.py` is `bin/classify` renamed, which is the only change the vendoring is
    allowed to make. A formatter that reached one copy and not the other would leave the
    refs agreeing and the behaviour diverging, which is the harder failure to see.
    """
    mine = hashlib.sha256((ML_VENDOR / ml_name).read_bytes()).hexdigest()
    theirs = hashlib.sha256((ENDPOINT_VENDOR / endpoint_name).read_bytes()).hexdigest()
    assert (
        mine == theirs
    ), f"{ml_name} and {endpoint_name} differ at the same vendored ref"
