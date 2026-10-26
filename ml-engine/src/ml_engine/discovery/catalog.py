"""Matching enumerated endpoint rows against the agent catalog.

The endpoint enumerates and the collector classifies: a managed Mac ships ~875 rows naming
every application, formula and extension on it, and holds no catalog. That split is what
lets a new signature re-match evidence already collected instead of triggering a fleet
re-scan.

Upstream's `bin/classify` is called, not reimplemented: it is ai-detection-spec's reference
matcher, held to the spec's conformance vectors, and a second implementation here would answer
differently without anything failing. Measured at 0.61 ms for an 875-row payload, so 10,000
Macs cost about six seconds. Calling it as a library also sends no telemetry: upstream raises
its Amplitude event in `main()`, not in the matcher.
"""

import hashlib
import importlib.machinery
import importlib.util
import json
import logging
import pathlib
from dataclasses import dataclass
from types import ModuleType
from typing import Any, Mapping, Optional, Sequence

_VENDOR = pathlib.Path(__file__).resolve().parent / "_vendor"

# The floor: the catalog document the vendored release attaches. A Discovery Source Config
# carries the catalog that actually runs, so this is only what an unconfigured source falls
# back to.
_FLOOR = _VENDOR / "catalog.json"
# What a catalog document is validated against before it is read (SPEC.md 4).
_CATALOG_SCHEMA = _VENDOR / "catalog.schema.json"


def _no_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Refuse a duplicate key. `json.loads` keeps the last occurrence silently, so an agent
    carrying `identifiers` twice loses its first list -- and the fleet then reports a missed
    agent as absent, which is the failure this module exists to prevent. A source config is
    typed by a person, so this is a live risk rather than a theoretical one.
    """
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate key {key!r}")
        out[key] = value
    return out


def _load_matcher() -> ModuleType:
    """Import the vendored `bin/classify` as a module.

    By path, because upstream ships it extensionless and it is vendored verbatim --
    renaming it to `.py` is the only change the vendoring makes.
    """
    loader = importlib.machinery.SourceFileLoader(
        "_ai_detection_spec_classify",
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

    `running`, `superseded` and `only_superseded` are what SPEC.md 6.6 has a matcher report:
    whether a live route proved the agent, the ids of the rows an identifier the vendor has
    replaced matched, and whether every row was one. AgentObservations carries none of them
    yet.
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
    running: bool
    superseded: tuple[str, ...]
    only_superseded: bool

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

    A `gap` is a branch that could not look -- a wedged Docker daemon, a missing table --
    not one that found nothing, so reading `findings` without `gaps` draws the wrong
    conclusion.

    `absences` are the third answer and NOT gaps: the branch read the machine and there
    was nothing there, no container runtime or no systemd bus. Folding them in would make
    every Mac without Docker permanently unable to say absence is assertable, which is
    false about the thing anyone would ask. A runtime that IS present and unread reports
    `unreadable:<runtime>`, which is a gap and stays one.
    """

    findings: tuple[Finding, ...]
    gaps: tuple[dict[str, Any], ...]
    scans: tuple[dict[str, Any], ...]
    absences: tuple[dict[str, Any], ...]
    unmatched: int
    dropped: int
    rows_total: int

    @property
    def complete(self) -> bool:
        """True when no branch was left unread, so absence means absence."""
        return not self.gaps

    @property
    def scanned_at(self) -> Optional[int]:
        """The newest `ver` across scan rows: when this device last looked.

        The payload's own timestamp, not a file mtime -- redeploying the file resets the
        mtime without changing the truth. Every dated marker counts, whichever bucket it
        landed in: a branch that reported `absent` still says when it looked.
        """
        stamps = [
            e
            for e in (
                _epoch(r.get("ver")) for r in (*self.scans, *self.gaps, *self.absences)
            )
            if e is not None
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
        self._kind_rank = _matcher.kind_rank(self._routes)
        # Which kinds say an agent is running rather than installed: declared per route, and
        # passed to upstream's describe(), which otherwise reads a routes.yaml beside itself
        # that this package does not ship.
        self._live_kinds = _matcher.Registry(self._routes).live_kinds

    @classmethod
    def from_source(
        cls,
        catalog_json: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
    ) -> "Matcher":
        """Build from a config-supplied catalog document, falling back to the vendored floor.

        Signatures ride in the source config, so adding one is a config change rather than
        an image rebuild and works on an engine with no route to the internet. The catalog is
        an ai-detection-spec catalog document (SPEC.md 4), such as the catalog.json a release
        attaches, and it carries its own routes.
        """
        source = catalog_json.encode() if catalog_json else _FLOOR.read_bytes()
        try:
            doc = json.loads(source, object_pairs_hook=_no_duplicate_pairs)
        except json.JSONDecodeError as exc:
            raise ValueError(f"catalog is not JSON: {exc}") from exc
        if not isinstance(doc, dict) or "format" not in doc:
            raise ValueError(
                "catalog is not a catalog document: it names no `format`. This engine reads "
                "ai-detection-spec catalog documents, such as the catalog.json a release "
                "attaches",
            )
        catalog, routes = _from_document(doc)
        return cls(catalog, routes, logger, catalog_source=source)

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
            blob = json.dumps(self._catalog, sort_keys=True).encode()
            return "norm:" + hashlib.sha256(blob).hexdigest()[:12]
        return hashlib.sha256(self._catalog_source).hexdigest()[:12]

    @property
    def agent_count(self) -> int:
        return len(self._catalog.get("agents") or ())

    def match(self, rows: Sequence[Mapping[str, Any]]) -> MatchResult:
        """Classify one device's payload.

        Counts what upstream drops: a row whose `kind` is in no route can never match, and is
        neither matched nor unmatched. That shipped once, browser-extension rows invisible for
        months while row counts stayed right.
        """
        raw = [dict(r) for r in rows]
        findings_by_agent, unmatched, gaps, scans, absences, dropped_rows = (
            _matcher.classify(raw, self._catalog, self._routes)
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

        dropped = len(dropped_rows)
        if dropped:
            self._log.warning(
                "%s row(s) carried a kind absent from the route registry and were dropped by the "
                "matcher; a route is missing from the catalog",
                dropped,
            )

        return MatchResult(
            findings=findings,
            gaps=tuple(gaps),
            scans=tuple(scans),
            absences=tuple(absences),
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

        # Upstream names the row that speaks for a finding, and gives its version, and its
        # path where that row's kind carries one -- the rule every consumer of the matcher
        # shares, rather than one this collector keeps beside it. The flags say which rows
        # matched an identifier the vendor has replaced.
        flags = [bool(hit.get("superseded")) for hit, _row in evidence]
        described = _matcher.describe(rows, self._kind_rank, flags, self._live_kinds)
        primary = rows[described["primary"]]
        # As text whatever the row held: the record's fields are strict strings, and match()
        # takes rows that never passed the envelope's checks.
        version, path = described.get("version"), described.get("path")

        # Permissions only: an extension's provenance token rides in `extra`, and goes nowhere
        # yet -- AgentObservations has no field for it. osquery joins with ", ", so each part
        # is stripped, or " storage" would be a different permission from "storage".
        permissions = tuple(
            p.strip() for p in str(primary.get("perms") or "").split(",") if p.strip()
        )
        return Finding(
            agent_id=agent_id,
            name=str(meta.get("name") or agent_id),
            classification=str(meta.get("classification") or ""),
            evidence=tuple(rows),
            primary_kind=str(primary.get("kind") or ""),
            primary_id=str(primary.get("id") or ""),
            version=None if version is None else str(version),
            install_path=None if path is None else str(path),
            permissions=permissions,
            running=any(row.get("kind") in self._live_kinds for row in rows),
            superseded=tuple(
                str(row.get("id") or "") for row, flag in zip(rows, flags) if flag
            ),
            only_superseded=all(flags),
        )


def _from_document(doc: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """A catalog document as the catalog and route registry the matcher works in.

    Read by upstream's own reader, so no second reading of a document exists. It validates
    the document against the vendored schema, and refuses whole a format it does not read or
    an identifier it could not index (SPEC.md 4, 6 and 10). That is every check the matcher
    needs, made once at load: a catalog that reached the matcher malformed would fail on every
    device instead, naming a key rather than the entry that is wrong. It refuses by exiting,
    as a command line does; here a refusal is a ValueError.
    """
    try:
        catalog, routes = _matcher.from_document(
            doc,
            "the catalog document",
            schema=_CATALOG_SCHEMA,
        )
    except SystemExit as exc:
        raise ValueError(str(exc.code)) from None
    return catalog, routes


def _epoch(value: Any) -> Optional[int]:
    """A scan row's `ver` as unix seconds, or None if it is not one.

    `str.isdigit()` is true for characters `int()` refuses -- "²" among them -- so the
    check has to be the conversion itself.
    """
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None
