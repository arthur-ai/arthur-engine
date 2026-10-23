#!/usr/bin/env bash
# Run the EC2 install script as a stack ships it -- the runCommand of a rendered
# deploy/arthur-ai-discovery.cfn.yaml -- as root under sh, against this checkout served over
# file://, and assert on what it installed. Needs root, systemd as PID 1, python3 and osquery;
# without osquery the script installs it from pkg.osquery.io.
#
#     tools/render-cfn-template.sh HEAD > /tmp/arthur-ai-discovery.cfn.yaml
#     sudo ARTHUR_TEST_INSTALLS_UNITS=1 test/run-ec2-install.sh /tmp/arthur-ai-discovery.cfn.yaml
#
# Rendered beforehand, as the checkout's owner: git refuses root a repository it does not own.
# The checkout must hold the bytes the template pins, which a clean checkout of the rendered
# ref does.
#
# IT WRITES TO THE MACHINE -- /usr/local/arthur, /etc/systemd/system, /var/lib/arthur -- and
# removes it all afterwards. Hence the variable: on a workstation, it refuses. CI runs it on a
# hosted runner; docs/mdm/ec2.md's real-instance run is the acceptance check, not this.
#
# WHY RUN IT AND NOT ONLY LINT IT. test/lint.sh reads the script. This runs the bytes a stack
# ships, under dash: each fetch against the checksum the renderer pinned, the paths and modes,
# a second run that changes nothing, and a file served with other bytes failing the run.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT=arthur-ai-discovery
RUNTIME_DROPIN="/run/systemd/system/$UNIT.service.d"
fails=0
bad()   { printf 'FAIL: %s\n' "$1"; fails=$((fails + 1)); }
case_() { echo "$1"; mark=$fails; }
ok()    { [ "$fails" -eq "$mark" ] && printf 'ok: %s\n' "$1"; }

[ "${ARTHUR_TEST_INSTALLS_UNITS:-}" = 1 ] || {
  echo "refusing: this installs files under /usr/local and /etc/systemd. Set"
  echo "ARTHUR_TEST_INSTALLS_UNITS=1 on a machine you can throw away."; exit 1; }
[ "$(id -u)" = 0 ] || { echo "FAIL: needs root, as the association runs it"; exit 1; }
[ -d /run/systemd/system ] || { echo "FAIL: systemd is not PID 1 here"; exit 1; }
[ -s "${1:-}" ] || { echo "FAIL: pass a template rendered by tools/render-cfn-template.sh"; exit 1; }

work="$(mktemp -d)" || exit 1
cleanup() {
  systemctl disable --now "$UNIT.timer" >/dev/null 2>&1
  systemctl stop "$UNIT.service" >/dev/null 2>&1
  rm -rf "/etc/systemd/system/$UNIT.service.d" "$RUNTIME_DROPIN" /usr/local/arthur /var/lib/arthur
  rm -f "/etc/systemd/system/$UNIT.service" "/etc/systemd/system/$UNIT.timer"
  systemctl daemon-reload
  rm -rf "$work"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM

# The runCommand block, dedented: the script exactly as the document hands it to sh.
python3 - "$1" > "$work/script.sh" <<'PY' || { echo "FAIL: no runCommand block in $1"; exit 1; }
import re, sys
tpl = open(sys.argv[1]).read()
(indent, body), = re.findall(r"^( *)runCommand:\n\1  - \|\n((?:\1    .*\n|\n)+)", tpl, re.M)
sys.stdout.write("".join(l[len(indent) + 4:] + "\n" for l in body.rstrip("\n").split("\n")))
PY
grep -q "{{ baseUrl }}" "$work/script.sh" || { echo "FAIL: the script takes no {{ baseUrl }}"; exit 1; }
grep -Eq '^ *fetch .* SHA256_[A-Z]+$' "$work/script.sh" \
  && { echo "FAIL: $1 is not rendered: a checksum is still a placeholder"; exit 1; }
# SSM substitutes the document parameter into the command; so does this.
with_base() { sed "s|{{ baseUrl }}|$1|" "$work/script.sh" > "$2"; }
with_base "file://$ROOT" "$work/install.sh"
grep -E '^ *fetch [^ ]+ [^ ]+ [0-7]+ [0-9a-f]{64}$' "$work/install.sh" > "$work/fetches"
[ -s "$work/fetches" ] || { echo "FAIL: the rendered script fetches nothing"; exit 1; }

# The timer may fire the moment it starts, on a runner up longer than OnBootSec. What the unit
# runs is test/run-systemd.sh's question; here it runs nothing. A runtime drop-in sorts after
# ec2.conf, so its ExecStart is the one that holds, and the script never writes under /run.
mkdir -p "$RUNTIME_DROPIN"
printf '[Service]\nExecStart=\nExecStart=/bin/true\n' > "$RUNTIME_DROPIN/zz-test.conf"

installed() {  # every destination's sha256 and mode, one line each
  while read -r _ _ dest _ _; do
    printf '%s %s %s\n' "$dest" "$(sha256sum < "$dest" 2>/dev/null | cut -d' ' -f1)" \
      "$(stat -c %a "$dest" 2>/dev/null)"
  done < "$work/fetches"
}

case_ "== the rendered script installs each file where it is run ================="
sh "$work/install.sh" > "$work/run1" 2>&1; status=$?
[ "$status" -eq 0 ] || bad "the script exited $status under sh: $(tail -5 "$work/run1")"
while read -r _ src dest mode sha; do
  [ -f "$dest" ] || { bad "$src was not installed at $dest"; continue; }
  [ "$(sha256sum < "$dest" | cut -d' ' -f1)" = "$sha" ] || bad "$dest is not the bytes pinned for $src"
  [ "$(stat -c %a "$dest")" = "$mode" ] || bad "$dest has mode $(stat -c %a "$dest"), not $mode"
done < "$work/fetches"
[ "$(systemctl is-enabled "$UNIT.timer" 2>/dev/null)" = enabled ] || bad "the timer is not enabled"
[ "$(systemctl is-active "$UNIT.timer" 2>/dev/null)" = active ] || bad "the timer is not active"
dropins="$(systemctl show -p DropInPaths --value "$UNIT.service")"
case "$dropins" in
  *"/etc/systemd/system/$UNIT.service.d/ec2.conf"*) ;;
  *) bad "systemd did not load the EC2 drop-in: DropInPaths=$dropins" ;;
esac
ok "$(wc -l < "$work/fetches" | tr -d ' ') files at their pinned sha256 and modes; timer enabled and active"

case_ "== a second run changes nothing ============================================"
before="$(installed)"
entered="$(systemctl show -p ActiveEnterTimestampMonotonic --value "$UNIT.timer")"
sh "$work/install.sh" > "$work/run2" 2>&1; status=$?
[ "$status" -eq 0 ] || bad "the second run exited $status: $(tail -5 "$work/run2")"
[ "$(installed)" = "$before" ] || bad "the second run changed a file: $(diff <(echo "$before") <(installed))"
[ "$(systemctl show -p ActiveEnterTimestampMonotonic --value "$UNIT.timer")" = "$entered" ] \
  || bad "the second run restarted the timer"
ok "every file and mode as it was; the timer not restarted"

case_ "== a file served with other bytes fails the run and replaces nothing ======="
mirror="$work/mirror"
while read -r _ src _ _ _; do
  mkdir -p "$mirror/$(dirname "$src")" && cp "$ROOT/$src" "$mirror/$src"
done < "$work/fetches"
read -r _ first first_dest _ _ < "$work/fetches"
printf '\n' >> "$mirror/$first"
with_base "file://$mirror" "$work/tampered.sh"
before="$(installed)"
sh "$work/tampered.sh" > "$work/run3" 2>&1; status=$?
[ "$status" -ne 0 ] || bad "the script succeeded with $first served as other bytes"
grep -qF "$first_dest.new: FAILED" "$work/run3" \
  || bad "the run's output does not name the refused file: $(tail -3 "$work/run3")"
[ "$(installed)" = "$before" ] || bad "a refused download replaced an installed file"
ok "exit $status; the output names $first_dest.new; every installed file as it was"

[ "$fails" -eq 0 ] && echo "ec2 install: PASS" || echo "ec2 install: FAIL ($fails)"
[ "$fails" -eq 0 ]
