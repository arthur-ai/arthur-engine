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


class TestLoadTimeValidation:
    """A malformed catalog fails once, at load, not once per device.

    The vendored matcher reaches for these keys directly and rebuilds its index inside
    classify(), which runs per Mac -- so without this a bad config raises KeyError on
    every device in the fleet, each time as a scan failure naming a key rather than a
    config naming itself.
    """

    @pytest.mark.parametrize(
        "catalog,expected",
        [
            ({"version": 2}, "no 'agents' list"),
            (
                {"version": 2, "agents": [{"name": "x", "classification": "c"}]},
                "index 0",
            ),
            (
                {"version": 2, "agents": [{"id": "aider", "classification": "c"}]},
                "aider has no 'name'",
            ),
            ({"version": 2, "agents": ["not-a-mapping"]}, "not a mapping"),
        ],
    )
    def test_a_malformed_catalog_is_refused_with_the_entry_named(
        self,
        catalog: dict,
        expected: str,
    ) -> None:
        """The message names the agent id when there is one, else its index."""
        with pytest.raises(ValueError, match=expected):
            Matcher.from_source(catalog_yaml=yaml.safe_dump(catalog))

    @pytest.mark.parametrize(
        "routes,expected",
        [
            ({"routes": {}}, "no 'platforms' list"),
            ({"platforms": ["darwin"]}, "no 'routes' mapping"),
            (
                {"platforms": ["darwin"], "routes": {"npm": {"kind": "npm"}}},
                "route npm has no 'match'",
            ),
            (
                {"platforms": ["darwin"], "routes": {"npm": {"match": "exact"}}},
                "route npm has no 'kind'",
            ),
        ],
    )
    def test_malformed_routes_are_refused_with_the_route_named(
        self,
        routes: dict,
        expected: str,
    ) -> None:
        with pytest.raises(ValueError, match=expected):
            Matcher.from_source(
                catalog_yaml=CATALOG,
                routes_yaml=yaml.safe_dump(routes),
            )

    def test_the_vendored_floor_passes_its_own_validation(self) -> None:
        """The guard must not have made the shipped catalog unloadable."""
        assert Matcher.from_source().agent_count == 22


class TestCatalogHashUsesFileBytes:
    """`catalog_sha` exists to join against upstream's telemetry, so it must be upstream's
    number -- which is sha256 over the file's BYTES."""

    def test_the_floor_still_matches_upstreams_value(self) -> None:
        assert Matcher.from_source().catalog_sha == "dbb22a107953"

    def test_crlf_does_not_change_the_hash_the_way_read_text_would(
        self,
        tmp_path: pathlib.Path,
    ) -> None:
        """Path.read_text() performs universal-newline translation, so a CRLF catalog
        decodes to LF and re-encodes to different bytes than the file holds -- a hash
        that is stable, plausible, and not the one upstream computed."""
        import hashlib

        crlf = CATALOG.replace("\n", "\r\n")
        expected = hashlib.sha256(crlf.encode()).hexdigest()[:12]
        assert Matcher.from_source(catalog_yaml=crlf).catalog_sha == expected
        assert expected != hashlib.sha256(CATALOG.encode()).hexdigest()[:12]


class TestScanTimestamps:
    """A scan row's `ver` comes off a device payload, so it can be anything."""

    @pytest.mark.parametrize("ver", ["²", "not-a-number", "", "1e9"])
    def test_an_unparseable_ver_is_ignored_rather_than_raising(self, ver: str) -> None:
        """`str.isdigit()` is true for characters `int()` refuses -- "²" among them -- so
        the check has to be the conversion itself."""
        m = Matcher.from_source(catalog_yaml=CATALOG)
        assert m.match([scan("apps", ver=ver)]).scanned_at is None

    def test_a_usable_ver_still_wins(self) -> None:
        m = Matcher.from_source(catalog_yaml=CATALOG)
        result = m.match([scan("apps", ver="²"), scan("browser", ver="1790100381")])
        assert result.scanned_at == 1790100381


class TestCatalogShapes:
    """A source config is typed by a person, so these are live risks."""

    def test_a_duplicate_key_is_refused_rather_than_silently_losing_one(self) -> None:
        """yaml.safe_load keeps the last occurrence. An agent carrying `npm:` twice would
        lose its first list, and the fleet would report a missed agent as absent."""
        dupe = (
            "version: 2\n"
            "agents:\n"
            "  - id: codex-cli\n"
            "    name: Codex CLI\n"
            "    classification: Coding agent\n"
            "    platforms: [darwin]\n"
            "    npm: ['@openai/codex']\n"
            "    npm: ['@openai/other']\n"
        )
        with pytest.raises(ValueError, match="duplicate key"):
            Matcher.from_source(catalog_yaml=dupe)

    def test_a_scalar_where_a_list_belongs_is_refused(self) -> None:
        """The vendored matcher indexes a string CHARACTER BY CHARACTER, so
        `npm: openclaw` becomes seven one-letter identifiers -- wrong without erroring.
        """
        scalar = yaml.safe_dump(
            {
                "version": 2,
                "classifications": ["Coding agent"],
                "agents": [
                    {
                        "id": "openclaw",
                        "name": "OpenClaw",
                        "classification": "Coding agent",
                        "platforms": ["darwin"],
                        "npm": "openclaw",
                    },
                ],
            },
        )
        with pytest.raises(ValueError, match="list of strings"):
            Matcher.from_source(catalog_yaml=scalar)

    def test_an_unknown_route_on_an_agent_is_refused(self) -> None:
        bad = yaml.safe_dump(
            {
                "version": 2,
                "classifications": ["Coding agent"],
                "agents": [
                    {
                        "id": "x",
                        "name": "X",
                        "classification": "Coding agent",
                        "platforms": ["darwin"],
                        "not_a_route": ["v"],
                    },
                ],
            },
        )
        with pytest.raises(ValueError, match="unknown route"):
            Matcher.from_source(catalog_yaml=bad)

    def test_an_unhandled_match_mode_is_refused_at_load(self) -> None:
        """build_index raises KeyError on a mode it does not branch on -- once per device
        rather than once at load."""
        routes = yaml.safe_dump(
            {
                "version": 1,
                "platforms": ["darwin"],
                "routes": {"npm": {"kind": "npm", "match": "fuzzy"}},
            },
        )
        with pytest.raises(ValueError, match="match mode"):
            Matcher.from_source(catalog_yaml=CATALOG, routes_yaml=routes)

    def test_a_superseded_entry_without_its_key_is_refused(self) -> None:
        bad = yaml.safe_dump(
            {
                "version": 2,
                "classifications": ["Coding agent"],
                "agents": [
                    {
                        "id": "x",
                        "name": "X",
                        "classification": "Coding agent",
                        "platforms": ["darwin"],
                        "superseded": [{"route": "npm"}],
                    },
                ],
            },
        )
        with pytest.raises(ValueError, match="superseded"):
            Matcher.from_source(catalog_yaml=bad)

    def test_the_shipped_floor_still_loads(self) -> None:
        assert Matcher.from_source().agent_count == 22

    def test_a_catalog_sharing_fields_through_an_anchor_still_loads(self) -> None:
        """`<<` carries a tag PyYAML has no constructor for -- construct_mapping flattens
        it -- so the duplicate check has to skip it rather than construct it. Otherwise
        every catalog using an anchor fails to load while yaml.safe_load accepts it."""
        shared = (
            "version: 2\n"
            "classifications: [Coding agent]\n"
            "_base: &base\n"
            "  classification: Coding agent\n"
            "  platforms: [darwin]\n"
            "agents:\n"
            "  - id: codex-cli\n"
            "    name: Codex CLI\n"
            "    <<: *base\n"
            "    npm: ['@openai/codex']\n"
        )
        m = Matcher.from_source(catalog_yaml=shared)
        assert m.agent_count == 1
        result = m.match([row("npm", "@openai/codex")])
        assert [f.agent_id for f in result.findings] == ["codex-cli"]

    def test_a_merge_key_does_not_disable_duplicate_detection(self) -> None:
        """The skip must be for the merge tag alone, not for the check."""
        dupe = (
            "version: 2\n"
            "_base: &base {classification: Coding agent, platforms: [darwin]}\n"
            "agents:\n"
            "  - id: x\n"
            "    name: X\n"
            "    <<: *base\n"
            "    npm: ['a']\n"
            "    npm: ['b']\n"
        )
        with pytest.raises(ValueError, match="duplicate key"):
            Matcher.from_source(catalog_yaml=dupe)
