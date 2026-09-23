"""The vendored upstream tree is verbatim, and stays that way.

This guard is here because it already failed once: running `black` over the discovery
package reformatted upstream's `bin/classify` in place. Nothing broke and every test
still passed -- which is the point. A vendored matcher that has been quietly rewritten
is no longer the reference implementation it is vendored to be, and the next re-vendor
would have produced a diff nobody could explain.

The formatters are excluded from `_vendor/` in `.pre-commit-config.yaml` and mypy
excludes it in `pyproject.toml`. This asserts the outcome rather than the settings, so
it still fails if some future tool arrives without an exclusion.
"""

import hashlib
import pathlib

import pytest

VENDOR = (
    pathlib.Path(__file__).resolve().parents[3]
    / "src"
    / "ml_engine"
    / "discovery"
    / "_vendor"
)
MANIFEST = VENDOR / "SHA256SUMS"


def _manifest() -> dict[str, str]:
    entries = {}
    for line in MANIFEST.read_text().splitlines():
        if line.strip():
            digest, name = line.split(maxsplit=1)
            entries[name.strip()] = digest
    return entries


def test_manifest_covers_every_vendored_file() -> None:
    """A file added to the tree without a checksum would otherwise be unguarded."""
    on_disk = {
        p.name
        for p in VENDOR.iterdir()
        if p.name not in {"__init__.py", "SHA256SUMS", "__pycache__"}
    }
    assert on_disk == set(_manifest())


@pytest.mark.parametrize("name", sorted(_manifest()))
def test_vendored_file_is_unmodified(name: str) -> None:
    actual = hashlib.sha256((VENDOR / name).read_bytes()).hexdigest()
    assert actual == _manifest()[name], (
        f"{name} differs from the vendored upstream release. If a formatter rewrote it, "
        f"restore it and add an exclusion; if you meant to re-vendor, regenerate SHA256SUMS."
    )


def test_vendor_stamp_names_a_real_ref() -> None:
    stamp = dict(
        line.split(maxsplit=1)  # type: ignore[misc]
        for line in (VENDOR / "VERSION").read_text().splitlines()
        if line.strip()
    )
    assert stamp["repo"].strip().endswith("osquery-ai-discovery.git")
    assert stamp["ref"].strip()
    assert len(stamp["sha"].strip()) == 40
