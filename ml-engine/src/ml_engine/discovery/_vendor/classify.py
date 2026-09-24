#!/usr/bin/env python3
"""Turn osquery output into findings, using catalog/agents.yaml.

    osqueryi --json < dist/discovery-darwin.sql | bin/classify
    bin/discover --deep | bin/classify

This is the reference implementation of matching. It is deliberately small and meant
to be read: if you want to know what a signature means, this is the answer, and any
other implementation that disagrees with it is wrong.

Standard library only, except PyYAML for the catalog.
"""
import argparse
import json
import os
import pathlib
import re
import sys
import time
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = ROOT / "catalog" / "agents.yaml"
DEFAULT_ROUTES = ROOT / "catalog" / "routes.yaml"

# The catalog schema version this matcher understands. See load_catalog: a NEWER catalog
# warns and matches what it can, because refusing would turn version skew into
# "no agents found" -- which is the one error this repo exists to avoid.
CATALOG_VERSION = 2


def _yaml(path):
    """Read a YAML file, importing yaml LAZILY.

    The lazy import is load-bearing, not tidiness: image_repo() and image_repos() are
    imported by tools/ and used on machines with no PyYAML, and a module-level
    `import yaml` would make that fail at import time for callers that never touch a
    catalog.
    """
    try:
        import yaml
    except ImportError:
        sys.exit("PyYAML is required to read the catalog: pip install pyyaml")
    return yaml.safe_load(pathlib.Path(path).read_text())


def load_catalog(path):
    doc = _yaml(path)
    # THE DORMANT FIELD, NOW LOAD-BEARING. catalog/agents.yaml has carried `version` since
    # the beginning and nothing read it, so nothing could disagree with it. A downloaded
    # bin/classify can meet a newer catalog than it knows; warn and match what is
    # recognisable rather than refusing, because a refusal reads downstream as a clean
    # fleet. Unknown per-agent fields are already rejected by tools/validate_catalog.py,
    # so the risk here is a route this matcher has no registry entry for -- which arrives
    # as unmatched rows, not as silence.
    version = doc.get("version")
    if isinstance(version, int) and version > CATALOG_VERSION:
        print(f"classify: catalog is version {version}; this matcher understands "
              f"{CATALOG_VERSION}. Matching what it can -- newer routes will read as "
              f"unmatched rows rather than findings.", file=sys.stderr)
    return doc


def load_routes(path=DEFAULT_ROUTES):
    """The route registry: catalog/routes.yaml. See that file's header for why."""
    return _yaml(path)


class Registry:
    """The route vocabulary, derived from catalog/routes.yaml rather than hardcoded.

    Five hardcoded copies of this used to have to agree. `ext` was missing from one of
    them from the beginning and every browser-extension row was DROPPED -- see the
    `unmatched` branch at the foot of classify().
    """

    def __init__(self, routes):
        self.platforms = list(routes["platforms"])
        self.groups = {k: list(v) for k, v in routes.get("platform_groups", {}).items()}
        self.routes = routes["routes"]
        self.match = {n: r["match"] for n, r in self.routes.items()}
        self.retired = {n for n, r in self.routes.items() if r.get("retired")}
        # A route that reads ANOTHER route's catalog values. `container_images` matches the
        # same repository names as `images` and differs only in the row kind it arrives on,
        # so an agent declares its image once and both routes index it.
        #
        # THE ALTERNATIVE WAS DUPLICATION, and it would have rotted: two lists of the same
        # names, no check that they agree, and a container route silently one name behind
        # the image route the day somebody edited only one. Catalogued once is the whole
        # point -- catalog/agents.yaml's header says an agent carries EVERY route it ships
        # through, and an image reached two ways is still one image.
        #
        # Deliberately NOT read by tools/agent_status.py: an aliased route contributes no
        # catalog key, so `agent.get(route, [])` finds nothing there and the identifier is
        # counted once, under the route that owns it. Coverage counts identifiers, not the
        # number of ways one can be reached.
        self.values_from = {n: r["values_from"] for n, r in self.routes.items()
                            if r.get("values_from")}
        # kind -> the routes reachable through the GENERIC loop. `tool-dir` routes are
        # excluded on purpose: pypi evidence arrives as kind='file' through the TOOL_DIR
        # bridge, and listing it here as well is what let a PyPI-only signature claim an
        # npm package of the same name -- npm's `mcp` is Mintlify's, and it was reported
        # as the MCP SDK until the two were split.
        self.kind_routes = {}
        for name, r in self.routes.items():
            if r["match"] == "tool-dir":
                self.kind_routes.setdefault(r["kind"], [])
                continue
            self.kind_routes.setdefault(r["kind"], []).append(name)

    def expand(self, platform):
        """A route's platform to the concrete platforms it covers ('posix' -> both)."""
        return self.groups.get(platform, [platform])

    def platforms_of(self, route):
        return self.expand(self.routes[route]["platform"])

    def path_routes(self):
        """Every route whose value is a `~/`-rooted path, in declaration order.

        The tuple ("state_dirs", "binaries", "model_stores") was written out by hand in
        bin/classify, tools/validate_catalog.py and tools/agent_status.py. This is that
        list, derived.
        """
        return [n for n, m in self.match.items() if m.startswith("home-")]


# EVERY PLATFORM'S HOME ROOTS, MATCHED AT ONCE -- not one platform chosen by a caller.
#
# bin/classify runs OFF the machine, over a payload that a fleet collector may have
# merged from many hosts, so there is no such thing as "the platform" here: a single
# input can legitimately carry /Users/dana/.claude and /home/dana/.claude. An earlier
# design took a platform argument, which would have made a mixed payload match only half
# of itself and reported the rest as unmatched.
#
# One alternation rather than one pattern per platform, because path routes are compared
# against every candidate row -- docs/signature-lifecycle-v2.md's scaling note -- so a
# per-platform list would multiply the glob count by three for no gain.
#
# /root gets its own alternative: root's home is not under /home, and a `[^/]+`
# component cannot reach it. Verified against `users.directory` on Ubuntu and Fedora.
HOME_ROOTS = r"(?:/Users/[^/]+/|/home/[^/]+/|/root/)"


def home_pattern(value, mode):
    """Compile a `~/`-rooted catalog value into a regex over real paths.

    THE ANCHOR IS PER ROUTE, and that is the whole point of having two modes.

      home-dir     `~/.claude` -> matches `.../.claude` and `.../.claude/` and NOT
                   `.../.claudefoo`. The glob was front-anchored only, so `.claudefoo`
                   DID match -- confirmed on a real Linux box, where `/home/%/.%/`
                   returns both directories side by side.
      home-prefix  `~/.local/bin/hermes` -> still matches hermes-acp and hermes-agent,
                   which is DELIBERATE: one `uv tool install` writes all three commands
                   and they are the same install. Anchoring this mode would lose two of
                   the three, which is why the missing `$` is not a blanket fix.
    """
    body = re.escape(value[2:])                      # strip the leading '~/'
    if mode == "home-dir":
        return re.compile("^" + HOME_ROOTS + body + "/?$")
    return re.compile("^" + HOME_ROOTS + body)


def build_index(catalog, registry):
    """Map every catalog identifier to the agent that claims it.

    Routes differ in how they match, and conflating them is how false positives
    happen: `mcp` as an exact npm package name is a real signal, but `mcp` as a
    substring also matches `libxdmcp`, an X11 library. Exact where exact is right.

    Which route matches how is now DECLARED, in catalog/routes.yaml, rather than
    written out as four route-name tuples here. A route added there is indexed here
    without an edit -- and a route this function does not know about is a KeyError at
    build time instead of rows that quietly match nothing.
    """
    exact, prefix, glob = {}, [], []
    for agent in catalog["agents"]:
        base = {k: agent[k] for k in ("id", "name", "classification")}
        # WHICH GENERATION A VALUE BELONGS TO, CARRIED ON THE VALUE ITSELF. `meta` was one
        # dict shared by every route value of an agent, so a finding could say WHICH agent
        # was found and never which identifier era found it -- a match on the current
        # bundle id and a match on one the vendor replaced rendered identically.
        #
        # Per-value rather than threading the matched route/value out of classify(): the
        # flag then arrives with the hit, through every match mode, with no extra plumbing
        # in the loop that does the matching. The shared dict is reused where there is no
        # flag to add, so this costs one dict per superseded value and nothing otherwise.
        #
        # Keyed on (route, value): OpenClaw ships an npm package and a Homebrew cask both
        # called `openclaw`, so keying on the value alone would label one for the other.
        superseded = {(str(s["route"]), str(s["value"]))
                      for s in agent.get("superseded", []) or []}

        def meta_for(route, value, _base=base, _sup=superseded):
            # A LABEL, NEVER A FILTER. This marks a finding; it must never withhold one.
            # The machines a superseded identifier exists for are exactly the ones nothing
            # else will find, so anything that dropped them here would be the empty result
            # this repo is built to refuse, wearing a new name.
            if (route, str(value)) in _sup:
                return {**_base, "superseded": True}
            return _base

        for route, mode in registry.match.items():
            # `values_from` lets a route index another's values -- see Registry. Absent,
            # a route reads its own key, which is every route but one.
            src = registry.values_from.get(route, route)
            for value in agent.get(src, []):
                # SUPERSESSION IS KEYED ON THE ROUTE THAT HOLDS THE VALUE, not the one
                # indexing it. `container_images` borrows `images:`, so a value it matches
                # is listed under `images` and a superseded record names `images` -- which
                # is also what validate_catalog checks the value against. Looking it up
                # under the borrowing route would never match, and the label would silently
                # never appear on an aliased route.
                meta = meta_for(src, value)
                if mode in ("exact", "tool-dir"):
                    # A trailing `*` is a prefix, e.g. @modelcontextprotocol/*. No agent
                    # uses one today; the form is kept because removing it would silently
                    # turn a future scoped signature into a literal name with a star.
                    if str(value).endswith("*"):
                        prefix.append((str(value)[:-1], route, meta))
                    else:
                        # str() because `ports` values are integers in YAML and a row's
                        # id is always text.
                        exact[(route, str(value))] = meta
                elif mode == "prefix":
                    prefix.append((str(value), route, meta))
                elif mode == "exact-normalised":
                    # Exact on the NORMALISED repository, never a substring. `ollama` as
                    # a substring would claim `myorg/ollama-fork` and `not-ollama`, and
                    # an image name is attacker-choosable in a way a bundle id is not:
                    # anyone can `docker tag` anything.
                    exact[(route, image_repo(value))] = meta
                elif mode.startswith("home-"):
                    glob.append((home_pattern(str(value), mode), route, meta))
                else:
                    raise KeyError(f"routes.yaml: {route} declares unknown match "
                                   f"mode {mode!r}")
    return exact, prefix, glob


# How a docker_images row names an image, read off 28 real images on a developer Mac
# rather than reasoned about. All four rules below are load-bearing:
#
#   alpine:3.20                                 Docker Hub library: NO registry, NO library/
#   authzed/spicedb:latest                      Docker Hub org:     NO docker.io/ prefix
#   ghcr.io/ggml-org/llama.cpp:server           anywhere else:      registry host IS present
#   public.ecr.aws/docker/library/python:3.12   ...including a path that contains 'library/'
#   nextbite-backend:latest                     a LOCAL build is shaped like a Hub library
#                                               image and cannot be told apart from one
#
# So a catalog value is normalised the same way a row is, and then compared exactly. The
# local-build case is why exact matching matters: `docker tag alpine ollama/ollama` would
# produce a finding, and nothing can distinguish that from the real image -- which is a
# property of container images, not a defect here, and is recorded in README.md.
def image_repo(tag):
    """One tag string to its normalised repository. 'ghcr.io/x/y:v1' -> 'ghcr.io/x/y'."""
    tag = tag.strip()
    # The tag separator is the last ':' AFTER the last '/'. A registry may carry a port --
    # localhost:5000/foo -- and splitting on the last ':' outright would eat the port and
    # leave 'localhost'.
    colon, slash = tag.rfind(":"), tag.rfind("/")
    repo = tag[:colon] if colon > slash else tag
    for implicit in ("docker.io/", "index.docker.io/", "registry-1.docker.io/"):
        if repo.startswith(implicit):
            repo = repo[len(implicit):]
            break
    # Only at the very front, and only once the registry is gone: 'library/' is implicit on
    # Docker Hub, but public.ecr.aws/docker/library/python legitimately contains it.
    if repo.startswith("library/") and "/" not in repo[len("library/"):]:
        repo = repo[len("library/"):]
    return repo


def image_repos(tags):
    """Every repository a docker_images row names.

    ONE ROW CAN NAME SEVERAL, and missing that means missing the image entirely rather
    than matching it loosely. Measured: after `docker tag alpine:3.20 probe/multitag:a`
    and `:b`, osquery returned ONE row whose tags column was
    "probe/multitag:a,probe/multitag:b,alpine:3.20". A matcher comparing the whole field
    matches none of the three, and a multi-tagged image is completely ordinary -- every
    `:latest` alongside a version tag is one.
    """
    return [image_repo(t) for t in tags.split(",") if t.strip()]


def _corroborates(agent, row):
    """Does the process holding this port look like the agent that claims it?"""
    haystack = f"{row.get('loc', '')} {row.get('extra', '')}".lower()
    needles = {agent["id"].replace("-", ""), agent["name"].lower().replace(" ", "")}
    return any(n and n in haystack.replace("-", "").replace(" ", "") for n in needles)


# WHICH ROW KINDS CAN SATISFY WHICH ROUTES IS NOW DECLARED, NOT LISTED HERE.
#
# This used to be a hand-written dict, and it is the single most expensive list in this
# repo's history: kind='ext' was missing from it from the beginning, so every
# browser-extension row fell off the end of classify()'s loop -- DROPPED, not unmatched,
# invisible even under --show-unmatched. Verified on a real Mac: the Claude extension was
# collected correctly, carried a correct identifier and permissions, and did not appear
# in the output. Claude was still reported through its native-messaging bridge, so the
# fleet-visible symptom was one route quietly missing rather than an agent going unseen,
# which is why it survived for months.
#
# Registry.kind_routes is that mapping, inverted from catalog/routes.yaml. Two properties
# the old dict had to state by hand and this one gets by construction:
#
#   * a route's kind is registered even when the route matches nothing, so an unclaimed
#     row is UNMATCHED rather than dropped -- which is why `ports` stays in the registry
#     with `retired: true` long after it stopped being a signature, and why the retired
#     `model` kind is simply absent from routes.yaml rather than half-present here;
#   * a bundle id is never looked for in an npm row, because npm_packages produces node
#     packages by construction and checking a bundle id there would only invite a
#     coincidence.

# pipx and uv give each installed tool a directory named for the PACKAGE, so the tool
# name is recoverable from the path and can be matched against the pypi route.
#
# Without this, PyPI-installed agents are enumerated and then silently dropped. The
# endpoint cannot query python_packages -- 15.6s with no WHERE push-down -- so it globs
# these directories instead, and those rows arrive as kind 'file' whose only routes are
# the path ones. aider installs as 'aider-chat' under uv, its state_dir is ~/.aider, and
# the two never meet: the evidence says aider and the classifier says nothing.
#
# Caught by 25-python-agents asserting on the classifier rather than on row counts. The
# count-based version passed throughout, because the row was present the whole time.
#
# HOME_ROOTS rather than a hardcoded /Users/, so a uv tool install under /home/dana or
# /root resolves the same way. That was one of three hand copies of the same prefix; the
# other two were this file's path globs and tools/agent_status.py's replay.
TOOL_DIR = re.compile(
    "^" + HOME_ROOTS + r"\.local/(?:pipx/venvs|share/uv/tools)/([^/]+)/?$")



# A row that says a branch could not look, rather than what it found. bin/container-scan
# emits one when the Docker daemon is absent, not serving, or wedged past the wall clock.
#
# IT HAS TO BE HANDLED EXPLICITLY OR IT DISAPPEARS. A kind outside KIND_ROUTES is dropped
# at the foot of the loop below -- not unmatched, DROPPED, invisible even under
# --show-unmatched, because `elif kind in KIND_ROUTES` is the only thing that collects
# anything. So the row built specifically to stop a wedged daemon reading as an empty
# machine would have been swallowed by the classifier one hop after surviving the scan.
GAP_KIND = "scan"
# `extra` on a scan row: "ok" means the branch ran and the rows beside it are real. Anything
# else is a reason it could not look. `ver` is when the scan ran, in unix seconds, so a
# cached payload dates itself and a consumer can judge staleness without stat()ing anything.
SCAN_OK = "ok"
STALE_AFTER = 24 * 3600


def classify(rows, catalog, routes=None):
    """Match rows against the catalog. `routes` is catalog/routes.yaml, loaded once.

    The registry and the index are built ONCE here rather than per row, and the caller
    may pass a pre-loaded `routes` so a tool classifying many payloads does not re-read
    the file. Left optional so the existing two-argument call keeps working.
    """
    registry = Registry(routes if routes is not None else load_routes())
    exact, prefix, glob = build_index(catalog, registry)
    kind_routes = registry.kind_routes
    findings, unmatched, gaps, scans = defaultdict(list), [], [], []

    for row in rows:
        kind, ident, loc = row.get("kind"), row.get("id", ""), row.get("loc", "")
        hit = None

        if kind == GAP_KIND:
            # A dated success is provenance, not a gap. Splitting them here is what lets
            # `cat`-ing a cache file produce the same reading as a live scan.
            (scans if row.get("extra") == SCAN_OK else gaps).append(row)
            continue

        # A pipx/uv tool directory names its package. Try that before the path globs,
        # which describe state directories rather than install locations.
        tool = TOOL_DIR.match(ident) or TOOL_DIR.match(loc)
        if tool and kind in {registry.routes[r]["kind"]
                             for r, m in registry.match.items() if m == "tool-dir"}:
            name = tool.group(1)
            # The routes a tool directory can legitimately name: the tool-dir routes
            # themselves, plus the package routes that share their match mode. A pipx or
            # uv directory holds a PyPI distribution, and the same name is meaningful as
            # an npm package for agents that ship both.
            bridged = [r for r, m in registry.match.items() if m == "tool-dir"]
            bridged += [r for r, m in registry.match.items()
                        if m == "exact" and registry.routes[r]["kind"] == "npm"]
            for route in bridged:
                if (route, name) in exact:
                    hit = exact[(route, name)]
                    break
            if hit is None:
                for pre, proute, meta in prefix:
                    if proute in bridged and name.startswith(pre):
                        hit = meta
                        break

        # Before the generic loop, because the identifier has to be normalised first and
        # there may be several of them in the one field.
        if not hit:
            for route in kind_routes.get(kind, []):
                if registry.match[route] != "exact-normalised":
                    continue
                for repo in image_repos(ident):
                    if (route, repo) in exact:
                        hit = exact[(route, repo)]
                        break
                if hit:
                    break

        for route in [] if hit else kind_routes.get(kind, []):
            if (route, ident) in exact:
                candidate = exact[(route, ident)]
                # A port number alone is not a signature. 8080 is held by half the
                # web servers ever written, and claiming llama.cpp for every one of
                # them is a confident wrong finding on a large share of machines.
                # Require the owning process to corroborate: `ollama` on 11434 is a
                # finding, an unknown process on 11434 is a question for the
                # collector, not an identification.
                if route in registry.retired and not _corroborates(candidate, row):
                    continue
                hit = candidate
                break
            for pre, proute, meta in prefix:
                if proute == route and ident.startswith(pre):
                    hit = meta
                    break
            if hit:
                break
            for pattern, proute, meta in glob:
                if proute == route and (pattern.match(ident) or pattern.match(loc)):
                    hit = meta
                    break
            if hit:
                break
        if hit:
            findings[hit["id"]].append((hit, row))
        elif kind in kind_routes:
            # UNMATCHED, NOT DROPPED, and the difference is the whole reason the registry
            # exists. A kind absent from it falls off the end of this loop and is
            # discarded in silence -- see the note above kind_routes.
            unmatched.append(row)

    return findings, unmatched, gaps, scans


# --- TELEMETRY -----------------------------------------------------------------------
#
# ONE anonymous event per run, so that "is anyone on a stale catalog", "does anyone turn
# the deep scan on" and "which gap reasons actually fire in the field" stop being guesses.
#
# IT LIVES BELOW main() AND RUNS FROM NOWHERE ELSE. tools/agent_status.py loads this file
# with SourceFileLoader.exec_module and does so inside CI; anything at module scope -- a
# client, a config read, an import with a side effect -- would execute there. Keeping the
# work inside main() also means the test suite, and every tool that imports image_repo(),
# send nothing without having to remember not to.
#
# bin/discover and bin/container-scan send NOTHING, and that is not an oversight to
# correct later. They run as root on endpoints under MDM. bin/classify runs OFF the
# endpoint, over a payload somebody already chose to collect, and that difference is the
# whole reason this is defensible here and would not be there.
#
# WHAT IS NEVER SENT is the load-bearing half, and test/test_telemetry.py asserts it
# rather than trusting this paragraph: no hostname, no username, no path, no row `loc`,
# no agent identifier, and no exception MESSAGE. Messages carry paths --
# "FileNotFoundError: /Users/dana/payload.json" -- which is how a crash reporter leaks a
# home directory and the name of the person who owns it. The exception TYPE and the line
# it came from carry the same diagnostic value and none of that.
#
# `bin/classify --telemetry-check` prints the exact event and sends nothing. The README
# promises you never have to take this project on trust; a field list you could not print
# would be exactly that.
AMPLITUDE_URL = "https://api2.amplitude.com/2/httpapi"
# A write-only ingest key is public by nature -- every web application using Amplitude
# ships one in its bundle where anyone can read it. That means events can be FORGED, which
# is a reason to distrust volume in the dashboard, not a reason to pretend the key is a
# secret. It is NOT the project's secret key, which authenticates the Export and Dashboard
# APIs and must never appear here: the two are the same length and sit next to each other
# on the same settings page, and the only thing that tells them apart by eye is that this
# one is lowercase hex.
#
# An empty value is a supported state, not a broken one -- _telemetry_off() reports "no
# ingest key is configured" as a reason, so a fork that strips this line sends nothing and
# says so, rather than failing silently.
AMPLITUDE_KEY = "f1de48c62586e91cc0a5b9a2f0ae51d7"
# Two seconds, spent AFTER stdout is flushed, and never retried. A 429 we retried would
# charge the user's run a second time for data that is not theirs.
TELEMETRY_TIMEOUT = 2.0
# THE FIELD LIST, DECLARED ONCE. docs/telemetry.md is checked against this by
# tools/check_doc_numbers.py, so the published list cannot drift from the sent one -- the
# five-hardcoded-lists-that-had-to-agree bug, pre-empted this time.
EVENT_FIELDS = (
    "catalog_sha", "catalog_schema_version", "catalog_agents", "catalog_skew",
    "classify_sha",
    "rows_total", "findings_agents", "findings_rows", "unmatched_rows", "dropped_rows",
    "payload_bytes", "payload_packed_bytes",
    "gap_rows", "scan_rows",
    "kinds_seen", "deep_scan",
    "gap_reasons", "gap_unhealthy_code", "gap_timeout_seconds",
    "stale_branches", "newest_scan_age_seconds",
    "host_os", "host_os_release", "payload_platform", "python_version",
    "output_mode", "show_unmatched", "duration_ms",
    "error_type", "error_site", "phase",
)
# A CLOSED VOCABULARY, because `kind` and `extra` arrive from a payload this process did
# not produce. A collector merging many hosts, or a hand-edited file, can put any string
# in either field, and forwarding it verbatim would turn an analytics property into a
# channel for arbitrary text out of a machine we are supposed to be describing in counts.
# Anything unrecognised becomes "other" -- which is itself a finding worth seeing.
GAP_REASONS = ("absent", "no-cache", "error", "unhealthy", "timeout", "unreadable")
OTHER = "other"


def _env_off(name):
    return os.environ.get(name, "").strip().lower() in {"0", "false", "no", "off"}


def _amplitude_key():
    return os.environ.get("AI_DISCOVERY_AMPLITUDE_KEY", "").strip() or AMPLITUDE_KEY


def _telemetry_off():
    """Why this run will not send, or None if it will.

    A REASON RATHER THAN A BOOLEAN. "Sent nothing because it is switched off" and "sent
    nothing because the key is missing" are the same silence otherwise, and telling those
    two apart is the distinction this entire repo is built around. --telemetry-check
    prints it.
    """
    if _env_off("AI_DISCOVERY_TELEMETRY"):
        return "AI_DISCOVERY_TELEMETRY is set to off"
    if os.environ.get("CI"):
        # Otherwise every gate, scenario and pull request lands in the same dataset as the
        # field, and the field is the only part that cannot be measured another way. CI is
        # set by GitHub Actions, GitLab, CircleCI and Travis alike.
        return "CI is set; this is a build, not a use"
    if not _amplitude_key():
        return "no ingest key is configured"
    return None


def _install_id(create=True):
    """A random, persisted, anonymous id, and whether this run is the one that made it.

    `create=False` for --telemetry-check: asking what a run WOULD send must not be the
    thing that creates the identity it would send under. A diagnostic with a side effect
    is a diagnostic you cannot run twice and get the same answer from.

    uuid4 -- NEVER derived from hostname, MAC or username. A pseudonym computed from a
    real machine identifier is still a machine identifier, and it is reversible by anyone
    holding a list of candidates. Amplitude requires at least 5 characters and rejects
    reserved words like "anonymous"; 32 hex characters satisfies both.

    An unwritable home -- a read-only image, a locked-down collector, a CI sandbox -- falls
    back to an ephemeral id, so that install counts inflate rather than a run dying on a
    telemetry file. Losing the count is survivable; losing the answer is not.
    """
    import uuid

    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"),
                                                             ".config")
    path = pathlib.Path(base) / "ai-discovery" / "install-id"
    try:
        existing = path.read_text().strip()
        if len(existing) >= 5:
            return existing, False
    except OSError:
        pass
    if not create:
        return "(no install id yet -- this run would create one)", True
    ident = uuid.uuid4().hex
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(ident + "\n")
        path.chmod(0o600)
    except OSError:
        pass
    return ident, True


def _sha(path):
    """The first 12 hex of sha256, or "" if the file cannot be read.

    A CONTENT HASH RATHER THAN A VERSION FIELD. catalog/agents.yaml carries a schema
    `version` and nothing that says which release it came from, and a hand-bumped revision
    field is one more number that can be wrong -- catalog/routes.yaml's header states the
    rule that no field may exist unless code reads it. A hash is true by construction and
    needs nobody to remember it. It is meaningless until releases are hashed and mapped on
    the other side; docs/telemetry.md says so rather than implying the number stands alone.
    """
    import hashlib

    try:
        return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()[:12]
    except OSError:
        return ""


def _kind_platforms(routes):
    """kind -> the concrete platforms its routes cover, from catalog/routes.yaml.

    Derived, not listed. A hardcoded darwin/linux kind split here would be the sixth copy
    of a vocabulary that has to agree with five others, which is the bug that dropped
    every `ext` row for months.
    """
    groups = routes.get("platform_groups", {})
    out = {}
    for spec in routes["routes"].values():
        out.setdefault(spec["kind"], set()).update(
            groups.get(spec["platform"], [spec["platform"]]))
    return out


def _payload_platform(kinds, kind_platforms):
    """Which platform the PAYLOAD came from -- not the one classify is running on.

    Those are different machines and routinely different systems: an analyst on a Mac
    reads a Linux fleet's rows. Only a kind exclusive to one platform is evidence; `file`
    and `npm` are posix and say nothing. A payload merged from both is a real and
    supported state, so it gets its own word rather than being forced into one.
    """
    seen = {p for k in kinds for p in kind_platforms.get(k, ())
            if len(kind_platforms.get(k, ())) == 1}
    if len(seen) > 1:
        return "mixed"
    return next(iter(seen)) if seen else "unknown"


def _packed_size(raw):
    """Bytes after gzip -9 and base64, or None if it cannot be computed.

    None rather than 0: a size of zero is a claim about a payload, and "we did not
    measure" is not that claim.
    """
    import base64
    import gzip

    try:
        return len(base64.b64encode(gzip.compress(raw.encode("utf-8", "replace"), 9)))
    except Exception:
        return None


def _error_site(exc):
    """basename:lineno of the frame that raised. NEVER the full path.

    A full path names the checkout directory, which on a developer machine names the user.
    """
    tb, last = exc.__traceback__, None
    while tb is not None:
        last, tb = tb, tb.tb_next
    if last is None:
        return ""
    return f"{os.path.basename(last.tb_frame.f_code.co_filename)}:{last.tb_lineno}"


def telemetry_props(state, started):
    """The event properties, from whatever the run has established so far.

    Progressive on purpose: a crash during rendering still reports the catalog and the row
    counts, because a crash report that says only "it broke" cannot be acted on.
    """
    import platform as _platform

    props = dict(state["props"])
    props["host_os"] = _platform.system() or "unknown"
    # MAJOR ONLY. "25.6.0" narrows a machine further than "25" does, and the question this
    # answers -- which OS generations are in use -- is answered by the major.
    props["host_os_release"] = (_platform.release() or "").split(".")[0].split("-")[0]
    props["python_version"] = _platform.python_version()
    props["duration_ms"] = int((time.time() - started) * 1000)
    return props


def telemetry_event(props, event_type, install_id):
    import uuid

    return {
        "device_id": install_id,
        "event_type": event_type,
        "time": int(time.time() * 1000),
        # Dedupes a retry inside Amplitude's 7-day window. We never retry, but a proxy or
        # a load balancer might.
        "insert_id": uuid.uuid4().hex,
        # THE ONE FIELD THAT IS NOT A COUNT. "$remote" tells Amplitude to take the source
        # address of this request and geolocate it. It is personal data under GDPR and
        # docs/telemetry.md says so in those words.
        "ip": "$remote",
        "os_name": props.get("host_os", ""),
        "os_version": props.get("host_os_release", ""),
        "event_properties": props,
    }


def telemetry_send(event):
    """Post one event, and let nothing about it reach the caller.

    THE ONE PLACE IN THIS REPO WHERE SWALLOWING AN ERROR IS CORRECT. Everywhere else a
    failure that produces no output is the bug -- an empty result indistinguishable from a
    clean machine. Here the answer is already printed and flushed; nothing downstream reads
    this, nobody is waiting on it, and a stack trace from an analytics call would be the
    tool inventing a failure it did not have. KeyboardInterrupt is a BaseException and is
    deliberately not caught: Ctrl-C means stop, including stopping this.
    """
    import urllib.request

    body = json.dumps({"api_key": _amplitude_key(), "events": [event]}).encode()
    req = urllib.request.Request(
        os.environ.get("AI_DISCOVERY_AMPLITUDE_URL") or AMPLITUDE_URL,
        data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TELEMETRY_TIMEOUT) as resp:
            resp.read()
    except Exception:
        pass


def telemetry_finish(state, started, event_type):
    off = _telemetry_off()
    if off and not state.get("check"):
        return
    props = telemetry_props(state, started)
    install_id, first_run = _install_id(create=not state.get("check"))
    event = telemetry_event(props, event_type, install_id)
    if state.get("check"):
        # Diagnostic mode: print what WOULD go, say whether it would, send nothing.
        json.dump({"would_send": off is None, "reason": off,
                   "endpoint": os.environ.get("AI_DISCOVERY_AMPLITUDE_URL") or AMPLITUDE_URL,
                   "event": event}, sys.stdout, indent=2, sort_keys=True)
        print()
        return
    if first_run:
        # STDERR, NEVER STDOUT. A notice on stdout would land inside the JSON document that
        # --json callers pipe into a parser, which is a broken run caused by a courtesy.
        print("classify: sending one anonymous usage event per run to Amplitude -- counts, "
              "not identifiers. `bin/classify --telemetry-check` prints exactly what is "
              "sent; AI_DISCOVERY_TELEMETRY=0 turns it off. See docs/telemetry.md.",
              file=sys.stderr)
    # AFTER the answer is on its way, so a stalled network cannot delay the bytes the
    # caller is actually waiting for.
    sys.stdout.flush()
    telemetry_send(event)


def main():
    started = time.time()
    # `phase` is which stage was running, so a crash report says WHERE rather than only
    # that there was one. `props` accumulates as facts become known.
    state = {"phase": "args", "props": {}, "check": False}
    try:
        _run(state, started)
    except SystemExit as exc:
        # Included because argparse's exit 2 and the missing-PyYAML sys.exit are real
        # deployment failures worth counting, and the sender needs only urllib -- so it
        # still works when PyYAML is the very thing that is missing. Exit 0 is --help.
        if exc.code not in (0, None):
            state["props"].update(error_type="SystemExit", error_site="",
                                  phase=state["phase"])
            telemetry_finish(state, started, "classify_crash")
        raise
    except Exception as exc:
        state["props"].update(error_type=type(exc).__name__, error_site=_error_site(exc),
                              phase=state["phase"])
        telemetry_finish(state, started, "classify_crash")
        # RE-RAISED UNTOUCHED. The traceback and the exit code are what the operator sees
        # today and reporting a crash must not change either of them.
        raise
    else:
        telemetry_finish(state, started, "classify_run")


def _run(state, started):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", nargs="?", help="osquery JSON; omit to read stdin")
    ap.add_argument("--catalog", default=DEFAULT_CATALOG)
    ap.add_argument("--routes", default=DEFAULT_ROUTES,
                    help="the route registry (catalog/routes.yaml)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--show-unmatched", action="store_true",
                    help="also list rows no signature claimed")
    ap.add_argument("--telemetry-check", action="store_true",
                    help="print the usage event this run would send, send nothing, and "
                         "stop. See docs/telemetry.md")
    args = ap.parse_args()
    state["check"] = args.telemetry_check

    state["phase"] = "read"
    raw = pathlib.Path(args.input).read_text() if args.input else sys.stdin.read()
    rows = json.loads(raw)

    state["phase"] = "classify"
    catalog = load_catalog(args.catalog)
    routes = load_routes(args.routes)
    findings, unmatched, gaps, scans = classify(rows, catalog, routes)
    # ONE clock reading for the whole report. time.time() used to be called three times
    # per scan row inside a comprehension, so two rows in one payload could straddle a
    # second boundary and date themselves differently from the same scan.
    now = int(time.time())
    aged = [(max(0, now - int(r.get("ver") or 0)), r) for r in scans]
    stale = [(a, r) for a, r in aged if a > STALE_AFTER]

    state["props"].update(_measure(raw, rows, findings, unmatched, gaps, scans, aged,
                                   stale, catalog, routes, args))
    if state["check"]:
        # Before rendering, and instead of it. This mode answers "what leaves my machine",
        # and mixing the report into that answer would make it harder to read and to pipe.
        return

    state["phase"] = "render"
    if args.json:
        json.dump({
            # `superseded` NAMES THE ROWS, and does not touch them. The evidence list is
            # raw rows passed through verbatim -- a consumer diffs them against its own
            # collection -- so the label rides beside it rather than being written into
            # rows that no osquery payload would ever carry it in.
            #
            # `only_superseded` is the fleet-actionable one: every identifier that matched
            # belongs to a release the vendor has moved past, which says this machine has
            # not updated. A finding with a mix is an ordinary current install that also
            # still carries an old artefact.
            "findings": [
                {"id": aid, "name": hits[0][0]["name"],
                 "classification": hits[0][0]["classification"],
                 "evidence": [r for _, r in hits],
                 **({"superseded": [r.get("id") for m, r in hits if m.get("superseded")],
                     "only_superseded": all(m.get("superseded") for m, _ in hits)}
                    if any(m.get("superseded") for m, _ in hits) else {})}
                for aid, hits in sorted(findings.items())
            ],
            # Omitted rather than emitted empty when it was not computed. An empty
            # list says "nothing was unclassified", which is a strong and usually
            # wrong claim -- 686 rows on the reference Mac. A missing key makes a
            # consumer ask for it instead of believing it.
            **({"unmatched": unmatched} if args.show_unmatched else {}),
            # `gaps` is not subject to that argument and is never hidden behind a flag.
            # It is not a computed absence but a positive report that a branch could not
            # look, and a consumer that treats findings as complete while a gap is open
            # is drawing the wrong conclusion from the right data.
            **({"gaps": gaps} if gaps else {}),
            # Provenance for the branches that DID run, with the age computed here so a
            # consumer never has to know that `ver` holds unix seconds.
            **({"scans": [{"id": r.get("id"), "at": int(r.get("ver") or 0),
                           "age_seconds": age, "stale": age > STALE_AFTER}
                          for age, r in aged]} if scans else {}),
        }, sys.stdout, indent=2)
        print()
        return

    # FIRST, and above the findings, because it changes what the findings mean. "No AI
    # agents found" under an unread branch is not an answer.
    # Staleness is judged HERE rather than on the endpoint. A cache is read with `cat`, so
    # the endpoint cannot check an mtime -- the payload carries its own timestamp instead and
    # the consumer decides what counts as old.
    def ago(seconds):
        return (f"{seconds // 86400}d" if seconds >= 86400 else
                f"{seconds // 3600}h" if seconds >= 3600 else
                f"{seconds // 60}m" if seconds >= 60 else f"{seconds}s")

    # A line per branch would be six lines of noise on a healthy Mac, so the fresh case is
    # one summary line and only the stale branches are named. Staleness is the part a reader
    # has to act on: a `cat` of a cache file cannot check its own mtime, so if nobody reads
    # the timestamp, a writer that stopped a month ago looks exactly like a current scan.
    for age, row in stale:
        print(f"STALE: {row.get('id', '?')} last scanned {ago(age)} ago. The scheduled "
              f"writer may have stopped. These rows are real but not current.")
    if aged and not stale:
        print(f"{len(aged)} branch{'es' if len(aged) > 1 else ''} scanned, "
              f"newest {ago(min(a for a, _ in aged))} ago")
    if aged:
        print()

    for row in gaps:
        # `loc` IS NOT ALWAYS A SOCKET, and defaulting it to "the socket" was wrong in a
        # way that read as authoritative. bin/discover's per-branch markers write
        # loc: "" -- so a failed `apps` branch rendered as
        # "COULD NOT LOOK: apps -- the socket reported 'error'", naming a socket that had
        # nothing to do with it. There is now no substituted noun: a marker either names
        # a place or the sentence does not claim one.
        reason, where, branch = row.get("extra", ""), row.get("loc") or "", row.get("id", "?")
        at = f" at {where}" if where else ""
        if reason == "absent":
            # Was "no Docker socket on this Mac". Two things wrong with that: containers
            # are no longer the only branch that reports absent -- the Linux systemd
            # branch does too -- and "this Mac" is not a safe thing for a matcher that
            # reads a mixed-platform fleet payload to say about anything.
            detail = f"no socket{at}" if where else "not present on this machine"
        elif reason == "no-cache":
            detail = (f"nothing has been written to {where or 'the cache'}. The scheduled "
                      f"writer is not installed, or has never run")
        elif reason == "error":
            # THE REASON bin/discover ACTUALLY EMITS, and the one this renderer had no
            # branch for. It means the branch ran and failed -- a missing table, a bad
            # query, a permission wall -- not that a daemon was unreachable.
            detail = f"the {branch} query ran and failed{at}"
        elif reason.startswith("unhealthy:"):
            detail = f"what answers{at or ' there'} answered {reason.split(':', 1)[1]}"
        elif reason.startswith("timeout:"):
            detail = (f"whatever answers{at or ' there'} accepted the connection and then "
                      f"stalled; gave up at {reason.split(':', 1)[1]}s")
        elif reason.startswith("unreadable:"):
            # `absent` was the only word a machine with no Docker socket could get, so a
            # Podman host read as one with no containers. The runtime is named because the
            # fix differs: Colima wants a candidate path in bin/container-scan, Podman
            # wants a different tool.
            detail = (f"a {reason.split(':', 1)[1]} runtime is installed{at} and is not "
                      f"read by this scan. Any containers it holds are uncounted")
        else:
            detail = f"reported {reason!r}" + (f" for {where}" if where else "")
        print(f"COULD NOT LOOK: {branch} -- {detail}")
    if gaps:
        print("  These are not findings and not an absence of them. That part of the "
              "machine was not read.\n")

    if not findings:
        print("No AI agents found." if not gaps else
              "No AI agents found in the parts that could be read.")
    for aid, hits in sorted(findings.items()):
        meta = hits[0][0]
        print(f"\n{meta['name']}  [{meta['classification']}]")
        for hit, row in hits:
            detail = row.get("loc") or row.get("id")
            ver = f"  {row['ver']}" if row.get("ver") else ""
            # Marked on the row, because the row is where a reader is looking when they
            # wonder why an identifier looks unfamiliar.
            old = "   <- earlier release" if hit.get("superseded") else ""
            print(f"    {row['kind']:7} {row.get('id','')}{ver}{old}")
            if detail and detail != row.get("id"):
                print(f"            {detail}")
        # SAID ONCE, WHEN IT IS THE WHOLE FINDING. A machine matched only on identifiers
        # the vendor has replaced is a machine that has not updated, and that is a fact
        # about the fleet rather than about this agent -- invisible while every row
        # rendered the same way.
        if all(h.get("superseded") for h, _ in hits):
            print("    Every identifier that matched belongs to an earlier release. "
                  "This machine has not updated.")

    if args.show_unmatched and unmatched:
        print(f"\nUnmatched ({len(unmatched)} rows no signature claimed):")
        for row in unmatched:
            print(f"    {row['kind']:7} {row.get('id','')}")

    # Exit 0 either way. Finding nothing is a valid answer, not an error.


def _measure(raw, rows, findings, unmatched, gaps, scans, aged, stale, catalog,
             routes, args):
    """Counts, and nothing but counts. Every value here is a number, a bool, or a word
    from a vocabulary this file declares.
    """
    kind_platforms = _kind_platforms(routes)
    known = set(kind_platforms) | {GAP_KIND}
    counts = defaultdict(int)
    for row in rows:
        kind = row.get("kind")
        counts[kind if kind in known else OTHER] += 1

    findings_rows = sum(len(hits) for hits in findings.values())
    reasons, codes, timeouts = set(), [], []
    for row in gaps:
        extra = row.get("extra") or ""
        head = extra.split(":", 1)[0]
        reasons.add(head if head in GAP_REASONS else OTHER)
        tail = extra.split(":", 1)[1] if ":" in extra else ""
        if head == "unhealthy" and tail.isdigit():
            codes.append(int(tail))
        if head == "timeout" and tail.isdigit():
            timeouts.append(int(tail))

    props = {
        "catalog_sha": _sha(args.catalog),
        "catalog_schema_version": catalog.get("version"),
        "catalog_agents": len(catalog.get("agents") or []),
        # The condition load_catalog already warns about on stderr. Counting it says how
        # often a downloaded classifier is older than the catalog beside it.
        "catalog_skew": isinstance(catalog.get("version"), int)
                        and catalog["version"] > CATALOG_VERSION,
        "classify_sha": _sha(__file__),
        "rows_total": len(rows),
        "findings_agents": len(findings),
        "findings_rows": findings_rows,
        # Always populated regardless of --show-unmatched: the flag gates the OUTPUT, not
        # the list, so counting it here changes no behaviour.
        "unmatched_rows": len(unmatched),
        # THE NUMBER NOTHING IN THIS TREE HAS EVER COUNTED. A row whose kind is in no route
        # falls off the end of classify()'s loop and is discarded in silence -- not
        # unmatched, DROPPED, invisible even under --show-unmatched. That is the bug that
        # hid every browser-extension row for months, and it was found by accident. A
        # non-zero value here on somebody's fleet is the same bug happening again.
        "dropped_rows": max(0, len(rows) - findings_rows - len(unmatched) - len(gaps)
                            - len(scans)),
        "gap_rows": len(gaps),
        "scan_rows": len(scans),
        # DOES WHAT WE COLLECT STILL FIT THE CHANNEL IT HAS TO TRAVEL THROUGH? Measured
        # from the bytes this process actually read, because row counts cannot answer it:
        # a real payload here runs 110 bytes a row for `brew` and 293 for `ext`, a 2.7x
        # spread, so a payload can grow a third in bytes while the row count barely moves.
        #
        # `packed` is gzip level 9 THEN base64, matching tools/measure_payload.py, because
        # a channel carrying one text value pays for the encoding too and the two figures
        # have to be comparable. THE 30KB BUDGET IS SELF-IMPOSED -- a Jamf Extension
        # Attribute convention this project keeps to, not a documented platform limit --
        # so the number is reported and the threshold is the reader's.
        "payload_bytes": len(raw.encode("utf-8", "replace")),
        "payload_packed_bytes": _packed_size(raw),
        "kinds_seen": ",".join(sorted(counts)),
        # An image row, or a containers marker either way it went. The marker is what makes
        # a FAILED deep scan count as an attempt: asking and being refused is use.
        "deep_scan": any(k in counts for k in ("image",))
                     or any(r.get("id") == "containers" for r in gaps + scans),
        "gap_reasons": ",".join(sorted(reasons)),
        "gap_unhealthy_code": max(codes) if codes else None,
        "gap_timeout_seconds": max(timeouts) if timeouts else None,
        "stale_branches": len(stale),
        "newest_scan_age_seconds": min((a for a, _ in aged), default=None),
        "payload_platform": _payload_platform(set(counts), kind_platforms),
        "output_mode": "json" if args.json else "text",
        "show_unmatched": bool(args.show_unmatched),
    }
    # A key whose value is unknown is OMITTED rather than sent as 0. "No timeout happened"
    # and "a timeout of zero seconds" are different facts, and Amplitude cannot tell them
    # apart once both are a number.
    return {k: v for k, v in props.items() if v is not None}


if __name__ == "__main__":
    main()
