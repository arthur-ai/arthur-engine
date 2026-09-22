"""Matching, and the three things about it that are easy to get quietly wrong.

The grain (one agent through several routes is one finding), gaps (a branch that could
not look is not a branch that found nothing), and dropped rows (a kind absent from the
route registry is discarded in silence by the matcher, which is a bug this project has
already shipped once).
"""

import base64
import gzip
import io
import json
import pathlib

import pytest
import yaml

from discovery.catalog import Matcher, is_gap

COLLECTOR_OUTPUT = pathlib.Path("/var/lib/arthur")

# A catalog small enough to reason about, in the real schema. One agent deliberately
# claims two routes, because that is the case the grain decision turns on.
CATALOG = yaml.safe_dump(
    {
        "version": 2,
        "classifications": ["Coding agent"],
        "agents": [
            {
                "id": "codex-cli",
                "name": "Codex CLI",
                "classification": "Coding agent",
                "platforms": ["darwin"],
                "npm": ["@openai/codex"],
                "binaries": ["~/.local/bin/codex"],
            },
            {
                "id": "claude-desktop",
                "name": "Claude Desktop",
                "classification": "Coding agent",
                "platforms": ["darwin"],
                "bundle_ids": ["com.anthropic.claudefordesktop"],
            },
        ],
    },
)


def row(kind: str, id: str, **over: str) -> dict[str, str]:
    base = {"kind": kind, "id": id, "ver": "", "loc": "", "extra": "", "perms": ""}
    base.update(over)
    return base


def scan(branch: str, extra: str = "ok", ver: str = "1790100381") -> dict[str, str]:
    return row("scan", branch, ver=ver, extra=extra)


@pytest.fixture
def matcher() -> Matcher:
    return Matcher.from_source(catalog_yaml=CATALOG)


# --- the floor ---------------------------------------------------------------------


def test_floor_catalog_is_the_vendored_one() -> None:
    m = Matcher.from_source()
    assert m.agent_count == 22
    # Upstream's own catalog_sha, computed over file bytes. If this changes, the vendor
    # tree moved and every record's recorded catalog version moved with it.
    assert m.catalog_sha == "dbb22a107953"


def test_a_catalog_built_from_a_mapping_marks_its_hash_as_not_upstreams() -> None:
    assert Matcher({"version": 2, "agents": []}, {"routes": {}}).catalog_sha.startswith(
        "norm:",
    )


def test_config_supplied_catalog_replaces_the_floor(matcher: Matcher) -> None:
    assert matcher.agent_count == 2


# --- the grain ---------------------------------------------------------------------


def test_one_agent_through_two_routes_is_one_finding(matcher: Matcher) -> None:
    """The case the (device, agent) grain exists for.

    Codex CLI ships as an npm global AND a CLI shim. Keyed per route this is two
    findings for one install; keyed per agent it is one finding with two rows.
    """
    result = matcher.match(
        [
            row("npm", "@openai/codex", ver="0.5.0"),
            row(
                "file",
                "/Users/nori/.local/bin/codex",
                loc="/Users/nori/.local/bin/codex",
            ),
            scan("packages"),
        ],
    )
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.agent_id == "codex-cli"
    assert len(finding.evidence) == 2
    assert set(finding.kinds) == {"npm", "file"}


def test_primary_kind_prefers_the_earlier_declared_route(matcher: Matcher) -> None:
    """`npm` is declared before `binaries` in routes.yaml, so npm speaks for the finding."""
    result = matcher.match(
        [
            row(
                "file",
                "/Users/nori/.local/bin/codex",
                loc="/Users/nori/.local/bin/codex",
            ),
            row(
                "npm",
                "@openai/codex",
                ver="0.5.0",
                loc="/opt/homebrew/lib/node_modules",
            ),
        ],
    )
    finding = result.findings[0]
    assert finding.primary_kind == "npm"
    assert finding.version == "0.5.0"
    assert finding.install_path == "/opt/homebrew/lib/node_modules"


def test_permissions_split_into_a_tuple(matcher: Matcher) -> None:
    result = matcher.match(
        [row("app", "com.anthropic.claudefordesktop", perms="tabs,<all_urls>")],
    )
    assert result.findings[0].permissions == ("tabs", "<all_urls>")


def test_findings_are_ordered_by_agent_id(matcher: Matcher) -> None:
    result = matcher.match(
        [row("app", "com.anthropic.claudefordesktop"), row("npm", "@openai/codex")],
    )
    assert [f.agent_id for f in result.findings] == ["claude-desktop", "codex-cli"]


# --- gaps are not absence ----------------------------------------------------------


def test_a_branch_that_could_not_look_is_a_gap_not_an_empty_result(
    matcher: Matcher,
) -> None:
    result = matcher.match([scan("containers", extra="unhealthy:000"), scan("apps")])
    assert result.findings == ()
    assert len(result.gaps) == 1
    assert result.gaps[0]["id"] == "containers"
    # The load-bearing assertion: this device must not read as "no agents".
    assert not result.complete


def test_a_healthy_scan_row_is_provenance_not_a_finding(matcher: Matcher) -> None:
    result = matcher.match([scan("apps"), scan("browser")])
    assert result.findings == ()
    assert len(result.scans) == 2
    assert result.gaps == ()
    assert result.complete


@pytest.mark.parametrize(
    "extra",
    [
        "absent",
        "unhealthy:000",
        "unhealthy:no-units",
        "timeout:30",
        "error",
        "no-cache",
    ],
)
def test_every_non_ok_outcome_reads_as_a_gap(matcher: Matcher, extra: str) -> None:
    result = matcher.match([scan("containers", extra=extra)])
    assert len(result.gaps) == 1
    assert is_gap(result.gaps[0])


def test_scanned_at_is_the_newest_ver_across_branches(matcher: Matcher) -> None:
    result = matcher.match(
        [
            scan("apps", ver="1790100381"),
            scan("containers", extra="absent", ver="1790100999"),
        ],
    )
    assert result.scanned_at == 1790100999


def test_scanned_at_is_none_when_no_branch_dated_itself(matcher: Matcher) -> None:
    assert matcher.match([row("npm", "@openai/codex")]).scanned_at is None


# --- the silent drop ---------------------------------------------------------------


def test_a_kind_absent_from_the_registry_is_counted_not_lost(matcher: Matcher) -> None:
    """Upstream discards these without counting them. That is the historical `ext` bug:
    rows collected correctly, never surfaced, for months, while row counts stayed right.
    """
    result = matcher.match([row("wormhole", "something"), row("npm", "@openai/codex")])
    assert result.dropped == 1
    assert result.rows_total == 2


def test_arithmetic_reconciles_when_nothing_is_dropped(matcher: Matcher) -> None:
    rows = [
        row("npm", "@openai/codex"),
        row("app", "com.unrelated.thing"),
        scan("apps"),
    ]
    result = matcher.match(rows)
    evidence = sum(len(f.evidence) for f in result.findings)
    assert (
        evidence + result.unmatched + len(result.gaps) + len(result.scans)
        == result.rows_total
    )
    assert result.dropped == 0


def test_version_skew_warns_rather_than_refusing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Refusing would read downstream as a clean fleet, which is the error to avoid."""
    newer = yaml.safe_dump({"version": 99, "agents": []})
    Matcher.from_source(catalog_yaml=newer)
    assert "Matching what it can" in caplog.text


# --- against what actually ships ---------------------------------------------------


@pytest.mark.skipif(
    not (COLLECTOR_OUTPUT / "inventory.ea").is_file(),
    reason="no collector output on this machine; run arthur-discovery's dist/collect.sh",
)
def test_real_payload_reconciles_and_collapses_routes() -> None:
    ea = (COLLECTOR_OUTPUT / "inventory.ea").read_text().strip()
    rows = json.loads(
        gzip.GzipFile(
            fileobj=io.BytesIO(base64.b64decode(ea[8:], validate=True)),
        ).read(),
    )

    result = Matcher.from_source().match(rows)

    evidence = sum(len(f.evidence) for f in result.findings)
    assert (
        evidence + result.unmatched + len(result.gaps) + len(result.scans)
        == result.rows_total
    )
    assert result.dropped == 0, "a route is missing from the vendored routes.yaml"
    assert result.findings, "this Mac is known to carry agents"
    # The grain actually collapsing something, on real evidence rather than a fixture.
    assert evidence > len(result.findings)
    assert result.scanned_at is not None
