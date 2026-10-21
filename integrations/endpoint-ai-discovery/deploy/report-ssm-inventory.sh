#!/bin/bash
# Run the collector, then write what it wrote as this instance's SSM custom inventory, which
# the SSM Agent uploads when the instance's inventory association runs and the SSM API serves
# to Arthur. This is the EC2 half of the carrier -- report-guest-attributes.sh's counterpart
# -- so collect-linux.sh stays vendor-neutral. Run by arthur-ai-discovery.service through the
# drop-in in arthur-ai-discovery.service.d/ec2.conf; see docs/mdm/ec2.md.
#
#   Custom:ArthurAIDiscovery, one entry per part of each of two values:
#     inventory   the framed value, `ERROR:oversize:<bytes>`, or `no-cache`
#     status      the status line, or `no-cache`, plus what happened to THIS run:
#                   failed=<UTC>     the collector exited non-zero
#                   osquery=absent   ...because the runner found no osqueryi
#
#   An entry is {"Key", "Part", "Parts", "Sha256", "Value"}. A custom inventory value holds
#   at most 4,096 characters, so each value is cut into parts of that size, numbered from 1;
#   Sha256 is the WHOLE value's, so the reader can tell a whole from a part. The ML Engine's
#   discovery/cloud/ec2/client.py reads exactly this, and test/lint.sh holds the two to it.
#
# BOTH VALUES ARE WRITTEN ON EVERY RUN, with a value that names its state. An absent or empty
# value reads as an instance with no AI tools on it.
#
# NO CREDENTIAL AND NO API CALL. This writes a file; the SSM Agent uploads it with the
# instance's own SSM permissions. So the upload is not visible from here: a refused one shows
# in the agent's log and the association's status (ec2.md, section 06), and the reader dates
# the instance by the status line, which stops advancing.
#
# THE FILE IS REPLACED, NEVER WRITTEN IN PLACE. The agent may read it at any moment, and a
# rename is the one write it cannot see half of. The temporary file does not end in .json, so
# the agent never takes it for inventory.
set -uo pipefail
export LC_ALL=C

COLLECT="${ARTHUR_COLLECT:-/usr/local/arthur/collect-linux.sh}"
OUT="${ARTHUR_OUT_DIR:-/var/lib/arthur}"
IMDS="${ARTHUR_IMDS_URL:-http://169.254.169.254}"
SSM_DATA="${ARTHUR_SSM_DATA_DIR:-/var/lib/amazon/ssm}"
TYPE_NAME="Custom:ArthurAIDiscovery"
FILE_NAME="ArthurAIDiscovery.json"
# SSM's cap on one custom inventory value, in characters. Every value here is ASCII.
PART=4096

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
partial=""
# A signal ENDS the run. Trapping it only to clean up would let the script carry on with its
# working directory gone, and every write after that would be misreported.
trap 'rm -rf "$work"; [ -z "$partial" ] || rm -f "$partial"' EXIT
trap 'exit 1' HUP INT TERM

# --- collect ---------------------------------------------------------------------------------
# Its stderr reaches the journal unchanged; a copy is kept to name why a run failed. The
# collector keeps the last good scan when a run fails, so the files below may be older than
# this run -- the status line dates itself, and `failed=` says this run did not succeed.
ARTHUR_OUT_DIR="$OUT" "$COLLECT" 2> "$work/collect.err"
collected=$?
cat "$work/collect.err" >&2

# THE TWO VALUES DESCRIBE ONE STATE. With no framed value there is no scan to describe,
# whatever status.txt says, so the status is no-cache whenever the inventory is.
if [ -s "$OUT/inventory.ea" ] && [ -s "$OUT/status.txt" ]; then
  scanned=1; status="$(tr -d '\n' < "$OUT/status.txt")"
else
  scanned=0; status="no-cache"
fi
if [ "$collected" -ne 0 ]; then
  status="$status failed=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  # UPSTREAM'S DIAGNOSIS, READ RATHER THAN RE-DERIVED. test/lint.sh fails if the vendored
  # runner stops printing this.
  grep -q "no osqueryi found" "$work/collect.err" && status="$status osquery=absent"
fi
if [ "$scanned" = 1 ]; then
  inventory="$(tr -d '\n' < "$OUT/inventory.ea")"
else
  inventory="no-cache"
fi

# --- where -----------------------------------------------------------------------------------
# The agent reads custom inventory from a directory named for the instance, and only IMDS says
# which instance this is: a glob of the agent's directory could find a stale one baked into
# the image this instance was launched from.
#   --noproxy '*'   IMDS is link-local, and a fleet-wide proxy must not carry it
imds() {
  rm -f "$work/body" "$work/curl.err"
  code="$(curl -sS --noproxy '*' --max-time 5 --retry 2 --retry-delay 1 --retry-connrefused \
            -o "$work/body" -w '%{http_code}' "$@" 2> "$work/curl.err")"
  [ -n "$code" ] || code=000
}
why() { { head -c 300 "$work/body"; head -c 300 "$work/curl.err"; } 2>/dev/null | tr '\n' ' '; }

imds -X PUT -H 'X-aws-ec2-metadata-token-ttl-seconds: 60' "$IMDS/latest/api/token"
if [ "$code" != 200 ]; then
  echo "arthur: cannot get an IMDSv2 token from $IMDS (HTTP $code: $(why)). Is this an EC2" \
       "instance with its metadata service enabled? Nothing can be reported without the" \
       "instance id." >&2
  exit 1
fi
token="$(cat "$work/body")"
imds -H "X-aws-ec2-metadata-token: $token" "$IMDS/latest/meta-data/instance-id"
instance_id="$(cat "$work/body" 2>/dev/null)"
if [ "$code" != 200 ] || ! printf '%s' "$instance_id" | grep -Eq '^i-[0-9a-f]{8,17}$'; then
  echo "arthur: IMDS did not return an instance id (HTTP $code: $(why))." >&2
  exit 1
fi

if [ ! -d "$SSM_DATA" ]; then
  echo "arthur: no SSM Agent data directory at $SSM_DATA. Is the SSM Agent installed? It" \
       "uploads what this writes; nothing can be reported without it." >&2
  exit 1
fi
dir="$SSM_DATA/$instance_id/inventory/custom"
mkdir -p "$dir" || { echo "arthur: cannot create $dir" >&2; exit 1; }

# --- write -----------------------------------------------------------------------------------
if command -v sha256sum >/dev/null 2>&1; then
  sha256() { sha256sum | cut -d' ' -f1; }
else
  sha256() { shasum -a 256 | cut -d' ' -f1; }
fi
# The framed value is base64 and the status line is the collector's and the reporter's
# tokens, so neither should carry a control character. One that does is dropped from the
# whole value before it is cut and hashed, so the parts still make the value they claim.
clean() { printf '%s' "$1" | tr -d '\000-\037'; }
# A part as JSON string content: a quote or backslash is escaped, which leaves the value the
# reader decodes -- and the 4,096 characters SSM counts -- unchanged.
escape() { local s="${1//\\/\\\\}"; printf '%s' "${s//\"/\\\"}"; }
inventory="$(clean "$inventory")"
status="$(clean "$status")"

# One entry per part of the value: KEY VALUE, appended to $work/content.
parts() {
  local key="$1" value="$2" length="${#2}" count digest n offset
  count=$(( (length + PART - 1) / PART )); [ "$count" -gt 0 ] || count=1
  digest="$(printf '%s' "$value" | sha256)"
  n=1; offset=0
  while [ "$n" -le "$count" ]; do
    [ -s "$work/content" ] && printf ',' >> "$work/content"
    printf '{"Key":"%s","Part":"%s","Parts":"%s","Sha256":"%s","Value":"%s"}' \
      "$key" "$n" "$count" "$digest" "$(escape "${value:$offset:$PART}")" >> "$work/content"
    n=$((n + 1)); offset=$((offset + PART))
  done
}

: > "$work/content"
parts inventory "$inventory"
parts status "$status"

umask 077
partial="$(mktemp "$dir/.arthur-inventory.XXXXXX")" || {
  echo "arthur: cannot write in $dir" >&2; exit 1; }
{
  printf '{"SchemaVersion":"1.0","TypeName":"%s","Content":[' "$TYPE_NAME"
  cat "$work/content"
  printf ']}\n'
} > "$partial" && mv -f "$partial" "$dir/$FILE_NAME" || {
  echo "arthur: could not write $dir/$FILE_NAME" >&2; exit 1; }
partial=""

echo "arthur: wrote $TYPE_NAME for $instance_id (inventory ${#inventory} characters) for" \
     "the SSM Agent's next inventory upload; status: $status"

# The unit fails when the collector did -- the journal and `systemctl --failed` are where a
# broken instance shows -- while the file keeps the best evidence.
[ "$collected" -eq 0 ] || exit 1
exit 0
