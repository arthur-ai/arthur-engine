#!/usr/bin/env bash
# Static checks on what THIS repo owns. No VM, no network — runs in about a second, so CI
# can gate on it.
#
# This repo owns the deployable and nothing else. The queries, the runner, the Docker guard
# and the wall-clock bound live in osquery-ai-discovery and are vendored at a pinned ref;
# their regression suite is upstream's — `test/lint.sh`, `test/docker_states.sh` and
# thirteen VM scenarios at the vendored ref, run by upstream CI. Duplicating any of it here
# is how the two drift apart.
#
# So what is checked here is the seam: that nothing outside vendor/ implements discovery,
# that the built collector carries the vendored tree, and that the framing this repo owns
# is still in it.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
fail=0

# --- one implementation, and it is the vendored one --------------------------------------
# THE GUARD FOR THIS REPO'S LARGEST PAST MISTAKE. It carried a second, hand-written osquery
# implementation -- three .sql files and a runner reimplementing the Docker guard and the
# bound -- beside the vendored one. They diverged in the way that matters and nothing said
# so: the local query filtered to a list of known bundle ids while the deployed one
# enumerates, so the two answered different questions about the same Mac and both looked
# healthy. A second copy does not announce itself; it has to be forbidden.
python3 - "$ROOT" <<'ONE' || fail=1
import os, re, sys
root = sys.argv[1]
# Documentation quotes SQL on purpose, and this file names osqueryi to forbid it. Neither
# is an implementation, so both are out of scope -- the scan covers what executes.
SKIP_DIRS = {".git", "vendor", "docs"}
SELF = os.path.join("test", "lint.sh")
bad = []
for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
    for fn in filenames:
        rel = os.path.relpath(os.path.join(dirpath, fn), root)
        if rel == SELF or rel.endswith(".md"):
            continue
        if fn.endswith(".sql"):
            bad.append(f"{rel}: a .sql file outside vendor/")
            continue
        try:
            text = open(os.path.join(dirpath, fn), encoding="utf-8").read()
        except (OSError, UnicodeDecodeError):
            continue
        # AN INVOCATION, NOT A MENTION, AND COMMENTS ARE MENTIONS. The pattern reads
        # `osqueryi --` as a call, which is also how prose spells it: a comment in
        # test/run-collector.sh explaining why it does NOT probe for osqueryi failed this
        # check. That is the same defect the interpreter guard below was fixed for, in the
        # other direction -- a checker that cannot tell code from prose about code reports
        # on the prose. A commented-out invocation does not run, so dropping comment lines
        # costs nothing; a trailing comment after real code still leaves the code scanned.
        code = "\n".join(l for l in text.splitlines()
                          if not l.strip().startswith(("#", "--")))
        # bin/discover is the only thing that runs queries, and it is vendored; anything
        # here that shells out to osqueryi directly is a second runner with its own guard,
        # its own bound and its own bugs.
        if re.search(r"osqueryi[\"']?\s+(--|<|\$)", code):
            bad.append(f"{rel}: invokes osqueryi directly -- use the vendored bin/discover")
        # dist/collect.sh embeds bin/ and dist/ as base64, so real SQL never appears in it
        # as text. Plaintext here means someone pasted a query in beside the payload.
        if re.search(r"\bFROM\s+(apps|npm_packages|homebrew_packages|chrome_extensions|"
                     r"listening_ports|launchd|docker_images)\b", code):
            bad.append(f"{rel}: contains an osquery query in plaintext")
for b in sorted(set(bad)):
    print(f"FAIL: {b}")
if bad:
    print("       The only osquery implementation is vendor/osquery-ai-discovery/. "
          "Re-vendor with tools/vendor-queries.sh; do not write queries here.")
    sys.exit(1)
print("ok: no osquery implementation outside vendor/osquery-ai-discovery/")
ONE

# --- the shell this repo ships -----------------------------------------------------------
# dist/collect.sh is generated, which is exactly why it is syntax-checked: a template edit
# in tools/build-collector.py produces it unexamined, and bash reports a syntax error only
# when the Policy runs on a Mac.
for f in "$ROOT"/tools/vendor-queries.sh "$ROOT"/dist/collect.sh; do
  bash -n "$f" || { echo "FAIL: bash syntax in ${f#$ROOT/}"; fail=1; }
done

# --- the vendored tree is verbatim --------------------------------------------------------
# The ref stamp names a release; only this says the files still match it. A formatter
# reaching into vendor/ leaves the tag right and the bytes wrong, and tools/bundle.py is
# what BUILDS the deployable. Regenerate with tools/vendor-queries.sh.
if [ -f "$ROOT/vendor/osquery-ai-discovery/SHA256SUMS" ]; then
  if ( cd "$ROOT/vendor/osquery-ai-discovery" && shasum -a 256 --quiet --check SHA256SUMS >/dev/null 2>&1 ); then
    echo "vendor tree: ok, every file matches the manifest written when it was vendored"
  else
    echo "FAIL: a vendored file differs from the manifest:"
    # `|| true` because this file runs under `set -euo pipefail`: the failing shasum
    # propagates through the pipe, the subshell is a bare command in an else body, and
    # `set -e` would abort here -- taking the remediation line, `fail=1`, and every
    # remaining check in this file with it.
    ( cd "$ROOT/vendor/osquery-ai-discovery" && shasum -a 256 --check SHA256SUMS 2>&1 | grep -v ': OK$' | sed 's/^/      /' ) || true
    echo "      The tree must be verbatim. Restore it, or re-vendor to adopt the change."
    fail=1
  fi

  # AND THAT THE MANIFEST COVERS EVERY FILE. `shasum --check` reads the manifest, so a
  # file ADDED to the tree passes it by not being mentioned -- and the build packs bin/
  # and dist/ into dist/collect.sh, so an extra one there ships to every Mac.
  extra="$( cd "$ROOT/vendor/osquery-ai-discovery" && \
    comm -23 <(find . -type f ! -name VERSION ! -name SHA256SUMS | sort) \
             <(sed 's/^[0-9a-f]*  //' SHA256SUMS | sort) || true )"
  if [ -n "$extra" ]; then
    echo "FAIL: vendored file(s) the manifest does not list:"
    echo "$extra" | sed 's/^/      /'
    echo "      Re-vendor to adopt them, or delete them. bin/ and dist/ ship to every Mac."
    fail=1
  else
    echo "vendor tree: ok, the manifest lists every file present"
  fi
else
  echo "FAIL: vendor/osquery-ai-discovery/SHA256SUMS is missing; re-vendor to write it"
  fail=1
fi

# --- the vendored tree, and the deployable built around it -------------------------------
# Both can rot silently: a vendored tree edited by hand, and a dist/collect.sh built before
# the last vendor. Not conditional on vendor/ existing -- without it there is no discovery
# implementation in this repo at all, which is a failure and not a reason to skip.
[ -d "$ROOT/vendor/osquery-ai-discovery" ] || {
  echo "FAIL: no vendor/osquery-ai-discovery/ -- run tools/vendor-queries.sh <ref>"
  echo "lint: FAIL"; exit 1; }

# THE VENDORED TREE IS NOT WRITTEN TO, INCLUDING BY US. tools/vendor-queries.sh removes and
# rewrites vendor/ wholesale, so anything else that appears there is either a hand edit or a
# build artifact -- and one of each has now happened: build-collector.py imports the vendored
# bundler, Python dropped a __pycache__ beside it, and it was committed. A tracked file in a
# directory the vendor script deletes shows up as a deletion on every re-vendor.
if find "$ROOT/vendor" -name "__pycache__" -o -name "*.pyc" | grep -q .; then
  echo "FAIL: vendor/ carries a Python build artifact:"
  find "$ROOT/vendor" -name "__pycache__" -o -name "*.pyc" | sed "s|$ROOT/|      |"
  echo "      The build must not write into the vendored tree; see vendored_bundler()."
  fail=1
else
  echo "vendor tree: ok, no build artifacts written into it"
fi

python3 "$ROOT/tools/build-collector.py" --check || fail=1

python3 - "$ROOT" <<'VENDOR' || fail=1
import os, plistlib, re, subprocess, sys
root = sys.argv[1]
v = os.path.join(root, "vendor", "osquery-ai-discovery")

# The catalog is vendored FOR THE COLLECTOR and must never reach a Mac. The payload list is
# checked by build-collector.py; this checks the built artifact, which is what deploys.
built = os.path.join(root, "dist", "collect.sh")
if os.path.exists(built):
    text = open(built).read()

    # THE ARTHUR HALF IS INSIDE THE PAYLOAD NOW, so a guard that greps dist/collect.sh for
    # `arthur1.` finds nothing -- and a guard that finds nothing either fails for the wrong
    # reason or passes vacuously. Both are worse than the scan they replaced. The driver is
    # read back out of the built artifact instead, which is the version of these checks that
    # asserts on what a Mac actually runs.
    driver = subprocess.run([sys.executable, os.path.join(root, "tools", "build-collector.py"),
                             "--driver-of", built],
                            capture_output=True, text=True)
    if driver.returncode != 0:
        print(f"FAIL: cannot read the driver out of dist/collect.sh: "
              f"{driver.stderr.strip()[:200]}"); sys.exit(1)
    driver = driver.stdout

    # Everything that EXECUTES on a Mac: upstream's wrapper plus our driver, with the base64
    # body left out. Scanning the body would be scanning an alphabet -- it can spell anything.
    _mark = "AI_DISCOVERY_PAYLOAD_EOF"
    _head, _, _rest = text.partition(f"<<'{_mark}'\n")
    _, _, _tail = _rest.partition(f"\n{_mark}\n")
    shipped = _head + _tail + "\n" + driver

    # CODE, NOT THE PROSE ABOUT CODE. The guards below ask whether the collector still
    # WRITES `arthur1.` and `ERROR:oversize`, and the driver explains both at length in
    # comments -- so without stripping them, replacing the frame leaves the guard passing
    # on its own explanation.
    driver_code = "\n".join(l for l in driver.splitlines()
                            if not l.strip().startswith("#"))

    # BUILT BY THE VENDORED BUNDLER, NOT BY A SECOND COPY OF ONE. This repo carried its own
    # reproducible tar, base64 wrapping and extraction preamble until upstream shipped the
    # same thing at v0.6.0. Two implementations of one mechanism is the failure this repo is
    # organised around, and the local one is gone -- asserted, because it is exactly the kind
    # of thing that grows back the next time the bundler is inconvenient.
    if "GENERATED by tools/bundle.py from osquery-ai-discovery" not in text:
        print("FAIL: dist/collect.sh was not built by the vendored bundler. The extraction "
              "half is upstream's; see tools/build-collector.py."); sys.exit(1)
    bc = open(os.path.join(root, "tools", "build-collector.py")).read()
    for banned in ("gzip.compress", "b64encode"):
        if banned in bc:
            print(f"FAIL: tools/build-collector.py calls {banned} -- it is building its own "
                  f"payload again. The bundler is vendored; hand it a --driver."); sys.exit(1)
    # routes.yaml arrived with v0.3.0 as a second catalog file. The guard is a list of
    # names, so a new one is not covered until it is named -- which is the whole failure
    # mode: a catalog file reaching a Mac, invisible inside a base64 blob.
    for forbidden in ("agents.yaml", "routes.yaml", "catalog/"):
        if forbidden in text:
            print(f"FAIL: dist/collect.sh mentions {forbidden!r} -- the endpoint holds no "
                  f"catalog. See docs/architecture.md."); sys.exit(1)
    if text.count("AI_DISCOVERY_PAYLOAD_EOF") != 2:
        print("FAIL: dist/collect.sh has a nested payload marker -- it may be embedding a "
              "previous copy of itself"); sys.exit(1)

    # THE COLLECTOR CALLS A VENDORED PROGRAM, AND UPSTREAM MAY DROP A FLAG -- a bump would
    # then ship a collector whose only real work exits 1 on every Mac. Every flag the
    # collector passes must still be one discover accepts.
    disc = open(os.path.join(v, "bin", "discover")).read()
    accepted = set(re.findall(r"^\s*(--[a-z-]+)\)", disc, re.M))
    accepted |= set(re.findall(r"\|(--[a-z-]+)\)", disc))
    # The invocation only -- to its last continued line. A fixed-size window instead read the
    # comments that follow, and the prose there names --framed to explain why it is gone.
    cmd = []
    for line in driver[driver.index('"$AI_DISCOVERY_ROOT/bin/discover"'):].splitlines():
        cmd.append(line)
        if not line.rstrip().endswith("\\"):
            break
    called = set(re.findall(r"--[a-z-]+", "\n".join(cmd)))
    gone = sorted(called - accepted)
    if gone:
        print(f"FAIL: dist/collect.sh passes {gone} to bin/discover, which no longer accepts "
              f"it. The vendored runner changed; see tools/build-collector.py."); sys.exit(1)
    print(f"collector: ok, calls discover with {sorted(called)}, all still accepted")

    # Framing is this tree's job and this is the only implementation of it. Dropping the
    # step would leave the attribute empty, which reads as a Mac with nothing on it.
    if "arthur1." not in driver_code:
        print("FAIL: dist/collect.sh writes no arthur1. value -- bin/discover no longer "
              "frames, so this repo must. See tools/build-collector.py."); sys.exit(1)
    # THE COLD-DOCKER PING BOUND. A scheduled scan is always the cold case, and too short a
    # ping reports `unhealthy:000` against a healthy daemon -- silent, exit 0, and it looks
    # fine to anyone checking by hand, because checking warms the daemon. Asserted because
    # reverting to the default would be invisible again.
    m = re.search(r'DOCKER_PING_TIMEOUT="\$\{DOCKER_PING_TIMEOUT:-([0-9]+)\}"', driver)
    if not m:
        print("FAIL: dist/collect.sh does not set DOCKER_PING_TIMEOUT -- container-scan's "
              "default times out on a cold Docker Desktop, so a scheduled scan reports "
              "unhealthy:000 against a healthy daemon. See tools/build-collector.py."); sys.exit(1)
    ours = int(m.group(1))
    if ours < 10:
        print(f"FAIL: dist/collect.sh sets DOCKER_PING_TIMEOUT={ours}s. A cold Docker "
              f"Desktop was measured at 1.69s and a wedged engine answers 500 at about 10s; "
              f"below 10 the branch cannot tell those apart from a dead socket."); sys.exit(1)
    # AND IT MUST STAY AN OVERRIDE. Upstream moved this default 1 -> 8 in v0.4.0 and could
    # move it past ours, at which point the export lowers the bound rather than raising it.
    vend = open(os.path.join(v, "bin", "container-scan")).read()
    vm = re.search(r'TIMEOUT="\$\{DOCKER_PING_TIMEOUT:-([0-9]+)\}"', vend)
    if vm and ours < int(vm.group(1)):
        print(f"FAIL: dist/collect.sh sets DOCKER_PING_TIMEOUT={ours}s, BELOW the vendored "
              f"container-scan's own default of {vm.group(1)}s. The export now lowers the "
              f"bound instead of raising it. See tools/build-collector.py."); sys.exit(1)
    print(f"ping bound: ok, collector {ours}s >= vendored default "
          f"{vm.group(1) if vm else '?'}s and >= the 10s wedged-engine floor")

    # NO INTERPRETER ON THE ENDPOINT. The framing step was `python3 -c` and python3 is not
    # part of macOS -- /usr/bin/python3 is a shim for the active developer directory, so a Mac
    # without Command Line Tools ran the collector, wrote nothing, and reported `no-cache`:
    # the same value a Mac with no AI tools reports. The fleet's largest blind spot looked
    # like a clean result. gzip, base64 and plutil are all base macOS, so the dependency is
    # gone; this keeps it gone, because reaching for an interpreter is the obvious way to
    # write the next feature here and the failure it reintroduces is silent.
    interp = re.search(r"(?:^|[|;&(]\s*)(python3?|/usr/bin/python3|ruby|perl|osascript)\b[^\n]*",
                       shipped, re.M)
    if interp:
        print(f"FAIL: dist/collect.sh invokes an interpreter ({interp.group(1)}). The endpoint "
              f"runs on base macOS only -- python3 needs Command Line Tools, whose absence is "
              f"silent. Use gzip/base64/plutil. See tools/build-collector.py."); sys.exit(1)
    print("collector: ok, no interpreter in the collector's own code")

    # WHAT THE PAYLOAD NEEDS IS NOT WHAT THE WRAPPER NEEDS, AND THE DOCS MUST SAY SO. The
    # guard above checks this repo's code. It passed while bin/discover called python3 in
    # seven places and container-scan in three -- all of them shipped inside the very file
    # being checked -- and a "needs only osquery" claim went out on the strength of it. On a
    # Mac without Command Line Tools /usr/bin/python3 is a dead shim, so that claim sent an
    # operator looking anywhere but at the cause. Derive the prerequisite from the payload
    # instead of restating it, and fail when the runbook and the bytes disagree.
    # INVOCATIONS, NOT MENTIONS. Counting any occurrence of the word counts COMMENTS, so a
    # payload whose comments discuss python3 reads as one that requires it. A check that
    # cannot tell code from prose about code reports the wrong state confidently.
    def _interp(path):
        hits = []
        for line in open(path):
            s = line.strip()
            if s.startswith("#") or s.startswith("--") or not s:
                continue            # shell comment, SQL comment, blank
            if re.search(r"(?:^|[|;&(`]|\$\(|\s)(python3?|jq|perl|ruby|node|deno)\b", line):
                hits.append(s[:60])
        return hits
    needs = [h for f in ("bin/discover", "bin/container-scan")
             for h in _interp(os.path.join(v, f))]
    runbook = open(os.path.join(root, "docs", "mdm", "jamf-pro.md")).read()
    claims_none = "Nothing else — no interpreter" in runbook
    lists_python = "| python3 3.7+ |" in runbook
    if needs and (claims_none or not lists_python):
        print("FAIL: the vendored payload invokes python3, but docs/mdm/jamf-pro.md does "
              "not list it as a prerequisite. The endpoint needs what the payload needs, not "
              "what the wrapper needs."); sys.exit(1)
    if not needs and lists_python:
        print("FAIL: docs/mdm/jamf-pro.md lists python3 as a prerequisite, but nothing in "
              "the payload invokes it any more. Drop the row."); sys.exit(1)
    print(f"prereqs: ok, payload {'needs' if needs else 'does not need'} python3 and the "
          f"runbook agrees")

    # An oversize payload must write a REASON, not nothing and not a truncated value. The
    # cap is a property of the reporting channel, so it is this repo's to enforce.
    if "ERROR:oversize" not in driver_code:
        print("FAIL: dist/collect.sh does not report ERROR:oversize -- an attribute that is "
              "absent, empty or stale reads as a Mac with no AI tools on it."); sys.exit(1)

# A vendored ref pinned to a bare commit is legitimate but provisional, and saying so out
# loud is the only thing that stops it becoming permanent by inattention.
version = os.path.join(v, "VERSION")
if not os.path.exists(version):
    print("FAIL: vendor/osquery-ai-discovery/VERSION missing. Run tools/vendor-queries.sh.")
    sys.exit(1)
info = dict(l.split(None, 1) for l in open(version).read().splitlines() if l.strip())
print(f"vendor: ok, ref {info.get('ref','?').strip()} ({info.get('kind','?').strip()})")
if "PROVISIONAL" in info.get("kind", ""):
    print("        note: pinned to a commit, not a tag. Pin a tag once one carries this.")

for f in ("deploy/com.arthur.ai-discovery.plist",):
    path = os.path.join(root, f)
    with open(path, "rb") as fh:
        d = plistlib.load(fh)
    argv = d["ProgramArguments"]
    if not argv[0].endswith("collect.sh"):
        print(f"FAIL: {f} does not run the built collector: {argv}"); sys.exit(1)
    if not d.get("RunAtLoad"):
        print(f"FAIL: {f} RunAtLoad is false; a fresh Mac reports nothing until the first "
              f"interval elapses"); sys.exit(1)
    print(f"plist: ok, {os.path.basename(f)} -> {argv[0].split('/')[-1]}")
VENDOR

[ "$fail" -eq 0 ] && echo "lint: PASS" || echo "lint: FAIL"
exit "$fail"
