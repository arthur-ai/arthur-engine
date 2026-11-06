#!/bin/sh
# SOC-222: fail if a built image still trusts the compromised eMudhra
# "emSign ECC Root CA - G3" root. Checks the system CA bundle
# (/etc/ssl/certs/ca-certificates.crt) and every other *.pem / *.crt file in
# the image, which covers Python's certifi (*/certifi/cacert.pem), grpcio's
# grpc/_cython/_credentials/roots.pem, pip's vendored certifi and Debian's
# per-cert /etc/ssl/certs/*.pem links. The cert is matched by its SHA-256
# fingerprint, so relabelled or reformatted copies are still caught.
#
# The Dockerfiles strip G3 by content and fail their own build if a copy
# survives; this check re-verifies the image that was actually produced.
# Same check as arthur-scope's scripts/check_no_emsign_g3.sh, except that it
# looks at every PEM file rather than only certifi, and does not skip pip's
# vendored certifi (the Dockerfiles filter that one too).
#
# Also flags any other file that embeds the root as DER (compiled-in root stores
# such as litellm's Rust extension or Go binaries), matched by the subject string.
#
# Usage: .github/scripts/check_no_emsign_g3.sh <image>
#   e.g. .github/scripts/check_no_emsign_g3.sh arthurplatform/genai-engine-cpu:2.1.1040
# Needs: docker, awk, GNU tar, openssl.
set -eu

IMAGE="$1"
G3_SHA256="86A1ECBA089C4A8D3BBE2734C612BA341D813E043CF9E8A862CD5C57A36BBE6B"

WORK=$(mktemp -d)
CID=$(docker create "$IMAGE")
trap 'docker rm "$CID" >/dev/null 2>&1 || true; rm -rf "$WORK"' EXIT

# Print the SHA-256 fingerprint (uppercase hex, no colons) of every cert in a PEM bundle.
fingerprints() {
  awk -v cmd="openssl x509 -noout -fingerprint -sha256" '
    /-----BEGIN CERTIFICATE-----/ { pem = "" }
    { pem = pem $0 "\n" }
    /-----END CERTIFICATE-----/ { printf "%s", pem | cmd; close(cmd) }
  ' "$1" | sed 's/.*=//; s/://g' | tr 'a-f' 'A-F'
}

# Unpack the whole image filesystem in one pass (plain sh has no pipefail, so a
# failed export is recorded in a marker file). Everything is needed: the PEM
# bundles, and every other file, because compiled TLS stacks (litellm's Rust
# extension, Go binaries) embed the root store as DER and no *.pem shows it.
# Symlinks come out as links; they are read back through `docker cp -L` below
# rather than followed here, where an absolute target would resolve on the host.
mkdir "$WORK/fs"
{ docker export "$CID" || touch "$WORK/export-failed"; } \
  | tar -xf - -C "$WORK/fs" --no-same-owner --no-same-permissions 2> "$WORK/tar.err" \
  || { cat "$WORK/tar.err" >&2; echo "ERROR: cannot read the filesystem of $IMAGE" >&2; exit 1; }
if [ -e "$WORK/export-failed" ]; then
  echo "ERROR: cannot export $IMAGE" >&2
  exit 1
fi
if [ ! -e "$WORK/fs/etc/ssl/certs/ca-certificates.crt" ] && [ ! -L "$WORK/fs/etc/ssl/certs/ca-certificates.crt" ]; then
  echo "skip: /etc/ssl/certs/ca-certificates.crt not found in $IMAGE"
fi

FOUND=0
CHECKED=0
check_bundle() { # <path in image> <local copy>
  count=$(grep -c 'BEGIN CERTIFICATE' "$2" || true)
  [ "$count" -gt 0 ] || return 0
  CHECKED=$((CHECKED + 1))
  if fingerprints "$2" | grep -qx "$G3_SHA256"; then
    printf 'FAIL: %s (%s certs) still trusts emSign ECC Root CA - G3\n' "$1" "$count"
    FOUND=1
  elif [ "$count" -gt 1 ]; then
    printf 'ok:   %s (%s certs)\n' "$1" "$count"
  fi
}

( cd "$WORK/fs" && find . -type f \( -name '*.pem' -o -name '*.crt' \) ) | sed 's|^\.||' > "$WORK/files.list"
while IFS= read -r p; do
  check_bundle "$p" "$WORK/fs$p"
done < "$WORK/files.list"

# A link that exists but can't be followed fails the check.
( cd "$WORK/fs" && find . -type l \( -name '*.pem' -o -name '*.crt' \) ) | sed 's|^\.||' > "$WORK/links.list"
while IFS= read -r p; do
  if ! docker cp -L "$CID:$p" - > "$WORK/link.tar" || ! tar -xOf "$WORK/link.tar" > "$WORK/link.pem"; then
    printf 'FAIL: %s exists in %s but could not be read\n' "$p" "$IMAGE"
    FOUND=1
    continue
  fi
  check_bundle "$p" "$WORK/link.pem"
done < "$WORK/links.list"

# Binaries that compile in a root store (litellm's rust_bridge, uv, Go's x509
# bundles) carry the certificate as DER. Match the DER encoding of its subject CN
# (OID 2.5.4.3, PrintableString, length 23, then the name) rather than the bare
# name, so source files and comments that merely mention the root do not match.
DER_CN='\x06\x03\x55\x04\x03\x13\x17emSign ECC Root CA - G3'
( cd "$WORK/fs" && find . -type f ! -name '*.pem' ! -name '*.crt' -size +1k \
    -exec grep -laP -- "$DER_CN" {} + ) | sed 's|^\.||' > "$WORK/embed.list" || true
while IFS= read -r p; do
  [ -n "$p" ] || continue
  printf 'FAIL: %s embeds emSign ECC Root CA - G3 (compiled-in root store)\n' "$p"
  FOUND=1
done < "$WORK/embed.list"

if [ "$FOUND" -ne 0 ]; then
  echo "ERROR: $IMAGE still trusts emSign ECC Root CA - G3 or has an unreadable bundle (SOC-222)"
  exit 1
fi
echo "$IMAGE does not trust emSign ECC Root CA - G3 ($CHECKED certificate files checked)"
