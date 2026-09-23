"""Matching enumerated endpoint rows against the agent catalog.

The endpoint enumerates and the collector classifies: a managed Mac ships ~875 rows naming
every application, formula and extension on it, and holds no catalog. That split is what
lets a new signature re-match evidence already collected instead of triggering a fleet
re-scan.

Upstream's `bin/classify` is called, not reimplemented -- its own docstring says any
implementation that disagrees with it is wrong. Measured at 0.61 ms for an 875-row
payload, so 10,000 Macs cost about six seconds. Calling it as a library also sends no
telemetry: upstream raises its Amplitude event in `main()`, not in the matcher.
"""

import hashlib
import importlib.machinery
import importlib.util
import logging
import pathlib
from dataclasses import dataclass
from types import ModuleType
from typing import Any, Mapping, Optional, Sequence

import yaml

_VENDOR = pathlib.Path(__file__).resolve().parent / "_vendor"

# The floor. A Discovery Source Config carries the catalog that actually runs, so these
# are only what an unconfigured source falls back to.
_FLOOR_CATALOG = _VENDOR / "agents.yaml"
_FLOOR_ROUTES = _VENDOR / "routes.yaml"

_GAP_KIND = "scan"
_SCAN_OK = "ok"


def _load_matcher() -> ModuleType:
    """Import the vendored `bin/classify` as a module.

    By path, because upstream ships it extensionless and it is vendored verbatim --
    renaming it to `.py` is the only change the vendoring makes.
    """
    loader = importlib.machinery.SourceFileLoader(
        "_ai_discovery_classify",
        str(_VENDOR / "classify.py"),
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if (
        spec is None
    ):  # pragma: no cover -- defensive; a missing vendor tree is a build fault
        raise RuntimeError(f"vendored matcher is not loadable at {_VENDOR}")
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


_matcher = _load_matcher()


@dataclass(frozen=True)
class Finding:
    """One agent on one device, with every row that proved it.

    Per (device, agent), not per row: one agent commonly arrives through several routes at
    once -- Codex CLI as an npm package and a CLI shim, Claude Desktop as a bundle id and
    a native-messaging host -- and a per-route finding reports one install several times.
    Measured on a developer Mac: 10 agents across 20 evidence rows.
    """

    agent_id: str
    name: str
    classification: str
    evidence: tuple[dict[str, Any], ...]
    primary_kind: str
    primary_id: str
    version: Optional[str]
    install_path: Optional[str]
    permissions: tuple[str, ...]

    @property
    def kinds(self) -> tuple[str, ...]:
        """Every route kind that proved this agent, in the order they appeared."""
        seen: dict[str, None] = {}
        for row in self.evidence:
            seen.setdefault(str(row.get("kind", "")), None)
        return tuple(seen)


@dataclass(frozen=True)
class MatchResult:
    """What one device's payload turned out to hold.

    A non-`ok` scan row means a branch could not look -- a wedged Docker daemon, a missing
    table -- not that it found nothing. Absence is only assertable for branches whose
    marker says `ok`, so reading `findings` without `gaps` draws the wrong conclusion.
    """

    findings: tuple[Finding, ...]
    gaps: tuple[dict[str, Any], ...]
    scans: tuple[dict[str, Any], ...]
    unmatched: int
    dropped: int
    rows_total: int

    @property
    def complete(self) -> bool:
        """True when every branch reported `ok`, so absence means absence."""
        return not self.gaps

    @property
    def scanned_at(self) -> Optional[int]:
        """The newest `ver` across scan rows: when this device last looked.

        The payload's own timestamp, not a file mtime -- redeploying the file resets the
        mtime without changing the truth.
        """
        stamps = [
            int(r["ver"])
            for r in (*self.scans, *self.gaps)
            if str(r.get("ver", "")).isdigit()
        ]
        return max(stamps) if stamps else None


class Matcher:
    """The catalog, loaded once and reused across every device in a scan.

    Upstream rebuilds its index inside `classify()` -- 13% of the 0.6 ms per device, not
    worth defeating. Re-parsing the YAML per device would be.
    """

    def __init__(
        self,
        catalog: Mapping[str, Any],
        routes: Mapping[str, Any],
        logger: Optional[logging.Logger] = None,
        catalog_source: Optional[bytes] = None,
    ) -> None:
        self._catalog = dict(catalog)
        self._routes = dict(routes)
        self._catalog_source = catalog_source
        self._log = logger or logging.getLogger(__name__)
        self._route_rank = self._rank_routes(self._routes)

        version = self._catalog.get("version")
        if isinstance(version, int) and version > _matcher.CATALOG_VERSION:
            # Refusing would read downstream as a clean fleet.
            self._log.warning(
                "catalog is version %s; the vendored matcher understands %s. "
                "Matching what it can -- newer routes arrive as unmatched rows.",
                version,
                _matcher.CATALOG_VERSION,
            )

    @staticmethod
    def _rank_routes(routes: Mapping[str, Any]) -> dict[str, int]:
        """Rank each row kind by where its route is declared in routes.yaml.

        Picks which row speaks for a finding when several proved it. Upstream's order,
        which puts vendor-controlled identifiers first -- a bundle id before a path glob,
        an OCI label before a tag anyone can set. A tie-break, not a claim about truth.
        """
        rank: dict[str, int] = {}
        declared = routes.get("routes") or {}
        for i, (_name, spec) in enumerate(declared.items()):
            kind = (spec or {}).get("kind")
            if isinstance(kind, str) and kind not in rank:
                rank[kind] = i
        return rank

    @classmethod
    def from_source(
        cls,
        catalog_yaml: Optional[str] = None,
        routes_yaml: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ) -> "Matcher":
        """Build from config-supplied YAML, falling back to the vendored floor.

        Signatures ride in the source config, so adding one is a config change rather than
        an image rebuild and works on an engine with no route to the internet.
        """
        catalog_bytes = (
            catalog_yaml.encode() if catalog_yaml else _FLOOR_CATALOG.read_bytes()
        )
        routes_bytes = (
            routes_yaml.encode() if routes_yaml else _FLOOR_ROUTES.read_bytes()
        )
        catalog = yaml.safe_load(catalog_bytes.decode("utf-8"))
        routes = yaml.safe_load(routes_bytes.decode("utf-8"))
        if not isinstance(catalog, dict) or not isinstance(routes, dict):
            raise ValueError("catalog and routes must each parse to a YAML mapping")
        _validate(catalog, routes)
        return cls(catalog, routes, logger, catalog_source=catalog_bytes)

    @property
    def catalog_sha(self) -> str:
        """First 12 hex of sha256 over the catalog, matching upstream's `catalog_sha`.

        A content hash rather than a revision field, for upstream's stated reason: a
        hand-bumped number is one more thing that can be wrong, and a hash is true by
        construction. Recorded per record so a finding stays diagnosable later.

        Over the SOURCE BYTES, because that is what upstream's `_sha()` hashes. A
        re-serialized parse, or text decoded through `read_text()`'s universal-newline
        translation, gives a number that is stable, plausible and agrees with nothing.
        """
        if self._catalog_source is None:
            # Built from a mapping with no source text. Still stable and still useful
            # for spotting drift between runs, but it is not upstream's number, so it
            # is marked rather than passed off as one.
            blob = yaml.safe_dump(self._catalog, sort_keys=True).encode()
            return "norm:" + hashlib.sha256(blob).hexdigest()[:12]
        return hashlib.sha256(self._catalog_source).hexdigest()[:12]

    @property
    def agent_count(self) -> int:
        return len(self._catalog.get("agents") or ())

    def match(self, rows: Sequence[Mapping[str, Any]]) -> MatchResult:
        """Classify one device's payload.

        Reconciles its own arithmetic: upstream drops a row whose `kind` is not in the
        route registry -- neither matched nor unmatched, just gone. That shipped once,
        browser-extension rows invisible for months while row counts stayed right.
        """
        raw = [dict(r) for r in rows]
        findings_by_agent, unmatched, gaps, scans = _matcher.classify(
            raw,
            self._catalog,
            self._routes,
        )

        findings = tuple(
            sorted(
                (
                    self._build(agent_id, evidence)
                    for agent_id, evidence in findings_by_agent.items()
                ),
                key=lambda f: f.agent_id,
            ),
        )

        evidence_rows = sum(len(f.evidence) for f in findings)
        dropped = max(
            0,
            len(raw) - evidence_rows - len(unmatched) - len(gaps) - len(scans),
        )
        if dropped:
            self._log.warning(
                "%s row(s) carried a kind absent from the route registry and were dropped by the "
                "matcher; a route is missing from routes.yaml",
                dropped,
            )

        return MatchResult(
            findings=findings,
            gaps=tuple(gaps),
            scans=tuple(scans),
            unmatched=len(unmatched),
            dropped=dropped,
            rows_total=len(raw),
        )

    def _build(
        self,
        agent_id: str,
        evidence: Sequence[tuple[Mapping[str, Any], Mapping[str, Any]]],
    ) -> Finding:
        rows = [dict(row) for _hit, row in evidence]
        meta = dict(evidence[0][0])

        primary = min(
            rows,
            key=lambda r: self._route_rank.get(
                str(r.get("kind", "")),
                len(self._route_rank),
            ),
        )

        perms = str(primary.get("perms") or "")
        return Finding(
            agent_id=agent_id,
            name=str(meta.get("name") or agent_id),
            classification=str(meta.get("classification") or ""),
            evidence=tuple(rows),
            primary_kind=str(primary.get("kind") or ""),
            primary_id=str(primary.get("id") or ""),
            version=str(primary.get("ver")) or None if primary.get("ver") else None,
            install_path=(
                str(primary.get("loc")) or None if primary.get("loc") else None
            ),
            permissions=tuple(p for p in perms.split(",") if p),
        )


def _validate(catalog: Mapping[str, Any], routes: Mapping[str, Any]) -> None:
    """Fail a malformed catalog once, at load, rather than once per device.

    The matcher reaches for these keys directly and rebuilds its index inside `classify()`,
    which runs per device -- so without this, a bad config raises KeyError on every Mac in
    the fleet, each time naming a key rather than the config entry that is wrong.
    """
    agents = catalog.get("agents")
    if not isinstance(agents, list):
        raise ValueError("catalog has no 'agents' list")
    for i, agent in enumerate(agents):
        if not isinstance(agent, dict):
            raise ValueError(f"catalog agent at index {i} is not a mapping")
        for key in ("id", "name", "classification"):
            if not agent.get(key):
                where = agent.get("id") or f"index {i}"
                raise ValueError(f"catalog agent {where} has no '{key}'")

    if not isinstance(routes.get("platforms"), list):
        raise ValueError("routes has no 'platforms' list")
    declared = routes.get("routes")
    if not isinstance(declared, dict):
        raise ValueError("routes has no 'routes' mapping")
    for name, spec in declared.items():
        if not isinstance(spec, dict):
            raise ValueError(f"route {name} is not a mapping")
        for key in ("kind", "match"):
            if not spec.get(key):
                raise ValueError(f"route {name} has no '{key}'")


def is_gap(row: Mapping[str, Any]) -> bool:
    """A scan row saying a branch could not look, as opposed to one saying it did."""
    return row.get("kind") == _GAP_KIND and row.get("extra") != _SCAN_OK
