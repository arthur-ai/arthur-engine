#!/usr/bin/env python
"""Re-vendor discovery/_vendor/ at the ai-detection-spec tag the endpoint vendors.

    integrations/endpoint-ai-discovery/tools/vendor-queries.sh v0.16.2
    cd ml-engine
    uv run python scripts/vendor_ai_detection_spec.py

The tag comes from the endpoint's VERSION stamp, not an argument, and the stamp is
copied byte for byte: the two trees must vendor one ref, and test_vendor_parity.py
fails when they don't.

What comes across, and from where:

    classify.py           the release's `classify`; must equal bin/classify at the tag
    catalog.json          the release's asset, and nothing else's: it is exported when
                          the release is published, so `source.commit` must name the tag
    catalog.schema.json   the release's asset; must equal schema/ at the tag
    evidence.schema.json  likewise
    vectors.json          conformance/vectors.json at the tag; no release attaches it

Each asset must match the sha256 GitHub records for it. Nothing is written until every
file is fetched and checked, so a refusal leaves the tree as it was. SHA256SUMS is
written last, and test_vendor_tree.py holds the tree to it.

Needs `gh`, authenticated for the upstream repo. Only a tag with a published release
can be vendored: a commit the endpoint pins as PROVISIONAL has no catalog.json to bring.
"""

import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from typing import NoReturn

ML_ENGINE = pathlib.Path(__file__).resolve().parents[1]
DEST = ML_ENGINE / "src" / "ml_engine" / "discovery" / "_vendor"
ENDPOINT_STAMP = (
    ML_ENGINE.parent
    / "integrations"
    / "endpoint-ai-discovery"
    / "vendor"
    / "ai-detection-spec"
    / "VERSION"
)
GITHUB = "https://github.com/"

# vendored name -> (release asset, the file at the tag it must equal, if any)
FROM_RELEASE = {
    "classify.py": ("classify", "bin/classify"),
    "catalog.json": ("catalog.json", None),
    "catalog.schema.json": ("catalog.schema.json", "schema/catalog.schema.json"),
    "evidence.schema.json": ("evidence.schema.json", "schema/evidence.schema.json"),
}
FROM_TREE = {"vectors.json": "conformance/vectors.json"}
MANIFEST_ORDER = [*FROM_RELEASE, *FROM_TREE, "VERSION"]
# Arthur's files in the package, not upstream's: never vendored, never in the manifest.
OURS = {"__init__.py", "SHA256SUMS", "__pycache__"}


def fail(message: str) -> NoReturn:
    sys.exit(f"vendor: {message}")


def gh(*args: str) -> bytes:
    try:
        return subprocess.run(["gh", *args], capture_output=True, check=True).stdout
    except FileNotFoundError:
        fail("needs the GitHub CLI, gh")
    except subprocess.CalledProcessError as e:
        fail(f"gh {' '.join(args)}: {e.stderr.decode().strip()}")


def sha256(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def endpoint_stamp() -> tuple[dict[str, str], bytes]:
    if not ENDPOINT_STAMP.is_file():
        fail(f"no {ENDPOINT_STAMP}. Run tools/vendor-queries.sh <tag> there first.")
    raw = ENDPOINT_STAMP.read_bytes()
    stamp: dict[str, str] = {}
    for line in raw.decode().splitlines():
        if line.strip():
            key, _, value = line.partition(" ")
            stamp[key.strip()] = value.strip()
    return stamp, raw


def fetch(repo: str, tag: str, commit: str) -> dict[str, bytes]:
    release = json.loads(gh("release", "view", tag, "-R", repo, "--json", "assets"))
    digests = {a["name"]: a["digest"] for a in release["assets"]}
    assets = [asset for asset, _ in FROM_RELEASE.values()]
    missing = [a for a in assets if not digests.get(a)]
    if missing:
        fail(f"release {tag} has no digest for {', '.join(missing)}")
    got: dict[str, bytes] = {}
    with tempfile.TemporaryDirectory() as tmp:
        patterns = [f"--pattern={a}" for a in assets]
        gh("release", "download", tag, "-R", repo, "-D", tmp, *patterns)
        for name, (asset, tree_path) in FROM_RELEASE.items():
            blob = pathlib.Path(tmp, asset).read_bytes()
            if f"sha256:{sha256(blob)}" != digests[asset]:
                fail(f"{asset} does not match the digest release {tag} records")
            if tree_path and blob != tree_file(repo, commit, tree_path):
                fail(f"release {tag}'s {asset} is not {tree_path} at {commit[:12]}")
            got[name] = blob
    for name, tree_path in FROM_TREE.items():
        got[name] = tree_file(repo, commit, tree_path)
    exported = json.loads(got["catalog.json"])["source"]["commit"]
    if exported != commit:
        fail(
            f"release {tag}'s catalog.json was exported from {exported[:12]}, "
            f"not {commit[:12]}",
        )
    return got


def tree_file(repo: str, commit: str, path: str) -> bytes:
    accept = "Accept: application/vnd.github.raw+json"
    return gh("api", "-H", accept, f"repos/{repo}/contents/{path}?ref={commit}")


def main() -> None:
    stamp, raw_stamp = endpoint_stamp()
    tag, commit, url = stamp["ref"], stamp["sha"], stamp["repo"]
    if stamp["kind"] != "tag":
        fail(
            f"the endpoint pins {tag}, which is not a tag. catalog.json is a release "
            f"asset, so pin a released tag.",
        )
    if not url.startswith(GITHUB):
        fail(f"{url} is not on GitHub, where the release assets come from")
    repo = url.removeprefix(GITHUB).removesuffix(".git")
    tagged = gh("api", f"repos/{repo}/commits/{tag}", "--jq", ".sha").decode().strip()
    if tagged != commit:
        fail(
            f"{tag} now names {tagged[:12]}, but the endpoint vendored {commit[:12]}. "
            f"Re-run vendor-queries.sh.",
        )

    strays = {p.name for p in DEST.iterdir()} - OURS - set(MANIFEST_ORDER)
    if strays:
        fail(
            f"{DEST} holds {', '.join(sorted(strays))}, which this script does not "
            f"vendor. Remove it, or add it here.",
        )

    files = {**fetch(repo, tag, commit), "VERSION": raw_stamp}
    for name in MANIFEST_ORDER:
        (DEST / name).write_bytes(files[name])
    os.chmod(DEST / "classify.py", 0o755)
    manifest = "".join(f"{sha256(files[n])}  {n}\n" for n in MANIFEST_ORDER)
    (DEST / "SHA256SUMS").write_text(manifest)

    # The floor must load through the engine's own Matcher: the vendored reader, schema
    # and catalog, together.
    sys.path.insert(0, str(ML_ENGINE / "src" / "ml_engine"))
    from discovery.catalog import Matcher

    floor = Matcher.from_source()
    vectors = json.loads(files["vectors.json"])["vectors"]
    print(f"vendored {tag} ({commit[:12]}) into {DEST.relative_to(ML_ENGINE)}/")
    print(f"  format       {json.loads(files['catalog.json'])['format']}")
    print(f"  agents       {floor.agent_count}")
    print(f"  catalog_sha  {floor.catalog_sha}")
    print(f"  vectors      {len(vectors)}")
    print()
    print("next: if catalog_sha moved, update its pins in")
    print("      tests/unit/discovery/test_catalog.py, then uv run pytest tests/unit")


if __name__ == "__main__":
    main()
