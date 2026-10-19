#!/usr/bin/env bash
# Print the Compute Engine OS policy assignment pinned to one arthur-engine ref, ready for
# `gcloud compute os-config os-policy-assignments create --file`.
#
#   tools/render-os-policy.sh [REF]      # REF defaults to the commit checked out
#
# Every file the policy names gets its URL at REF and the sha256 of the bytes REF holds, read
# out of git rather than off the working tree: the OS policy refuses a file whose checksum does
# not match, so an uncommitted edit would pin bytes that no URL serves. The policy itself is
# REF's copy too. REF must be pushed to GitHub for raw.githubusercontent.com to serve it.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
TREE="integrations/endpoint-ai-discovery"
POLICY="deploy/arthur-ai-discovery.os-policy.yaml"
PREFIX="https://raw.githubusercontent.com/arthur-ai/arthur-engine/COMMIT/$TREE/"

die() { echo "render-os-policy: $*" >&2; exit 1; }

ref="${1:-HEAD}"
commit="$(git -C "$ROOT" rev-parse --verify --quiet "$ref^{commit}")" \
  || die "$ref is not a commit in this clone; fetch it first (git fetch --tags)"
# A tag stays readable in the URL; anything else is pinned to its commit, because a branch
# moves and the checksums would stop matching what it serves.
if git -C "$ROOT" show-ref --verify --quiet "refs/tags/$ref"; then pin="$ref"; else pin="$commit"; fi

policy="$(git -C "$ROOT" cat-file blob "$commit:$TREE/$POLICY" 2>/dev/null)" \
  || die "$ref has no $TREE/$POLICY; render a ref that carries it"

# Held until the whole policy has rendered: a failure part-way would otherwise leave a shorter
# policy in the redirect target, which still parses and installs less than it should.
out=""
src=""
while IFS= read -r line; do
  case "$line" in
    *"uri: $PREFIX"*)
      # Rebuilt from its indent, not substituted: bash versions disagree on escapes in the
      # replacement half of ${var/pattern/string}.
      src="${line##*"$PREFIX"}"
      line="${line%%uri:*}uri: https://raw.githubusercontent.com/arthur-ai/arthur-engine/$pin/$TREE/$src"
      ;;
    *"uri: "*"/COMMIT/"*)
      die "a file URL is not under $PREFIX, so its checksum cannot be read from this tree: $line"
      ;;
    *"sha256Checksum: "*)
      [ -n "$src" ] || die "a sha256Checksum with no file URL before it: $line"
      git -C "$ROOT" cat-file -e "$commit:$TREE/$src" 2>/dev/null || die "$ref has no $TREE/$src"
      sum="$(git -C "$ROOT" cat-file blob "$commit:$TREE/$src" | shasum -a 256 | cut -d' ' -f1)"
      line="${line%%sha256Checksum:*}sha256Checksum: $sum"
      src=""
      ;;
  esac
  out="$out$line"$'\n'
done <<<"$policy"
[ -z "$src" ] || die "the file URL for $src has no sha256Checksum after it"
printf '%s' "$out"
