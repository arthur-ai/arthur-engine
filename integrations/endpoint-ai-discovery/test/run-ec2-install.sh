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
# ships, under dash: a hybrid node left alone, each fetch against the checksum the renderer
# pinned, the paths and modes, a second run that downloads nothing, and a pin change whose last
# file is served wrong replacing none of the files verified before it.
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

installed() {  # every destination's sha256, mode and inode, one line each: a new inode is a replaced file
  while read -r _ _ dest _ _; do
    printf '%s %s %s\n' "$dest" "$(sha256sum < "$dest" 2>/dev/null | cut -d' ' -f1)" \
      "$(stat -c '%a %i' "$dest" 2>/dev/null)"
  done < "$work/fetches"
}

case_ "== a hybrid-activated node: nothing installed ============================"
AWS_SSM_INSTANCE_ID=mi-0123456789abcdef0 sh "$work/install.sh" > "$work/run0" 2>&1; status=$?
[ "$status" -eq 0 ] || bad "the script exited $status on a hybrid node: $(tail -3 "$work/run0")"
grep -q "mi-0123456789abcdef0 is not an EC2 instance" "$work/run0" \
  || bad "the output does not say why nothing was installed: $(tail -3 "$work/run0")"
while read -r _ _ dest _ _; do
  [ ! -e "$dest" ] || bad "a hybrid node got $dest"
done < "$work/fetches"
ok "exit 0, nothing written, and the output says why"

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

case_ "== a second run changes nothing, and downloads nothing ===================="
before="$(installed)"
entered="$(systemctl show -p ActiveEnterTimestampMonotonic --value "$UNIT.timer")"
# A base nothing serves: a run that downloaded any file would fail.
with_base "file://$work/nowhere" "$work/offline.sh"
sh "$work/offline.sh" > "$work/run2" 2>&1; status=$?
[ "$status" -eq 0 ] || bad "the second run exited $status, so it downloaded: $(tail -5 "$work/run2")"
[ "$(installed)" = "$before" ] || bad "the second run replaced a file: $(diff <(echo "$before") <(installed))"
[ "$(systemctl show -p ActiveEnterTimestampMonotonic --value "$UNIT.timer")" = "$entered" ] \
  || bad "the second run restarted the timer"
ok "no download; every file, mode and inode as it was; the timer not restarted"

# AN INSTALL FROM ANOTHER PIN: the first and last files differ from this one's, the rest match.
# Served with the last one's bytes wrong, the run must fail before replacing the first.
read -r _ first first_dest _ _ < "$work/fetches"
read -r _ last last_dest _ _ < <(tail -n 1 "$work/fetches")
printf '# another pin\n' >> "$first_dest"
printf '# another pin\n' >> "$last_dest"

case_ "== a file served with other bytes fails the run and replaces nothing ======="
mirror="$work/mirror"
while read -r _ src _ _ _; do
  mkdir -p "$mirror/$(dirname "$src")" && cp "$ROOT/$src" "$mirror/$src"
done < "$work/fetches"
printf '\n' >> "$mirror/$last"
with_base "file://$mirror" "$work/tampered.sh"
before="$(installed)"
sh "$work/tampered.sh" > "$work/run3" 2>&1; status=$?
[ "$status" -ne 0 ] || bad "the script succeeded with $last served as other bytes"
grep -qF "$last_dest.new: FAILED" "$work/run3" \
  || bad "the run's output does not name the refused file: $(tail -3 "$work/run3")"
[ "$(installed)" = "$before" ] \
  || bad "a refused download left a file replaced: $(diff <(echo "$before") <(installed))"
ok "exit $status; the output names $last_dest.new; $first_dest, verified before it, not replaced"

case_ "== served right, the run replaces just the files that differ ============="
before="$(installed)"
sh "$work/install.sh" > "$work/run4" 2>&1; status=$?
[ "$status" -eq 0 ] || bad "the run exited $status: $(tail -5 "$work/run4")"
while read -r _ src dest mode sha; do
  was="$(grep "^$dest " <<<"$before")"; now="$(grep "^$dest " <(installed))"
  [ "$(sha256sum < "$dest" | cut -d' ' -f1)" = "$sha" ] || bad "$dest is not the bytes pinned for $src"
  case "$dest" in
    # Replaced by a rename, so a new inode: a file written in place can be read half-written.
    "$first_dest"|"$last_dest")
      [ "$now" != "$was" ] || bad "$dest was not replaced"
      [ "${now##* }" != "${was##* }" ] || bad "$dest was written in place, not replaced"
      [ "$(stat -c %a "$dest")" = "$mode" ] || bad "$dest has mode $(stat -c %a "$dest"), not $mode" ;;
    *) [ "$now" = "$was" ] || bad "$dest was replaced though it held its pinned bytes" ;;
  esac
done < "$work/fetches"
[ -z "$(find /usr/local/arthur /etc/systemd/system -name '*.new' 2>/dev/null)" ] \
  || bad "a staged .new file was left behind: $(find /usr/local/arthur /etc/systemd/system -name '*.new')"
ok "$(basename "$first_dest") and $(basename "$last_dest") replaced, the rest untouched, nothing staged left"

[ "$fails" -eq 0 ] && echo "ec2 install: PASS" || echo "ec2 install: FAIL ($fails)"
[ "$fails" -eq 0 ]
