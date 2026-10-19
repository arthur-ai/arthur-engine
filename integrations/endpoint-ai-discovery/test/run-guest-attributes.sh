#!/usr/bin/env bash
# Run deploy/report-guest-attributes.sh against a fake metadata server and assert on exactly
# what it publishes. No VM, no osquery; the fake needs python3, the reporter does not.
#
#     test/run-guest-attributes.sh
#
# THE COLLECTOR IS A STUB HERE, because the question is what the REPORTER does with each thing
# a collector can leave behind -- a fresh scan, a kept one, none -- and a stub produces each on
# demand. test/run-collector.sh runs the real collector; test/run-systemd.sh runs the two
# together under systemd.
#
# ASSERTS ON BYTES. The failure this guards against is a key that is empty, stale or one byte
# too long, each of which reads as something it is not.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT="$ROOT/deploy/report-guest-attributes.sh"
fails=0
bad()   { printf 'FAIL: %s\n' "$1"; fails=$((fails + 1)); }
# Each case opens with `case_`; its closing `ok` prints only if nothing in it failed.
case_() { echo "$1"; mark=$fails; }
ok()    { [ "$fails" -eq "$mark" ] && printf 'ok: %s\n' "$1"; }

python3 -c "import http.server" 2>/dev/null || {
  echo "FAIL: this test needs python3 for the fake metadata server (the reporter does not)"
  exit 1; }

work="$(mktemp -d "${TMPDIR:-/tmp}/report-test.XXXXXX")" || exit 1
servers=""
cleanup() { for p in $servers; do kill "$p" 2>/dev/null; done; rm -rf "$work"; }
trap cleanup EXIT HUP INT TERM

leaked() { ls -d "${TMPDIR:-/tmp}"/arthur-report.* 2>/dev/null | sort; }
before="$(leaked)"

# start_fake MODE: a fresh fake and an empty store; sets $store, $url and $pid.
start_fake() {
  store="$work/store.$1.$RANDOM"; mkdir -p "$store"; rm -f "$work/port"
  python3 "$ROOT/test/fake-metadata-server.py" "$store" "$work/port" "$1" &
  pid=$!; servers="$servers $pid"
  for _ in $(seq 50); do [ -s "$work/port" ] && break; sleep 0.1; done
  [ -s "$work/port" ] || { echo "FAIL: the fake metadata server did not start"; exit 1; }
  url="http://127.0.0.1:$(cat "$work/port")/computeMetadata/v1/instance/guest-attributes/arthur"
}

# The stub stands in for collect-linux.sh: the case lays out $out, the stub sets the exit
# status and the stderr the reporter sees.
stub() {
  printf '#!/bin/bash\n%s\nexit %s\n' "${2:+echo \"$2\" >&2}" "$1" > "$work/collect"
  chmod +x "$work/collect"
}
report() {
  ARTHUR_COLLECT="$work/collect" ARTHUR_OUT_DIR="$out" ARTHUR_GUEST_ATTRIBUTES_URL="$url" \
    "$REPORT" > "$work/stdout" 2> "$work/stderr"
  rc=$?
}
is() { cmp -s <(printf '%s' "$2") "$store/arthur/$1"; }
TS='[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z'

case_ "== a clean scan is published as framed, without the trailing newline ======"
start_fake ok
out="$work/out.clean"; mkdir -p "$out"
printf 'arthur1.H4sIAAAA\n' > "$out/inventory.ea"
printf 'ok 2026-10-12T00:00:00Z rows=3 apps=ok\n' > "$out/status.txt"
stub 0; report
[ "$rc" -eq 0 ] || bad "a clean run exited $rc"
is inventory 'arthur1.H4sIAAAA' || bad "arthur/inventory is not the framed value, byte for byte"
is status 'ok 2026-10-12T00:00:00Z rows=3 apps=ok' || bad "arthur/status is not the status line"
grep -q "published arthur/inventory" "$work/stdout" || bad "a clean run did not say what it published"
ok "inventory and status published exactly, exit 0"

case_ "== a value of exactly the cap is accepted =================================="
# The collector's CAP judges the value; the file carries it plus one newline. Sent with the
# newline, a value at the cap would be 262,145 bytes and refused.
head -c 262144 /dev/zero | tr '\0' 'A' > "$work/at-cap"
{ cat "$work/at-cap"; printf '\n'; } > "$out/inventory.ea"
report
[ "$rc" -eq 0 ] || bad "a value at the cap exited $rc: $(head -c 200 "$work/stderr")"
cmp -s "$work/at-cap" "$store/arthur/inventory" || bad "a value at the cap was not published byte for byte"
ok "262,144 bytes on disk plus a newline published as 262,144 bytes"

case_ "== a refused inventory keeps the previous value and says so =============="
{ cat "$work/at-cap"; printf 'A\n'; } > "$out/inventory.ea"
report
[ "$rc" -ne 0 ] || bad "a refused inventory exited 0 -- the unit would look healthy"
cmp -s "$work/at-cap" "$store/arthur/inventory" || bad "the previous inventory value did not survive the refusal"
grep -Eq 'inventory=refused:400$' "$store/arthur/status" \
  || bad "arthur/status does not say the inventory was refused: $(cat "$store/arthur/status")"
grep -q "Maximum value of 262144 bytes allowed" "$work/stderr" || bad "the 400's reason was not logged"
ok "refused with 400: exit $rc, previous value kept, status says inventory=refused:400"

case_ "== a failed run serves the last good scan and dates the failure ========="
start_fake ok
printf 'arthur1.KEPT\n' > "$out/inventory.ea"
printf 'ok 2026-10-01T00:00:00Z rows=5 apps=ok\n' > "$out/status.txt"
stub 1 "arthur: discover failed. Is osquery installed?"; report
[ "$rc" -ne 0 ] || bad "a failed run exited 0"
is inventory 'arthur1.KEPT' || bad "the kept scan was not published"
grep -Eq "^ok 2026-10-01T00:00:00Z rows=5 apps=ok failed=$TS\$" "$store/arthur/status" \
  || bad "arthur/status does not carry the kept line plus failed=<UTC>: $(cat "$store/arthur/status")"
grep -q "discover failed" "$work/stderr" || bad "the collector's stderr did not reach the journal"
ok "kept scan published, status says failed=<UTC>, exit $rc"

case_ "== never collected, osquery absent: both keys name the state ============="
start_fake ok
out="$work/out.none"; mkdir -p "$out"
stub 1 "discover: no osqueryi found (set OSQI)"; report
[ "$rc" -ne 0 ] || bad "a VM with no osquery exited 0"
is inventory 'no-cache' || bad "arthur/inventory is not no-cache: $(cat "$store/arthur/inventory" 2>/dev/null)"
grep -Eq "^no-cache failed=$TS osquery=absent\$" "$store/arthur/status" \
  || bad "arthur/status does not name the state: $(cat "$store/arthur/status" 2>/dev/null)"
ok "inventory=no-cache, status=no-cache failed=<UTC> osquery=absent"

case_ "== guest attributes disabled: logged by name, nothing published =========="
start_fake disabled
printf 'arthur1.H4sIAAAA\n' > "$out/inventory.ea"
printf 'ok 2026-10-12T00:00:00Z rows=3 apps=ok\n' > "$out/status.txt"
stub 0; report
[ "$rc" -ne 0 ] || bad "a VM with guest attributes disabled exited 0"
grep -q "guest attributes are disabled on this VM" "$work/stderr" || bad "the 403 was not named"
grep -q "Guest attributes endpoint access is disabled." "$work/stderr" || bad "the server's 403 message was not logged"
[ -z "$(ls -A "$store")" ] || bad "something was stored while guest attributes were disabled"
ok "403 named in the journal, exit $rc, nothing stored"

case_ "== no metadata server: logged, not silent ================================="
start_fake ok; kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null
report
[ "$rc" -ne 0 ] || bad "an unreachable metadata server exited 0"
grep -q "cannot reach the metadata server" "$work/stderr" || bad "an unreachable server was not named"
ok "unreachable metadata server named, exit $rc"

case_ "== a scan status without its value publishes no-cache for both keys ====="
start_fake ok
out="$work/out.halfway"; mkdir -p "$out"
printf 'ok 2026-10-12T00:00:00Z rows=3 apps=ok\n' > "$out/status.txt"
stub 0; report
is inventory 'no-cache' || bad "arthur/inventory is not no-cache"
is status 'no-cache' || bad "arthur/status claims a scan the inventory does not carry: $(cat "$store/arthur/status")"
ok "status.txt without inventory.ea: both keys no-cache"

case_ "== a transient failure is retried ======================================="
start_fake flaky
out="$work/out.clean"
printf 'arthur1.H4sIAAAA\n' > "$out/inventory.ea"
printf 'ok 2026-10-12T00:00:00Z rows=3 apps=ok\n' > "$out/status.txt"
stub 0; report
[ "$rc" -eq 0 ] || bad "one 503 failed the run: $(head -c 200 "$work/stderr")"
is inventory 'arthur1.H4sIAAAA' || bad "the retried inventory was not published"
ok "a 503 retried through to success, exit 0"

case_ "== a reason logged is this request's, not the previous one's ============"
start_fake drop-status
{ cat "$work/at-cap"; printf 'A\n'; } > "$out/inventory.ea"
report
[ "$rc" -ne 0 ] || bad "a status that could not be written exited 0"
grep "arthur/status\|metadata server" "$work/stderr" | grep -q "Maximum value" \
  && bad "the status failure was logged with the inventory's 400 reason: $(cat "$work/stderr")"
grep -q "Maximum value of 262144 bytes allowed" "$work/stderr" || bad "the inventory's own 400 was not logged"
ok "inventory refused, status dropped: each logged with its own reason"

case_ "== a fleet-wide proxy does not carry the metadata request ==============="
start_fake ok
printf 'arthur1.H4sIAAAA\n' > "$out/inventory.ea"
stub 0
http_proxy=http://127.0.0.1:9 report
[ "$rc" -eq 0 ] || bad "with http_proxy set, the PUT went to the proxy: $(head -c 200 "$work/stderr")"
is inventory 'arthur1.H4sIAAAA' || bad "nothing reached the metadata server with http_proxy set"
ok "http_proxy set to a dead proxy: published directly, exit 0"

case_ "== a signal ends the run instead of misreporting it ======================"
start_fake ok
printf '#!/bin/bash\nsleep 30\n' > "$work/collect"; chmod +x "$work/collect"
ARTHUR_COLLECT="$work/collect" ARTHUR_OUT_DIR="$out" ARTHUR_GUEST_ATTRIBUTES_URL="$url" \
  "$REPORT" > "$work/stdout" 2> "$work/stderr" &
rpid=$!
for _ in $(seq 50); do pgrep -P "$rpid" >/dev/null && break; sleep 0.1; done
# What systemd does on stop or timeout: TERM to every process in the unit.
pkill -TERM -P "$rpid"; kill -TERM "$rpid"; wait "$rpid"; rc=$?
[ "$rc" -ne 0 ] || bad "a TERMed run exited 0"
grep -q "cannot reach the metadata server" "$work/stderr" && bad "a TERMed run blamed the metadata server"
[ -z "$(ls -A "$store")" ] || bad "a TERMed run published something"
ok "TERM during collection: exit $rc, nothing published, nothing misreported"

case_ "== the reporter leaves no working directory behind ======================="
[ "$before" = "$(leaked)" ] || bad "the reporter leaked a working directory"
ok "no arthur-report.* left by twelve runs"

[ "$fails" -eq 0 ] && echo "guest-attributes: PASS" || echo "guest-attributes: FAIL ($fails)"
[ "$fails" -eq 0 ]
