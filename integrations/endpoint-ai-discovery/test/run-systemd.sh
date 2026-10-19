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
servers=""; remounted=""
cleanup() {
  for m in $remounted; do umount "$m" 2>/dev/null; done
  systemctl disable --now "$UNIT.timer" >/dev/null 2>&1
  systemctl stop "$UNIT.service" >/dev/null 2>&1
  rm -rf "/etc/systemd/system/$UNIT.service.d" /usr/local/arthur /var/lib/arthur
  rm -f "/etc/systemd/system/$UNIT.service" "/etc/systemd/system/$UNIT.timer"
  systemctl daemon-reload
  for p in $servers; do kill "$p" 2>/dev/null; done
  rm -rf "$work"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM

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
  systemctl start "$UNIT.service" 2>/dev/null; started=$?
  result="$(systemctl show -p Result --value "$UNIT.service")"
}

# journald stores a unit's output asynchronously, so its last line may not be readable the
# moment the unit ends. Sync, and look again briefly, before deciding it is not there.
journal_has() {
  for _ in $(seq 20); do
    journalctl --sync 2>/dev/null
    journalctl -u "$UNIT.service" --since "$since" --no-pager -o cat > "$work/journal" 2>&1
    grep -q "$1" "$work/journal" && return 0
    sleep 0.25
  done
  return 1
}

case_ "== installed where the units and the reporter expect it ================="
install -d -m 755 /usr/local/arthur
install -m 755 "$ROOT/dist/collect-linux.sh" /usr/local/arthur/collect-linux.sh
install -m 755 "$ROOT/deploy/report-guest-attributes.sh" /usr/local/arthur/report-guest-attributes.sh
install -m 644 "$ROOT/deploy/$UNIT.service" "$ROOT/deploy/$UNIT.timer" /etc/systemd/system/
systemctl daemon-reload
systemd-analyze verify "/etc/systemd/system/$UNIT.service" "/etc/systemd/system/$UNIT.timer" \
  > "$work/verify" 2>&1 || bad "systemd-analyze verify: $(cat "$work/verify")"
# ENABLED, NOT STARTED. Started now, a timer whose OnBootSec has passed fires within its random
# delay and could run against the real metadata host before the drop-in points it at the fake.
# It is started, and its schedule checked, after the runs below.
systemctl enable "$UNIT.timer" >/dev/null 2>&1 || bad "the timer would not enable"
[ "$(systemctl is-enabled "$UNIT.timer")" = enabled ] || bad "the timer is not enabled"
ok "units verify; timer enabled"

case_ "== one run under systemd publishes what the collector framed ============="
start_fake ok
activate
[ "$started" -eq 0 ] && [ "$result" = success ] || bad "the unit ended '$result' (start exited $started)"
[ "$(head -c 8 "$store/arthur/inventory" 2>/dev/null)" = arthur1. ] || bad "arthur/inventory is not an arthur1. value"
cmp -s <(tr -d '\n' < /var/lib/arthur/inventory.ea) "$store/arthur/inventory" \
  || bad "arthur/inventory is not the value the collector framed, byte for byte"
grep -Eq '^(ok|degraded) [0-9-]+T[0-9:]+Z rows=[0-9]+ ' "$store/arthur/status" \
  || bad "arthur/status is not a status line: $(cat "$store/arthur/status" 2>/dev/null)"
journal_has "published arthur/inventory" || bad "the journal does not say what was published: $(tail -5 "$work/journal")"
ok "Result=success; inventory $(wc -c < "$store/arthur/inventory" | tr -d ' ') bytes; status: $(cut -d' ' -f1-3 "$store/arthur/status")"

case_ "== a hardened host: /tmp and /var/tmp mounted noexec ===================="
# The bundle unpacks its runner and executes it. Shown both ways, so this case cannot pass
# vacuously: run by hand with no TMPDIR the collector fails here; under the unit, whose TMPDIR
# is under /var/lib/arthur, it succeeds.
for m in /tmp /var/tmp; do
  if mount --bind "$m" "$m" && mount -o remount,bind,noexec "$m"; then
    remounted="$m $remounted"
  else
    bad "could not remount $m noexec"
  fi
done
env -u TMPDIR ARTHUR_OUT_DIR="$work/by-hand" /usr/local/arthur/collect-linux.sh > /dev/null 2>&1
by_hand=$?
[ "$by_hand" -ne 0 ] || bad "the collector ran from a noexec /var/tmp, so this case proves nothing"
activate
[ "$started" -eq 0 ] && [ "$result" = success ] || bad "with noexec temp dirs the unit ended '$result'"
for m in $remounted; do umount "$m"; done; remounted=""
ok "by hand with no TMPDIR: exit $by_hand; under the unit: Result=$result"

case_ "== guest attributes disabled: the unit fails and the journal says why ===="
start_fake disabled
activate
[ "$started" -ne 0 ] && [ "$result" != success ] || bad "the unit succeeded with nothing published"
journal_has "guest attributes are disabled on this VM" || bad "the journal does not name the 403: $(tail -3 "$work/journal")"
ok "Result=$result; the journal names the disabled endpoint"

case_ "== EC2: the drop-in runs the SSM reporter in place of this one ==========="
install -m 755 "$ROOT/deploy/report-ssm-inventory.sh" /usr/local/arthur/report-ssm-inventory.sh
install -m 644 "$ROOT/deploy/$UNIT.service.d/ec2.conf" "/etc/systemd/system/$UNIT.service.d/ec2.conf"
rm -f "$work/imds-port"
python3 "$ROOT/test/fake-imds.py" "$work/imds-port" ok &
servers="$servers $!"
for _ in $(seq 50); do [ -s "$work/imds-port" ] && break; sleep 0.1; done
ssm="$work/ssm"; mkdir -p "$ssm"
printf '[Service]\nEnvironment=ARTHUR_IMDS_URL=http://127.0.0.1:%s\nEnvironment=ARTHUR_SSM_DATA_DIR=%s\n' \
  "$(cat "$work/imds-port")" "$ssm" > "/etc/systemd/system/$UNIT.service.d/test.conf"
systemctl daemon-reload
exec_start="$(systemctl show -p ExecStart --value "$UNIT.service")"
case "$exec_start" in
  *report-guest-attributes.sh*) bad "with the drop-in the unit still runs the guest-attribute reporter: $exec_start" ;;
  *report-ssm-inventory.sh*) ;;
  *) bad "with the drop-in the unit does not run the SSM reporter: $exec_start" ;;
esac
activate
[ "$started" -eq 0 ] && [ "$result" = success ] || bad "the EC2 unit ended '$result' (start exited $started)"
inv="$ssm/i-0123456789abcdef0/inventory/custom/ArthurAIDiscovery.json"
python3 - "$inv" /var/lib/arthur/inventory.ea <<'PY' || bad "the custom inventory does not carry the collector's value"
import json, sys
parts = [e for e in json.load(open(sys.argv[1]))["Content"] if e["Key"] == "inventory"]
value = "".join(e["Value"] for e in sorted(parts, key=lambda e: int(e["Part"])))
assert value == open(sys.argv[2]).read().replace("\n", ""), "not the framed value"
PY
journal_has "wrote Custom:ArthurAIDiscovery" || bad "the journal does not say what was written: $(tail -3 "$work/journal")"
# Back to the Compute Engine unit, pointed at a fake, before the timer is started below.
rm -f "/etc/systemd/system/$UNIT.service.d/ec2.conf"
start_fake disabled
ok "Result=$result; the custom inventory carries the value the collector framed"

case_ "== started, the timer schedules the next run ============================"
systemctl start "$UNIT.timer" || bad "the timer would not start"
[ "$(systemctl is-active "$UNIT.timer")" = active ] || bad "the timer is not active"
# A runner up for longer than OnBootSec plus its random delay fires the timer the moment it
# starts, and while the run it triggered is under way systemd reports no next elapse at all.
# Wait that run out: when it ends, OnUnitActiveSec schedules the next one from it.
for attempt in $(seq 60); do
  next="$(systemctl show -p NextElapseUSecMonotonic --value "$UNIT.timer")"
  case "$next" in ""|infinity|0|n/a) [ "$attempt" -lt 60 ] && sleep 0.5 ;; *) break ;; esac
done
case "$next" in ""|infinity|0|n/a) bad "the timer has nothing scheduled (NextElapseUSecMonotonic=$next)" ;; esac
ok "timer active; next run at monotonic $next"

[ "$fails" -eq 0 ] && echo "systemd: PASS" || echo "systemd: FAIL ($fails)"
[ "$fails" -eq 0 ]
