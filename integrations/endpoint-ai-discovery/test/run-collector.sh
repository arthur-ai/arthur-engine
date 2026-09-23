#!/usr/bin/env bash
# Run dist/collect.sh and assert on what it produced. Needs osquery and a Mac; about 15s.
#
#     test/run-collector.sh              # a scratch output directory, cleaned up
#     sudo test/run-collector.sh         # what Jamf does -- more rows, same assertions
#
# WHY THIS EXISTS BESIDE test/lint.sh. lint is static: it reads dist/collect.sh and proves
# the framing step is present, that the payload carries the vendored tree and that every
# flag the collector passes is still one bin/discover accepts. It cannot prove the file
# RUNS. Nothing did. The extraction preamble -- mktemp, `base64 -D` with a `-d` fallback,
# tar, chmod -- is the only executable code this repo owns, and until this script it was
# exercised only when a human happened to run the collector by hand. That is the exact
# shape of the empty-bash-array defect in CLAUDE.md's table: bash 3.2 only, so it worked on
# the machine it was written on and died on every Mac.
#
# ASSERTS ON COUNTS AND IDENTIFIERS, NEVER ON "DID IT PARSE". Every defect this project has
# found was plausible output with wrong values and exit code zero.
#
# ROOT IS NOT REQUIRED, and the assertions are chosen so it does not change the answer. A
# Policy runs this as root and sees more rows; the properties checked below -- the framed
# value is this scan, the two attribute files agree on the branch list, a failed run keeps
# the last good one -- hold either way.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COLLECT="$ROOT/dist/collect.sh"
fail=0
note() { printf 'ok: %s\n' "$1"; }
bad()  { printf 'FAIL: %s\n' "$1"; fail=1; }

[ -x "$COLLECT" ] || { echo "FAIL: no dist/collect.sh -- run tools/build-collector.py"; exit 1; }

# NO PREREQUISITE PROBE HERE, DELIBERATELY. The obvious opening is a loop over the four
# absolute paths the vendored runner searches -- and that is a copy of an upstream thing,
# which this repo has already watched drift once. The collector finds its own interpreter
# of queries and says so when it cannot; a missing prerequisite is diagnosed below from
# that message, by the code that owns the search rather than by a second copy of it.

# THE TEST NEEDS python3; THE COLLECTOR MUST NOT, and that asymmetry is the point. On a Mac
# without Command Line Tools /usr/bin/python3 is a stub that prints an install prompt and
# exits 1 -- which is why the endpoint has no interpreter in it at all. This script runs on a
# build machine, so it may use one; checked up front so a missing interpreter fails here
# saying that, rather than halfway through an assertion block.
python3 -c "import json" 2>/dev/null || {
  echo "FAIL: this test needs a working python3 (the collector does not, deliberately)."
  echo "      /usr/bin/python3 is a stub without Command Line Tools: xcode-select --install"
  exit 1; }

[ "$(uname -s)" = Darwin ] || { echo "FAIL: this runs the macOS collector; $(uname -s) is not it."; exit 1; }

work="$(mktemp -d "${TMPDIR:-/var/tmp}/collector-test.XXXXXX")" || exit 1
trap 'rm -rf "$work"' EXIT HUP INT TERM
out="$work/arthur"

# A LEAKED WORK DIRECTORY IS A DISK THAT FILLS ON A SCHEDULE. collect.sh extracts its
# payload to a private temp directory and removes it from a trap. `exec`ing the runner
# there would replace the shell and skip the trap, which on an Ongoing schedule leaves one
# copy of the payload behind per run and shows up months later as a full volume. Snapshot
# rather than assert-none: another process's run is not this test's business.
leaked() { ls -d "${TMPDIR:-/var/tmp}"/arthur-collect.* /var/tmp/arthur-collect.* 2>/dev/null | sort -u; }
before="$(leaked)"

echo "== a clean run =========================================================="
ARTHUR_OUT_DIR="$out" "$COLLECT" > "$work/stdout" 2> "$work/stderr"
status=$?
sed 's/^/    /' "$work/stderr"
if [ "$status" -ne 0 ]; then
  # A MISSING PREREQUISITE IS NOT A DEFECT, and the collector already says which it is --
  # the vendored runner prints "no osqueryi found" and the collector asks whether osquery is
  # installed. Read the diagnosis off that rather than probing for the binary here, where a
  # second copy of the search path would drift from the one that matters.
  if grep -q "no osqueryi found" "$work/stderr"; then
    echo "FAIL: osquery is not installed on this machine. That is a prerequisite, not a"
    echo "      defect in the collector -- install osquery, or set OSQI, and run again."
  else
    bad "collect.sh exited $status on a healthy Mac"
  fi
  sed 's/^/    /' "$work/stdout"
  echo "collector: FAIL"; exit 1
fi
note "collect.sh exited 0"

for f in inventory.json inventory.ea status.txt; do
  [ -s "$out/$f" ] || bad "$f is missing or empty"
done
[ "$fail" -eq 0 ] || { echo "collector: FAIL"; exit 1; }
note "wrote inventory.json, inventory.ea and status.txt"

# ONE LINE, because the Extension Attribute reader is `cat` and Jamf wraps the output in
# <result>. base64 wraps at different widths across implementations and versions, and a
# wrapped value carries newlines into the attribute.
lines="$(wc -l < "$out/inventory.ea" | tr -d ' ')"
[ "$lines" = 1 ] || bad "inventory.ea is $lines lines; the attribute must be one"

# 644, or the EA script cannot read the value the Policy wrote as root.
mode="$(stat -f '%OLp' "$out/inventory.ea")"
[ "$mode" = 644 ] || bad "inventory.ea is mode $mode, not 644 -- the EA runs as a user"

case "$(head -c 8 "$out/inventory.ea")" in
  arthur1.) note "inventory.ea carries the arthur1. frame, one line, mode 644" ;;
  *) bad "inventory.ea does not start with arthur1." ;;
esac

# THE FRAMED VALUE MUST BE THIS SCAN, AND THAT IS THIS REPO'S OWN DEFECT. discover's exit
# status used to be discarded, so a run that collected nothing left the previous
# inventory.json in place and the framing step re-framed it into a fresh-looking value and
# exited 0. A Mac that had lost osquery reported `ok` with a green policy, having collected
# nothing. Round-tripping the attribute back to the payload is what makes that visible: it
# proves the value was built from the bytes sitting next to it, not from a previous run.
tail -c +9 "$out/inventory.ea" > "$work/frame.b64"
if base64 -D -i "$work/frame.b64" -o "$work/frame.gz" 2>/dev/null \
   || base64 -d "$work/frame.b64" > "$work/frame.gz" 2>/dev/null; then
  if gzip -dc "$work/frame.gz" > "$work/frame.json" 2>/dev/null; then
    cmp -s "$work/frame.json" "$out/inventory.json" \
      && note "inventory.ea decodes byte-for-byte to inventory.json" \
      || bad "inventory.ea decodes to something other than inventory.json -- the attribute is not this scan"
  else
    bad "inventory.ea is not gzip after base64 -- the frame is corrupt"
  fi
else
  bad "inventory.ea is not base64 after the arthur1. prefix"
fi

# UNDER THE CAP, AND THE CAP IS READ OFF THE COLLECTOR so the two cannot drift apart. The
# budget is this repo's, not Jamf's -- what it buys is that our loud failure fires before
# Jamf's unobserved one.
# READ OUT OF THE PAYLOAD, because that is where the Arthur half lives now. `sed` over
# dist/collect.sh used to find this line; the driver is inside the bundle, so the artifact's
# text no longer carries it and the old form silently found nothing.
cap="$("$ROOT/tools/build-collector.py" --driver-of "$COLLECT" \
        | sed -n 's/^CAP=\([0-9]*\)$/\1/p' | head -1)"
[ -n "$cap" ] || bad "dist/collect.sh no longer sets CAP -- the size budget is unguarded"
# MEASURED THE WAY THE COLLECTOR MEASURES IT: the file carries the framed value plus one
# trailing newline, and the cap is judged on the value. The one-byte difference is why the
# number below matches what collect.sh printed rather than the size on disk.
bytes="$(( $(wc -c < "$out/inventory.ea" | tr -d ' ') - 1 ))"
raw="$(wc -c < "$out/inventory.json" | tr -d ' ')"
if [ -n "$cap" ] && [ "$bytes" -ge "$cap" ]; then
  bad "framed value is $bytes bytes against a $cap cap -- this Mac would report ERROR:oversize"
else
  note "framed $raw bytes of JSON into $bytes ($(( bytes * 100 / ${cap:-262144} ))% of cap)"
fi

echo "== the payload, and what the two attribute files agree on ================"
python3 - "$out/inventory.json" "$out/status.txt" <<'PY' || fail=1
import json, re, sys, time
inv, status_path = sys.argv[1], sys.argv[2]
rows = json.load(open(inv))
status = open(status_path).read()
bad = []

# Not "is it valid JSON". A composed artifact that dies on its first table returns a valid,
# empty, entirely plausible array.
if not rows:
    bad.append("the payload has no rows at all -- a clean Mac and a failed scan look alike")

COLS = {"kind", "id", "ver", "loc", "extra", "perms"}
off = [r for r in rows if set(r) != COLS]
if off:
    bad.append(f"{len(off)} rows violate the six-column contract: {off[0]}")

# ONE STATUS LINE, and its vocabulary is what a Smart Group matches on.
if status.count("\n") != 1:
    bad.append(f"status.txt must be exactly one line, got {status.count(chr(10))}")
first, stamp, rest = status.split(maxsplit=2)
if first not in ("ok", "degraded"):
    bad.append(f"status starts with {first!r}, want ok or degraded")
if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", stamp):
    bad.append(f"status timestamp is not ISO-8601 UTC: {stamp!r}")
tokens = {k: v for k, v in (p.split("=", 1) for p in rest.split() if "=" in p)}
for k, v in tokens.items():
    if k == "rows":
        continue
    if not (v in ("ok", "absent", "error") or v.startswith(("unhealthy:", "timeout:"))):
        bad.append(f"unknown outcome {v!r} for branch {k}")

# THE TWO ATTRIBUTE FILES MUST DESCRIBE THE SAME SCAN. They are written by different steps
# and read by different Extension Attributes, so a branch that reports in one and not the
# other is a Mac whose Smart Group and whose payload disagree about what ran. Derived from
# each other rather than from a hardcoded branch list, which would only trail the real one:
# the portable branches were split out of their macOS neighbours upstream and a pinned list
# would have kept passing while saying less.
scans = {r["id"]: r for r in rows if r["kind"] == "scan"}
branches = set(tokens) - {"rows"}
if set(scans) != branches:
    bad.append(f"status names {sorted(branches)} but the payload carries markers for "
               f"{sorted(scans)}")

# A DATED MARKER IS HOW A READER TELLS AN OLD VALUE FROM A NEW ONE. The file's mtime cannot
# be used -- a redeploy resets it without changing the truth -- so freshness is a property
# of the payload, and this is the assertion that a kept-but-stale scan cannot pass.
now = time.time()
for name, r in scans.items():
    if not str(r["ver"]).isdigit() or not (0 < now - int(r["ver"]) < 3600):
        bad.append(f"branch {name} is dated {r['ver']!r}, which is not a timestamp from this run")

# The endpoint enumerates and matches nothing, so the catalog must not be in the payload --
# and it must not be reachable through it either.
blob = json.dumps(rows)
for leak in ("agents.yaml", "routes.yaml"):
    if leak in blob:
        bad.append(f"the payload mentions {leak} -- the endpoint holds no catalog")

for b in bad:
    print(f"FAIL: {b}")
if bad:
    sys.exit(1)
print(f"ok: {len(rows)} rows, {len(scans)} branches, status {first}, "
      f"containers={tokens.get('containers', '?')}")
PY

echo "== a failed scan must keep the last good one ============================="
# THIS REPO SHIPPED THE OPPOSITE, TWICE OVER. First a failed run republished the previous
# payload as if it were fresh; the fix is not to delete the good scan either, because on an
# Ongoing schedule a transient failure is ordinary and reporting a well-equipped Mac as
# empty is the same wrong answer in the other direction. What must happen: keep the last
# successful value, serve it, and fail the POLICY so Jamf's log says the latest attempt did
# not run.
#
# DISCOVER IS BROKEN BY TAKING ITS ARTIFACT AWAY, not by hiding osqueryi -- the vendored
# runner searches four absolute paths, so a test cannot unstall that from the outside. The
# collector branch under test is "discover exited non-zero", and DISCOVER_BASE reaches it
# by the same door.
before_phase="$fail"
cp "$out/inventory.ea" "$work/ea.before"
cp "$out/status.txt" "$work/status.before"
DISCOVER_BASE="$work/no-such-artifact.sql" ARTHUR_OUT_DIR="$out" "$COLLECT" \
  > "$work/stdout2" 2> "$work/stderr2"
status=$?
sed 's/^/    /' "$work/stderr2"
[ "$status" -ne 0 ] || bad "a scan that could not run exited 0 -- the Policy would show green"
cmp -s "$work/ea.before" "$out/inventory.ea" \
  || bad "a failed run rewrote inventory.ea -- the last good scan was lost or re-dated"
cmp -s "$work/status.before" "$out/status.txt" \
  || bad "a failed run rewrote status.txt"
grep -q "keeping the last successful scan" "$work/stderr2" \
  || bad "a failed run did not say it was serving an older value"
[ "$fail" -eq "$before_phase" ] && note "failed scan: exit $status, both attribute values untouched"

echo "== with nothing to fall back on, no value at all ========================="
# An attribute that is absent, empty or stale is indistinguishable from a Mac with no AI
# tools on it. With no previous scan there is nothing honest to serve, so the collector must
# leave NO file behind claiming to be a result: both attributes then report `no-cache`,
# which is true and is what the "not reporting" Smart Group finds.
fresh="$work/fresh"
DISCOVER_BASE="$work/no-such-artifact.sql" ARTHUR_OUT_DIR="$fresh" "$COLLECT" \
  > /dev/null 2> "$work/stderr3"
status=$?
sed 's/^/    /' "$work/stderr3"
[ "$status" -ne 0 ] || bad "a first-ever scan that could not run exited 0"
for f in inventory.json inventory.ea status.txt; do
  [ -e "$fresh/$f" ] && bad "$f was left behind with no successful scan to back it"
done
note "no previous scan: exit $status, no partial attribute value written"

echo "== the payload directory is not left on disk ============================="
after="$(leaked)"
if [ "$before" = "$after" ]; then
  note "no arthur-collect.* work directory left behind by three runs"
else
  bad "the extraction directory leaked: $(echo "$after" | comm -13 <(echo "$before") - | tr '\n' ' ')"
fi

[ "$fail" -eq 0 ] && echo "collector: PASS" || echo "collector: FAIL"
exit "$fail"
