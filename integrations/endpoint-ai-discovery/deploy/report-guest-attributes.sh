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

work="$(mktemp -d "${TMPDIR:-/tmp}/arthur-report.XXXXXX")" || {
  echo "arthur: cannot create a working directory" >&2; exit 1; }
trap 'rm -rf "$work"' EXIT HUP INT TERM

# --- collect ---------------------------------------------------------------------------------
# Its stderr reaches the journal unchanged; a copy is kept to name why a run failed. The
# collector keeps the last good scan when a run fails, so the files below may be older than
# this run -- the status line dates itself, and `failed=` says this run did not succeed.
ARTHUR_OUT_DIR="$OUT" "$COLLECT" 2> "$work/collect.err"
collected=$?
cat "$work/collect.err" >&2

if [ -s "$OUT/status.txt" ]; then
  status="$(tr -d '\n' < "$OUT/status.txt")"
else
  status="no-cache"
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
if [ -s "$OUT/inventory.ea" ]; then
  tr -d '\n' < "$OUT/inventory.ea" > "$work/inventory"
else
  printf 'no-cache' > "$work/inventory"
fi

# --- publish ---------------------------------------------------------------------------------
# The HTTP code decides, never curl's exit status alone: `curl -s` exits 0 on a 400.
put() {
  code="$(curl -sS --max-time 10 -o "$work/body" -w '%{http_code}' -X PUT \
            -H 'Metadata-Flavor: Google' --data-binary @"$2" "$URL/$1" 2> "$work/curl.err")"
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
