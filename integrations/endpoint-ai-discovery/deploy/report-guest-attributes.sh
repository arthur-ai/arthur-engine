#!/bin/bash
# Run the collector, then publish what it wrote to this VM's guest attributes, where the
# Compute Engine API serves them to Arthur. This is the Compute Engine half of the carrier --
# the job a Jamf Extension Attribute does by `cat`-ing a file -- so collect-linux.sh stays
# vendor-neutral. Run by arthur-ai-discovery.service; see docs/mdm/gce.md.
#
#   arthur/inventory   the framed value, `ERROR:oversize:<bytes>`, or `no-cache`
#   arthur/status      the status line, or `no-cache`, plus what happened to THIS run:
#                        failed=<UTC>            the collector exited non-zero
#                        osquery=absent          ...because the runner found no osqueryi
#                        inventory=refused:<n>   the inventory write was refused, so the key
#                                                still holds the previous value
#
# EVERY KEY IS WRITTEN ON EVERY RUN, with a value that names its state. An absent or empty key
# reads as a VM with no AI tools on it.
#
# NO CREDENTIAL AND NO ROUTE. The metadata server is local to the VM, and writing its own
# guest attributes needs no service account. A VM with guest attributes disabled answers 403
# and nothing can be published from it; that is logged by name and the unit fails.
set -uo pipefail

COLLECT="${ARTHUR_COLLECT:-/usr/local/arthur/collect-linux.sh}"
OUT="${ARTHUR_OUT_DIR:-/var/lib/arthur}"
URL="${ARTHUR_GUEST_ATTRIBUTES_URL:-http://metadata.google.internal/computeMetadata/v1/instance/guest-attributes/arthur}"

# The unit sets TMPDIR under /var/lib/arthur, because a hardened image mounts /tmp and /var/tmp
# noexec and the collector runs what it unpacks.
[ -z "${TMPDIR:-}" ] || mkdir -p -m 700 "$TMPDIR" || { echo "arthur: cannot create $TMPDIR" >&2; exit 1; }
# A collector built on osquery-ai-discovery before v0.14.0 left an empty osquery-<n>
# directory in TMPDIR on every osqueryi exit, and no temp cleaner reads the unit's TMPDIR.
# Only there, only that name, only empty: in a shared TMPDIR a running osqueryi's directory
# is empty too.
case "${TMPDIR:-}" in
  "$OUT"/*) find "$TMPDIR" -maxdepth 1 -type d -name 'osquery-*' -empty -delete 2>/dev/null ;;
esac
work="$(mktemp -d "${TMPDIR:-/tmp}/arthur-report.XXXXXX")" || {
  echo "arthur: cannot create a working directory" >&2; exit 1; }
# A signal ENDS the run. Trapping it only to clean up would let the script carry on with its
# working directory gone, and every write after that would be misreported.
trap 'rm -rf "$work"' EXIT
trap 'exit 1' HUP INT TERM

# --- collect ---------------------------------------------------------------------------------
# Its stderr reaches the journal unchanged; a copy is kept to name why a run failed. The
# collector keeps the last good scan when a run fails, so the files below may be older than
# this run -- the status line dates itself, and `failed=` says this run did not succeed.
ARTHUR_OUT_DIR="$OUT" "$COLLECT" 2> "$work/collect.err"
collected=$?
cat "$work/collect.err" >&2

# THE TWO KEYS DESCRIBE ONE STATE. With no framed value there is no scan to describe, whatever
# status.txt says, so the status is no-cache whenever the inventory is.
if [ -s "$OUT/inventory.ea" ] && [ -s "$OUT/status.txt" ]; then
  scanned=1; status="$(tr -d '\n' < "$OUT/status.txt")"
else
  scanned=0; status="no-cache"
fi
if [ "$collected" -ne 0 ]; then
  status="$status failed=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  # UPSTREAM'S DIAGNOSIS, READ RATHER THAN RE-DERIVED. The runner searches four paths for
  # osqueryi; a second copy of that search here would drift from the one that decides.
  # test/lint.sh fails if the vendored runner stops printing this.
  grep -q "no osqueryi found" "$work/collect.err" && status="$status osquery=absent"
fi

# The value only: inventory.ea ends in one newline for a `cat`-ing reader, and a value of
# exactly the 262,144-byte cap would be one byte over it with the newline sent.
if [ "$scanned" = 1 ]; then
  tr -d '\n' < "$OUT/inventory.ea" > "$work/inventory"
else
  printf 'no-cache' > "$work/inventory"
fi

# --- publish ---------------------------------------------------------------------------------
# The HTTP code decides, never curl's exit status alone: `curl -s` exits 0 on a 400.
#   --noproxy '*'   the metadata server is link-local, and a fleet-wide proxy must not carry it
#   --retry         a transient failure (5xx, timeout, refused) is retried; a 400 or 403 is an
#                   answer and is not
# The response files are cleared first: curl leaves them untouched when nothing arrives, and a
# reason logged for this request must not be the previous one's.
put() {
  rm -f "$work/body" "$work/curl.err"
  code="$(curl -sS --noproxy '*' --max-time 10 --retry 2 --retry-delay 1 --retry-connrefused \
            -o "$work/body" -w '%{http_code}' -X PUT -H 'Metadata-Flavor: Google' \
            --data-binary @"$2" "$URL/$1" 2> "$work/curl.err")"
  [ -n "$code" ] || code=000
}

why() { { head -c 300 "$work/body"; head -c 300 "$work/curl.err"; } 2>/dev/null | tr '\n' ' '; }

unpublishable() {
  case "$code" in
    403) echo "arthur: guest attributes are disabled on this VM (HTTP 403: $(why)). Set" \
              "enable-guest-attributes=TRUE in its metadata; nothing can be reported until" \
              "then." >&2 ;;
    000) echo "arthur: cannot reach the metadata server at $URL ($(why)). Is this a" \
              "Compute Engine VM?" >&2 ;;
    *)   return 1 ;;
  esac
}

put inventory "$work/inventory"
if [ "$code" != 200 ]; then
  unpublishable && exit 1
  # REFUSED, AND THE KEY STILL HOLDS THE PREVIOUS VALUE. The status line says so, or the VM
  # would go on serving an old inventory with nothing to show why.
  echo "arthur: arthur/inventory refused (HTTP $code: $(why)); it still holds the previous" \
       "value" >&2
  status="$status inventory=refused:$code"
fi

printf '%s' "$status" > "$work/status"
put status "$work/status"
if [ "$code" != 200 ]; then
  unpublishable || echo "arthur: arthur/status refused (HTTP $code: $(why))" >&2
  exit 1
fi

echo "arthur: published arthur/inventory ($(wc -c < "$work/inventory" | tr -d ' ') bytes)" \
     "and arthur/status: $status"

# The unit fails when the collector did, or when the inventory was refused -- the journal and
# `systemctl --failed` are where a broken VM shows -- while the keys keep the best evidence.
case "$status" in *inventory=refused:*) exit 1 ;; esac
[ "$collected" -eq 0 ] || exit 1
exit 0
