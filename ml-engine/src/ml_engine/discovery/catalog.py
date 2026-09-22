"""Matching enumerated endpoint rows against the agent catalog.

The endpoint enumerates and the collector classifies -- a managed Mac ships ~875 rows
naming every application, Homebrew formula and browser extension on it, and holds no
catalog at all. That split is what lets a new signature re-match evidence already
collected instead of triggering a fleet re-scan, and it is why this module exists on
this side of the wire.

UPSTREAM'S MATCHER IS CALLED, NOT REIMPLEMENTED. `_vendor/classify.py` is `bin/classify`
verbatim, and its own docstring says why: "if you want to know what a signature means,
this is the answer, and any other implementation that disagrees with it is wrong." A
second matcher here would be a second answer to that question, which is the failure the
whole vendoring arrangement exists to prevent. Measured at 0.61 ms for an 875-row
payload, so 10,000 Macs cost about six seconds and there is nothing to optimise by
inlining the loop.

Calling `classify()` as a library function also sends no telemetry. Upstream's
Amplitude event is raised in `main()`, not in the matcher, so importing it is silent by
construction rather than by remembering to set an environment variable -- which matters
because this runs inside a customer network.
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

    Loaded by path rather than as a normal import because upstream ships it as an
    extensionless executable and it is vendored verbatim; renaming it to `.py` is the
    only change the vendoring makes.
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

    The grain is per (device, agent) rather than per row: one agent commonly arrives
    through several routes at once -- Codex CLI as both an npm package and a CLI shim,
    Claude Desktop as a bundle id and a native-messaging host -- and emitting one
    finding per route would report a single install several times over. Measured on a
    developer Mac: 10 agents across 20 evidence rows.
    """

    agent_id: str
    name: str
    classification: str
    evidence: tuple[dict[str, Any], ...]
    primary_kind: str
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

    `gaps` is the half that is easy to drop and expensive to drop. A non-`ok` scan row
    means a branch could not look -- a wedged Docker daemon, a table this osquery build
    lacks -- and it is NOT a report that the branch found nothing. Absence is only
    assertable for branches whose marker says `ok`, so a consumer that reads `findings`
    without reading `gaps` is drawing the wrong conclusion from the right data.
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
        """The newest `ver` across scan rows: when this device last actually looked.

        Unix seconds, and the payload's own timestamp rather than anything derived from
        a file's mtime -- a config-management tool that redeploys the file resets the
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

    Holding it is what makes the per-device cost 0.6 ms: upstream rebuilds its index
    inside `classify()`, which is 13% of that and not worth defeating, but re-reading
    and re-parsing the YAML per device would not be.
    """

    def __init__(
        self,
        catalog: Mapping[str, Any],
        routes: Mapping[str, Any],
        logger: Optional[logging.Logger] = None,
        catalog_source: Optional[str] = None,
    ) -> None:
        self._catalog = dict(catalog)
        self._routes = dict(routes)
        self._catalog_source = catalog_source
        self._log = logger or logging.getLogger(__name__)
        self._route_rank = self._rank_routes(self._routes)

        version = self._catalog.get("version")
        if isinstance(version, int) and version > _matcher.CATALOG_VERSION:
            # Upstream's choice, and the right one: refusing would read downstream as a
            # clean fleet, which is the single error this project is built against.
            self._log.warning(
                "catalog is version %s; the vendored matcher understands %s. "
                "Matching what it can -- newer routes arrive as unmatched rows.",
                version,
                _matcher.CATALOG_VERSION,
            )

    @staticmethod
    def _rank_routes(routes: Mapping[str, Any]) -> dict[str, int]:
        """Rank each row kind by where its route is declared in routes.yaml.

        Used only to pick which row speaks for a finding when several proved it. The
        order is upstream's, not ours -- it happens to put vendor-controlled identifiers
        first (a bundle id before a path glob, an OCI label before a tag anyone can
        set) which is the preference this project states anyway. A tie-break, not a
        judgement about which evidence is true.
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

        Signatures ride in the Discovery Source Config so that adding one is a config
        change rather than an image rebuild, and so an engine with no route out to the
        internet can still be updated. The floor is what an unconfigured source gets.
        """
        catalog_text = catalog_yaml if catalog_yaml else _FLOOR_CATALOG.read_text()
        routes_text = routes_yaml if routes_yaml else _FLOOR_ROUTES.read_text()
        catalog = yaml.safe_load(catalog_text)
        routes = yaml.safe_load(routes_text)
        if not isinstance(catalog, dict) or not isinstance(routes, dict):
            raise ValueError("catalog and routes must each parse to a YAML mapping")
        return cls(catalog, routes, logger, catalog_source=catalog_text)

    @property
    def catalog_sha(self) -> str:
        """First 12 hex of sha256 over the catalog, matching upstream's `catalog_sha`.

        A content hash rather than a revision field, for upstream's stated reason: a
        hand-bumped number is one more thing that can be wrong, and a hash is true by
        construction. Recorded per record so a finding stays diagnosable later.

        Hashed over the SOURCE BYTES, because that is what upstream hashes -- its
        `_sha()` reads the file. Hashing a re-serialized parse instead produces a
        perfectly stable number that silently agrees with nothing: measured on the
        vendored catalog, file bytes give dbb22a107953 and a normalized dump gives
        9557c8387835. Only the first joins against upstream's own telemetry.
        """
        if self._catalog_source is None:
            # Built from a mapping with no source text. Still stable and still useful
            # for spotting drift between runs, but it is not upstream's number, so it
            # is marked rather than passed off as one.
            blob = yaml.safe_dump(self._catalog, sort_keys=True).encode()
            return "norm:" + hashlib.sha256(blob).hexdigest()[:12]
        return hashlib.sha256(self._catalog_source.encode()).hexdigest()[:12]

    @property
    def agent_count(self) -> int:
        return len(self._catalog.get("agents") or ())

    def match(self, rows: Sequence[Mapping[str, Any]]) -> MatchResult:
        """Classify one device's payload.

        Reconciles its own arithmetic, because upstream drops a row whose `kind` is not
        in the route registry -- neither matched nor unmatched, just gone. That is a
        real bug this project has already shipped once: browser-extension rows were
        collected correctly, with correct identifiers, and never appeared for months
        while every row count stayed right. `dropped` is how a caller notices.
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
            version=str(primary.get("ver")) or None if primary.get("ver") else None,
            install_path=(
                str(primary.get("loc")) or None if primary.get("loc") else None
            ),
            permissions=tuple(p for p in perms.split(",") if p),
        )


def is_gap(row: Mapping[str, Any]) -> bool:
    """A scan row saying a branch could not look, as opposed to one saying it did."""
    return row.get("kind") == _GAP_KIND and row.get("extra") != _SCAN_OK
