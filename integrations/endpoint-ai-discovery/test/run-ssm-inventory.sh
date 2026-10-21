#!/usr/bin/env bash
# Run deploy/report-ssm-inventory.sh against a fake IMDS and assert on exactly the custom
# inventory file it writes. No instance, no SSM Agent, no osquery; the fake and the checks
# need python3, the reporter does not.
#
#     test/run-ssm-inventory.sh
#
# THE COLLECTOR IS A STUB HERE, because the question is what the REPORTER does with each thing
# a collector can leave behind -- a fresh scan, a kept one, none -- and a stub produces each on
# demand. test/run-collector.sh runs the real collector; test/run-systemd.sh runs the two
# together under systemd.
#
# ASSERTS ON THE VALUES THE PARTS MAKE, not on the file's shape alone: a part dropped, a part
# cut short or a hash taken before a value was cleaned each leaves valid JSON behind, and each
# reads as something it is not.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="$ROOT/deploy/report-ssm-inventory.sh"
INSTANCE_ID="i-0123456789abcdef0"
fails=0
bad()   { printf 'FAIL: %s\n' "$1"; fails=$((fails + 1)); }
# Each case opens with `case_`; its closing `ok` prints only if nothing in it failed.
case_() { echo "$1"; mark=$fails; }
ok()    { [ "$fails" -eq "$mark" ] && printf 'ok: %s\n' "$1"; }

python3 -c "import http.server" 2>/dev/null || {
  echo "FAIL: this test needs python3 for the fake IMDS (the reporter does not)"
  exit 1; }

work="$(mktemp -d "${TMPDIR:-/tmp}/report-test.XXXXXX")" || exit 1
servers=""
cleanup() { for p in $servers; do kill "$p" 2>/dev/null; done; rm -rf "$work"; }
trap cleanup EXIT HUP INT TERM

leaked() { ls -d "${TMPDIR:-/tmp}"/arthur-report.* 2>/dev/null | sort; }
before="$(leaked)"

# start_fake MODE: a fresh fake IMDS; sets $imds and $pid.
start_fake() {
  rm -f "$work/port"
  python3 "$ROOT/test/fake-imds.py" "$work/port" "$1" &
  pid=$!; servers="$servers $pid"
  for _ in $(seq 50); do [ -s "$work/port" ] && break; sleep 0.1; done
  [ -s "$work/port" ] || { echo "FAIL: the fake IMDS did not start"; exit 1; }
  imds="http://127.0.0.1:$(cat "$work/port")"
}

# The stub stands in for collect-linux.sh: the case lays out $out, the stub sets the exit
# status and the stderr the reporter sees.
stub() {
  printf '#!/bin/bash\n%s\nexit %s\n' "${2:+echo \"$2\" >&2}" "$1" > "$work/collect"
  chmod +x "$work/collect"
}
report() {
  ARTHUR_COLLECT="$work/collect" ARTHUR_OUT_DIR="$out" ARTHUR_IMDS_URL="$imds" \
    ARTHUR_SSM_DATA_DIR="$ssm" "$REPORT" > "$work/stdout" 2> "$work/stderr"
  rc=$?
}
file() { printf '%s' "$ssm/$INSTANCE_ID/inventory/custom/ArthurAIDiscovery.json"; }

# The file's two values, reassembled the way the ML Engine's client does, into
# $work/values/<key>; prints a problem and fails when the parts do not make a whole.
values() {
  rm -rf "$work/values"; mkdir -p "$work/values"
  python3 - "$(file)" "$work/values" <<'PY'
import hashlib, json, os, sys
doc = json.load(open(sys.argv[1]))
assert doc["SchemaVersion"] == "1.0", doc["SchemaVersion"]
assert doc["TypeName"] == "Custom:ArthurAIDiscovery", doc["TypeName"]
parts = {}
for e in doc["Content"]:
    assert set(e) == {"Key", "Part", "Parts", "Sha256", "Value"}, sorted(e)
    assert all(isinstance(v, str) for v in e.values()), "every value is a string"
    assert len(e["Value"]) <= 4096, f"{e['Key']} part {e['Part']}: {len(e['Value'])} chars"
    parts.setdefault(e["Key"], []).append(e)
assert sorted(parts) == ["inventory", "status"], sorted(parts)
for key, es in parts.items():
    count = {int(e["Parts"]) for e in es}
    digest = {e["Sha256"] for e in es}
    assert len(count) == 1 and len(digest) == 1, f"{key}: parts disagree"
    numbers = sorted(int(e["Part"]) for e in es)
    assert numbers == list(range(1, count.pop() + 1)), f"{key}: parts {numbers}"
    value = "".join(e["Value"] for e in sorted(es, key=lambda e: int(e["Part"])))
    assert hashlib.sha256(value.encode()).hexdigest() == digest.pop(), f"{key}: hash"
    with open(os.path.join(sys.argv[2], key), "w") as f:
        f.write(value)
    with open(os.path.join(sys.argv[2], key + ".parts"), "w") as f:
        f.write(str(len(es)))
PY
}
is() { cmp -s <(printf '%s' "$2") "$work/values/$1"; }
TS='[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z'

case_ "== a clean scan is written as the instance's custom inventory ============="
start_fake ok
ssm="$work/ssm.clean"; mkdir -p "$ssm"
out="$work/out.clean"; mkdir -p "$out"
printf 'arthur1.H4sIAAAA\n' > "$out/inventory.ea"
printf 'ok 2026-10-12T00:00:00Z rows=3 apps=ok\n' > "$out/status.txt"
stub 0; report
[ "$rc" -eq 0 ] || bad "a clean run exited $rc: $(head -c 300 "$work/stderr")"
[ -f "$(file)" ] || bad "nothing was written at $(file)"
values || bad "the file's parts do not make two values"
is inventory 'arthur1.H4sIAAAA' || bad "inventory is not the framed value, byte for byte"
is status 'ok 2026-10-12T00:00:00Z rows=3 apps=ok' || bad "status is not the status line"
mode="$(stat -c %a "$(file)" 2>/dev/null || stat -f %Lp "$(file)")"
[ "$mode" = 600 ] || bad "the inventory file is mode $mode, readable beyond root"
grep -q "wrote Custom:ArthurAIDiscovery for $INSTANCE_ID" "$work/stdout" \
  || bad "a clean run did not say what it wrote"
ok "inventory and status written exactly, mode 600, exit 0"

case_ "== a value at the budget is cut into 64 parts that make it again =========="
head -c 262144 /dev/zero | tr '\0' 'A' > "$work/at-cap"
{ cat "$work/at-cap"; printf '\n'; } > "$out/inventory.ea"
report
[ "$rc" -eq 0 ] || bad "a value at the budget exited $rc: $(head -c 200 "$work/stderr")"
values || bad "a value at the budget did not reassemble"
cmp -s "$work/at-cap" "$work/values/inventory" || bad "the 64 parts do not make the value"
[ "$(cat "$work/values/inventory.parts")" = 64 ] \
  || bad "262,144 characters made $(cat "$work/values/inventory.parts") parts, not 64"
ok "262,144 characters plus the file's newline: 64 parts of 4,096, reassembled byte for byte"

case_ "== the file is replaced, and nothing half-written is left beside it ======="
printf 'arthur1.SECOND\n' > "$out/inventory.ea"
report
values && is inventory 'arthur1.SECOND' || bad "the second run did not replace the first"
[ -z "$(ls -A "$(dirname "$(file)")" | grep -v '^ArthurAIDiscovery.json$')" ] \
  || bad "files beside the inventory: $(ls -A "$(dirname "$(file)")")"
ok "replaced in place by rename; the directory holds only ArthurAIDiscovery.json"

case_ "== a failed run serves the last good scan and dates the failure ========="
printf 'arthur1.KEPT\n' > "$out/inventory.ea"
printf 'ok 2026-10-01T00:00:00Z rows=5 apps=ok\n' > "$out/status.txt"
stub 1 "arthur: discover failed. Is osquery installed?"; report
[ "$rc" -ne 0 ] || bad "a failed run exited 0"
values || bad "a failed run's file did not reassemble"
is inventory 'arthur1.KEPT' || bad "the kept scan was not written"
grep -Eq "^ok 2026-10-01T00:00:00Z rows=5 apps=ok failed=$TS\$" "$work/values/status" \
  || bad "status does not carry the kept line plus failed=<UTC>: $(cat "$work/values/status")"
grep -q "discover failed" "$work/stderr" || bad "the collector's stderr did not reach the journal"
ok "kept scan written, status says failed=<UTC>, exit $rc"

case_ "== never collected, osquery absent: both values name the state ==========="
out="$work/out.none"; mkdir -p "$out"
stub 1 "discover: no osqueryi found (set OSQI)"; report
[ "$rc" -ne 0 ] || bad "an instance with no osquery exited 0"
values || bad "the file did not reassemble"
is inventory 'no-cache' || bad "inventory is not no-cache: $(cat "$work/values/inventory")"
grep -Eq "^no-cache failed=$TS osquery=absent\$" "$work/values/status" \
  || bad "status does not name the state: $(cat "$work/values/status")"
ok "inventory=no-cache, status=no-cache failed=<UTC> osquery=absent"

case_ "== a scan status without its value writes no-cache for both ============="
out="$work/out.halfway"; mkdir -p "$out"
printf 'ok 2026-10-12T00:00:00Z rows=3 apps=ok\n' > "$out/status.txt"
stub 0; report
values || bad "the file did not reassemble"
is inventory 'no-cache' || bad "inventory is not no-cache"
is status 'no-cache' || bad "status claims a scan the inventory does not carry: $(cat "$work/values/status")"
ok "status.txt without inventory.ea: both values no-cache"

case_ "== a quote, a backslash or a control character cannot break the file ======"
out="$work/out.odd"; mkdir -p "$out"
printf 'arthur1.H4sI\n' > "$out/inventory.ea"
printf 'ok 2026-10-12T00:00:00Z note="a\\b"\tx\n' > "$out/status.txt"
stub 0; report
values || bad "a status with a quote and a backslash did not make valid parts"
is status 'ok 2026-10-12T00:00:00Z note="a\b"x' \
  || bad "the status was not kept, less its tab: $(cat "$work/values/status")"
ok "quote and backslash escaped, tab dropped before hashing; the parts still make the value"

case_ "== no IMDS: named, and nothing written ===================================="
ssm="$work/ssm.noimds"; mkdir -p "$ssm"
out="$work/out.clean"
start_fake ok; kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null
report
[ "$rc" -ne 0 ] || bad "an unreachable IMDS exited 0"
grep -q "cannot get an IMDSv2 token" "$work/stderr" || bad "an unreachable IMDS was not named"
[ -z "$(ls -A "$ssm")" ] || bad "something was written without an instance id"
ok "unreachable IMDS named, exit $rc, nothing written"

case_ "== IMDS refuses a token, or answers with no instance id: named ==========="
start_fake token-refused; report
[ "$rc" -ne 0 ] && grep -q "HTTP 403" "$work/stderr" || bad "a refused token was not named: $(cat "$work/stderr")"
start_fake not-an-id; report
[ "$rc" -ne 0 ] && grep -q "did not return an instance id" "$work/stderr" \
  || bad "an answer that is not an instance id was used: $(cat "$work/stderr")"
[ -z "$(ls -A "$ssm")" ] || bad "something was written without a real instance id"
ok "403 and a non-id answer both named, nothing written"

case_ "== no SSM Agent: named, and nothing written =============================="
start_fake ok
ssm="$work/ssm.absent"
report
[ "$rc" -ne 0 ] || bad "an instance with no SSM Agent exited 0"
grep -q "no SSM Agent data directory" "$work/stderr" || bad "the missing agent was not named"
[ ! -e "$ssm" ] || bad "the reporter created the agent's directory itself"
ok "missing agent directory named, exit $rc"

case_ "== a fleet-wide proxy does not carry the IMDS request ===================="
ssm="$work/ssm.proxy"; mkdir -p "$ssm"
http_proxy=http://127.0.0.1:9 report
[ "$rc" -eq 0 ] || bad "with http_proxy set, IMDS went to the proxy: $(head -c 200 "$work/stderr")"
[ -f "$(file)" ] || bad "nothing was written with http_proxy set"
ok "http_proxy set to a dead proxy: IMDS reached directly, exit 0"

case_ "== a signal ends the run instead of misreporting it ======================"
ssm="$work/ssm.term"; mkdir -p "$ssm"
printf '#!/bin/bash\nsleep 30\n' > "$work/collect"; chmod +x "$work/collect"
ARTHUR_COLLECT="$work/collect" ARTHUR_OUT_DIR="$out" ARTHUR_IMDS_URL="$imds" \
  ARTHUR_SSM_DATA_DIR="$ssm" "$REPORT" > "$work/stdout" 2> "$work/stderr" &
rpid=$!
for _ in $(seq 50); do pgrep -P "$rpid" >/dev/null && break; sleep 0.1; done
# What systemd does on stop or timeout: TERM to every process in the unit.
pkill -TERM -P "$rpid"; kill -TERM "$rpid"; wait "$rpid"; rc=$?
[ "$rc" -ne 0 ] || bad "a TERMed run exited 0"
[ -z "$(ls -A "$ssm")" ] || bad "a TERMed run wrote something"
ok "TERM during collection: exit $rc, nothing written"

ssm="$work/ssm.tmpdir"; mkdir -p "$ssm"
case_ "== the unit's TMPDIR loses empty osquery-<n> directories, and nothing else ===="
start_fake ok
out="$work/out.tmpdir"; mkdir -p "$out/tmp/osquery-11111" "$out/tmp/osquery-22222" "$out/tmp/other"
: > "$out/tmp/osquery-22222/kept"
mkdir -p "$work/shared/osquery-33333"
printf 'arthur1.H4sIAAAA\n' > "$out/inventory.ea"
printf 'ok 2026-10-12T00:00:00Z rows=3 apps=ok\n' > "$out/status.txt"
stub 0
for t in "$out/tmp" "$work/shared"; do
  TMPDIR="$t" ARTHUR_COLLECT="$work/collect" ARTHUR_OUT_DIR="$out" ARTHUR_IMDS_URL="$imds" ARTHUR_SSM_DATA_DIR="$ssm" \
    "$REPORT" > "$work/stdout" 2> "$work/stderr" || bad "a clean run with TMPDIR=$t exited $?"
done
[ ! -e "$out/tmp/osquery-11111" ] || bad "an empty osquery-<n> directory was left in the unit's TMPDIR"
[ -f "$out/tmp/osquery-22222/kept" ] && [ -d "$out/tmp/other" ] \
  || bad "the cleanup removed more than empty osquery-<n> directories"
[ -d "$work/shared/osquery-33333" ] \
  || bad "the cleanup reached a TMPDIR outside ARTHUR_OUT_DIR, where an osqueryi may be running"
ok "cleared under ARTHUR_OUT_DIR; a non-empty one, another name and a shared TMPDIR kept"

case_ "== the reporter leaves no working directory behind ======================="
[ "$before" = "$(leaked)" ] || bad "the reporter leaked a working directory"
ok "no arthur-report.* left behind"

[ "$fails" -eq 0 ] && echo "ssm-inventory: PASS" || echo "ssm-inventory: FAIL ($fails)"
[ "$fails" -eq 0 ]
