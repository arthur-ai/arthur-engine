#!/usr/bin/env bash
# Install the Linux collector, the reporter and the systemd units at their real paths, run
# them under systemd against a fake metadata server, and assert on what was published and what
# the journal says. Needs root, systemd as PID 1, osquery and python3.
#
#     sudo ARTHUR_TEST_INSTALLS_UNITS=1 test/run-systemd.sh
#
# IT WRITES TO THE MACHINE -- /usr/local/arthur, /etc/systemd/system, /var/lib/arthur -- and
# removes it all afterwards. Hence the variable: on a workstation, it refuses. CI runs it on a
# hosted runner; docs/mdm/gce.md's real-VM run is the acceptance check, not this.
#
# WHY UNDER SYSTEMD AND NOT JUST THE SCRIPT. test/run-guest-attributes.sh proves what the
# reporter publishes. This proves the units run it: ExecStart, the paths the files are
# installed at, the unit failing when nothing can be published, and the journal saying why.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT=arthur-ai-discovery
fails=0
bad()   { printf 'FAIL: %s\n' "$1"; fails=$((fails + 1)); }
case_() { echo "$1"; mark=$fails; }
ok()    { [ "$fails" -eq "$mark" ] && printf 'ok: %s\n' "$1"; }

[ "${ARTHUR_TEST_INSTALLS_UNITS:-}" = 1 ] || {
  echo "refusing: this installs files under /usr/local and /etc/systemd. Set"
  echo "ARTHUR_TEST_INSTALLS_UNITS=1 on a machine you can throw away."; exit 1; }
[ "$(id -u)" = 0 ] || { echo "FAIL: needs root, as the unit runs"; exit 1; }
[ -d /run/systemd/system ] || { echo "FAIL: systemd is not PID 1 here"; exit 1; }
python3 -c "import http.server" 2>/dev/null || { echo "FAIL: the fake server needs python3"; exit 1; }

work="$(mktemp -d)" || exit 1
servers=""
cleanup() {
  systemctl disable --now "$UNIT.timer" >/dev/null 2>&1
  rm -rf "/etc/systemd/system/$UNIT.service.d" /usr/local/arthur /var/lib/arthur
  rm -f "/etc/systemd/system/$UNIT.service" "/etc/systemd/system/$UNIT.timer"
  systemctl daemon-reload
  for p in $servers; do kill "$p" 2>/dev/null; done
  rm -rf "$work"
}
trap cleanup EXIT HUP INT TERM

start_fake() {
  store="$work/store.$1"; mkdir -p "$store"; rm -f "$work/port"
  python3 "$ROOT/test/fake-metadata-server.py" "$store" "$work/port" "$1" &
  servers="$servers $!"
  for _ in $(seq 50); do [ -s "$work/port" ] && break; sleep 0.1; done
  [ -s "$work/port" ] || { echo "FAIL: the fake metadata server did not start"; exit 1; }
  # Pointed at the fake by drop-in, as an admin overrides a packaged unit.
  mkdir -p "/etc/systemd/system/$UNIT.service.d"
  printf '[Service]\nEnvironment=ARTHUR_GUEST_ATTRIBUTES_URL=http://127.0.0.1:%s/computeMetadata/v1/instance/guest-attributes/arthur\n' \
    "$(cat "$work/port")" > "/etc/systemd/system/$UNIT.service.d/test.conf"
  systemctl daemon-reload
}

# One activation now, rather than waiting out OnBootSec. Type=oneshot, so `start` returns when
# the run has ended, and fails when it did.
activate() {
  since="$(date '+%Y-%m-%d %H:%M:%S')"
  systemctl start "$UNIT.service"; started=$?
  result="$(systemctl show -p Result --value "$UNIT.service")"
  journalctl -u "$UNIT.service" --since "$since" --no-pager -o cat > "$work/journal" 2>&1
}

case_ "== installed where the units and the reporter expect it ================="
install -d -m 755 /usr/local/arthur
install -m 755 "$ROOT/dist/collect-linux.sh" /usr/local/arthur/collect-linux.sh
install -m 755 "$ROOT/deploy/report-guest-attributes.sh" /usr/local/arthur/report-guest-attributes.sh
install -m 644 "$ROOT/deploy/$UNIT.service" "$ROOT/deploy/$UNIT.timer" /etc/systemd/system/
systemctl daemon-reload
systemd-analyze verify "/etc/systemd/system/$UNIT.service" "/etc/systemd/system/$UNIT.timer" \
  > "$work/verify" 2>&1 || bad "systemd-analyze verify: $(cat "$work/verify")"
systemctl enable --now "$UNIT.timer" >/dev/null 2>&1 || bad "the timer would not enable"
[ "$(systemctl is-active "$UNIT.timer")" = active ] || bad "the timer is not active"
[ -n "$(systemctl show -p NextElapseUSecMonotonic --value "$UNIT.timer")" ] || bad "the timer has nothing scheduled"
ok "units verify, timer enabled and scheduled"

case_ "== one run under systemd publishes what the collector framed ============="
start_fake ok
activate
[ "$started" -eq 0 ] && [ "$result" = success ] || bad "the unit ended '$result' (start exited $started): $(tail -5 "$work/journal")"
[ "$(head -c 8 "$store/arthur/inventory" 2>/dev/null)" = arthur1. ] || bad "arthur/inventory is not an arthur1. value"
cmp -s <(tr -d '\n' < /var/lib/arthur/inventory.ea) "$store/arthur/inventory" \
  || bad "arthur/inventory is not the value the collector framed, byte for byte"
grep -Eq '^(ok|degraded) [0-9-]+T[0-9:]+Z rows=[0-9]+ ' "$store/arthur/status" \
  || bad "arthur/status is not a status line: $(cat "$store/arthur/status" 2>/dev/null)"
grep -q "published arthur/inventory" "$work/journal" || bad "the journal does not say what was published"
ok "Result=success; inventory $(wc -c < "$store/arthur/inventory" | tr -d ' ') bytes; status: $(cut -d' ' -f1-3 "$store/arthur/status")"

case_ "== guest attributes disabled: the unit fails and the journal says why ===="
start_fake disabled
activate
[ "$started" -ne 0 ] && [ "$result" != success ] || bad "the unit succeeded with nothing published"
grep -q "guest attributes are disabled on this VM" "$work/journal" || bad "the journal does not name the 403: $(tail -3 "$work/journal")"
ok "Result=$result; the journal names the disabled endpoint"

[ "$fails" -eq 0 ] && echo "systemd: PASS" || echo "systemd: FAIL ($fails)"
[ "$fails" -eq 0 ]
