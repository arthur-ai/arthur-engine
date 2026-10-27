#!/usr/bin/env python3
"""Match evidence rows against a catalog and name the agents they prove (SPEC.md 6).

    osqueryi --json < osquery/dist/discovery-darwin.sql | bin/classify
    osquery/bin/discover --deep | bin/classify
    bin/classify --catalog catalog.json rows.json

The reference matcher for ai-detection-spec. It reads evidence rows from any binding, and a
catalog in either form: a catalog document (SPEC.md 4), such as the catalog.json a release
attaches, or this repository's authoring form, catalog/agents.yaml beside
catalog/routes.yaml. It is small so that it can be read, and it is not the definition of
matching: where it disagrees with conformance/vectors.json, it is wrong.

Standard library only, except PyYAML for the authoring form and jsonschema for a catalog
document, which is validated before it is read.
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
CATALOG_SCHEMA = ROOT / "schema" / "catalog.schema.json"

# WHAT THIS MATCHER READS. A catalog document names its version in `format`, the authoring
# form in `version`, and either one this matcher does not read is refused (SPEC.md 10): an
# error the operator sees, never a catalog matched in part.
FORMATS = frozenset({"ai-detection-spec/0.2"})
# Bumped with the format when matching changes: a matcher that predates Windows home roots
# would read this catalog and report every Windows path unmatched.
CATALOG_VERSION = 4


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
    return yaml.safe_load(pathlib.Path(path).read_text(encoding="utf-8"))


def read_catalog(path, routes_path=DEFAULT_ROUTES):
    """The catalog and its route registry, from either form a catalog takes.

    TOLD APART BY `format`, and it has to be. Read as the authoring form, a catalog document's
    agents carry no route keys, so every row came back unmatched and the report said "No AI
    agents found" -- this repository's own catalog.json, read as a clean machine.

    JSON is parsed without PyYAML, so a catalog document needs only jsonschema.
    """
    try:
        doc = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except ValueError:
        doc = _yaml(path)
    if isinstance(doc, dict) and "format" in doc:
        return from_document(doc, path)
    return load_catalog(path, doc), load_routes(routes_path)


def from_document(doc, where="the catalog", schema=CATALOG_SCHEMA):
    """A catalog document (SPEC.md 4) as the catalog and route registry this file works in.

    REFUSED, NEVER READ IN PART: a `format` this matcher does not support (SPEC.md 10), a
    document the schema rejects (SPEC.md 4), and an identifier it could not index (SPEC.md
    6). Each would otherwise match less than the catalog says, and say nothing. `schema=None`
    skips only the JSON Schema step, for the rendered-SQL tests, which run without jsonschema.
    """
    fmt = doc.get("format") if isinstance(doc, dict) else None
    if fmt not in FORMATS:
        sys.exit(f"classify: {where} is format {fmt!r}, and this matcher reads "
                 f"{', '.join(sorted(FORMATS))}. Refusing it rather than matching nothing "
                 f"(SPEC.md 10).")
    if schema is not None:
        errors = schema_errors(doc, schema)
        if errors:
            sys.exit(f"classify: {where} does not validate against {schema} (SPEC.md 4):\n  "
                     + "\n  ".join(errors[:5]))
    try:
        routes = {"platforms": list(doc["platforms"]),
                  "platform_groups": dict(doc["platform_groups"]),
                  "routes": {name: {k: v for k, v in r.items() if k != "bindings"}
                             for name, r in doc["routes"].items()}}
        agents = []
        for a in doc["agents"]:
            entry = {k: a[k] for k in ("id", "name", "classification", "platforms")}
            superseded = []
            for ident in a["identifiers"]:
                entry.setdefault(ident["route"], []).append(ident["value"])
                if ident["status"] == "superseded":
                    superseded.append({"route": ident["route"], "value": ident["value"],
                                       **ident["superseded"]})
            if superseded:
                entry["superseded"] = superseded
            agents.append(entry)
        # No `version`: that is the authoring form's, and `format` was checked above.
        catalog = {"classifications": doc["classifications"], "agents": agents}
        own = {n for n, r in routes["routes"].items()
               if not r.get("values_from") and not r.get("retired")}
        stray = sorted({f"{a['id']} on {i['route']!r}" for a in doc["agents"]
                        for i in a["identifiers"] if i["route"] not in own})
    except (KeyError, TypeError, AttributeError) as exc:
        sys.exit(f"classify: {where} says {fmt!r} and is not a catalog document: "
                 f"{type(exc).__name__} {exc}")
    if stray:
        sys.exit(f"classify: {where} puts identifiers where no route indexes them -- an "
                 f"undeclared, borrowing or retired route (SPEC.md 4.4 rules 1 and 2): "
                 f"{', '.join(stray)}")
    return catalog, routes


def schema_errors(doc, schema):
    """Where `doc` fails the JSON Schema at `schema`, as `path: message`."""
    try:
        import jsonschema
    except ImportError:
        sys.exit("classify: a catalog document is validated before it is read (SPEC.md 4), "
                 "and that needs jsonschema: pip install jsonschema")
    try:
        loaded = json.loads(pathlib.Path(schema).read_text(encoding="utf-8"))
    except OSError:
        sys.exit(f"classify: a catalog document is validated against {schema}, which is "
                 f"missing. A release attaches catalog.schema.json: put it in schema/, "
                 f"beside bin/.")
    return [f"{'/'.join(map(str, e.absolute_path)) or '(document)'}: {e.message}"
            for e in jsonschema.Draft202012Validator(loaded).iter_errors(doc)]


def load_catalog(path, doc=None):
    """The authoring form, catalog/agents.yaml. A catalog document goes through
    read_catalog(), and is refused here rather than read as a catalog with no agents."""
    doc = _yaml(path) if doc is None else doc
    if isinstance(doc, dict) and "format" in doc:
        sys.exit(f"classify: {path} is a catalog document ({doc['format']!r}); read it with "
                 f"read_catalog(), which takes its routes from it")
    version = doc.get("version") if isinstance(doc, dict) else None
    if version != CATALOG_VERSION:
        sys.exit(f"classify: {path} is catalog version {version!r}, and this matcher reads "
                 f"{CATALOG_VERSION}. Refusing it rather than matching it in part (SPEC.md "
                 f"10); use the bin/classify released with it.")
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
        # AN UNKNOWN MODE STOPS HERE, on every route (SPEC.md 6.4.8). Checked per value in
        # build_index(), it never fired on a route with no values, and any `home-` mode was
        # read as home-prefix.
        unknown = [f"{n} declares {m!r}" for n, m in self.match.items() if m not in MATCH_MODES]
        if unknown:
            raise ValueError(f"routes.yaml: unknown match mode: {'; '.join(unknown)}. This "
                             f"matcher implements {', '.join(sorted(MATCH_MODES))}")
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
        # excluded on purpose: pypi evidence arrives as kind='file' through the TOOL_DIRS
        # bridge, and listing it here as well is what let a PyPI-only signature claim an
        # npm package of the same name -- npm's `mcp` is Mintlify's, and it was reported
        # as the MCP SDK until the two were split.
        self.kind_routes = {}
        for name, r in self.routes.items():
            if r["match"] == "tool-dir":
                self.kind_routes.setdefault(r["kind"], [])
                continue
            self.kind_routes.setdefault(r["kind"], []).append(name)

        # KINDS WHOSE ROW SAYS THE AGENT IS RUNNING, not only installed. Declared per route
        # with `live: true` in catalog/routes.yaml; a finding with one of these kinds in its
        # evidence is marked `running`. Every other route reports presence.
        self.live_kinds = frozenset(r["kind"] for r in self.routes.values() if r.get("live"))

    def bridged(self):
        """The routes a pipx or uv tool directory can name: the `tool-dir` routes, and
        nothing else. The directory is named for a PyPI distribution.

        It also used to try every npm route, "for agents that ship both". None does, and
        the only row that ever exercised it was a synthetic control naming a uv directory
        `openclaw`, which PyPI does not carry. Computed here once; bin/classify,
        tools/agent_status.py and osquery/tools/render_match.py each computed it before,
        and three copies is the shape of the `ext` bug."""
        return [r for r, m in self.match.items() if m == "tool-dir"]

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
# input can legitimately carry /Users/dana/.claude, /home/dana/.claude and
# C:\Users\dana\.claude. An earlier design took a platform argument, which would have made
# a mixed payload match only half of itself and reported the rest as unmatched.
#
# One pattern per value, alternating over every root, rather than one per platform,
# because path routes are compared against every candidate row --
# docs/signature-lifecycle.md's scaling note.
#
# EACH ROOT HAS ITS OWN SEPARATORS (SPEC.md 6.4.7), so each entry is (root, separator, one
# path component): `/` under a POSIX root, where `\` is an ordinary filename character, and
# either under a Windows root, which accepts both. So `/home/u\.claude` is not `~/.claude`
# and `C:\Users\u/.claude` is. The drive is any letter in either case, because it carries
# no identity; `Users` is compared as written, like everything else (SPEC.md 6.4).
#
# /root gets its own alternative: root's home is not under /home, and a `[^/]+`
# component cannot reach it. Verified against `users.directory` on Ubuntu and Fedora.
ROOT_KINDS = (
    (r"(?:/Users/[^/]+/|/home/[^/]+/|/root/)", "/", r"[^/]+"),
    (r"[A-Za-z]:[\\/]Users[\\/][^\\/]+[\\/]", r"[\\/]", r"[^\\/]+"),
)


def _under(root, sep, rel):
    """`rel`, a `/`-separated path below a home (SPEC.md 4.4 rule 4), as a regex below `root`."""
    return root + sep.join(re.escape(part) for part in rel.split("/"))


# THE MATCH MODES. The spec declares them in schema/catalog.schema.json; this is a copy,
# because bin/classify ships without schema/. test/test_conformance.py holds the two equal,
# tools/validate_catalog.py reads this one, and Registry refuses any other mode.
MATCH_MODES = frozenset({"exact", "prefix", "exact-normalised", "home-dir", "home-prefix",
                         "tool-dir"})


def home_pattern(value, mode):
    """Compile a `~/`-rooted catalog value into a regex over real paths.

    THE ANCHOR IS PER ROUTE, and that is the whole point of having two modes.

      home-dir     `~/.claude` -> matches `.../.claude` and `.../.claude/` and NOT
                   `.../.claudefoo`. The glob was front-anchored only, so `.claudefoo`
                   DID match -- confirmed on a real Linux box, where `/home/%/.%/`
                   returns both directories side by side.
      home-prefix  `~/.local/bin/claude` -> that path, or anything under it, and nothing
                   that merely starts with its name: `claude-monitor`, a third-party
                   usage tool, is not Claude Code. A value ending in `/` claims everything
                   under it, which is how a version directory is reached. A command's
                   siblings (hermes-acp, muse-bin-<version>) are not claimed: the command
                   itself is always written with them, so the agent is found anyway.
    """
    # `\Z`, NOT `$`: Python's `$` also matches before a final newline, which neither the
    # format nor osquery's regex_match does. osquery/tools/render_match.py writes it as `$`.
    rel = value[2:]                                  # strip the leading '~/'
    if mode == "home-dir":
        alts = (_under(root, sep, rel) + sep + "?" for root, sep, _ in ROOT_KINDS)
        return re.compile("^(?:" + "|".join(alts) + r")\Z")
    # A group rather than a lookahead: osquery/dist/signatures.sql hands this pattern to osquery's
    # regex_match, and a pattern it cannot compile aborts the whole statement.
    alts = (_under(root, sep, rel) + ("" if value.endswith("/") else "(?:" + sep + r"|\Z)")
            for root, sep, _ in ROOT_KINDS)
    return re.compile("^(?:" + "|".join(alts) + ")")


def build_index(catalog, registry):
    """Map every catalog identifier to the agent that claims it.

    Routes differ in how they match, and conflating them is how false positives
    happen: `mcp` as an exact npm package name is a real signal, but `mcp` as a
    substring also matches `libxdmcp`, an X11 library. Exact where exact is right.

    Which route matches how is now DECLARED, in catalog/routes.yaml, rather than
    written out as four route-name tuples here. A route added there is indexed here
    without an edit -- and a mode this function does not know is refused by Registry,
    and again here, instead of rows that quietly match nothing.
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
        # in the loop that does the matching. It costs one small dict per catalog value.
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
            #
            # `route` and `value` name the identifier itself -- on the route that holds it --
            # so a finding can say which identifier proved each row, not only which agent.
            meta = {**_base, "route": route, "value": str(value)}
            if (route, str(value)) in _sup:
                meta["superseded"] = True
            return meta

        for route, mode in registry.match.items():
            # A RETIRED ROUTE IDENTIFIES NOTHING, and tools/validate_catalog.py refuses a
            # value under one. Skipped here as well, so a catalog from elsewhere that
            # carries one cannot make it fire.
            if route in registry.retired:
                continue
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
                    # EXACT MEANS EXACT. A trailing `*` used to turn a value into a prefix
                    # here, which no agent used, the rendered SQL refused, and a spec would
                    # have had to define as a fourth mode hiding inside the first.
                    # tools/validate_catalog.py now refuses one.
                    exact[(route, str(value))] = meta
                elif mode == "prefix":
                    prefix.append((str(value), route, meta))
                elif mode == "exact-normalised":
                    # Exact on the NORMALISED repository, never a substring. `ollama` as
                    # a substring would claim `myorg/ollama-fork` and `not-ollama`, and
                    # an image name is attacker-choosable in a way a bundle id is not:
                    # anyone can `docker tag` anything.
                    exact[(route, image_repo(value))] = meta
                elif mode in ("home-dir", "home-prefix"):
                    glob.append((home_pattern(str(value), mode), route, meta))
                else:
                    raise ValueError(f"routes.yaml: unknown match mode: {route} declares "
                                     f"{mode!r}")
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
# ROOT_KINDS rather than a hardcoded /Users/, so a uv tool install under /home/dana, /root
# or C:\Users\dana resolves the same way. That was one of three hand copies of the same
# prefix; the other two were this file's path globs and tools/agent_status.py's replay.
#
# The layouts are written once, here; tools/validate_catalog.py reads them for overlaps.
# The AppData pair is where pipx and uv put a tool on Windows by default, read off
# windows-2025 (survey runs 40393754308 and 40396366136: `pipx environment`, `uv tool dir`).
TOOL_LAYOUTS = ("~/.local/pipx/venvs/", "~/.local/share/uv/tools/",
                "~/AppData/Local/pipx/pipx/venvs/", "~/AppData/Roaming/uv/tools/")
# ONE PATTERN PER KIND OF ROOT, each capturing the name as group 1. Not one alternation: a
# group number cannot be shared across branches, and the rendered SQL reads group 1.
TOOL_DIRS = tuple(
    re.compile("^" + root + "(?:" + "|".join(_under("", sep, lay[2:]) for lay in TOOL_LAYOUTS)
               + ")(" + part + ")" + sep + r"?\Z")
    for root, sep, part in ROOT_KINDS)


def tool_names(*paths):
    """The package each path names as a pipx or uv tool directory, in the order given."""
    for path in paths:
        for pattern in TOOL_DIRS:
            m = pattern.match(path)
            if m:
                yield m.group(1)
                break



# A scan marker (SPEC.md 5.2): a row about a source rather than about what it holds. No route
# declares this kind, so it is handled before the route loop or it would be DROPPED -- the
# row that exists to stop a wedged daemon reading as an empty machine, swallowed by the
# matcher one hop after surviving the scan.
SCAN_KIND = "scan"
# AN EXTENSION ROW'S `extra` IS ITS BROWSER, then at most one provenance token: `unreferenced`
# (on disk, never loaded) or `sideloaded:<sha256>` (registered, not from the Web Store). A
# token ending in `:` carries a value. osquery/test/lint.sh holds these to the tokens the
# osquery binding emits.
PROVENANCE = ("unreferenced", "sideloaded:")


def provenance(row):
    """An `ext` row's provenance token, or ''."""
    if row.get("kind") != "ext":
        return ""
    tail = (row.get("extra") or "").split(",")[1:]
    token = tail[-1].strip() if tail else ""
    return token if any(token.startswith(t) if t.endswith(":") else token == t
                        for t in PROVENANCE) else ""


# Two presentation choices for primary() and describe(), not matching rules. `ver` needs no
# table: it is a version wherever it is set (SPEC.md 5.1).
#
#   INSTALL_KINDS  read from an install record -- a package database, a bundle, a manifest
#   PATH_KINDS     `loc` is where the agent is installed. Not `proc`, whose `loc` may be the
#                  interpreter running it, nor `image`, `container` or `ilabel`, whose `loc`
#                  is an id, nor `uninstall`, whose `loc` is a registry key
INSTALL_KINDS = frozenset({"app", "brew", "deb", "ext", "jbplugin", "msix", "npm", "rpm",
                           "uninstall", "vscodeext"})
PATH_KINDS = frozenset({"app", "brew", "daemon", "desktop", "ext", "file", "jbplugin", "msix",
                        "nmh", "npm", "port", "unit", "vscodeext"})


def kind_rank(routes):
    """Each row kind's place in catalog/routes.yaml, by the first route that carries it.

    The registry declares vendor-controlled identifiers first -- a bundle id before a path
    glob -- so this breaks ties between rows that are otherwise equally good evidence.
    """
    rank = {}
    for spec in (routes.get("routes") or {}).values():
        kind = (spec or {}).get("kind")
        if isinstance(kind, str):
            rank.setdefault(kind, len(rank))
    return rank


def primary(rows, rank, superseded=None, live=None):
    """The index of the row that speaks for a finding: its version, its path, its address.

    ONE ANSWER FOR EVERY CONSUMER. A finding is one agent proved by several rows, and a
    consumer that records one version and one location has to pick a row. Each picking its
    own way is how two dashboards disagree about the same machine, so the rule is here:

      presence before liveness    a running process names a process, not an install, and
                                  an address taken from one moves whenever it stops
      loaded before unreferenced  a browser profile keeps old version directories, and the
                                  first row is often one of them
      an install record next      a row of a kind read from a package database, a bundle
                                  or a manifest (INSTALL_KINDS), whether or not this one's
                                  version could be read. `deb claude-code` speaks before
                                  `~/.claude/`, which appears on first run; and a bundle id
                                  stays ahead of its Homebrew cask when the bundle declares
                                  no version, because the KIND decides, not the string
      current before superseded   `superseded`, when given, is one flag per row: the
                                  identifier that matched it belongs to a release the
                                  vendor has replaced (see build_index)
      then kind_rank

    Ties keep evidence order, so one payload always gives one answer.
    """
    flags = list(superseded) if superseded is not None else [False] * len(rows)
    # `live` is the registry's live kinds; absent, this repo's own registry's, as
    # classify() defaults its catalog and routes.
    live = Registry(load_routes()).live_kinds if live is None else live

    def key(i):
        row = rows[i]
        kind = row.get("kind")
        return (kind in live,
                provenance(row) == "unreferenced",
                kind not in INSTALL_KINDS,
                bool(flags[i]),
                rank.get(kind, len(rank)),
                i)
    return min(range(len(rows)), key=key)


def describe(rows, rank, superseded=None, live=None):
    """`primary`, plus that row's `version`, and its `path` where its kind carries one.
    Omitted rather than emitted empty: an empty version reads as a known blank, not as none."""
    i = primary(rows, rank, superseded, live)
    row = rows[i]
    out = {"primary": i}
    if row.get("ver"):
        out["version"] = row["ver"]
    if row.get("kind") in PATH_KINDS and row.get("loc"):
        out["path"] = row["loc"]
    return out


# `extra` on a scan row: "ok" means the branch ran and the rows beside it are real. `ver` is
# when the scan ran, in unix seconds, so a cached payload dates itself and a consumer can
# judge staleness without stat()ing anything.
SCAN_OK = "ok"
# THE THIRD ANSWER, AND IT IS NOT A REASON THE BRANCH COULD NOT LOOK. `absent` says the
# branch read the machine and there was nothing there to read: no container runtime, no
# systemd bus socket. Filed as a gap it withholds "No AI agents found." from every machine
# that simply does not run containers -- the sentence is hedged whenever anything did not
# return `ok`, so that machine can never reach the unhedged one.
#
# It is bounded by what this scan knows to look for, and so is every other branch: `apps=ok`
# does not claim no AI app exists anywhere, only that none matched where it globbed. Holding
# `absent` to a higher standard than `ok` buys nothing and costs the clean answer on most of
# the fleet. A runtime that IS present and unread says `unreadable:<runtime>`, which is a gap
# and stays one -- that split is what makes this one safe.
SCAN_ABSENT = "absent"
STALE_AFTER = 24 * 3600


def classify(rows, catalog, routes=None):
    """Match rows against the catalog. `routes` is catalog/routes.yaml, loaded once.

    The registry and the index are built ONCE here rather than per row, and the caller
    may pass a pre-loaded `routes` so a tool classifying many payloads does not re-read
    the file. Left optional so the existing two-argument call keeps working.

    Returns `(findings, unmatched, gaps, scans, absences, dropped)`. `dropped` is returned
    rather than left to the caller's arithmetic: this loop is the only place that knows a
    row fell off it, and a reconciliation that forgets `absences` reads them as dropped.
    """
    registry = Registry(routes if routes is not None else load_routes())
    exact, prefix, glob = build_index(catalog, registry)
    kind_routes = registry.kind_routes
    tool_kinds = {registry.routes[r]["kind"] for r in registry.bridged()}
    findings, unmatched, gaps, scans, absences, dropped = defaultdict(list), [], [], [], [], []

    for row in rows:
        kind, ident, loc = row.get("kind"), row.get("id", ""), row.get("loc", "")
        hit = None

        if kind == SCAN_KIND:
            # A dated success is provenance, not a gap. Splitting them here is what lets
            # `cat`-ing a cache file produce the same reading as a live scan.
            # Three buckets, not two: ran (`scans`), read and found nothing there
            # (`absences`), could not read (`gaps`). Only the third makes findings
            # incomplete, and only the third should make a reader hedge.
            extra = row.get("extra")
            if extra == SCAN_OK:
                scans.append(row)
            elif extra == SCAN_ABSENT:
                absences.append(row)
            else:
                gaps.append(row)
            continue

        # A pipx/uv tool directory names its package. Try that before the path globs,
        # which describe state directories rather than install locations. `id` and `loc`
        # each yield a name (SPEC.md 6.4.6); taking only the first that parsed missed a row
        # whose `id` named another directory.
        if kind in tool_kinds:
            for name in tool_names(ident, loc):
                hit = next((exact[(r, name)] for r in registry.bridged() if (r, name) in exact),
                           None)
                if hit:
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
                hit = exact[(route, ident)]
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
            # exists. A kind absent from it can never match -- see the note above
            # kind_routes -- and is returned as dropped so that it is counted and said.
            unmatched.append(row)
        else:
            dropped.append(row)

    return findings, unmatched, gaps, scans, absences, dropped


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
# osquery/bin/discover and osquery/bin/container-scan send NOTHING, and that is not an oversight to
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
    "catalog_sha", "catalog_schema_version", "catalog_agents",
    "classify_sha",
    "rows_total", "findings_agents", "findings_rows", "unmatched_rows", "dropped_rows",
    "payload_bytes", "payload_packed_bytes",
    "gap_rows", "absence_rows", "scan_rows",
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
# Anything unrecognised becomes "other" -- which is itself a finding worth seeing. These are
# the schema's outcomes other than `ok`, by head; test/test_telemetry.py holds the copy equal.
GAP_REASONS = ("absent", "no-cache", "error", "unhealthy", "timeout", "unreadable")
OTHER = "other"


def _env_off(name):
    return os.environ.get(name, "").strip().lower() in {"0", "false", "no", "off"}


def _amplitude_key():
    return os.environ.get("AI_DETECTION_SPEC_AMPLITUDE_KEY", "").strip() or AMPLITUDE_KEY


def _telemetry_off():
    """Why this run will not send, or None if it will.

    A REASON RATHER THAN A BOOLEAN. "Sent nothing because it is switched off" and "sent
    nothing because the key is missing" are the same silence otherwise, and telling those
    two apart is the distinction this entire repo is built around. --telemetry-check
    prints it.
    """
    if _env_off("AI_DETECTION_SPEC_TELEMETRY"):
        return "AI_DETECTION_SPEC_TELEMETRY is set to off"
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
    path = pathlib.Path(base) / "ai-detection-spec" / "install-id"
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
    and `npm` come from every platform and say nothing. A payload merged from several is a
    real and supported state, so it gets its own word rather than being forced into one.
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
        os.environ.get("AI_DETECTION_SPEC_AMPLITUDE_URL") or AMPLITUDE_URL,
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
                   "endpoint": os.environ.get("AI_DETECTION_SPEC_AMPLITUDE_URL") or AMPLITUDE_URL,
                   "event": event}, sys.stdout, indent=2, sort_keys=True)
        print()
        return
    if first_run:
        # STDERR, NEVER STDOUT. A notice on stdout would land inside the JSON document that
        # --json callers pipe into a parser, which is a broken run caused by a courtesy.
        print("classify: sending one anonymous usage event per run to Amplitude -- counts, "
              "not identifiers. `bin/classify --telemetry-check` prints exactly what is "
              "sent; AI_DETECTION_SPEC_TELEMETRY=0 turns it off. See docs/telemetry.md.",
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
    ap.add_argument("input", nargs="?",
                    help="a JSON array of evidence rows (SPEC.md 5); omit to read stdin")
    ap.add_argument("--catalog", default=DEFAULT_CATALOG,
                    help="a catalog document, or the authoring form (catalog/agents.yaml)")
    ap.add_argument("--routes", default=DEFAULT_ROUTES,
                    help="the authoring form's route registry (catalog/routes.yaml); a "
                         "catalog document carries its own")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--show-unmatched", action="store_true",
                    help="also list rows no signature claimed")
    ap.add_argument("--telemetry-check", action="store_true",
                    help="print the usage event this run would send, send nothing, and "
                         "stop. See docs/telemetry.md")
    args = ap.parse_args()
    state["check"] = args.telemetry_check

    state["phase"] = "read"
    raw = (pathlib.Path(args.input).read_text(encoding="utf-8") if args.input
           else sys.stdin.read())
    rows = json.loads(raw)

    # Its own phase, so a refused catalog is counted as one rather than as a crash anywhere.
    state["phase"] = "catalog"
    catalog, routes = read_catalog(args.catalog, args.routes)
    state["phase"] = "classify"
    rank = kind_rank(routes)
    live_kinds = Registry(routes).live_kinds
    # DROPPED IS COUNTED AND SAID, not only sent in telemetry. A row whose kind no route
    # declares can never match, and a kind missing from a catalog is how every
    # browser-extension row once vanished without a trace (SPEC.md 6.1).
    findings, unmatched, gaps, scans, absences, dropped = classify(rows, catalog, routes)
    # ONE clock reading for the whole report. time.time() used to be called three times
    # per scan row inside a comprehension, so two rows in one payload could straddle a
    # second boundary and date themselves differently from the same scan.
    now = int(time.time())
    aged = [(max(0, now - int(r.get("ver") or 0)), r) for r in scans]
    stale = [(a, r) for a, r in aged if a > STALE_AFTER]

    state["props"].update(_measure(raw, rows, findings, unmatched, gaps, scans, absences,
                                   dropped, aged, stale, catalog, routes, args))
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
            #
            # `primary` is an index into `evidence`, and `version` and `path` are that row's
            # -- see primary(). An index rather than a copy, for the same reason.
            "findings": [
                {"id": aid, "name": hits[0][0]["name"],
                 "classification": hits[0][0]["classification"],
                 "evidence": [r for _, r in hits],
                 **describe([r for _, r in hits], rank,
                            [bool(m.get("superseded")) for m, _ in hits], live_kinds),
                 # Which identifier matched each evidence row, in the same order.
                 "matches": [{"route": m["route"], "value": m["value"]} for m, _ in hits],
                 **({"running": True}
                    if any(r.get("kind") in live_kinds for _, r in hits) else {}),
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
            **({"dropped": len(dropped)} if dropped else {}),
            # `gaps` is not subject to that argument and is never hidden behind a flag.
            # It is not a computed absence but a positive report that a branch could not
            # look, and a consumer that treats findings as complete while a gap is open
            # is drawing the wrong conclusion from the right data.
            **({"gaps": gaps} if gaps else {}),
            # Not folded into `gaps`: a branch that read the machine and found nothing to
            # read is a different claim from one that could not read it, and a consumer
            # that cannot tell them apart has to hedge on both.
            **({"absences": absences} if absences else {}),
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
        # way that read as authoritative. osquery/bin/discover's per-branch markers write
        # loc: "" -- so a failed `apps` branch rendered as
        # "COULD NOT LOOK: apps -- the socket reported 'error'", naming a socket that had
        # nothing to do with it. There is now no substituted noun: a marker either names
        # a place or the sentence does not claim one.
        reason, where, branch = row.get("extra", ""), row.get("loc") or "", row.get("id", "?")
        at = f" at {where}" if where else ""
        if reason == "no-cache":
            detail = (f"nothing has been written to {where or 'the cache'}. The scheduled "
                      f"writer is not installed, or has never run")
        elif reason == "error":
            # THE REASON osquery/bin/discover ACTUALLY EMITS, and the one this renderer had no
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
            # fix differs: Colima wants a candidate path in osquery/bin/container-scan, Podman
            # wants a different tool.
            detail = (f"a {reason.split(':', 1)[1]} runtime is installed{at} and is not "
                      f"read by this scan. Any containers it holds are uncounted")
        else:
            detail = f"reported {reason!r}" + (f" for {where}" if where else "")
        print(f"COULD NOT LOOK: {branch} -- {detail}")
    if gaps:
        print("  These are not findings and not an absence of them. That part of the "
              "machine was not read.\n")
    # Up here with the gaps, for the same reason: it changes what the headline means.
    if dropped:
        kinds = ", ".join(sorted({str(r.get("kind")) for r in dropped}))
        print(f"DROPPED: {len(dropped)} row(s) of a kind no route declares ({kinds}). They "
              f"cannot match anything; the catalog does not register their kind.\n")

    for row in absences:
        # No substituted noun here either: `loc` is the path the branch checked, so it is
        # evidence of where we looked and not of something that was there.
        where = row.get("loc") or ""
        print(f"NOTHING TO LOOK AT: {row.get('id', '?')} -- not present on this machine"
              + (f" (no {where})" if where else ""))
    if absences:
        # Deliberately NOT the sentence above. This branch read the machine; the absence
        # it reports is a finding about the machine rather than a hole in the report.
        print()

    if not findings:
        print("No AI agents found in the parts that could be read." if gaps else
              "No AI agents found in the rows this catalog can match." if dropped else
              "No AI agents found.")
    for aid, hits in sorted(findings.items()):
        meta = hits[0][0]
        live = "  running" if any(r.get("kind") in live_kinds for _, r in hits) else ""
        print(f"\n{meta['name']}  [{meta['classification']}]{live}")
        for hit, row in hits:
            detail = row.get("loc") or row.get("id")
            ver = f"  {row['ver']}" if row.get("ver") else ""
            # Marked on the row, because the row is where a reader is looking when they
            # wonder why an identifier looks unfamiliar.
            old = "   <- earlier release" if hit.get("superseded") else ""
            # An unreferenced extension is on disk and never loaded, so it is said beside the
            # row rather than left to read like an installed one.
            prov = provenance(row)
            prov = f"   <- {prov.split(':')[0]}" if prov else ""
            print(f"    {row['kind']:7} {row.get('id','')}{ver}{old}{prov}")
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


def _measure(raw, rows, findings, unmatched, gaps, scans, absences, dropped, aged, stale,
             catalog, routes, args):
    """Counts, and nothing but counts. Every value here is a number, a bool, or a word
    from a vocabulary this file declares.
    """
    kind_platforms = _kind_platforms(routes)
    known = set(kind_platforms) | {SCAN_KIND}
    counts = defaultdict(int)
    for row in rows:
        kind = row.get("kind")
        counts[kind if kind in known else OTHER] += 1

    findings_rows = sum(len(hits) for hits in findings.values())
    reasons, codes, timeouts = set(), [], []
    # Over both buckets. The split is about what a READER should conclude; how often each
    # outcome happens is the same question it always was, and dropping `absent` here would
    # silently retire a counter rather than change a meaning.
    for row in (*gaps, *absences):
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
        "dropped_rows": len(dropped),
        "gap_rows": len(gaps),
        "scan_rows": len(scans),
        # Counted apart from gap_rows for the same reason they are bucketed apart: a fleet
        # where this is high and gap_rows is zero is a fleet without containers, not a
        # fleet whose container scan is failing.
        "absence_rows": len(absences),
        # DOES WHAT WE COLLECT STILL FIT THE CHANNEL IT HAS TO TRAVEL THROUGH? Measured
        # from the bytes this process actually read, because row counts cannot answer it:
        # a real payload here runs 110 bytes a row for `brew` and 293 for `ext`, a 2.7x
        # spread, so a payload can grow a third in bytes while the row count barely moves.
        #
        # `packed` is gzip level 9 THEN base64, matching osquery/tools/measure_payload.py, because
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
