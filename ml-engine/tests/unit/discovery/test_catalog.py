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
from typing import Any

import pytest

from discovery.catalog import Matcher
from job_executors.discovery_scan import (
    DiscoveryConfigurationError,
    DiscoveryErrorCode,
    failure_code,
)
from tests.fakes.catalog import agent, document

COLLECTOR_OUTPUT = pathlib.Path("/var/lib/arthur")

# A catalog small enough to reason about, in the real schema. One agent deliberately
# claims two routes, because that is the case the grain decision turns on.
CATALOG = document(
    agent(
        "codex-cli",
        "Codex CLI",
        "Coding agent",
        npm=["@openai/codex"],
        binaries=["~/.local/bin/codex"],
    ),
    agent(
        "claude-desktop",
        "Claude Desktop",
        "Coding agent",
        bundle_ids=["com.anthropic.claudefordesktop"],
    ),
)


def row(kind: str, id: str, **over: str) -> dict[str, str]:
    base = {"kind": kind, "id": id, "ver": "", "loc": "", "extra": "", "perms": ""}
    base.update(over)
    return base


def scan(branch: str, extra: str = "ok", ver: str = "1790100381") -> dict[str, str]:
    return row("scan", branch, ver=ver, extra=extra)


@pytest.fixture
def matcher() -> Matcher:
    return Matcher.from_source(catalog_json=CATALOG)


# --- the floor ---------------------------------------------------------------------


def test_floor_catalog_is_the_vendored_one() -> None:
    m = Matcher.from_source()
    assert m.agent_count == 42
    # Upstream's own catalog_sha, computed over file bytes. If this changes, the vendor
    # tree moved and every record's recorded catalog version moved with it.
    assert m.catalog_sha == "4864f6a03d02"


def test_a_catalog_built_from_a_mapping_marks_its_hash_as_not_upstreams() -> None:
    assert Matcher(
        {"version": 3, "agents": []},
        {"platforms": ["darwin"], "routes": {}},
    ).catalog_sha.startswith("norm:")


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


def test_an_install_record_speaks_before_a_path(matcher: Matcher) -> None:
    """The npm row, read from a package manifest, describes the finding: its version and its
    install path. The rule is upstream's `primary()`; this holds the mapping to it."""
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


def test_a_running_row_does_not_speak_for_an_installed_agent(matcher: Matcher) -> None:
    """`proc` is declared before `npm` in the catalog's routes, but a process row carries no version
    and names an executable, not an install. Presence speaks; liveness stays evidence.
    """
    result = matcher.match(
        [
            row(
                "npm",
                "@openai/codex",
                ver="0.5.0",
                loc="/opt/homebrew/lib/node_modules/@openai/codex",
            ),
            row(
                "proc",
                "@openai/codex",
                loc="/opt/homebrew/lib/node_modules/@openai/codex/bin/codex",
            ),
        ],
    )
    finding = result.findings[0]
    assert finding.primary_kind == "npm"
    assert finding.version == "0.5.0"
    assert finding.install_path == "/opt/homebrew/lib/node_modules/@openai/codex"
    assert finding.kinds == ("npm", "proc")


def test_a_running_row_speaks_when_nothing_else_proved_the_agent(
    matcher: Matcher,
) -> None:
    result = matcher.match(
        [
            row(
                "proc",
                "@openai/codex",
                loc="/opt/homebrew/lib/node_modules/@openai/codex/bin/codex",
            ),
        ],
    )
    finding = result.findings[0]
    assert finding.primary_kind == "proc"
    assert finding.version is None
    # A process row's `loc` is the app, the agent binary or the node interpreter running
    # it, depending on the query, so it is not reported as where the agent is installed.
    assert finding.install_path is None


def test_a_bundle_without_a_version_still_speaks_before_its_cask() -> None:
    """The kind makes an install record, not whether its version could be read. Ranked by
    the version string, the record moved to the Caskroom whenever a bundle had none."""
    result = Matcher.from_source().match(
        [
            row("brew", "claude", ver="1.2.3", loc="/opt/homebrew/Caskroom/claude"),
            row(
                "app",
                "com.anthropic.claudefordesktop",
                loc="/Applications/Claude.app",
            ),
        ],
    )
    (finding,) = result.findings
    assert (finding.primary_kind, finding.primary_id) == (
        "app",
        "com.anthropic.claudefordesktop",
    )
    assert finding.version is None
    assert finding.install_path == "/Applications/Claude.app"


def test_a_current_identifier_speaks_before_one_the_vendor_replaced() -> None:
    """The matcher hands upstream which rows matched a superseded identifier. Without the
    flags, evidence order would let the replaced generation describe the finding."""
    catalog = document(
        agent(
            "openclaw",
            "OpenClaw",
            "Personal agent",
            superseded=[("npm", "moltbot")],
            npm=["openclaw", "moltbot"],
        ),
    )
    result = Matcher.from_source(catalog_json=catalog).match(
        [
            row(
                "npm",
                "moltbot",
                ver="0.1.0",
                loc="/opt/homebrew/lib/node_modules/moltbot",
            ),
            row(
                "npm",
                "openclaw",
                ver="2026.9.1",
                loc="/opt/homebrew/lib/node_modules/openclaw",
            ),
        ],
    )
    (finding,) = result.findings
    assert (finding.primary_id, finding.version) == ("openclaw", "2026.9.1")


def test_a_version_that_is_not_text_is_reported_as_text(matcher: Matcher) -> None:
    """`match()` is public and takes rows that never passed the envelope's checks, while
    the record's version is a strict string field."""
    rows: list[dict[str, Any]] = [
        {**row("npm", "@openai/codex", loc="/opt/homebrew/lib/node_modules"), "ver": 2},
    ]
    assert matcher.match(rows).findings[0].version == "2"


def test_an_apt_install_keeps_its_version_once_the_agent_has_run() -> None:
    """dpkg's row off a real apt install on Ubuntu 22.04, beside the state directory the
    first run creates. `file` is declared ahead of `deb` in the routes, and ranked by that
    alone the record lost its version and changed address on the user's first run."""
    result = Matcher.from_source().match(
        [
            row("file", "/home/dana/.claude/", loc="/home/dana/.claude/"),
            row("deb", "claude-code", ver="2.1.292-1"),
        ],
    )
    (finding,) = result.findings
    assert finding.agent_id == "claude-code"
    assert (finding.primary_kind, finding.primary_id) == ("deb", "claude-code")
    assert finding.version == "2.1.292-1"
    assert finding.install_path is None


_CLAUDE_IN_CHROME = document(
    agent(
        "claude-in-chrome",
        "Claude in Chrome",
        "Browser agent",
        extension_ids=["fcoeoabgfenejglbffodgkkbkcdhcgfn"],
    ),
)


def test_the_copy_the_browser_loads_speaks_before_a_leftover() -> None:
    """A profile keeps old version directories, and browser.sql marks each one Chrome never
    loads `unreferenced`, after the browser in `extra`. Read off a real profile: seven
    leftovers listed before the copy Chrome loads, so the first row reported a version that
    was not running."""
    ext = "fcoeoabgfenejglbffodgkkbkcdhcgfn"
    result = Matcher.from_source(catalog_json=_CLAUDE_IN_CHROME).match(
        [
            row("ext", ext, ver="1.0.94", extra="chrome,unreferenced", perms="tabs"),
            row("ext", ext, ver="1.0.97", extra="chrome,unreferenced", perms="tabs"),
            row(
                "ext",
                ext,
                ver="1.0.91",
                extra="chrome",
                perms="tabs, storage, debugger",
            ),
        ],
    )
    finding = result.findings[0]
    assert finding.version == "1.0.91"
    assert finding.permissions == ("tabs", "storage", "debugger")
    assert len(finding.evidence) == 3


def test_a_leftover_still_speaks_when_no_copy_is_loaded() -> None:
    ext = "fcoeoabgfenejglbffodgkkbkcdhcgfn"
    result = Matcher.from_source(catalog_json=_CLAUDE_IN_CHROME).match(
        [
            row("ext", ext, ver="1.0.94", extra="chrome,unreferenced", perms="tabs"),
            row("ext", ext, ver="1.0.97", extra="chrome,unreferenced", perms="tabs"),
        ],
    )
    assert result.findings[0].version == "1.0.94"


def test_permissions_split_into_a_tuple(matcher: Matcher) -> None:
    result = matcher.match(
        [row("app", "com.anthropic.claudefordesktop", perms="tabs,<all_urls>")],
    )
    assert result.findings[0].permissions == ("tabs", "<all_urls>")


@pytest.mark.parametrize("mark", ["unreferenced", "sideloaded:9f2c4e"])
def test_extension_provenance_is_not_a_permission(mark: str) -> None:
    """browser.sql marks an extension `unreferenced` or `sideloaded:<sha256>` after the
    browser in `extra`, and `perms` holds only permissions, joined by osquery with ", ".
    """
    result = Matcher.from_source(catalog_json=_CLAUDE_IN_CHROME).match(
        [
            row(
                "ext",
                "fcoeoabgfenejglbffodgkkbkcdhcgfn",
                extra=f"chrome,{mark}",
                perms="tabs, <all_urls>",
            ),
        ],
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
        "unhealthy:000",
        "unhealthy:no-units",
        "timeout:30",
        "error",
        "no-cache",
        "unreadable:podman",
    ],
)
def test_a_branch_that_could_not_look_reads_as_a_gap(
    matcher: Matcher,
    extra: str,
) -> None:
    result = matcher.match([scan("containers", extra=extra)])
    assert len(result.gaps) == 1
    assert not result.complete, "findings are partial while a branch went unread"


def test_absent_is_a_reading_and_not_a_gap(matcher: Matcher) -> None:
    """`absent` says the branch read the machine and there was nothing there -- no
    container runtime, no systemd bus. Counting it as a gap makes every Mac without
    Docker permanently unable to say absence is assertable, which is false about the
    thing anyone would ask."""
    result = matcher.match([scan("containers", extra="absent")])
    assert result.gaps == ()
    assert len(result.absences) == 1
    assert result.complete, "nothing went unread, so absence means absence"


def test_a_runtime_that_is_present_but_unread_is_still_a_gap(matcher: Matcher) -> None:
    """The distinction `absent` is safe to reclassify BECAUSE of: a Podman host holds
    containers this scan does not count, which is a hole and not an absence."""
    result = matcher.match([scan("containers", extra="unreadable:podman")])
    assert result.absences == ()
    assert len(result.gaps) == 1
    assert not result.complete


def test_an_absence_is_not_counted_as_a_dropped_row(matcher: Matcher) -> None:
    """Absences are a bucket of their own. Counted as rows the matcher lost, they would
    raise the alarm that says a route is missing from the catalog."""
    result = matcher.match(
        [
            scan("apps"),
            scan("containers", extra="absent"),
            scan("systemd", extra="absent"),
        ],
    )
    assert result.dropped == 0
    assert result.rows_total == 3


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
    """A row whose kind no route declares can never match, and is neither matched nor
    unmatched. That is the historical `ext` bug: rows collected correctly, never surfaced,
    for months, while row counts stayed right.
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


def test_a_catalog_that_is_not_a_document_is_refused() -> None:
    """The authoring form a release builds its document from is not read here."""
    with pytest.raises(ValueError, match="not JSON"):
        Matcher.from_source(catalog_json="version: 3\nagents: []\n")
    with pytest.raises(ValueError, match="names no `format`"):
        Matcher.from_source(catalog_json=json.dumps({"version": 3, "agents": []}))


def test_a_catalog_document_the_schema_refuses_is_refused() -> None:
    """Validated before it is read (SPEC.md 4), so a document missing a member fails the
    scan, naming the member, rather than matching what is left."""
    document = json.loads(CATALOG)
    del document["classifications"]
    with pytest.raises(ValueError, match="classifications"):
        Matcher.from_source(catalog_json=json.dumps(document))


def test_a_duplicate_key_in_a_catalog_document_is_refused() -> None:
    text = CATALOG.replace(
        '"format": "ai-detection-spec/0.2"',
        '"format": "ai-detection-spec/0.2", "format": "ai-detection-spec/0.2"',
    )
    with pytest.raises(ValueError, match="duplicate key 'format'"):
        Matcher.from_source(catalog_json=text)


@pytest.mark.parametrize(
    "text",
    [
        "version: 3\nagents: []\n",
        json.dumps({"version": 3, "agents": []}),
        CATALOG.replace('"classifications"', '"classification"'),
        CATALOG.replace(
            '"format": "ai-detection-spec/0.2"',
            '"format": "ai-detection-spec/0.2", "format": "ai-detection-spec/0.2"',
        ),
        # The catalog.json v0.15.0 attached. A source config pasted from it is refused on
        # every scan once the engine moves to 0.2, and only the config can fix that.
        CATALOG.replace('"ai-detection-spec/0.2"', '"ai-detection-spec/0.1"'),
    ],
    ids=["not-json", "no-format", "schema", "duplicate-key", "previous-format"],
)
def test_a_refused_catalog_fails_the_scan_as_the_configs_to_fix(text: str) -> None:
    """A plain ValueError reaches the Platform as PROVIDER_ERROR, the vendor's fault, and
    the admin is sent to Jamf or AWS for a catalog only they can replace."""
    with pytest.raises(DiscoveryConfigurationError) as refused:
        Matcher.from_source(catalog_json=text)
    assert failure_code(refused.value) == DiscoveryErrorCode.NOT_CONFIGURED


def test_an_identifier_on_a_route_that_borrows_another_is_refused() -> None:
    """`running_apps` matches `bundle_ids` identifiers and has none of its own, so one
    placed on it would match nothing, in silence (SPEC.md 4.4 rule 1)."""
    bad = document(
        agent("x", "X", "Coding agent", running_apps=["com.example.agent"]),
    )
    with pytest.raises(ValueError, match="running_apps"):
        Matcher.from_source(catalog_json=bad)


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
    # Every bucket, so a Mac without Docker -- an `absent` marker -- reconciles too.
    assert (
        evidence
        + result.unmatched
        + len(result.gaps)
        + len(result.scans)
        + len(result.absences)
        + result.dropped
        == result.rows_total
    )
    assert result.dropped == 0, "a route is missing from the vendored catalog"
    assert result.findings, "this Mac is known to carry agents"
    # The grain actually collapsing something, on real evidence rather than a fixture.
    assert evidence > len(result.findings)
    assert result.scanned_at is not None


class TestCatalogHashUsesFileBytes:
    """`catalog_sha` exists to join against upstream's telemetry, so it must be upstream's
    number -- which is sha256 over the file's BYTES."""

    def test_the_floor_still_matches_upstreams_value(self) -> None:
        assert Matcher.from_source().catalog_sha == "4864f6a03d02"

    def test_crlf_does_not_change_the_hash_the_way_read_text_would(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """Path.read_text() performs universal-newline translation, so a CRLF catalog
        decodes to LF and re-encodes to different bytes than the file holds -- a hash
        that is stable, plausible, and not the one upstream computed."""
        import hashlib

        lf = json.dumps(json.loads(CATALOG), indent=1)
        crlf = lf.replace("\n", "\r\n")
        expected = hashlib.sha256(crlf.encode()).hexdigest()[:12]
        assert Matcher.from_source(catalog_json=crlf).catalog_sha == expected
        assert expected != hashlib.sha256(lf.encode()).hexdigest()[:12]


class TestScanTimestamps:
    """A scan row's `ver` comes off a device payload, so it can be anything."""

    @pytest.mark.parametrize("ver", ["²", "not-a-number", "", "1e9"])
    def test_an_unparseable_ver_is_ignored_rather_than_raising(self, ver: str) -> None:
        """`str.isdigit()` is true for characters `int()` refuses -- "²" among them -- so
        the check has to be the conversion itself."""
        m = Matcher.from_source(catalog_json=CATALOG)
        assert m.match([scan("apps", ver=ver)]).scanned_at is None

    def test_a_usable_ver_still_wins(self) -> None:
        m = Matcher.from_source(catalog_json=CATALOG)
        result = m.match([scan("apps", ver="²"), scan("browser", ver="1790100381")])
        assert result.scanned_at == 1790100381
